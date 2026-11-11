#!/usr/bin/env node
/*
 * Walk-forward backtest of the swing rules, using the SAME analysis code the skill runs (egx_chart.js).
 *
 *   node tests/backtest.js ~/Downloads/egx-bars-2026-11-11.json     real bars saved by EGX.downloadBars([...]) in ThndrX
 *   node tests/backtest.js --selftest                               random-walk series: proves the harness runs, says nothing about EGX
 *   options: --order 5000 (EGP per trade, for fees)  --slip 0.5 (ATR lost when a stop fills)  --out backtest.json
 *
 * No look-ahead: on day i the analysis sees only bars 0..i and the EGX30 bars up to that date. A signal on day i is
 * traded from day i+1. One position per ticker at a time.
 *
 * Entry rules = egx_gates.swing_verdict without the parts history cannot give (news, red events, price band):
 *   no script drop · setup pullback-at-support or breakout-retest · daily trend not down · RS20 known and >= 0 ·
 *   Down regime needs RS20 and RS60 > 0 · breakout-retest within 1 ATR of its entry · R:R after fees >= 2.
 * Fills: pullback-at-support buys the next open unless it is above maxEntry; breakout-retest is a limit at the entry for 5 sessions.
 * Exits = egx_manage.py: stop (fills `slip` ATR worse, or at the open on a gap) · half off at +1R, stop to breakeven ·
 *   rest at the plan target · after the partial the stop trails the highest close - 2.5 ATR, never down ·
 *   time stop after 10 sessions under +0.5R (sold at the next open). The swing-low trail of egx_manage.py is not modelled.
 *
 * What this cannot tell you: 300 bars is about 14 months and one market phase; prices may be unadjusted for dividends and
 * bonus shares; stocks that were delisted are missing; fills ignore the order book. Treat the result as evidence, not proof.
 */
const fs = require('fs'), path = require('path');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const SELF = args.includes('--selftest');
const ORDER = +opt('order', 5000), SLIP = +opt('slip', 0.5), OUT = opt('out', 'backtest.json');
const file = args.find((a, i) => !a.startsWith('--') && !(args[i - 1] || '').match(/^--(order|slip|out)$/));
const PASS = { trades: 100, expectancy: 0.2 };

let DATA = [];
global.window = {}; global.sessionStorage = { getItem() { return null; }, setItem() {} };
global.document = { body: { innerText: '' }, querySelectorAll: (q) => q === 'iframe' ? [{ contentWindow: { tradingViewApi: { activeChart: () => ({ exportData: async () => ({ schema: [{}, { sourceTitle: 'BT, EGX' }, {}, {}, {}, { plotId: 'vol' }], data: DATA }), symbol: () => 'X', resolution: () => '1D' }) } } }] : [] };
eval(fs.readFileSync(path.join(__dirname, '../skills/egx-check/scripts/egx_chart.js'), 'utf8'));
const EGX = window.EGX;

// Thndr fees per side, as in egx.py DEFAULT_CONFIG
const feeSide = (v) => 2 + Math.min(Math.max(v * 0.003 / 100, 1), 250) + v * 0.175 / 100;

function synthetic() {
  let seed = 7; const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-9)) * Math.cos(2 * Math.PI * rnd());
  const mk = (p0, vol) => { const out = []; let p = p0, t = 1700000000 - (1700000000 % 86400); for (let i = 0; i < 700; i++) { const o = p * (1 + gauss() * vol * 0.3); p = o * (1 + gauss() * vol); const h = Math.max(o, p) * (1 + Math.abs(gauss()) * vol * 0.5), l = Math.min(o, p) * (1 - Math.abs(gauss()) * vol * 0.5); out.push([t, o, h, l, p, 2e6 + rnd() * 2e6]); t += 86400; } return out; };
  const bars = { EGX30: mk(30000, 0.01) };
  for (let k = 0; k < 20; k++) bars['RW' + String(k).padStart(2, '0')] = mk(5 + rnd() * 60, 0.022);
  return { made: 'synthetic random walk (no drift)', bars };
}

function accept(R, idx, shares) {
  const p = R.plan, why = [];
  if (R.drop || !p || !p.target) return null;
  if (!['pullback-at-support', 'breakout-retest'].includes(p.type)) return null;
  if (R.trend.daily === 'down') return null;
  if (R.rs.rs20 == null || R.rs.rs20 < 0) return null;
  if (idx.regime === 'Down' && !(R.rs.rs20 > 0 && R.rs.rs60 > 0)) return null;
  if (p.type === 'breakout-retest' && p.entryDistATR > 1) return null;
  const q = Math.max(1, Math.floor(ORDER / p.entry)), fb = feeSide(p.entry * q);
  const net = ((p.target - p.entry) * q - fb - feeSide(p.target * q)) / ((p.entry - p.stop) * q + fb + feeSide(p.stop * q));
  return net >= 2 ? p : null;
}

function simulate(rows, i, p, atr) {
  // returns null (no fill) or { entryI, exitI, r, how }
  let e = null, ei = null;
  if (p.type === 'pullback-at-support') { const o = rows[i + 1][1]; if (o > p.maxEntry || o <= p.stop) return null; e = o; ei = i + 1; }
  else for (let j = i + 1; j <= Math.min(i + 5, rows.length - 1); j++) if (rows[j][3] <= p.entry) { e = Math.min(rows[j][1], p.entry); ei = j; if (e <= p.stop) return null; break; }
  if (e == null) return null;
  const R1 = e - p.stop; let stop = p.stop, partial = false, hiClose = e, left = 1, pnl = 0, how = 'open at end of data', xi = rows.length - 1;
  const q = Math.max(1, Math.floor(ORDER / e)); let fees = feeSide(e * q);
  const sell = (price, frac) => { pnl += (price - e) * frac; fees += feeSide(price * q * frac); left -= frac; };
  for (let j = ei; j < rows.length; j++) {
    const [, o, h, l, c] = rows[j];
    if (l <= stop) { const fill = (j > ei && o < stop ? o : stop) - SLIP * atr; /* every stop fill pays the slippage, breakeven stops too */ sell(fill, left); how = partial ? 'partial then stop' : 'stop'; xi = j; break; }
    if (!partial && h >= e + R1) { sell(e + R1, 0.5); partial = true; stop = Math.max(stop, e); }
    if (h >= p.target) { sell(p.target, left); how = 'target'; xi = j; break; }
    hiClose = Math.max(hiClose, c);
    if (partial) stop = Math.max(stop, Math.min(hiClose - 2.5 * atr, c - 0.01));
    if (!partial && j - ei + 1 >= 10 && c < e + 0.5 * R1 && j + 1 < rows.length) { sell(rows[j + 1][1], left); how = 'time stop'; xi = j + 1; break; }
  }
  if (left > 0) sell(rows[rows.length - 1][4], left);
  return { entryI: ei, exitI: xi, r: (pnl - fees / q) / R1, how };
}

(async () => {
  if (!SELF && !file) { console.log('usage: node tests/backtest.js <egx-bars.json> | --selftest'); process.exit(2); }
  const src = SELF ? synthetic() : JSON.parse(fs.readFileSync(file.replace(/^~/, process.env.HOME), 'utf8'));
  const IDX = src.bars.EGX30;
  if (!IDX || IDX.length < 215) { console.log('EGX30 bars missing or under 215: the regime and relative strength cannot be computed'); process.exit(2); }
  const trades = []; let signals = 0, nofill = 0;
  for (const [tk, rows] of Object.entries(src.bars)) {
    if (tk === 'EGX30' || rows.length < 80) continue;
    let busyUntil = -1;
    for (let i = 60; i < rows.length - 2; i++) {
      if (i <= busyUntil) continue;
      const idxRows = IDX.filter((r) => r[0] <= rows[i][0]);
      if (idxRows.length < 210 || idxRows[idxRows.length - 1][0] !== rows[i][0]) continue;
      const idx = EGX._setIndexBars(idxRows); if (!idx) continue;
      DATA = rows.slice(0, i + 1);
      let R; try { R = await EGX.analyze(tk); } catch (e) { continue; }
      const p = accept(R, idx); if (!p) continue;
      signals++;
      const t = simulate(rows, i, p, R.atr); if (!t) { nofill++; continue; }
      busyUntil = t.exitI;
      trades.push({ tk, signal: new Date(rows[i][0] * 1000).toISOString().slice(0, 10), exit: new Date(rows[t.exitI][0] * 1000).toISOString().slice(0, 10), exitT: rows[t.exitI][0], setup: p.type, regime: idx.regime, days: t.exitI - t.entryI + 1, how: t.how, r: +t.r.toFixed(3) });
    }
  }
  const stats = (T) => {
    if (!T.length) return { trades: 0 };
    const rs = T.map((x) => x.r), sum = rs.reduce((a, b) => a + b, 0), wins = rs.filter((x) => x > 0), loss = rs.filter((x) => x <= 0);
    let eq = 0, peak = 0, dd = 0; [...T].sort((a, b) => a.exitT - b.exitT).forEach((x) => { eq += x.r; peak = Math.max(peak, eq); dd = Math.max(dd, peak - eq); });
    const mean = sum / rs.length, sd = Math.sqrt(rs.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(1, rs.length - 1));
    return { trades: T.length, winPct: +(100 * wins.length / T.length).toFixed(1), expectancyR: +mean.toFixed(3), ci95: +(1.96 * sd / Math.sqrt(rs.length)).toFixed(3), totalR: +sum.toFixed(1),
      profitFactor: loss.length && wins.length ? +(wins.reduce((a, b) => a + b, 0) / -loss.reduce((a, b) => a + b, 0)).toFixed(2) : null, maxDrawdownR: +dd.toFixed(1), avgDays: +(T.reduce((a, b) => a + b.days, 0) / T.length).toFixed(1) };
  };
  const by = (k) => Object.fromEntries([...new Set(trades.map((t) => t[k]))].sort().map((v) => [v, stats(trades.filter((t) => t[k] === v))]));
  const all = stats(trades), res = { made: new Date().toISOString(), source: SELF ? 'SYNTHETIC random walk' : path.basename(file), dataMade: src.made, tickers: Object.keys(src.bars).length - 1, order: ORDER, slipATR: SLIP, signals, notFilled: nofill, all, bySetup: by('setup'), byRegime: by('regime'), byExit: by('how'), trades };
  const row = (name, s) => s.trades ? `${name.padEnd(22)} ${String(s.trades).padStart(5)}  win ${String(s.winPct).padStart(5)}%  exp ${String(s.expectancyR).padStart(7)}R ±${s.ci95}  PF ${s.profitFactor ?? '-'}  maxDD ${s.maxDrawdownR}R  ${s.avgDays}d` : `${name.padEnd(22)}     0`;
  console.log(`${res.source} · ${res.tickers} tickers · ${signals} signals, ${nofill} not filled · order ${ORDER} EGP · stop slippage ${SLIP} ATR`);
  console.log(row('ALL', all));
  for (const [title, g] of [['setup', res.bySetup], ['regime', res.byRegime], ['exit', res.byExit]]) for (const [k, s] of Object.entries(g)) console.log(row(title + ': ' + k, s));
  const neg = Object.entries(res.bySetup).filter(([, s]) => s.trades >= 20 && s.expectancyR <= 0).map(([k]) => k);
  const pass = all.trades >= PASS.trades && all.expectancyR - all.ci95 > 0 && all.expectancyR >= PASS.expectancy && !neg.length;
  res.pass = !SELF && pass;
  console.log(SELF ? 'SELFTEST: the harness runs. Random-walk numbers say nothing about EGX; a fair harness should show about zero or negative expectancy here.'
    : pass ? `PASS LINE MET: ${all.trades} trades, expectancy ${all.expectancyR}R (95% interval above zero), no losing setup.`
      : `PASS LINE NOT MET (needs >= ${PASS.trades} trades, expectancy >= ${PASS.expectancy}R with its 95% interval above zero, no losing setup${neg.length ? '; losing: ' + neg.join(', ') : ''}). Do not size up on these rules.`);
  if (!SELF) { fs.writeFileSync(OUT, JSON.stringify(res, null, 1)); console.log('written: ' + OUT); }
})();
