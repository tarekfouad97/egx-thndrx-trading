// builds examples/sample-run.json from synthetic bars (sample data, not real prices)
const fs=require('fs');let DATA=[];
global.window={};global.sessionStorage={getItem(){return null},setItem(){}};
global.document={querySelectorAll:(q)=>q==='iframe'?[{contentWindow:{tradingViewApi:{activeChart:()=>({exportData:async()=>({schema:[{},{sourceTitle:'Sample Co, EGX'},{},{},{},{plotId:'vol'}],data:DATA}),symbol:()=>'X'})}}}]:[]};
eval(fs.readFileSync(process.argv[2]||require('path').join(__dirname,'../skills/egx-check/scripts/egx_chart.js'),'utf8'));
function series(seed,drift,n=300,p=20){const out=[];let t=1767225600;for(let i=0;i<n;i++){const w=Math.sin(i/(7+seed))*0.018;p=p*(1+drift+w*0.35+Math.sin(i*1.3+seed)*0.005);const o=p*(1+Math.sin(i+seed)*0.004),c=p,h=Math.max(o,c)*1.012,l=Math.min(o,c)*0.988;out.push([t,o,h,l,c,3e6+((i*7919+seed*997)%2e6)]);t+=86400;}return out;}
(async()=>{
 DATA=series(0,0.0006,300,48000);await window.EGX.analyze('EGX30');
 const C=DATA.map(r=>r[4]),n=C.length,ma=(k,e=n)=>C.slice(e-k,e).reduce((a,b)=>a+b)/k;
 const idx={date:'2026-11-08',last:+C[n-1].toFixed(2),ma20:+ma(20).toFixed(2),ma50:+ma(50).toFixed(2),ma50Slope:+((ma(50)/ma(50,n-20)-1)*100).toFixed(2),ma200:+ma(200).toFixed(2),ch20:+((C[n-1]/C[n-21]-1)*100).toFixed(2),ch60:+((C[n-1]/C[n-61]-1)*100).toFixed(2),fromHigh:-4.1,regime:'Correction'};
 const stocks=[];
 for(const [tk,seed,drift,p] of (process.env.SEEDS?JSON.parse(process.env.SEEDS):[['DEMO1',1,0.0012,22],['DEMO2',2,0.0004,31],['DEMO3',3,-0.001,15],['DEMO4',4,0.002,80]])){DATA=series(seed,drift,300,p);const R=await window.EGX.analyze(tk,{history:true});R.candles=DATA.slice(-120).map(r=>[new Date(r[0]*1000).toISOString().slice(0,10),+r[1].toFixed(2),+r[2].toFixed(2),+r[3].toFixed(2),+r[4].toFixed(2)]);stocks.push(R);}
 stocks[0].verdict='valid';stocks[0].sector='Banks';stocks[0].reasons=['Price at support zone with two dated touches','R:R above 2 and stop 1-3 ATR','No red events before the order expires'];stocks[0].news=[{title:'Sample Co posts higher 9M profit (sample)',source:'Example News',url:'https://example.com/news/1',date:'2026-11-07',impact:'+',fresh:true,summary:'Profit up 20% y/y (sample item).'}];stocks[0].drawn={ok:true,made:6};
 stocks[0].page={market:'closed',cash:250.24,book:{bidPct:61,askPct:39,bestBid:22.1,bestAsk:22.14,spreadPct:0.18,side:'buyers heavier'},band:[17.7,26.5]};
 stocks[0].financials={ok:true,scores:{'الصحة المالية':'69%','النمو':'86%'},metrics:{'مضاعف الربحية':'8.4','العائد على حقوق الملكية':'21%'}};
 stocks[1].verdict='wait';stocks[1].sector='Real Estate';stocks[1].wait_for='Price to pull back to the entry and EGX30 to close above MA50';stocks[1].reasons=['Entry is more than 2 ATR below the last close'];stocks[1].news_checked=true;stocks[1].news=[];stocks[1].drawn={ok:true,made:5};
 stocks[2].verdict='not_valid';stocks[2].sector='Basic Resources';stocks[2].reasons=['Daily and weekly trend down'];stocks[2].news=[{title:'Sample Co 3 results date set (sample)',source:'Example Disclosure',url:'https://example.com/disclosure/2',date:'2026-11-06',impact:'0'}];stocks[2].red_events=[{type:'results',date:'2026-11-10',source:'Example Disclosure',url:'https://example.com/disclosure/2'}];stocks[2].drawn={ok:true,made:4};
 if(!stocks[3].drop) stocks[3].drop='rr'; stocks[3].verdict='dropped';
 const run={meta:{command:'Loop 30',created:'2026-11-08T21:30',trading_day:'2026-11-09',amount:15287,equity:50858.16,cash:250.24,risk_pct:2,user:'Sample',summary:'Sample run built from synthetic data for documentation and tests.',include_wait_orders:true},
  market:{egx30:idx,page:{gainers:108,losers:115,usdEgp:54.12,sectors:[['البنوك',-0.46],['العقارات',-0.01],['الرعاية الصحية والأدوية',5.75]]},macro:[{title:'CBE MPC meeting (sample)',source:'Example',url:'https://example.com/cbe',date:'2026-11-13'}],usd_egp:54.12},
  catalysts:[{tk:'DEMO1',company:'Sample Co',type:'expansion',summary:'New plant adds 30% capacity (sample)',source:'Example News',url:'https://example.com/news/1',date:'2026-11-05',direction:'+',moved_pct:1.2,moved_atr:0.4,priced_in:false,status:'confirmed'}],
  stocks,
  holdings:[{tk:'FUND1',qty:8176,avgPrice:1.93,price:2.02,value:16541,pnl:752,pnlPct:4.76,is_fund:true},{tk:'DEMO2',qty:20,avgPrice:30,price:31.2,value:624,pnl:24,pnlPct:4,sector:'Real Estate',action:'hold',stop:28.9,target:34.5,reasons:['Above support 29.5 (2 touches)','No sell signal'],analysis:stocks[1],news_checked:true}]};
 fs.writeFileSync(process.argv[3],JSON.stringify(run,null,1));console.log('written',process.argv[3]);
})();
