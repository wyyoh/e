"""Count ALL bounded cargo multisets before route ordering, no energy pruning.
The strict grouping key preserves deadlines, priority and first-batch status.
This count is a diagnostic, not a count of feasible complete sorties.
"""
from pathlib import Path
from collections import Counter
import json, time, numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main():
    boxes=json.loads((ROOT/'data/boxes.json').read_text())
    types=json.loads((ROOT/'data/types.json').read_text())
    keys=['site','kind','mass_kg','volume_m3','first_batch','first_deadline_s','expected_delivery_s','priority','hard_deadline_s']
    strict=Counter(tuple(b[k] for k in keys) for b in boxes)
    physical=Counter((b['site'],b['kind'],b['mass_kg'],round(b['volume_m3']*1000)) for b in boxes)
    result={'boxes':len(boxes),'strict_classes':len(strict),'physical_classes':len(physical),'count_meaning':'unordered bounded cargo multisets, capacity-only, excluding empty; not routes or energy-feasible trips','types':{}}
    for g in types:
        Q=g['max_payload_kg'];V=round(g['max_volume_m3']*1000);start=time.monotonic()
        # Object integers avoid overflow and prove the count exactly.
        a=np.zeros((Q+1,V+1),dtype=object);a[0,0]=1
        for key,count in strict.items():
            w=int(key[2]);v=round(key[3]*1000);b=a.copy()
            for k in range(1,min(count,Q//w,V//v)+1):
                b[k*w:,k*v:]+=a[:-k*w,:-k*v]
            a=b
        result['types'][g['id']]={'cargo_multisets':int(a.sum())-1,'seconds':time.monotonic()-start}
    # Terrain times are generally NON-METRIC. Check whether shortcutting is safe.
    legs=json.loads((ROOT/'data/legs.json').read_text());nodes=['O01']+sorted({b['site'] for b in boxes});idx={n:i for i,n in enumerate(nodes)}
    violations=[]
    for g in types:
        t=np.zeros((16,16));e=np.zeros((16,16))
        for l in legs:
            a,b=idx[l['from']],idx[l['to']]
            t[a,b]=l['up_m']/g['up_mps']+l['distance_m']/g['cruise_mps']+l['down_m']/g['down_mps']
            e[a,b]=g['battery_kwh']*l['distance_m']/g['empty_range_m']+g['empty_mass_kg']*9.81*l['up_m']/(g['up_efficiency']*3600000)
        best=None
        for a in range(16):
            for b in range(16):
                for c in range(1,16):
                    if len({a,b,c})<3:continue
                    # Includes a base handover at the intermediate node.
                    delta=t[a,b]-(t[a,c]+t[c,b]+g['handover_base_s'])
                    if best is None or delta>best['time_saving_s']:
                        best={'type':g['id'],'from':nodes[a],'via':nodes[c],'to':nodes[b],
                         'direct_flight_s':t[a,b],'via_flight_plus_base_service_s':t[a,c]+t[c,b]+g['handover_base_s'],
                         'time_saving_s':delta,'direct_empty_energy_kwh':e[a,b],'via_empty_energy_kwh':e[a,c]+e[c,b]}
        violations.append(best)
    result['shortcut_audit']=violations
    result['elementary_route_dominance_proved']=False
    (ROOT/'results/enumeration_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
