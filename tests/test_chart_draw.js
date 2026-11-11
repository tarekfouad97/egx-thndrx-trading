// Node harness for v3 drawing, verify and intraday with a mocked TradingView chart.
const fs = require('fs'), path = require('path');
let RES = '1D', DAILY = [], M5 = [], nextId = 1;
const shapes = new Map(), studies = [];
const ch = {
  exportData: async () => ({ schema: [{}, { sourceTitle: 'TEST, EGX' }, {}, {}, {}, { plotId: 'vol' }], data: RES === '5' ? M5 : DAILY }),
  symbol: () => 'uuid-test', resolution: () => RES,
  setResolution: (r, cb) => { RES = r; cb && cb(); },
  setVisibleRange: () => {},
  createShape: async (pt, o) => { const id = 's' + nextId++; shapes.set(id, { pts: [pt], props: { text: o.text, ...o.overrides }, shape: o.shape }); return id; },
  createMultipointShape: async (pts, o) => { const id = 's' + nextId++; shapes.set(id, { pts, props: { text: o.text, ...o.overrides }, shape: o.shape }); return id; },
  getAllShapes: () => [...shapes.keys()].map((id) => ({ id, name: shapes.get(id).shape })),
  getShapeById: (id) => ({ getPoints: () => shapes.get(id).pts, getProperties: () => shapes.get(id).props }),
  removeEntity: (id) => shapes.delete(id),
  getAllStudies: () => studies.map((s) => ({ id: s.id, name: 'Moving Average' })),
  getStudyById: (id) => ({ getInputValues: () => [{ id: 'length', value: studies.find((s) => s.id === id).len }] }),
  createStudy: async (name, a, b, inp) => { const id = 'st' + nextId++; studies.push({ id, len: inp.length }); return id; },
};
global.window = {}; global.sessionStorage = { getItem() { return null; }, setItem() {} };
global.innerWidth = 1440; global.innerHeight = 900;
global.document = { querySelectorAll: (q) => (q === 'iframe' ? [{ contentWindow: { tradingViewApi: { activeChart: () => ch } }, getBoundingClientRect: () => ({ left: 300, top: 80, right: 1100, bottom: 700 }) }] : []),
  body: { innerText: '', appendChild() {} }, getElementById: () => null, createElement: () => ({ style: {} }) };
global.getComputedStyle = () => ({ color: '' });
eval(fs.readFileSync(path.join(__dirname, '../skills/egx-check/scripts/egx_chart.js'), 'utf8'));
const E = window.EGX;
let fails = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) fails++; };

function daily(n = 300) { const out = []; let p = 20, t = Date.UTC(2025, 9, 1) / 1000; for (let i = 0; i < n; i++) { p = p * (1 + 0.003 + Math.sin(i / 9) * 0.006 + Math.sin(i * 1.7) * 0.0012); const o = p * (1 + Math.sin(i) * 0.003), h = Math.max(o, p) * 1.01, l = Math.min(o, p) * 0.99; out.push([t, o, h, l, p, 600000 + ((i * 7919) % 300000)]); t += 86400; } return out; }
function fivemin() { // 3 prior sessions + today; Cairo = UTC+2 in Nov, session 10:00 -> 08:00 UTC
  const out = []; let p = 50;
  for (let d = 0; d < 4; d++) { const base = Date.UTC(2026, 10, 1 + d, 8, 0) / 1000; const nb = d === 3 ? 30 : 54;
    for (let i = 0; i < nb; i++) { const today = d === 3; const drift = today ? (i < 6 ? 0 : i < 12 ? 0.004 : 0.0008) : Math.sin(i / 5) * 0.002; p = p * (1 + drift); const o = p * 0.999, h = p * 1.003, l = p * 0.997; out.push([base + i * 300, o, h, l, p, today && i >= 6 && i < 12 ? 90000 : 30000]); } }
  return out;
}
(async () => {
  DAILY = daily(); M5 = fivemin();
  await E.market().catch(() => {}); // EGX30 open fails in the mock: fine
  const R = await E.analyze('TEST');
  ok(R.receipts && R.receipts.analyse && R.receipts.analyse.bars === 300, 'analyse receipt');
  ok(R.draw && R.draw.marks.length > 0, 'draw spec has marks: ' + (R.draw && R.draw.marks.map((m) => m.kind).join(',')));
  const d = await E.draw('TEST', { events: [{ date: '2026-08-20', kind: 'event', label: 'results' }, { date: '2026-07-01', kind: 'catalyst', label: 'deal' }] });
  ok(d.ok, `draw ok: made ${d.made}/${d.planned}, studies ${JSON.stringify(d.studies)}`);
  ok(studies.length === 2, 'MA50 + MA200 added');
  await E.draw('TEST'); ok(studies.length === 2, 'MAs not duplicated on redraw');
  ok([...shapes.values()].filter((s) => String(s.props.text).startsWith('EGX·')).length === E.get('TEST').draw.marks.length, 'redraw cleared old marks');
  let v = await E.verifyChart('TEST'); ok(v.ok, 'verify ok: ' + JSON.stringify(v.problems));
  // tamper: move the stop line, verify must fail
  const stopId = [...shapes.entries()].find(([, s]) => String(s.props.text).includes('وقف'))[0];
  shapes.get(stopId).pts = [{ time: 0, price: 1 }];
  v = await E.verifyChart('TEST'); ok(!v.ok && v.problems.some((p) => p.startsWith('stop')), 'verify catches a moved stop: ' + v.problems.join('; '));
  shapes.delete(stopId);
  v = await E.verifyChart('TEST'); ok(!v.ok && v.problems.includes('stop missing'), 'verify catches a deleted stop');
  RES = '5'; v = await E.verifyChart('TEST'); ok(!v.ok && v.problems.some((p) => p.startsWith('resolution')), 'verify catches wrong resolution'); RES = '1D';
  // T0
  const T = await E.intraday('TEST', { alreadyOpen: true });
  ok(T && T.session && T.session.bars === 30, 'intraday: today = 30 bars, ' + (T.session && T.session.from + '-' + T.session.to));
  ok(T.vwap && T.openingRange && T.openingRange.from === '10:00', 'intraday: VWAP + opening range from 10:00');
  console.log('   T0', JSON.stringify({ plan: T.plan, drop: T.drop, relVol: T.relVol }));
  if (T.plan) {
    const dt0 = await E.drawT0('TEST'); ok(dt0.ok, 'drawT0 ok ' + dt0.made + '/' + dt0.planned);
    const v0 = await E.verifyChart('TEST', { t0: true }); ok(v0.ok, 'T0 verify ok ' + JSON.stringify(v0.problems));
  }
  const back = await E.daily(); ok(back.ok && RES === '1D', 'back to 1D');
  ok(E.receipts('TEST').daily.draw && E.receipts('TEST').daily.verify, 'receipts exported');
  // call log (proof for the step ledger)
  E.chartRect(4); E.exportToPage(['TEST']);
  const ex = JSON.parse(E.exportRun(['TEST']));
  const fns = ex.calls.map((c) => c[0]);
  ok(ex.egxjs === E.version && ['draw', 'verifyChart', 'intraday', 'daily', 'chartRect', 'exportToPage'].every((f) => fns.includes(f)), 'call log exported: ' + [...new Set(fns)].join(','));
  const vAt = E.receipts('TEST').t0 ? E.receipts('TEST').t0.verify.at : 0, cr = ex.calls.filter((c) => c[0] === 'chartRect').pop();
  ok(cr[2] >= vAt && ex.calls.every((c) => c.length === 4 && typeof c[2] === 'number'), 'call log rows are [fn, ticker, time, ok], chartRect after the verify');
  ok(ex.calls.find((c) => c[0] === 'verifyChart' && c[3] === 0), 'a failed verify is logged as not ok');
  E.clearExport();
  process.exit(fails ? 1 : 0);
})();
