// Node harness: run egx_chart.js analyze() on synthetic series with a mocked chart.
const fs=require('fs'), assert=require('node:assert/strict');
let DATA=[];
global.window={}; global.sessionStorage={getItem(){return null},setItem(){}};
global.document={querySelectorAll:(q)=>q==='iframe'?[{contentWindow:{tradingViewApi:{activeChart:()=>({exportData:async()=>({schema:[{},{sourceTitle:'TEST, EGX'},{},{},{},{plotId:'vol'}],data:DATA}),symbol:()=>'X'})}}}]:[]};
eval(fs.readFileSync(process.argv[2]||require('path').join(__dirname,'../skills/egx-check/scripts/egx_chart.js'),'utf8'));
function series(kind,n=300){const out=[];let p=20,t=1767225600;for(let i=0;i<n;i++){const drift=kind==='up'?0.004:kind==='down'?-0.004:kind==='ath'?0.006:0;const w=Math.sin(i/9)*0.02;p=p*(1+drift+w*0.3+(Math.sin(i*1.7)*0.004));const o=p*(1+Math.sin(i)*0.003),c=p,h=Math.max(o,c)*1.01,l=Math.min(o,c)*0.99;out.push([t,o,h,l,c,500000+((i*7919)%300000)]);t+=86400;}return out;}
(async()=>{
 for(const k of ['up','down','side','ath','short']) {
  DATA=series(k,k==='short'?40:300);
  const R=await window.EGX.analyze('T'+k,{history:true});
  assert.equal(R.bars,DATA.length);
  if(k==='short') assert.equal(R.drop,'new');
  else {
   assert.ok(Number.isFinite(R.atr) && R.atr>0);
   assert.ok(R.momentum.rsi>=0 && R.momentum.rsi<=100);
   if(R.history) assert.equal(R.history.predictive,false);
   assert.equal(R.rs.rs20,undefined,'no benchmark must not create RS');
  }
 }
 DATA=series('side');DATA[100][0]=DATA[99][0];
 await assert.rejects(window.EGX.analyze('BAD'),/timestamps/);
 DATA=series('side');DATA[100][2]=0;
 await assert.rejects(window.EGX.analyze('BAD'),/OHLCV/);
 DATA=series('side');DATA[100][4]=NaN;
 await assert.rejects(window.EGX.analyze('BAD'),/OHLCV/);
 DATA=series('side').map(r=>[r[0],20,20.1,19.9,20,r[5]]);
 assert.equal((await window.EGX.analyze('FLAT')).momentum.rsi,50);
 console.log('PASS analysis assertions: series, missing benchmark, retrospective history, malformed bars, flat RSI');
})().catch(e=>{console.error(e);process.exitCode=1;});
