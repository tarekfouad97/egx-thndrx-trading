"""Render a clearly labelled synthetic design preview, without writing trading memory."""
import copy
import json
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/egx-check/scripts'))
import egx
import egx_page
run=json.loads((ROOT/'examples/sample-run.json').read_text())
run['meta'].update(demo=True,cash=20000,summary='Illustrative session: one planned allocation, one watchlist idea. Remaining capital stays in cash.',include_wait_orders=False)
for s in run['stocks']:
    s['verdict']='dropped' if s.get('drop') else 'valid' if s['tk']=='DEMO1' else 'wait'
    s.pop('gates',None)
    s['_shot_uri']=egx_page.img_uri(ROOT / s.get('screenshot',''))
    if s['tk']=='DEMO1':
        s.pop('_shot_uri',None)  # target is changed for this illustrative plan
        s['plan']['target']=41
        s['plan']['rr']=round((41-s['plan']['entry'])/(s['plan']['entry']-s['plan']['stop']),2)
        s['reasons']=['Synthetic support scenario with a defined invalidation level.','حجم الصفقة محسوب بعد الرسوم والانزلاق السعري. الأرقام للتوضيح فقط.','Recheck the live quote and disclosures before considering an order.']
    if s['tk']=='DEMO2': s['wait_for']='Price to return to support; rerun the full check before allocating.'
    if s.get('_shot_uri'): s['_shot_time']='· synthetic screenshot'
egx.allocate(run,copy.deepcopy(egx.DEFAULT_CONFIG))
path=ROOT/'examples/report-preview.html'
path.write_text(egx_page.build_html(run,egx.DEFAULT_CONFIG,path.name,egx.VERSION),encoding='utf-8')
print(path)
