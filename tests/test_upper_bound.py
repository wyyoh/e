from pathlib import Path
import sys,json,copy,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from verify_upper_bound import verify

def main():
 d=json.loads((ROOT/'data/baseline.json').read_text());out=[]
 r,_,_=verify(ROOT/'data/baseline.json');assert r['failed']==0
 for case in ['duplicate_box','wrong_battery_type','negative_start','teleport_return','resource_overlap']:
  x=copy.deepcopy(d)
  if case=='duplicate_box':x['flights'][0]['box_ids'][0]=x['flights'][0]['box_ids'][1]
  if case=='wrong_battery_type':x['flights'][0]['battery']='C-BAT99'
  if case=='negative_start':x['flights'][0]['start_s']=-1.
  if case=='teleport_return':x['flights'][0]['return_s']=0.
  if case=='resource_overlap':
   rid=x['flights'][0]['aircraft'];j=next(j for j in x['flights'][1:] if j['aircraft']==rid);j['start_s']=0.
  with tempfile.TemporaryDirectory() as z:
   p=Path(z)/'bad.json';p.write_text(json.dumps(x));r,_,_=verify(p);caught=r['failed']>0
  assert caught,case;out.append({'case':case,'rejected':caught})
 (ROOT/'results/upper_bound_negative_tests.json').write_text(json.dumps(out,indent=2));print('upper-bound negative tests PASS',len(out))
if __name__=='__main__':main()
