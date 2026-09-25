"""One-command fresh-input verification of all delivered witnesses and tables."""
from common import *
from replay import verify
from search import internal_check
from physics import Model
import csv,subprocess,sys

def main():
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'src/raw_audit.py')],check=True)
    reports={}
    for name in ['baseline','best','feasible_22']:
        p=load(ROOT/f'results/{name}_incumbent.json');internal=internal_check(p['flights'],Model(inputs()));r,flights,boxes,*_=verify(p)
        assert r['failed']==0;r['internal_recomputed']=internal;reports[name]=r
        if name=='best':
            with (ROOT/'results/box_assignment.csv').open(encoding='utf-8',newline='') as f:stored={b['box_id']:b for b in csv.DictReader(f)}
            assert set(stored)=={b['box_id'] for b in boxes}
            for b in boxes:
                assert stored[b['box_id']]['flight_id']==b['flight_id']
                assert abs(float(stored[b['box_id']]['delivery_s'])-b['delivery_s'])<1e-7
    save(ROOT/'results/release_validation.json',reports)
    print({k:dict(checks=v['checks'],failed=v['failed'],makespan_s=v['metrics']['makespan_s']) for k,v in reports.items()})
if __name__=='__main__':main()
