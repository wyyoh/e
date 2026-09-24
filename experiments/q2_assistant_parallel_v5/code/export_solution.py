from core import *
import csv,json,sys,hashlib
from pathlib import Path

def rows_write(out,name,rows):
 (out/(name+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
 if not rows:return
 keys=list(rows[0])
 for r in rows:
  for k in r:
   if k not in keys:keys.append(k)
 with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(tuple,list,dict)) else v for k,v in row.items()})

def produce(plan,out,label='Q2-R'):
 out.mkdir(exist_ok=True,parents=True);metrics,sch=schedule(plan,True)
 assert metrics['hard_late_boxes']==0
 seen=[i for k in plan for i in k[1]];assert sorted(seen)==list(range(len(B)))
 flights=[];stops=[];legs=[];phases=[];deliveries=[];bats=[]
 # IDs ordered by start, then actual aircraft; not an additional precedence.
 sch.sort(key=lambda x:(x['start_s'],x['aircraft'],x['task']))
 for no,s in enumerate(sch,1):
  fid=f'{label}-{no:02d}';k=s['task'];e=evaluate(k);t=T[k[0]];st=s['start_s']
  slacks=[B[i]['hard_deadline_s']-(st+v) for i,v in e['delivery'] if B[i]['hard_deadline_s'] is not None]
  flights.append({'flight_id':fid,'type':k[0],'aircraft':s['aircraft'],'battery':s['battery'],'route':['O01',*k[2],'O01'],'box_ids':[B[i]['id'] for i in k[1]],'box_count':len(k[1]),'payload_kg':e['mass'],'volume_m3':e['volume'],'start_s':st,'prep_s':e['prep'],'takeoff_s':s['takeoff_s'],'return_s':s['return_s'],'last_delivery_s':max(st+v for _,v in e['delivery']),'energy_kwh':e['energy'],'return_soc':e['soc'],'charge_duration_s':e['charge'],'charge_end_s':s['charge_end_s'],'work_s':e['duration'],'flight_s':e['flight'],'min_hard_slack_s':min(slacks) if slacks else None})
  bats.append({'flight_id':fid,'type':k[0],'aircraft':s['aircraft'],'battery':s['battery'],'task_start_s':st,'takeoff_s':s['takeoff_s'],'return_s':s['return_s'],'return_soc':e['soc'],'charge_start_s':s['return_s'],'charge_duration_s':e['charge'],'full_s':s['charge_end_s']})
  for j,l in enumerate(e['legs'],1):
   a,b=N[l['from']],N[l['to']];v=G[l['from'],l['to']];H=v['cruise_z'];begin=st+l['start_offset_s'];cur=begin
   lr={'flight_id':fid,'leg_index':j,'type':k[0],**l,'start_s':begin,'arrival_s':st+l['arrival_offset_s'],**{v0:v[v0] for v0 in ('distance_m','up_m','down_m','cruise_z')}};legs.append(lr)
   for stage,dur,p0,p1 in [('爬升',l['up_s'],(a['x'],a['y'],a['work_z']),(a['x'],a['y'],H)),('巡航',l['cruise_s'],(a['x'],a['y'],H),(b['x'],b['y'],H)),('下降',l['down_s'],(b['x'],b['y'],H),(b['x'],b['y'],b['work_z']))]:
    phases.append({'flight_id':fid,'leg_index':j,'from':a['id'],'to':b['id'],'stage':stage,'start_s':cur,'end_s':cur+dur,'x0':p0[0],'y0':p0[1],'z0':p0[2],'x1':p1[0],'y1':p1[1],'z1':p1[2],'payload_kg':l['payload_kg']});cur+=dur
   assert abs(cur-(st+l['arrival_offset_s']))<1e-7
  for sp in e['stops']:
   stops.append({'flight_id':fid,'site':sp['site'],'box_count':len(sp['ids']),'arrival_s':st+sp['arrival_offset_s'],'delivery_s':st+sp['delivery_offset_s'],'box_ids':[B[i]['id'] for i in sp['ids']]})
  for i,v in e['delivery']:
   b=B[i];tm=st+v;hard=b['hard_deadline_s'];late=max(0,tm-b['expected_delivery_s'])
   deliveries.append({**b,'flight_id':fid,'aircraft':s['aircraft'],'battery':s['battery'],'delivery_s':tm,'hard_slack_s':None if hard is None else hard-tm,'tardiness_s':late,'weighted_tardiness_s':b['priority']*late})
 deliveries.sort(key=lambda x:x['id'])
 metrics['used_aircraft']=len({x['aircraft'] for x in flights});metrics['used_batteries']=len({x['battery'] for x in flights})
 metrics['leg_count']=len(legs);metrics['phase_count']=len(phases)
 for name,rows in [('flights',flights),('deliveries',deliveries),('legs',legs),('phases',phases),('stops',stops),('battery_cycles',bats)]:rows_write(out,name,rows)
 (out/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2,allow_nan=False))
 (out/'decisions.json').write_text(json.dumps(as_decisions(plan),ensure_ascii=False,indent=2))
 return metrics

if __name__=='__main__':
 p=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/best.json';d=json.loads(p.read_text());plan=from_decisions(d['decisions'])
 print(produce(plan,ROOT/'results/main'))
