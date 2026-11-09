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
 *   await EGX.deep('COMI', {draw:true})      // open + full analysis + drawings + panels
 *   EGX.page()                               // cash, market status, order book, price band
 *   EGX.holdings()                           // current investments grid
 *   await EGX.financials()                   // البيانات المالية tab values
 *   EGX.get('COMI') / EGX.exportRun([...])   // stored results as JSON
 *
 * Every number is rounded; every level carries the bar dates it came from.
 * Rules are documented in references/analysis-rules.md (keep both in sync).
 */
(function () {
  if (window.EGX && window.EGX.version === '2.0.3') return;
  const VERSION = '2.0.4';
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

  const S = { results: load('results') || {}, index: load('index') || null, market: load('market') || null };

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
            return { ok: true, tk, title: d.title, bars: d.B.length, headerMatch: head.includes(tk) };
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
    const R = { tk, title, v: VERSION, asOf: n ? dt(B[n - 1].t) : null, bars: n, flags: [], evidence: [] };
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
    // draw spec
    R.draw = drawSpec(R);
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

  function drawSpec(R) {
    const L = [], p = R.plan, z = R.zones;
    if (z.support) L.push({ price: z.support.lo, text: `${MARK}دعم ${z.support.lo}-${z.support.hi} (${z.support.touches.map((x) => x.slice(5, 10)).join('، ')})`, color: '#f5a623', style: 2 });
    (z.resistance || []).slice(0, 2).forEach((r) => L.push({ price: r.lo, text: `${MARK}مقاومة ${r.lo}-${r.hi} (${r.n} لمسات)`, color: '#e74c3c', style: 2 }));
    if (p) {
      L.push({ price: p.entry, text: `${MARK}دخول ${p.entry}`, color: '#3498db', style: 0 });
      L.push({ price: p.stop, text: `${MARK}وقف ${p.stop}`, color: '#e74c3c', style: 0 });
      if (p.target) L.push({ price: p.target, text: `${MARK}هدف ${p.target}`, color: '#2ecc71', style: 0 });
      if (p.target2) L.push({ price: p.target2, text: `${MARK}هدف 2 ${p.target2}`, color: '#2ecc71', style: 2 });
    }
    const t = z.trendline && { pts: [z.trendline.from, z.trendline.to], text: MARK + (z.trendline.kind === 'rising-support' ? 'خط اتجاه صاعد' : 'قمم هابطة'), color: '#f5a623' };
    return { lines: L, trend: t };
  }

  async function draw(tk, { clear = true } = {}) {
    const R = S.results[tk]; if (!R || !R.draw) return { ok: false, error: 'analyse first' };
    const ch = chart(); let removed = 0;
    if (clear) for (const s of ch.getAllShapes()) { try { const pr = ch.getShapeById(s.id).getProperties(); if (String(pr.text || '').startsWith(MARK)) { ch.removeEntity(s.id); removed++; } } catch (e) {} }
    const { B } = await bars(); const t = B[B.length - 1].t; let made = 0;
    for (const l of R.draw.lines) { await ch.createShape({ time: t, price: l.price }, { shape: 'horizontal_line', text: l.text, overrides: { linecolor: l.color, textcolor: l.color, showLabel: true, linestyle: l.style, linewidth: 2, horzLabelsAlign: 'right', fontsize: 12 } }); made++; }
    if (R.draw.trend) { const toT = (s) => Date.parse(s + 'T00:00:00Z') / 1000; await ch.createMultipointShape(R.draw.trend.pts.map(([d, p]) => ({ time: toT(d), price: p })), { shape: 'trend_line', text: R.draw.trend.text, overrides: { linecolor: R.draw.trend.color, linewidth: 2, extendRight: true, showLabel: true, textcolor: R.draw.trend.color } }); made++; }
    try { ch.setVisibleRange({ from: t - 200 * 86400, to: t + 10 * 86400 }); } catch (e) {}
    return { ok: true, made, removed };
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
    const o = await open('EGX30');
    const { B } = await bars(); const C = B.map((b) => b.c), n = C.length;
    if (n < 210) return { ok: false, error: 'EGX30 chart not loaded', open: o };
    const ma = (k, end = n) => C.slice(end - k, end).reduce((a, b) => a + b, 0) / k;
    const ma50 = ma(50), ma50p = ma(50, n - 20), ma200 = ma(200), ma20 = ma(20), last = C[n - 1];
    const rising = ma50 > ma50p;
    const regime = last > ma50 && rising && last > ma200 ? 'Up' : last < ma50 && !rising && last < ma200 ? 'Down' : 'Correction';
    const hi = Math.max(...B.map((b) => b.h));
    const { PH, PL } = pivots(B, n - 130);
    S.index = { spark: C.slice(-60).map((x) => r2(x)), date: dt(B[n - 1].t), last: r2(last), ma20: r2(ma20), ma50: r2(ma50), ma50Slope: r2((ma50 / ma50p - 1) * 100), ma200: r2(ma200), ch20: r2((last / C[n - 21] - 1) * 100), ch60: r2((last / C[n - 61] - 1) * 100), fromHigh: r2((last / hi - 1) * 100), regime, lastHighs: PH.slice(-2).map((p) => [p.d, r2(p.p)]), lastLows: PL.slice(-2).map((p) => [p.d, r2(p.p)]) };
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
    try { return summary(await analyze(tk, opts)); } catch (e) { return `${tk} | UNKNOWN (${e.message})`; }
  }

  async function deep(tk, opts = {}) {
    const o = await open(tk); if (!o.ok && !opts.alreadyOpen) return { ok: false, ...o };
    const R = await analyze(tk, { ...opts, history: true });
    R.page = page();
    if (opts.financials !== false) R.financials = await financials();
    R.candles = await candlesNow(120);
    if (opts.draw !== false && R.draw) R.drawn = await draw(tk);
    return save(tk, R);
  }

  async function candlesNow(k = 120) { const { B } = await bars(); return B.slice(-k).map((b) => [dt(b.t), tick(b.o), tick(b.h), tick(b.l), tick(b.c)]); }

  // export stored results; full detail for `full` tickers, summary rows for the rest
  function exportRun(full = [], extra = {}) {
    const out = { egxjs: VERSION, index: S.index, stocks: [] };
    for (const [tk, R] of Object.entries(S.results)) {
      if (full.includes(tk)) out.stocks.push(R);
      else out.stocks.push({ tk, title: R.title, last: R.last, chg: R.chg, spark: R.spark, trend: R.trend, rs: R.rs, plan: R.plan, volume: R.volume && { avgValueM: R.volume.avgValueM }, score: R.score, drop: R.drop, bars: R.bars });
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

  window.EGX = { version: VERSION, open, bars, analyze, scan, deep, draw, page, holdings, financials, market, marketPage, candlesNow, chartRect,
    get: (tk) => S.results[tk], summary: (tk) => summary(S.results[tk]), exportRun, exportToPage, clearExport, reset: () => { S.results = {}; store('results', {}); return 'ok'; } };
})();
'EGX ' + window.EGX.version + ' ready';
