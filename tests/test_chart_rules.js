// Rule tests for egx_chart.js 3.2 (node tests/test_chart_rules.js). Same mock chart as test_chart.js.
const fs = require('fs'), path = require('path');
let DATA = [];
global.window = {}; global.sessionStorage = { getItem() { return null; }, setItem() {} };
global.document = { body: { innerText: '' }, querySelectorAll: (q) => q === 'iframe' ? [{ contentWindow: { tradingViewApi: { activeChart: () => ({ exportData: async () => ({ schema: [{}, { sourceTitle: 'TEST, EGX' }, {}, {}, {}, { plotId: 'vol' }], data: DATA }), symbol: () => 'X', resolution: () => '1D' }) } } }] : [] };
eval(fs.readFileSync(path.join(__dirname, '../skills/egx-check/scripts/egx_chart.js'), 'utf8'));
const EGX = window.EGX;
let bad = 0; const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) bad++; };
function series(kind, n = 300, lastT = 1767225600 + 299 * 86400) {
  const out = []; let p = 20, t = lastT - (n - 1) * 86400;
  for (let i = 0; i < n; i++) { const drift = kind === 'up' ? 0.004 : kind === 'down' ? -0.004 : kind === 'ath' ? 0.006 : 0; const w = Math.sin(i / 9) * 0.02; p = p * (1 + drift + w * 0.3 + Math.sin(i * 1.7) * 0.004); const o = p * (1 + Math.sin(i) * 0.003), c = p, h = Math.max(o, c) * 1.01, l = Math.min(o, c) * 0.99; out.push([t, o, h, l, c, 500000 + ((i * 7919) % 300000)]); t += 86400; }
  return out;
}
(async () => {
  let sample = null;
  for (const k of ['up', 'down', 'side', 'ath']) {
    DATA = series(k); const R = await EGX.analyze('T' + k);
    const br = R.zones.brokenSupportNowResistance || [];
    ok(br.every((z) => z.touches.some((t) => t.endsWith('L'))), k + ': every "broken support" zone holds a swing low (' + br.length + ' zones)');
    ok((R.zones.resistance || []).every((z) => !z.wasSupport || z.touches.some((t) => t.endsWith('L'))), k + ': resistance made only of highs is never called broken support');
    const boxes = R.draw.marks.filter((m) => m.shape === 'box').map((m) => m.lo + '-' + m.hi);
    ok(new Set(boxes).size === boxes.length, k + ': no zone is drawn twice (' + boxes.length + ' boxes)');
    if (R.plan) ok(R.plan.maxEntry > R.plan.entry, k + ': plan has a max entry above the entry (' + R.plan.entry + ' -> ' + R.plan.maxEntry + ')');
    ok(R.history === undefined, k + ': no biased setup history');
    if (R.plan && !sample) sample = R;
  }
  // unfinished daily bar: market open and the last bar is today's
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Cairo' }).format(new Date());
  DATA = series('side', 300, Date.parse(today + 'T00:00:00Z') / 1000);
  document.body.innerText = 'السوق مغلق'; const closed = await EGX.analyze('TP');
  ok(closed.bars === 300 && !closed.partialBarDropped, 'market closed: all 300 bars are used');
  document.body.innerText = 'السوق مفتوح'; const open = await EGX.analyze('TP');
  ok(open.bars === 299 && open.partialBarDropped === today && open.livePrice != null, "market open: today's unfinished bar is dropped, live price kept apart");
  ok(open.asOf !== today, 'market open: levels are as of the last finished bar (' + open.asOf + ')');
  // checksum: printed for the Python side (tests/test_egx.py compares it with egx_gates.sig_of)
  const ex = JSON.parse(EGX.exportRun([sample.tk])).stocks.find((s) => s.tk === sample.tk);
  ok(/^[0-9a-f]{16}$/.test(ex.sig), 'export carries a checksum per stock');
  console.log('SIG ' + JSON.stringify({ tk: ex.tk, last: ex.last, plan: ex.plan, drop: ex.drop, score: ex.score, receipts: ex.receipts, sig: ex.sig }));
  process.exit(bad ? 1 : 0);
})();
