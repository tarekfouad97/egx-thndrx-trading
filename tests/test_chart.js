// Node harness: run egx_chart.js analyze() on synthetic series with a mocked chart.
const fs=require('fs');
let DATA=[];
global.window={}; global.sessionStorage={getItem(){return null},setItem(){}};
global.document={querySelectorAll:(q)=>q==='iframe'?[{contentWindow:{tradingViewApi:{activeChart:()=>({exportData:async()=>({schema:[{},{sourceTitle:'TEST, EGX'},{},{},{},{plotId:'vol'}],data:DATA}),symbol:()=>'X'})}}}]:[]};
eval(fs.readFileSync(process.argv[2]||require('path').join(__dirname,'../skills/egx-check/scripts/egx_chart.js'),'utf8'));
function series(kind,n=300){const out=[];let p=20,t=1767225600;for(let i=0;i<n;i++){const drift=kind==='up'?0.004:kind==='down'?-0.004:kind==='ath'?0.006:0;const w=Math.sin(i/9)*0.02;p=p*(1+drift+w*0.3+(Math.sin(i*1.7)*0.004));const o=p*(1+Math.sin(i)*0.003),c=p,h=Math.max(o,c)*1.01,l=Math.min(o,c)*0.99;out.push([t,o,h,l,c,500000+((i*7919)%300000)]);t+=86400;}return out;}
(async()=>{for(const k of ['up','down','side','ath','short']){DATA=series(k,k==='short'?40:300);try{const R=await window.EGX.analyze('T'+k);console.log(k,'|',window.EGX.summary('T'+k),'| flags',R.flags.join(';'))}catch(e){console.log(k,'ERROR',e.stack.split('\n').slice(0,3).join(' '))}}})();
