/*
 * egx_chart.js — in-page helper for ThndrX (x.thndr.app), injected with the
 * Claude in Chrome javascript tool. Reads only what the page already has:
 * the TradingView chart's own exportData(), the watchlist search box and the
 * visible panels. It never calls Thndr servers and never touches the order
 * ticket (no buy / sell / confirm).
 *
 * Inject once per tab (paste the whole file), then call, for example:
 *   await EGX.market()                       // EGX30 regime + market page numbers
 *   await EGX.scan('COMI')                   // open + analyse, one-line summary
 *   await EGX.deep('COMI')                   // gates 1-2: open + full analysis + panels (no drawing)
 *   await EGX.draw('COMI', {events:[...]})   // gate 4: boxes, lines, event lines, MA50/MA200
 *   await EGX.verifyChart('COMI')            // gate 5: reads every EGX· mark back -> receipt
 *   await EGX.intraday('COMI')               // T0: 5-minute analysis (chart stays on 5 min)
 *   await EGX.drawT0('COMI'); await EGX.verifyChart('COMI', {t0:true}); await EGX.daily()
 *   EGX.page()                               // cash, market status, order book, price band
 *   EGX.holdings()                           // current investments grid
 *   await EGX.financials()                   // البيانات المالية tab values
 *   EGX.get('COMI') / EGX.exportRun([...])   // stored results as JSON
 *
 * Every number is rounded; every level carries the bar dates it came from.
 * Rules are documented in references/analysis-rules.md (keep both in sync).
 */
(function () {
  const VERSION = '3.0.0';
  if (window.EGX && window.EGX.version === VERSION) return;
  const MARK = 'EGX·'; // prefix on every drawing label, so we only ever clear our own lines
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clean = (s) => String(s || '').replace(/[‎‏؜]/g, '').trim();
  const num = (s) => {
    s = clean(s).replace(/,/g, '').replace('%', '').trim();
    if (!s || s === '--' || s === '-') return null;
    let m = 1;
    if (/ألف/.test(s)) { m = 1e3; s = s.replace('ألف', ''); }
    if (/مليون/.test(s)) { m = 1e6; s = s.replace('مليون', ''); }
    if (/مليار/.test(s)) { m = 1e9; s = s.replace('مليار', ''); }
    const v = parseFloat(s.replace(/[^\d.\-]/g, ''));
    return isNaN(v) ? null : v * m;
  };
  const r2 = (x, d = 2) => (x == null || !isFinite(x) ? null : Math.round(x * 10 ** d) / 10 ** d);
  const tick = (p) => (p == null ? null : p < 1 ? Math.round(p * 1000) / 1000 : Math.round(p * 100) / 100);
  const dt = (t) => new Date(t * 1000).toISOString().slice(0, 10);
  const store = (k, v) => { try { sessionStorage.setItem('EGX_' + k, JSON.stringify(v)); } catch (e) {} };
  const load = (k) => { try { return JSON.parse(sessionStorage.getItem('EGX_' + k)); } catch (e) { return null; } };

  const S = { results: load('results') || {}, index: load('index') || null, market: load('market') || null, shapes: load('shapes') || {} };
  const now = () => ({ at: Date.now(), iso: new Date().toISOString() });
  const toT = (s) => Date.parse(s + 'T00:00:00Z') / 1000;
  const cairo = (t) => { const p = new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date(t * 1000)); const g = (k) => (p.find((x) => x.type === k) || {}).value; return { d: `${g('year')}-${g('month')}-${g('day')}`, hm: `${g('hour') === '24' ? '00' : g('hour')}:${g('minute')}` }; };
  const sameRes = (a, b) => String(a).replace(/^1(?=[DWM])/, '') === String(b).replace(/^1(?=[DWM])/, '');

  // ---------- chart access ----------
  function api() {
    const f = [...document.querySelectorAll('iframe')].find((x) => { try { return x.contentWindow.tradingViewApi; } catch (e) { return false; } });
    if (!f) throw new Error('chart not found: open https://x.thndr.app/workspaces/default/trade');
    return f.contentWindow.tradingViewApi;
  }
  const chart = () => api().activeChart();
  async function bars() {
    const d = await chart().exportData({ includeTime: true, includeSeries: true });
    const vi = d.schema.findIndex((s) => s.plotId === 'vol');
    const title = clean(d.schema[1] && d.schema[1].sourceTitle).replace(/,\s*EGX$/, '');
    const B = d.data.map((r) => ({ t: r[0], o: r[1], h: r[2], l: r[3], c: r[4], v: vi > 0 ? r[vi] || 0 : 0 }));
    return { title, B, hasVol: vi > 0 };
  }

  // ---------- open a ticker through the watchlist search ----------
  async function open(tk, timeoutMs = 9000) {
    tk = String(tk).toUpperCase().trim();
    let inp = document.querySelector('input[placeholder="ابحث عن سهم"]');
    if (!inp || !inp.offsetParent) {
      const b = [...document.querySelectorAll('button')].find((b) => b.querySelector('[aria-label="search"]'));
      if (b) { b.click(); await sleep(400); }
      inp = document.querySelector('input[placeholder="ابحث عن سهم"]');
    }
    if (!inp) return { ok: false, tk, error: 'search box not found' };
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    inp.focus(); set.call(inp, tk); inp.dispatchEvent(new Event('input', { bubbles: true }));
    let panel = inp, btn = null;
    const t0 = Date.now();
    while (Date.now() - t0 < 4000 && !btn) {
      await sleep(250);
      panel = inp;
      for (let i = 0; i < 8 && panel; i++) { panel = panel.parentElement; if (panel && panel.querySelectorAll('button').length > 1 && panel.innerText.includes(tk)) break; }
      if (!panel) break;
      const leaf = [...panel.querySelectorAll('*')].find((e) => e.children.length === 0 && clean(e.textContent) === tk && e.closest('button'));
      btn = leaf && leaf.closest('button');
    }
    if (!btn) return { ok: false, tk, error: 'ticker not in search results' };
    let before = null; try { before = chart().symbol(); } catch (e) {}
    btn.click();
    while (Date.now() - t0 < timeoutMs) {
      await sleep(300);
      try {
        if (chart().symbol() !== before) {
          await sleep(500);
          const d = await bars();
          if (d.B.length) {
            const head = [...document.querySelectorAll('button.disable-widget-grab-handle')].map((b) => clean(b.innerText));
            let res = null; try { res = chart().resolution(); } catch (e) {}
            const rc = { ...now(), tk, title: d.title, headerMatch: head.includes(tk), symbol: chart().symbol(), resolution: res, bars: d.B.length, lastBar: dt(d.B[d.B.length - 1].t) };
            S.lastOpen = rc;
            return { ok: true, tk, title: d.title, bars: d.B.length, headerMatch: rc.headerMatch, receipt: rc };
          }
        }
      } catch (e) {}
    }
    return { ok: false, tk, error: 'chart did not switch (already open? call EGX.analyze directly)' };
  }

  // ---------- indicators ----------
  const smaArr = (A, k) => A.map((_, i) => (i + 1 < k ? null : A.slice(i + 1 - k, i + 1).reduce((a, b) => a + b, 0) / k));
  const emaArr = (A, k) => { const out = []; const a = 2 / (k + 1); let e = null; A.forEach((x, i) => { e = e == null ? x : x * a + e * (1 - a); out.push(i + 1 < k ? null : e); }); return out; };
  function rsiArr(C, k = 14) {
    const out = new Array(C.length).fill(null); if (C.length <= k) return out;
    let ag = 0, al = 0;
    for (let i = 1; i <= k; i++) { const x = C[i] - C[i - 1]; ag += Math.max(x, 0); al += Math.max(-x, 0); }
    ag /= k; al /= k; out[k] = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
    for (let i = k + 1; i < C.length; i++) { const x = C[i] - C[i - 1]; ag = (ag * (k - 1) + Math.max(x, 0)) / k; al = (al * (k - 1) + Math.max(-x, 0)) / k; out[i] = al === 0 ? 100 : 100 - 100 / (1 + ag / al); }
    return out;
  }
  function atrArr(B, k = 14) {
    const out = new Array(B.length).fill(null); if (B.length <= k) return out;
    const tr = (i) => Math.max(B[i].h - B[i].l, Math.abs(B[i].h - B[i - 1].c), Math.abs(B[i].l - B[i - 1].c));
    let a = 0; for (let i = 1; i <= k; i++) a += tr(i); a /= k; out[k] = a;
    for (let i = k + 1; i < B.length; i++) { a = (a * (k - 1) + tr(i)) / k; out[i] = a; }
    return out;
  }
  function pivots(B, from, k = 3) {
    const PH = [], PL = [];
    for (let i = Math.max(k, from); i < B.length - k; i++) {
      let hi = true, lo = true;
      for (let j = 1; j <= k; j++) {
        if (B[i].h < B[i - j].h || B[i].h < B[i + j].h) hi = false;
        if (B[i].l > B[i - j].l || B[i].l > B[i + j].l) lo = false;
      }
      if (hi) PH.push({ i, d: dt(B[i].t), p: B[i].h });
      if (lo) PL.push({ i, d: dt(B[i].t), p: B[i].l });
    }
    return { PH, PL };
  }
  function weekly(B) {
    const W = []; let key = null;
    for (const b of B) {
      const d = new Date(b.t * 1000); const day = (d.getUTCDay() + 1) % 7; // EGX week starts Sunday
      const start = new Date(d.getTime() - day * 864e5).toISOString().slice(0, 10);
      if (start !== key) { W.push({ ...b }); key = start; } else { const w = W[W.length - 1]; w.h = Math.max(w.h, b.h); w.l = Math.min(w.l, b.l); w.c = b.c; w.v += b.v; w.t = b.t; }
    }
    return W;
  }

  // ---------- full analysis on the chart that is open ----------
  async function analyze(tk, opts = {}) {
    const { title, B } = await bars();
    const n = B.length;
    const R = { tk, title, v: VERSION, asOf: n ? dt(B[n - 1].t) : null, bars: n, flags: [], evidence: [], receipts: (S.results[tk] && S.results[tk].receipts && opts.keepReceipts) ? S.results[tk].receipts : {} };
    if (S.lastOpen && S.lastOpen.tk === tk) R.receipts.open = S.lastOpen;
    let resNow = null; try { resNow = chart().resolution(); } catch (e) {}
    if (resNow != null && !sameRes(resNow, '1D')) throw new Error('chart is on ' + resNow + ', not 1D: call EGX.daily() first');
    R.receipts.analyse = { ...now(), version: VERSION, bars: n, lastBar: n ? dt(B[n - 1].t) : null, titleMatch: !title || title.toUpperCase().includes(tk) || (S.lastOpen && S.lastOpen.headerMatch) };
    if (n < 60) { R.drop = 'new'; R.flags.push('fewer than 60 daily bars'); return save(tk, R); }
    const C = B.map((b) => b.c), V = B.map((b) => b.v);
    const last = C[n - 1], prev = C[n - 2];
    const ATR = atrArr(B), atr = ATR[n - 1];
    const RSI = rsiArr(C), rsi = RSI[n - 1];
    const ma20 = smaArr(C, 20), ma50 = smaArr(C, 50), ma200 = smaArr(C, 200);
    const e12 = emaArr(C, 12), e26 = emaArr(C, 26);
    const macd = C.map((_, i) => (e12[i] != null && e26[i] != null ? e12[i] - e26[i] : null));
    const sig = emaArr(macd.map((x) => (x == null ? 0 : x)), 9);
    const hist = macd.map((x, i) => (x == null || i < 35 ? null : x - sig[i]));
    R.spark = C.slice(-30).map((x) => tick(x));
    R.last = tick(last); R.chg = r2((last / prev - 1) * 100); R.date = dt(B[n - 1].t);
    R.atr = r2(atr, 3); R.atrPct = r2((atr / last) * 100);
    // A. trend
    const { PH, PL } = pivots(B, n - 130);
    R.pivots = { highs: PH.slice(-2).map((p) => [p.d, tick(p.p)]), lows: PL.slice(-2).map((p) => [p.d, tick(p.p)]) };
    let trend = 'side';
    if (PH.length >= 2 && PL.length >= 2) {
      const h = PH.slice(-2), l = PL.slice(-2);
      if (h[1].p > h[0].p && l[1].p > l[0].p) trend = 'up'; else if (h[1].p < h[0].p && l[1].p < l[0].p) trend = 'down';
    }
    const W = weekly(B), WC = W.map((w) => w.c), w10 = smaArr(WC, 10), w30 = smaArr(WC, 30), wn = W.length;
    let wtrend = 'unknown';
    if (wn >= 34 && w30[wn - 1] != null && w30[wn - 5] != null) {
      const up = WC[wn - 1] > w10[wn - 1] && w10[wn - 1] > w30[wn - 1] && w30[wn - 1] > w30[wn - 5];
      const dn = WC[wn - 1] < w10[wn - 1] && w10[wn - 1] < w30[wn - 1] && w30[wn - 1] < w30[wn - 5];
      wtrend = up ? 'up' : dn ? 'down' : 'side';
    }
    R.trend = { daily: trend, weekly: wtrend, ma20: tick(ma20[n - 1]), ma50: tick(ma50[n - 1]), ma200: tick(ma200[n - 1]),
      ma50Slope: ma50[n - 21] ? r2((ma50[n - 1] / ma50[n - 21] - 1) * 100) : null,
      stack: ma200[n - 1] != null ? (ma20[n - 1] > ma50[n - 1] && ma50[n - 1] > ma200[n - 1] ? 'bull' : ma20[n - 1] < ma50[n - 1] && ma50[n - 1] < ma200[n - 1] ? 'bear' : 'mixed') : 'unknown',
      stretchMA20: r2((last - ma20[n - 1]) / atr), stretchMA50: r2((last - ma50[n - 1]) / atr) };
    if (R.trend.stretchMA20 > 2) R.flags.push('stretched >2 ATR above MA20');
    // B. zones
    const tol = Math.max(0.015 * last, 0.5 * atr);
    const P = [...PH.map((x) => ({ ...x, k: 'H' })), ...PL.map((x) => ({ ...x, k: 'L' }))].sort((a, b) => a.p - b.p);
    const Z = [];
    for (const x of P) { const z = Z[Z.length - 1]; if (z && x.p - z.lo <= 2 * tol) { z.pts.push(x); z.hi = x.p; } else Z.push({ lo: x.p, hi: x.p, pts: [x] }); }
    const minC15 = Math.min(...C.slice(-15));
    Z.forEach((z) => { z.n = z.pts.length; z.broken = minC15 < z.lo - 0.5 * atr; });
    const fmtZ = (z) => z && { lo: tick(z.lo), hi: tick(z.hi), n: z.n, touches: z.pts.map((p) => p.d + '@' + tick(p.p) + p.k), weak: z.n < 2 || undefined };
    let sup = Z.filter((z) => z.hi <= last * 1.01 && z.n >= 2 && !z.broken).sort((a, b) => b.hi - a.hi)[0] || null;
    if (!sup && PL.length) { const pl = PL[PL.length - 1]; if (pl.p < last) sup = { lo: pl.p, hi: pl.p, n: 1, pts: [{ ...pl, k: 'L' }] }; }
    const res = Z.filter((z) => z.lo > last * 1.005).sort((a, b) => a.lo - b.lo);
    const brokenSup = Z.filter((z) => z.broken && z.n >= 2 && z.lo > last * 1.005).map(fmtZ);
    const hi300 = Math.max(...B.map((b) => b.h)), lo300 = Math.min(...B.map((b) => b.l));
    const step = last >= 100 ? 10 : last >= 10 ? 1 : last >= 1 ? 0.5 : 0.05;
    const roundN = [Math.floor(last / step) * step, Math.ceil(last / step) * step].filter((x) => Math.abs(x - last) <= atr).map((x) => tick(x));
    R.zones = { support: fmtZ(sup), resistance: res.slice(0, 2).map(fmtZ), brokenSupportNowResistance: brokenSup.slice(0, 2), hi300: tick(hi300), lo300: tick(lo300), lastSwingLow: PL.length ? [PL[PL.length - 1].d, tick(PL[PL.length - 1].p)] : null, roundNumbers: [...new Set(roundN)] };
    // trendline through last two pivot lows (rising) if no close broke it
    let tline = null;
    if (PL.length >= 2) {
      const a = PL[PL.length - 2], b = PL[PL.length - 1];
      if (b.p > a.p) {
        const slope = (b.p - a.p) / (b.i - a.i); let ok = true;
        for (let i = a.i; i < n; i++) if (C[i] < a.p + slope * (i - a.i) - 0.25 * atr) { ok = false; break; }
        if (ok) tline = { kind: 'rising-support', from: [a.d, tick(a.p)], to: [b.d, tick(b.p)], now: tick(a.p + slope * (n - 1 - a.i)) };
      }
    }
    if (!tline && PH.length >= 2) {
      const a = PH[PH.length - 2], b = PH[PH.length - 1];
      if (b.p < a.p) tline = { kind: 'falling-highs', from: [a.d, tick(a.p)], to: [b.d, tick(b.p)], now: tick(a.p + ((b.p - a.p) / (b.i - a.i)) * (n - 1 - a.i)) };
    }
    R.zones.trendline = tline;
    // C. momentum
    let div = 'none';
    if (PL.length >= 2) { const a = PL[PL.length - 2], b = PL[PL.length - 1]; if (b.p < a.p && RSI[b.i] > RSI[a.i]) div = 'bullish'; }
    if (PH.length >= 2) { const a = PH[PH.length - 2], b = PH[PH.length - 1]; if (b.p > a.p && RSI[b.i] < RSI[a.i]) div = div === 'none' ? 'bearish' : div; }
    let cross = null;
    for (let i = n - 5; i < n; i++) if (hist[i - 1] != null && hist[i] != null) { if (hist[i - 1] <= 0 && hist[i] > 0) cross = 'bull ' + dt(B[i].t); if (hist[i - 1] >= 0 && hist[i] < 0) cross = 'bear ' + dt(B[i].t); }
    R.momentum = { rsi: r2(rsi, 1), rsiZone: rsi < 30 ? 'oversold' : rsi > 70 ? 'overbought' : 'neutral', rsiRising: RSI[n - 1] > RSI[n - 4], divergence: div, macdHist: r2(hist[n - 1], 3), macdCross: cross };
    // D. volatility
    const bw = C.map((_, i) => { if (i < 19) return null; const s = C.slice(i - 19, i + 1); const m = s.reduce((a, b) => a + b, 0) / 20; const sd = Math.sqrt(s.reduce((a, b) => a + (b - m) ** 2, 0) / 20); return (4 * sd) / m; });
    const bwWin = bw.slice(-120).filter((x) => x != null); const bwRank = bwWin.filter((x) => x < bw[n - 1]).length / bwWin.length;
    R.volatility = { atr: R.atr, atrPct: R.atrPct, bbWidthPct: r2(bw[n - 1] * 100), squeeze: bwRank <= 0.2, bbRank: r2(bwRank) };
    // E. volume & liquidity
    const v20 = V.slice(-20).reduce((a, b) => a + b, 0) / 20;
    let upV = 0, dnV = 0; for (let i = n - 20; i < n; i++) { if (C[i] > C[i - 1]) upV += V[i]; else if (C[i] < C[i - 1]) dnV += V[i]; }
    const val20 = B.slice(-20).reduce((a, b) => a + b.v * b.c, 0) / 20;
    R.volume = { lastVsAvg: r2(V[n - 1] / v20), upDownRatio: r2(dnV ? upV / dnV : 9), accumulation: upV > dnV, avgValueM: r2(val20 / 1e6), thin: val20 < 5e6 };
    // F. candles + breakout
    const cand = [];
    for (let i = n - 3; i < n; i++) {
      const b = B[i], p = B[i - 1], body = Math.abs(b.c - b.o), lw = Math.min(b.c, b.o) - b.l, uw = b.h - Math.max(b.c, b.o);
      const nearSup = sup && b.l <= sup.hi + atr; const nearRes = res[0] && b.h >= res[0].lo - atr;
      if (nearSup && lw >= 2 * body && uw <= Math.max(body, 0.1 * atr)) cand.push('hammer ' + dt(b.t));
      if (nearSup && b.c > b.o && p.c < p.o && b.c >= p.o && b.o <= p.c) cand.push('bullish engulfing ' + dt(b.t));
      if (nearSup && i >= 2 && p.h <= B[i - 2].h && p.l >= B[i - 2].l && b.c > p.h) cand.push('inside-bar break ' + dt(b.t));
      if (nearRes && uw >= 2 * body && lw <= Math.max(body, 0.1 * atr)) cand.push('shooting star ' + dt(b.t));
      if (nearRes && b.c < b.o && p.c > p.o && b.o >= p.c && b.c <= p.o) cand.push('bearish engulfing ' + dt(b.t));
    }
    let breakout = null;
    for (const z of Z.filter((z) => z.n >= 2)) for (let i = n - 5; i < n; i++) if (C[i - 1] <= z.hi && C[i] > z.hi && V[i] >= 1.5 * v20 && last > z.hi) breakout = { zone: fmtZ(z), date: dt(B[i].t), volX: r2(V[i] / v20) };
    R.patterns = { candles: cand, breakout, doubleBottom: PL.length >= 2 && Math.abs(PL[PL.length - 1].p - PL[PL.length - 2].p) <= 0.5 * atr ? [PL[PL.length - 2].d, PL[PL.length - 1].d] : null, higherLowAtSupport: !!(sup && PL.length >= 2 && PL[PL.length - 1].p > PL[PL.length - 2].p && PL[PL.length - 1].p <= sup.hi + atr) };
    // G. relative strength
    const ch = (k) => (n > k ? (last / C[n - 1 - k] - 1) * 100 : null);
    R.rs = { ch20: r2(ch(20)), ch60: r2(ch(60)) };
    if (S.index) { R.rs.rs20 = r2(R.rs.ch20 - S.index.ch20); R.rs.rs60 = r2(R.rs.ch60 - S.index.ch60); }
    // H. plan
    let plan = null;
    if (breakout) {
      const z = breakout.zone, e = z.hi, s = Math.min(z.lo - 0.5 * atr, e - atr);
      plan = { type: 'breakout-retest', entry: e, stop: s };
    } else if (sup) {
      const e = last - sup.hi <= 1.5 * atr ? last : sup.hi + 0.2 * atr;
      plan = { type: last - sup.hi <= 1.5 * atr ? 'pullback-at-support' : 'pullback-limit', entry: e, stop: Math.min(sup.lo - 0.5 * atr, e - atr) };
    }
    if (plan) {
      // target = just under the FIRST resistance above the entry (never skip a zone); none above -> 300-bar high
      const tz = res.filter((z) => z.lo * 0.995 > plan.entry * 1.01);
      plan.target = tz[0] ? tz[0].lo * 0.995 : hi300 * 0.995 > plan.entry * 1.01 && !res.length ? hi300 * 0.995 : null;
      plan.target2 = tz[1] ? tz[1].lo * 0.995 : null;
      ['entry', 'stop', 'target', 'target2'].forEach((k) => (plan[k] = tick(plan[k])));
      plan.rr = plan.target ? r2((plan.target - plan.entry) / (plan.entry - plan.stop)) : null;
      plan.stopATR = r2((plan.entry - plan.stop) / atr);
      plan.entryDistATR = r2((last - plan.entry) / atr);
      plan.fillSoon = plan.entryDistATR <= 2;
    }
    R.plan = plan;
    // checks + drop reason (same order as loop-30)
    const checks = {
      bars: true,
      rr: !!(plan && plan.rr >= 2),
      liquidity: !R.volume.thin,
      stopWidth: !!(plan && plan.stopATR >= 1 && plan.stopATR <= 3),
      targetAbovePrice: !!(plan && plan.target && plan.target > last * 1.01),
      notAtLimit: Math.abs(R.chg) < 18,
    };
    R.checks = checks;
    R.drop = !plan ? 'no-plan' : !checks.notAtLimit ? 'limit' : !checks.liquidity ? 'thin' : !checks.targetAbovePrice ? 'invalid' : !checks.rr ? 'rr' : !checks.stopWidth ? (plan.stopATR > 3 ? 'wide' : 'noise') : null;
    // I. score
    const sc = { trend: (trend === 'up') + (wtrend === 'up'), rs: R.rs.rs20 == null ? 0 : (R.rs.rs20 > 0) + (R.rs.rs60 > 0), rr: plan && plan.rr >= 3 ? 2 : plan && plan.rr >= 2 ? 1 : 0, volume: R.volume.accumulation || !!breakout ? 1 : 0, momentum: (R.momentum.rsi >= 40 && R.momentum.rsi <= 65 && R.momentum.rsiRising) || div === 'bullish' || (cross && cross.startsWith('bull')) ? 1 : 0, catalyst: opts.catalyst ? 1 : 0, regime: S.index && S.index.regime === 'Up' ? 1 : 0 };
    R.score = { total: Object.values(sc).reduce((a, b) => a + Number(b), 0), parts: sc };
    // evidence lines (English, dated) for the report
    const ev = R.evidence;
    ev.push(`Trend daily ${trend} (highs ${R.pivots.highs.map((x) => x.join(' ')).join(', ')}; lows ${R.pivots.lows.map((x) => x.join(' ')).join(', ')}), weekly ${wtrend}`);
    ev.push(`MA20 ${R.trend.ma20} / MA50 ${R.trend.ma50} (slope ${R.trend.ma50Slope}%) / MA200 ${R.trend.ma200}; stack ${R.trend.stack}; close ${r2(R.trend.stretchMA20)} ATR from MA20`);
    if (sup) ev.push(`Support ${tick(sup.lo)}-${tick(sup.hi)} touched ${sup.n}x: ${sup.pts.map((p) => p.d).join(', ')}`);
    if (res[0]) ev.push(`Resistance ${tick(res[0].lo)}-${tick(res[0].hi)} touched ${res[0].n}x: ${res[0].pts.map((p) => p.d).join(', ')}`);
    ev.push(`RSI14 ${R.momentum.rsi} (${R.momentum.rsiZone}), divergence ${div}, MACD hist ${R.momentum.macdHist}${cross ? ', cross ' + cross : ''}`);
    ev.push(`ATR14 ${R.atr} (${R.atrPct}%), BB width ${R.volatility.bbWidthPct}%${R.volatility.squeeze ? ' SQUEEZE' : ''}`);
    ev.push(`Volume last ${R.volume.lastVsAvg}x avg, up/down vol ${R.volume.upDownRatio}, avg value ${R.volume.avgValueM}M EGP/day`);
    if (R.rs.rs20 != null) ev.push(`RS vs EGX30: 20 bars ${R.rs.rs20}, 60 bars ${R.rs.rs60}`);
    if (cand.length) ev.push('Candles: ' + cand.join(', '));
    if (breakout) ev.push(`Breakout ${breakout.date} above ${breakout.zone.hi} on ${breakout.volX}x volume`);
    // draw spec (event lines are added by EGX.draw after the news gate)
    R.zones._first = { support: sup ? sup.pts.map((p) => p.d).sort()[0] : null, res: res.slice(0, 2).map((z) => z.pts.map((p) => p.d).sort()[0]), broken: Z.filter((z) => z.broken && z.n >= 2 && z.lo > last * 1.005).slice(0, 2).map((z) => z.pts.map((p) => p.d).sort()[0]) };
    R.draw = drawSpec(R, [], atr);
    if (opts.history) R.history = setupHistory(B, ATR, sup, plan);
    return save(tk, R);
  }

  // setup history test: how often a touch of today's support reached today's target before the stop (15 bars)
  function setupHistory(B, ATR, sup, plan) {
    if (!sup || !plan || !plan.target) return null;
    const n = B.length; let tries = 0, hits = 0, stops = 0; const dates = [];
    for (let i = 60; i < n - 16; i++) {
      const a = ATR[i]; if (!a) continue;
      if (B[i].l <= sup.hi + 0.25 * a && B[i].c >= sup.lo) {
        const e = B[i].c, s = sup.lo - 0.5 * a, t = e + (plan.target - plan.entry);
        let res = 'none';
        for (let j = i + 1; j <= i + 15; j++) { if (B[j].l <= s) { res = 'stop'; break; } if (B[j].h >= t) { res = 'target'; break; } }
        tries++; if (res === 'target') hits++; if (res === 'stop') stops++; dates.push(dt(B[i].t) + ':' + res); i += 5;
      }
    }
    return { tries, hits, stops, judge: tries < 3 ? 'too few to judge' : r2(hits / tries * 100) + '% hit', dates: dates.slice(-8) };
  }

  // ---------- drawing ----------
  // Every mark: { kind, shape: 'box'|'hline'|'trend'|'vline', text, color, ... }. Text always starts with MARK + ticker.
  function drawSpec(R, events = [], atr = R.atr) {
    const M = [], p = R.plan, z = R.zones, tag = `${MARK}${R.tk} `, f = z._first || {};
    const pad = (lo, hi) => (hi - lo < 0.2 * atr ? [tick(lo - 0.1 * atr), tick(hi + 0.1 * atr)] : [lo, hi]);
    if (z.support) { const [lo, hi] = pad(z.support.lo, z.support.hi); M.push({ kind: 'support', shape: 'box', from: f.support || R.asOf, lo, hi, text: `${tag}دعم ${z.support.lo}-${z.support.hi} (${z.support.touches.map((x) => x.slice(5, 10)).join('، ')})`, color: '#f5a623', fill: 'rgba(245,166,35,0.18)', style: 0 }); }
    (z.resistance || []).slice(0, 2).forEach((r, i) => { const [lo, hi] = pad(r.lo, r.hi); M.push({ kind: 'resistance' + (i + 1), shape: 'box', from: (f.res || [])[i] || R.asOf, lo, hi, text: `${tag}مقاومة ${r.lo}-${r.hi} (${r.n} لمسات)`, color: '#e74c3c', fill: 'rgba(231,76,60,0.15)', style: 0 }); });
    (z.brokenSupportNowResistance || []).slice(0, 1).forEach((r) => { const [lo, hi] = pad(r.lo, r.hi); M.push({ kind: 'broken', shape: 'box', from: (f.broken || [])[0] || R.asOf, lo, hi, text: `${tag}دعم مكسور ← مقاومة ${r.lo}-${r.hi}`, color: '#c0392b', fill: 'rgba(192,57,43,0.08)', style: 2 }); });
    if (p) {
      M.push({ kind: 'entry', shape: 'hline', price: p.entry, text: `${tag}دخول ${p.entry}`, color: '#3498db', style: 0 });
      M.push({ kind: 'stop', shape: 'hline', price: p.stop, text: `${tag}وقف ${p.stop}`, color: '#e74c3c', style: 0 });
      if (p.target) M.push({ kind: 'target', shape: 'hline', price: p.target, text: `${tag}هدف ${p.target}`, color: '#2ecc71', style: 0 });
      if (p.target2) M.push({ kind: 'target2', shape: 'hline', price: p.target2, text: `${tag}هدف 2 ${p.target2}`, color: '#2ecc71', style: 2 });
    }
    if (z.trendline) M.push({ kind: 'trend', shape: 'trend', pts: [z.trendline.from, z.trendline.to], text: tag + (z.trendline.kind === 'rising-support' ? 'خط اتجاه صاعد' : 'قمم هابطة'), color: '#f5a623', style: 0 });
    for (const e of events || []) {
      if (!e || !/^\d{4}-\d{2}-\d{2}$/.test(e.date || '')) continue;
      const cat = e.kind === 'catalyst';
      M.push({ kind: cat ? 'catalyst' : 'event', shape: 'vline', date: e.date, text: `${tag}${cat ? 'خبر' : 'حدث'} ${e.date}${e.label ? ' ' + e.label : ''}`, color: cat ? '#8e44ad' : '#e74c3c', style: cat ? 0 : 2 });
    }
    return { marks: M };
  }

  function clearMarks(ch, prefix) {
    let removed = 0;
    for (const s of ch.getAllShapes()) { try { const pr = ch.getShapeById(s.id).getProperties(); if (String(pr.text || '').startsWith(prefix)) { ch.removeEntity(s.id); removed++; } } catch (e) {} }
    return removed;
  }

  async function makeMark(ch, m, lastT) {
    const o = { linecolor: m.color, textcolor: m.color, color: m.color, linestyle: m.style, linewidth: 2, showLabel: true, fontsize: 12 };
    if (m.shape === 'hline') return ch.createShape({ time: lastT, price: m.price }, { shape: 'horizontal_line', text: m.text, overrides: { ...o, horzLabelsAlign: 'right' } });
    if (m.shape === 'vline') return ch.createShape({ time: toT(m.date), price: 0 }, { shape: 'vertical_line', text: m.text, overrides: { ...o, linewidth: 1 } });
    if (m.shape === 'trend') return ch.createMultipointShape(m.pts.map(([d, p]) => ({ time: toT(d), price: p })), { shape: 'trend_line', text: m.text, overrides: { ...o, extendRight: true } });
    const t1 = typeof m.from === 'number' ? m.from : toT(m.from);
    return ch.createMultipointShape([{ time: t1, price: m.hi }, { time: lastT, price: m.lo }], { shape: 'rectangle', text: m.text, overrides: { ...o, linewidth: 1, backgroundColor: m.fill, fillBackground: true, extendRight: true, horzLabelsAlign: 'right', vertLabelsAlign: 'top' } });
  }

  async function ensureMAs(ch) {
    const out = { ma50: false, ma200: false };
    try {
      const have = new Set();
      for (const s of ch.getAllStudies()) {
        if (!/moving average/i.test(s.name || '')) continue;
        try { const iv = ch.getStudyById(s.id).getInputValues(); const L = (iv.find((x) => x.id === 'length' || x.id === 'in_0') || {}).value; if (L) have.add(Number(L)); } catch (e) {}
      }
      for (const [k, len, col] of [['ma50', 50, '#2962ff'], ['ma200', 200, '#9c27b0']]) {
        if (have.has(len)) { out[k] = 'present'; continue; }
        try { await ch.createStudy('Moving Average', false, false, { length: len }, { 'plot.color': col, 'plot.linewidth': 2 }); out[k] = 'added'; }
        catch (e) { try { await ch.createStudy('Moving Average', false, false, [len]); out[k] = 'added'; } catch (e2) { out[k] = false; out.error = e2.message; } }
      }
    } catch (e) { out.error = e.message; }
    return out;
  }

  // gate 4: draw. events = [{date:'YYYY-MM-DD', kind:'event'|'catalyst', label}] from the news gate.
  async function draw(tk, { events = [], mas = true } = {}) {
    const R = S.results[tk]; if (!R || !R.zones) return { ok: false, error: 'analyse first' };
    if (S.lastOpen && S.lastOpen.tk !== tk) return { ok: false, error: `chart shows ${S.lastOpen.tk}, not ${tk}: EGX.open first` };
    const ch = chart(); if (!sameRes(ch.resolution(), '1D')) return { ok: false, error: 'chart not on 1D: EGX.daily() first' };
    R.draw = drawSpec(R, events, R.atr); R.events = events;
    const removed = clearMarks(ch, MARK);
    const { B } = await bars(); const lastT = B[B.length - 1].t;
    const ids = [], failed = [];
    for (const m of R.draw.marks) { try { const id = await makeMark(ch, m, lastT); if (id) ids.push({ id, kind: m.kind }); else failed.push(m.kind); } catch (e) { failed.push(m.kind + ': ' + e.message); } }
    S.shapes[tk] = ids; store('shapes', S.shapes);
    const studies = mas ? await ensureMAs(ch) : { skipped: true };
    try { ch.setVisibleRange({ from: lastT - 200 * 86400, to: lastT + 15 * 86400 }); } catch (e) {}
    R.drawn = { made: ids.length, planned: R.draw.marks.length, removed, failed, studies };
    R.receipts.draw = { ...now(), made: ids.length, planned: R.draw.marks.length, kinds: ids.map((x) => x.kind), failed, studies };
    delete R.receipts.verify; save(tk, R);
    return { ok: !failed.length && ids.length > 0, ...R.drawn };
  }

  // gate 5: read every EGX· mark back and compare it with the plan. The screenshot must be taken AFTER this.
  async function verifyChart(tk, { t0 = false } = {}) {
    const R = S.results[tk]; if (!R) return { ok: false, error: 'analyse first' };
    const spec = t0 ? R.t0 && R.t0.draw : R.draw; const reg = S.shapes[t0 ? tk + ':T0' : tk] || [];
    const prob = [];
    let ch; try { ch = chart(); } catch (e) { return { ok: false, error: e.message }; }
    if (!spec) prob.push('nothing drawn yet');
    let sym = null, res = null; try { sym = ch.symbol(); res = ch.resolution(); } catch (e) {}
    if (S.lastOpen && S.lastOpen.tk !== tk) prob.push(`chart shows ${S.lastOpen.tk}, not ${tk}`);
    if (S.lastOpen && sym && S.lastOpen.symbol && S.lastOpen.symbol !== sym) prob.push('chart symbol changed since EGX.open');
    if (S.lastOpen && S.lastOpen.headerMatch === false && String(S.lastOpen.title || '').toUpperCase() !== tk) prob.push('chart header and title do not show ' + tk);
    if (!sameRes(res, t0 ? '5' : '1D')) prob.push(`resolution ${res}, expected ${t0 ? '5' : '1D'}`);
    const live = new Set(); for (const s of ch.getAllShapes()) live.add(s.id);
    const tol = (p) => Math.max(p < 1 ? 0.0011 : 0.011, Math.abs(p) * 0.001);
    const marks = (spec && spec.marks) || [];
    const found = [];
    marks.forEach((m, i) => {
      const r = reg.filter((x) => x.kind === m.kind)[marks.filter((x, j) => j < i && x.kind === m.kind).length];
      if (!r || !live.has(r.id)) { prob.push(`${m.kind} missing`); return; }
      let pts = [], text = ''; try { const sh = ch.getShapeById(r.id); pts = sh.getPoints(); text = String(sh.getProperties().text || ''); } catch (e) { prob.push(`${m.kind} unreadable`); return; }
      if (!text.startsWith(MARK + tk) && !text.startsWith(MARK + 'T0 ' + tk)) prob.push(`${m.kind} label "${text.slice(0, 30)}" is not ${tk}`);
      const ps = pts.map((x) => x.price);
      if (m.shape === 'hline' && !(ps.length && Math.abs(ps[0] - m.price) <= tol(m.price))) prob.push(`${m.kind} at ${ps[0]}, planned ${m.price}`);
      if (m.shape === 'box') { const hi = Math.max(...ps), lo = Math.min(...ps); if (Math.abs(hi - m.hi) > tol(m.hi) || Math.abs(lo - m.lo) > tol(m.lo)) prob.push(`${m.kind} box ${lo}-${hi}, planned ${m.lo}-${m.hi}`); }
      if (m.shape === 'vline' && !(pts.length && Math.abs(pts[0].time - toT(m.date)) <= 86400)) prob.push(`${m.kind} line not on ${m.date}`);
      if (m.shape === 'trend' && !(ps.length === 2 && Math.abs(ps[0] - m.pts[0][1]) <= tol(m.pts[0][1]) && Math.abs(ps[1] - m.pts[1][1]) <= tol(m.pts[1][1]))) prob.push('trendline points differ');
      found.push(m.kind);
    });
    const ours = new Set(reg.map((x) => x.id)); let extra = 0;
    for (const s of ch.getAllShapes()) { try { const tx = String(ch.getShapeById(s.id).getProperties().text || ''); if (tx.startsWith(MARK) && !ours.has(s.id) && !(t0 ? (S.shapes[tk] || []) : (S.shapes[tk + ':T0'] || [])).some((x) => x.id === s.id)) extra++; } catch (e) {} }
    if (extra) prob.push(`${extra} EGX· mark(s) not from this check`);
    const studies = !t0 && R.drawn ? R.drawn.studies : null;
    if (studies && !studies.skipped && (!studies.ma50 || !studies.ma200)) prob.push('MA50/MA200 not on the chart');
    const rc = { ...now(), ok: !prob.length, t0, symbol: sym, resolution: res, expected: marks.length, found: found.length, kinds: found, problems: prob };
    if (t0) R.t0.receipts.verify = rc; else R.receipts.verify = rc;
    save(tk, R);
    return rc;
  }

  // back to the daily chart (after a T0 screenshot, or before a daily check)
  async function setRes(r) {
    const ch = chart(); if (sameRes(ch.resolution(), r)) return true;
    await new Promise((ok) => { let done = false; const fin = () => { if (!done) { done = true; ok(); } }; try { const pr = ch.setResolution(r, fin); if (pr && pr.then) pr.then(fin, fin); } catch (e) { fin(); } setTimeout(fin, 6000); });
    const want = r === '5' ? 300 : 86400, t0 = Date.now();
    while (Date.now() - t0 < 8000) { try { const { B } = await bars(); if (B.length > 3) { const d = B[B.length - 2].t - B[B.length - 3].t; if (r === '5' ? d === want : d >= 0.9 * want) return true; } } catch (e) {} await sleep(300); }
    return false;
  }
  async function daily() { const ok = await setRes('1D'); return { ok, resolution: chart().resolution() }; }

  // ---------- T0: same-session analysis on 5-minute bars ----------
  async function intraday(tk, opts = {}) {
    if (!opts.alreadyOpen) { const o = await open(tk); if (!o.ok) return { ok: false, ...o }; }
    if (!(await setRes('1D'))) return { ok: false, error: 'could not switch to 1D' };
    const D = await analyze(tk, { keepReceipts: true });
    D.page = page();
    if (!(await setRes('5'))) return { ok: false, error: 'could not switch to 5 minutes' };
    const { B } = await bars(); const n = B.length;
    const T0 = { tk, v: VERSION, flags: [], receipts: { analyse: { ...now(), version: VERSION, bars5: n } } };
    const lastDay = n ? cairo(B[n - 1].t).d : null;
    const T = B.filter((b) => cairo(b.t).d === lastDay), prior = B.filter((b) => cairo(b.t).d !== lastDay);
    T0.session = { day: lastDay, from: T.length ? cairo(T[0].t).hm : null, to: T.length ? cairo(T[T.length - 1].t).hm : null, bars: T.length };
    T0.receipts.analyse.lastBar = T.length ? `${lastDay} ${T0.session.to}` : null;
    const drop = (r) => { T0.drop = r; D.t0 = T0; save(tk, D); return T0; };
    if (T.length < 6) return drop('early');
    const ATR = atrArr(B), atr5 = ATR[n - 1], C = B.map((b) => b.c), rsi5 = rsiArr(C)[n - 1];
    let pv = 0, vv = 0; const VW = T.map((b) => { pv += ((b.h + b.l + b.c) / 3) * b.v; vv += b.v; return vv ? pv / vv : b.c; });
    const vwap = VW[VW.length - 1], last = T[T.length - 1].c;
    const OR = T.slice(0, 6), orHi = Math.max(...OR.map((b) => b.h)), orLo = Math.min(...OR.map((b) => b.l));
    const dayHi = Math.max(...T.map((b) => b.h)), prevClose = prior.length ? prior[prior.length - 1].c : null;
    const above = T.filter((b, i) => b.c > VW[i]).length / T.length;
    const days = {}; prior.forEach((b) => { (days[cairo(b.t).d] = days[cairo(b.t).d] || []).push(b.v); });
    const k = T.length, cumT = T.reduce((a, b) => a + b.v, 0);
    const past = Object.values(days).filter((v) => v.length >= k).map((v) => v.slice(0, k).reduce((a, b) => a + b, 0));
    T0.candles = T.slice(-60).map((b) => [cairo(b.t).hm, tick(b.o), tick(b.h), tick(b.l), tick(b.c)]);
    T0.vwap = tick(vwap); T0.last = tick(last); T0.atr5 = r2(atr5, 3); T0.rsi5 = r2(rsi5, 1);
    T0.openingRange = { hi: tick(orHi), lo: tick(orLo), from: cairo(OR[0].t).hm, to: cairo(OR[5].t).hm };
    T0.dayHigh = tick(dayHi); T0.dayChg = prevClose ? r2((last / prevClose - 1) * 100) : null;
    T0.vsEGX30 = S.index && S.index.chgToday != null && T0.dayChg != null ? r2(T0.dayChg - S.index.chgToday) : null;
    T0.aboveVwapShare = r2(above); T0.relVol = past.length >= 3 ? r2(cumT / (past.reduce((a, b) => a + b, 0) / past.length)) : null;
    const sup = D.zones && D.zones.support, res = D.zones && D.zones.resistance && D.zones.resistance[0];
    T0.daily = { support: sup ? [sup.lo, sup.hi] : null, resistance: res ? [res.lo, res.hi] : null, avgValueM: D.volume && D.volume.avgValueM };
    // setups, first that fits
    const L = T[T.length - 1], P = T[T.length - 2], avgV6 = (i) => T.slice(Math.max(0, i - 6), i).reduce((a, b) => a + b.v, 0) / Math.min(6, i);
    let plan = null;
    const brk = T.findIndex((b, i) => i >= 6 && b.c > orHi && b.v > avgV6(i));
    if (brk >= 0 && last > vwap && last > orHi) { const e = orHi; let s = Math.max(orHi - 0.3 * atr5, vwap); s = Math.min(s, e - atr5); plan = { setup: 'opening-range-breakout', entry: e, stop: s, trigger: `retest of ${tick(orHi)} after the ${cairo(T[brk].t).hm} breakout` }; }
    else if (above >= 0.7 && L.l <= vwap + 0.25 * atr5 && L.c > vwap) plan = { setup: 'vwap-pullback', entry: vwap, stop: vwap - 1.25 * atr5, trigger: `5-min close above VWAP ${tick(vwap)}` };
    else if (sup && L.l <= sup.hi + 0.25 * atr5 && L.c > L.o && L.c > P.h) { const e = L.c; plan = { setup: 'daily-support-bounce', entry: e, stop: Math.min(sup.lo - 0.25 * atr5, e - atr5), trigger: `hold above ${tick(sup.lo)}` }; }
    if (!plan) return drop('no-setup');
    const R1 = plan.entry - plan.stop;
    const cands = [dayHi, res && res.lo].filter((x) => x && x > plan.entry * 1.001);
    plan.target = cands.length ? Math.min(...cands) : plan.entry + 2 * R1; plan.targetFrom = !cands.length ? '2R (nothing above)' : plan.target === dayHi ? 'day high' : 'daily resistance';
    ['entry', 'stop', 'target'].forEach((x) => (plan[x] = tick(plan[x])));
    plan.rr = r2((plan.target - plan.entry) / (plan.entry - plan.stop)); plan.stopATR5 = r2((plan.entry - plan.stop) / atr5);
    plan.movePct = r2((plan.target / plan.entry - 1) * 100); plan.entryDistATR5 = r2((last - plan.entry) / atr5);
    plan.exitBy = '14:20'; plan.noEntryAfter = '13:30';
    T0.plan = plan;
    const sp = D.page && D.page.book && D.page.book.spreadPct;
    T0.drop = Math.abs(T0.dayChg || 0) >= 17 ? 'limit' : (T0.daily.avgValueM || 0) < 20 ? 'thin' : sp != null && sp > 0.3 ? 'spread' : plan.rr < 2 ? 'rr' : null;
    T0.evidence = [`Session ${lastDay} ${T0.session.from}-${T0.session.to} (${T.length} bars), last ${T0.last}, VWAP ${T0.vwap}, above VWAP ${Math.round(above * 100)}% of bars`,
      `Opening range ${T0.openingRange.lo}-${T0.openingRange.hi} (${T0.openingRange.from}-${T0.openingRange.to}), day high ${T0.dayHigh}, day ${T0.dayChg}%${T0.vsEGX30 != null ? ', vs EGX30 ' + T0.vsEGX30 : ''}`,
      `ATR5 ${T0.atr5}, RSI5 ${T0.rsi5}, relative volume ${T0.relVol ?? 'unknown'}`];
    D.t0 = T0; save(tk, D);
    return T0;
  }

  async function drawT0(tk) {
    const R = S.results[tk]; const T0 = R && R.t0; if (!T0 || !T0.plan) return { ok: false, error: 'run EGX.intraday first (and it needs a plan)' };
    const ch = chart(); if (!sameRes(ch.resolution(), '5')) return { ok: false, error: 'chart not on 5 minutes' };
    const tag = `${MARK}T0 ${tk} `, p = T0.plan, M = [];
    const { B } = await bars(); const lastT = B[B.length - 1].t; const first = B.find((b) => cairo(b.t).d === T0.session.day);
    M.push({ kind: 'range', shape: 'box', from: first ? first.t : lastT, lo: T0.openingRange.lo, hi: T0.openingRange.hi, text: `${tag}نطاق الافتتاح`, color: '#7f8c8d', fill: 'rgba(127,140,141,0.15)', style: 0 });
    M.push({ kind: 'vwap', shape: 'hline', price: T0.vwap, text: `${tag}VWAP ${T0.vwap}`, color: '#8e44ad', style: 2 });
    M.push({ kind: 'entry', shape: 'hline', price: p.entry, text: `${tag}دخول ${p.entry}`, color: '#3498db', style: 0 });
    M.push({ kind: 'stop', shape: 'hline', price: p.stop, text: `${tag}وقف ${p.stop}`, color: '#e74c3c', style: 0 });
    M.push({ kind: 'target', shape: 'hline', price: p.target, text: `${tag}هدف ${p.target}`, color: '#2ecc71', style: 0 });
    if (T0.daily.support) M.push({ kind: 'dsupport', shape: 'hline', price: T0.daily.support[1], text: `${tag}دعم يومي ${T0.daily.support[1]}`, color: '#f5a623', style: 2 });
    if (T0.daily.resistance) M.push({ kind: 'dresistance', shape: 'hline', price: T0.daily.resistance[0], text: `${tag}مقاومة يومية ${T0.daily.resistance[0]}`, color: '#e74c3c', style: 2 });
    T0.draw = { marks: M };
    const removed = clearMarks(ch, MARK + 'T0 ');
    const ids = [], failed = [];
    for (const m of M) { try { const id = await makeMark(ch, m, lastT); if (id) ids.push({ id, kind: m.kind }); else failed.push(m.kind); } catch (e) { failed.push(m.kind + ': ' + e.message); } }
    S.shapes[tk + ':T0'] = ids; store('shapes', S.shapes);
    T0.receipts.draw = { ...now(), made: ids.length, planned: M.length, kinds: ids.map((x) => x.kind), failed, removed };
    delete T0.receipts.verify; save(tk, R);
    return { ok: !failed.length, made: ids.length, planned: M.length, failed };
  }

  // ---------- page panels (read only) ----------
  function page() {
    const body = clean(document.body.innerText);
    const out = { market: /السوق مفتوح/.test(body) ? 'open' : /السوق مغلق/.test(body) ? 'closed' : 'unknown' };
    const st = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && /السوق (مفتوح|مغلق)/.test(e.textContent));
    if (st) { let a = st; for (let i = 0; i < 4 && a; i++) { a = a.parentElement; const m = clean(a.innerText).match(/([\d,]+\.\d+)\s*ج\.م/); if (m) { out.cash = num(m[1]); break; } } }
    const hue = (c) => { const m = (c.match(/\d+/g) || [0, 0, 0]).map(Number); return m[1] > m[0] + 30 ? 'G' : m[0] > m[1] + 30 ? 'R' : 'N'; };
    const box = [...document.querySelectorAll('div')].filter((d) => d.offsetParent && d.innerText.includes('الطلب') && d.innerText.includes('العرض') && d.innerText.includes('%')).sort((a, b) => a.innerText.length - b.innerText.length)[0];
    if (box) {
      const leaves = [...box.querySelectorAll('*')].filter((e) => e.children.length === 0 && clean(e.textContent)).map((e) => [clean(e.textContent), hue(getComputedStyle(e).color)]);
      const tot = leaves.filter(([t]) => /\(\s*\d+(\.\d+)?%\s*\)/.test(t));
      const g = tot.find((x) => x[1] === 'G'), r = tot.find((x) => x[1] === 'R');
      const pct = (s) => s && num(s[0].match(/\(([^)]+)\)/)[1]);
      const prices = leaves.filter(([t, c]) => /^\d+(\.\d+)?$/.test(t) && c !== 'N');
      const bid = prices.find((x) => x[1] === 'G'), ask = prices.find((x) => x[1] === 'R');
      out.book = { bidPct: pct(g), askPct: pct(r), bidVol: g && num(g[0].split('(')[0]), askVol: r && num(r[0].split('(')[0]), bestBid: bid && num(bid[0]), bestAsk: ask && num(ask[0]) };
      if (out.book.bestBid && out.book.bestAsk) out.book.spreadPct = r2((out.book.bestAsk / out.book.bestBid - 1) * 100);
      out.book.side = out.book.bidPct > 55 ? 'buyers heavier' : out.book.askPct > 55 ? 'sellers heavier' : 'balanced';
    }
    const band = body.match(/من\s*([\d.]+)\s*الي\s*([\d.]+)/); if (band) out.band = [num(band[1]), num(band[2])];
    return out;
  }

  function holdings() {
    const g = [...document.querySelectorAll('[role=grid]')].find((x) => x.offsetParent && x.innerText.includes('رمز السهم'));
    if (!g) return { ok: false, error: 'open the الاستثمارات الحالية tab' };
    const rows = [...g.querySelectorAll('[role=row]')].map((r) => [...r.querySelectorAll('[role=gridcell]')].map((c) => clean(c.innerText)));
    const data = rows.filter((r) => r.length >= 9), tks = rows.filter((r) => r.length === 1 && /^[A-Z0-9]{2,8}$/.test(r[0])).map((r) => r[0]);
    return { ok: true, items: data.map((r, i) => ({ tk: tks[i] || null, price: num(r[0]), dayChg: num(r[1]), avgPrice: num(r[2]), qty: num(r[3]), cost: num(r[4]), value: num(r[5]), weight: num(r[6]), pnl: num(r[7]), pnlPct: num(r[8]) })) };
  }

  async function financials() {
    const tab = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && clean(e.textContent) === 'البيانات المالية' && e.offsetParent);
    if (!tab) return { ok: false, error: 'financial tab not found' };
    tab.click(); await sleep(1500);
    let box = null;
    for (let i = 0; i < 10 && !box; i++) {
      box = [...document.querySelectorAll('div')].filter((d) => d.offsetParent && d.innerText.includes('تفاصيل المؤشرات') && d.innerText.includes('%') && d.innerText.length > 200).sort((a, b) => a.innerText.length - b.innerText.length)[0] || null;
      if (!box) await sleep(300);
    }
    const out = { ok: !!box, scores: {}, metrics: {} };
    if (box) {
      const L = clean(box.innerText).split('\n').map(clean).filter(Boolean);
      const k = L.indexOf('تفاصيل المؤشرات');
      let up = box; for (let i = 0; i < 4 && up; i++) { up = up.parentElement; const T = clean(up && up.innerText); const re = /(الصحة المالية|الكفاءة|النمو|الربحية|التقييم)\n(\d+%)/g; let m; while ((m = re.exec(T))) out.scores[m[1]] = m[2]; if (Object.keys(out.scores).length >= 3) break; }
      for (let i = k + 1; i < L.length - 1; i++) if (/^-?[\d.,]+%?$|^-$/.test(L[i + 1]) && !/^-?[\d.,]+%?$/.test(L[i])) { out.metrics[L[i]] = L[i + 1]; i++; }
    }
    const back = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && clean(e.textContent) === 'المخطط' && e.offsetParent); if (back) back.click();
    await sleep(500);
    return out;
  }

  // market page numbers (call on /market) + EGX30 regime from its chart (call on /trade with EGX30 open)
  function marketPage() {
    const t = clean(document.body.innerText);
    const g = (re) => { const m = t.match(re); return m ? m.slice(1) : null; };
    const egx30 = g(/EGX 30\s*\n?\s*([\d,]+\.\d+)\s*نقطة\s*\n?\s*([-+]?[\d.]+)%/);
    const sectors = []; const sm = t.split('نبض القطاعات')[1];
    if (sm) { const L = sm.split('\n').map(clean).filter(Boolean); for (let i = 0; i < L.length - 1 && sectors.length < 20; i++) if (/^[-+]?[\d.]+%$/.test(L[i + 1]) && /[؀-ۿ]/.test(L[i]) && !/الرابحين|الخاسرين/.test(L[i])) { sectors.push([L[i], num(L[i + 1])]); i++; } }
    return { egx30: egx30 && { value: num(egx30[0]), chg: num(egx30[1]) }, gainers: num((g(/الرابحين\s*\n?\s*(\d+)\s*\(/) || [])[0]), losers: num((g(/الخاسرين\s*\n?\s*(\d+)\s*\(/) || [])[0]), usdEgp: num((g(/دولار\/جنيه\s*\n?\s*([\d.]+)/) || [])[0]), sectors };
  }

  async function market() {
    const o = await open('EGX30'); await setRes('1D');
    const { B } = await bars(); const C = B.map((b) => b.c), n = C.length;
    if (n < 210) return { ok: false, error: 'EGX30 chart not loaded', open: o };
    const ma = (k, end = n) => C.slice(end - k, end).reduce((a, b) => a + b, 0) / k;
    const ma50 = ma(50), ma50p = ma(50, n - 20), ma200 = ma(200), ma20 = ma(20), last = C[n - 1];
    const rising = ma50 > ma50p;
    const regime = last > ma50 && rising && last > ma200 ? 'Up' : last < ma50 && !rising && last < ma200 ? 'Down' : 'Correction';
    const hi = Math.max(...B.map((b) => b.h));
    const { PH, PL } = pivots(B, n - 130);
    S.index = { spark: C.slice(-60).map((x) => r2(x)), date: dt(B[n - 1].t), last: r2(last), ma20: r2(ma20), ma50: r2(ma50), ma50Slope: r2((ma50 / ma50p - 1) * 100), ma200: r2(ma200), ch20: r2((last / C[n - 21] - 1) * 100), ch60: r2((last / C[n - 61] - 1) * 100), chgToday: r2((last / C[n - 2] - 1) * 100), fromHigh: r2((last / hi - 1) * 100), regime, lastHighs: PH.slice(-2).map((p) => [p.d, r2(p.p)]), lastLows: PL.slice(-2).map((p) => [p.d, r2(p.p)]) };
    store('index', S.index); return { ok: true, ...S.index };
  }

  // viewport rectangle of the chart (CSS px) -> pass to the computer `zoom` action with save_to_disk
  function chartRect(pad = 0) {
    const f = [...document.querySelectorAll('iframe')].find((x) => { try { return x.contentWindow.tradingViewApi; } catch (e) { return false; } });
    if (!f) return null;
    const r = f.getBoundingClientRect();
    return { region: [Math.max(0, Math.round(r.left - pad)), Math.max(0, Math.round(r.top - pad)), Math.round(r.right + pad), Math.round(r.bottom + pad)], viewport: [innerWidth, innerHeight] };
  }

  function save(tk, R) { S.results[tk] = R; store('results', S.results); return R; }

  function summary(R) {
    if (!R) return null;
    if (R.drop === 'new') return `${R.tk} | new listing (${R.bars} bars)`;
    const p = R.plan || {};
    return [R.tk, R.last, (R.chg > 0 ? '+' : '') + R.chg + '%', 'trend ' + R.trend.daily + '/' + R.trend.weekly, 'RS ' + (R.rs.rs20 ?? '?') + '/' + (R.rs.rs60 ?? '?'), 'E ' + p.entry, 'S ' + p.stop, 'T ' + p.target, 'RR ' + p.rr, 'stop ' + p.stopATR + 'ATR', 'dist ' + p.entryDistATR + 'ATR', 'val ' + R.volume.avgValueM + 'M', 'score ' + R.score.total, R.drop ? 'DROP:' + R.drop : 'OK'].join(' | ');
  }

  async function scan(tk, opts = {}) {
    const o = await open(tk);
    if (!o.ok) return `${tk} | UNKNOWN (${o.error})`;
    if (!(await setRes('1D'))) return `${tk} | UNKNOWN (chart not on 1D)`;
    try { return summary(await analyze(tk, opts)); } catch (e) { return `${tk} | UNKNOWN (${e.message})`; }
  }

  async function deep(tk, opts = {}) {
    if (!opts.alreadyOpen) { const o = await open(tk); if (!o.ok) return { ok: false, ...o }; }
    if (!(await setRes('1D'))) return { ok: false, tk, error: 'could not switch the chart to 1D' };
    const R = await analyze(tk, { ...opts, history: true });
    R.page = page();
    if (opts.financials !== false) R.financials = await financials();
    R.candles = await candlesNow(120);
    save(tk, R);
    if (opts.draw === true) R.drawn = await draw(tk, { events: opts.events || [] });
    return R;
  }

  async function candlesNow(k = 120) { const { B } = await bars(); return B.slice(-k).map((b) => [dt(b.t), tick(b.o), tick(b.h), tick(b.l), tick(b.c)]); }

  // export stored results; full detail for `full` tickers, summary rows for the rest
  function exportRun(full = [], extra = {}) {
    const out = { egxjs: VERSION, index: S.index, stocks: [] };
    for (const [tk, R] of Object.entries(S.results)) {
      if (full.includes(tk)) out.stocks.push(R);
      else out.stocks.push({ tk, title: R.title, last: R.last, chg: R.chg, spark: R.spark, trend: R.trend, rs: R.rs, plan: R.plan, volume: R.volume && { avgValueM: R.volume.avgValueM }, score: R.score, drop: R.drop, bars: R.bars, receipts: R.receipts, t0: R.t0 && { plan: R.t0.plan, drop: R.t0.drop, receipts: R.t0.receipts } });
    }
    return JSON.stringify({ ...out, ...extra });
  }

  // javascript_tool output is cut at ~1.5 KB, so long JSON is put in a page overlay and read with get_page_text.
  function exportToPage(full = [], extra = {}) {
    const json = exportRun(full, extra);
    clearExport();
    const a = document.createElement('article');
    a.id = 'egx-export';
    a.style.cssText = 'position:fixed;inset:0;z-index:2147483647;overflow:auto;background:#fff;color:#000;font:12px monospace;white-space:pre-wrap;padding:8px';
    a.textContent = 'EGX-EXPORT-BEGIN\n' + json + '\nEGX-EXPORT-END';
    document.body.appendChild(a);
    return 'exported ' + json.length + ' chars: read with get_page_text, then EGX.clearExport()';
  }
  function clearExport() { const e = document.getElementById('egx-export'); if (e) e.remove(); return 'cleared'; }

  // receipts of one ticker (what egx.py check reads)
  const receipts = (tk) => { const R = S.results[tk]; return R ? { tk, daily: R.receipts || null, t0: R.t0 ? R.t0.receipts : null } : null; };

  window.EGX = { version: VERSION, open, bars, analyze, scan, deep, draw, verifyChart, intraday, drawT0, daily, receipts, page, holdings, financials, market, marketPage, candlesNow, chartRect,
    get: (tk) => S.results[tk], summary: (tk) => summary(S.results[tk]), exportRun, exportToPage, clearExport, reset: () => { S.results = {}; store('results', {}); return 'ok'; } };
})();
'EGX ' + window.EGX.version + ' ready';
