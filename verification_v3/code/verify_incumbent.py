"""Independent direct verification of repository CSV: no scheduling decoder used.
Uses the published numeric geometry snapshot, not a fresh DEM extraction.
"""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,math,hashlib
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data';OUT=ROOT/'results'
def run():
 load=lambda n:json.loads((DATA/(n+'.json')).read_text())
 boxes={b['id']:b for b in load('boxes')};types={t['id']:t for t in load('types')};nodes={n['id']:n for n in load('nodes')};geo={(l['from'],l['to']):l for l in load('legs')}
 raw=(DATA/'remote_v2_incumbent.csv').read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 assert blob=='0afb0cf4f8108cea601cb5831b64610c895e422e'
 rows=list(csv.DictReader(raw.decode().splitlines()));used=Counter();flights=[];deliveries=[];legs=[];cycles=[];phases=[];ac=defaultdict(list);ba=defaultdict(list);checks=0
 def require(ok,message):
  nonlocal checks
  checks+=1
  if not ok:raise AssertionError(message)
 def close(a,b,name):require(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-7,name)
 for r in rows:
  fid=r['flight_id'];t=types[r['type']];ids=r['box_ids'].split('|');route=r['route'].split('|');start=float(r['start_s']);used.update(ids)
  require(start>=0,fid+' start');require(r['aircraft'] in t['aircraft'],fid+' aircraft');require(r['battery'] in [t['id']+f'-BAT{i+1:02d}' for i in range(t['battery_count'])],fid+' battery type')
  require(route[0]==route[-1]=='O01',fid+' return');require(set(route[1:-1])=={boxes[b]['site'] for b in ids},fid+' route delivery');require(len(set(route[1:-1]))==len(route[1:-1]),'CSV instance has no repeats; verifier scope is this incumbent only')
  mass=sum(boxes[b]['mass_kg'] for b in ids);volume=sum(round(boxes[b]['volume_m3']*1000) for b in ids)/1000
  require(mass<=t['max_payload_kg'] and volume<=t['max_volume_m3']+1e-12,fid+' capacity')
  prep=t['prep_s']+len(ids)*t['load_per_box_s'];now=start+prep;takeoff=now;energy=0.;q=mass;pure=0.;last_del=None;hard=[]
  for i,(a,b) in enumerate(zip(route[:-1],route[1:]),1):
   l=geo[a,b];H=l['max_dem_m']+50;up=H-nodes[a]['work_z'];down=H-nodes[b]['work_z'];require(up>=0 and down>=0,fid+' heights');close(up,l['up_m'],fid+' up binding');close(down,l['down_m'],fid+' down binding')
   durations=[up/t['up_mps'],l['distance_m']/t['cruise_mps'],down/t['down_mps']];time=sum(durations)
   L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
   # Reconstruct Watts and integrate time, independent of stored segment energy.
   power=t['battery_kwh']*3600000*t['cruise_mps']/L
   horizontal=power*durations[1]/3600000;climb=(t['empty_mass_kg']+q)*9.81*up/(t['up_efficiency']*3600000);e=horizontal+climb
   legs.append({'flight_id':fid,'leg':i,'from':a,'to':b,'payload_kg':q,'departure_s':now,'arrival_s':now+time,'flight_s':time,'horizontal_kwh':horizontal,'climb_kwh':climb,'energy_kwh':e});energy+=e;pure+=time
   endpoints=[(nodes[a]['x'],nodes[a]['y'],nodes[a]['work_z']),(nodes[a]['x'],nodes[a]['y'],H),(nodes[b]['x'],nodes[b]['y'],H),(nodes[b]['x'],nodes[b]['y'],nodes[b]['work_z'])]
   for k,(name,dt) in enumerate(zip(['climb','cruise','descent'],durations)):
    phases.append({'flight_id':fid,'leg':i,'kind':name,'start_s':now,'end_s':now+dt,'p0':endpoints[k],'p1':endpoints[k+1]});now+=dt
   if b!='O01':
    bids=[bid for bid in ids if boxes[bid]['site']==b];now+=t['handover_base_s']+len(bids)*t['handover_per_box_s'];last_del=now
    for bid in bids:
     x=boxes[bid];due=x['hard_deadline_s'];require(due is None or now<=due+1e-7,fid+' hard '+bid);late=max(0.,now-x['expected_delivery_s'])
     deliveries.append({'id':bid,'site':b,'flight_id':fid,'delivery_s':now,'expected_s':x['expected_delivery_s'],'hard_deadline_s':due,'lateness_s':late,'weighted_lateness_s':x['priority']*late})
     if due is not None:hard.append(due-now)
    q-=sum(boxes[bid]['mass_kg'] for bid in bids)
  require(q==0,fid+' empty return');budget=(1-t['reserve_pct']/100)*t['battery_kwh'];require(energy<=budget+1e-10,fid+' energy')
  soc=1-energy/t['battery_kwh'];charge=t['charge_full_s']*(.65*max(0,.9-soc)/.9+.35*(1-max(.9,soc))/.1)
  ac[r['aircraft']].append((start,now,fid));ba[r['battery']].append((start,now+charge,fid))
  flights.append({'flight_id':fid,'type':t['id'],'aircraft':r['aircraft'],'battery':r['battery'],'box_ids':ids,'route':route,'start_s':start,'takeoff_s':takeoff,'return_s':now,'last_delivery_s':last_del,'energy_kwh':energy,'soc':soc,'charge_s':charge,'full_s':now+charge,'payload_kg':mass,'volume_m3':volume,'work_s':now-start,'flight_s':pure,'min_hard_slack_s':min(hard) if hard else None})
  cycles.append({'flight_id':fid,'battery':r['battery'],'start_s':start,'return_s':now,'charge_s':charge,'full_s':now+charge})
 require(used==Counter(boxes.keys()), 'all 80 boxes exactly once')
 for name,tracks in [('aircraft',ac),('battery',ba)]:
  for rid,ints in tracks.items():
   ints.sort()
   for prev,nxt in zip(ints,ints[1:]):require(nxt[0]>=prev[1]-1e-7,f'{name} conflict {rid} {prev[2]} {nxt[2]}')
 metrics={'makespan_s':max(f['return_s'] for f in flights),'energy_kwh':sum(f['energy_kwh'] for f in flights),'sorties':len(flights),'last_delivery_s':max(d['delivery_s'] for d in deliveries),'weighted_tardiness_s':sum(d['weighted_lateness_s'] for d in deliveries),'late_boxes':sum(d['lateness_s']>1e-7 for d in deliveries),'min_return_soc':min(f['soc'] for f in flights),'min_hard_slack_s':min(d['hard_deadline_s']-d['delivery_s'] for d in deliveries if d['hard_deadline_s'] is not None),'used_aircraft':len(ac),'used_batteries':len(ba),'type_counts':dict(Counter(f['type'] for f in flights)),'checks':checks,'failed':0}
 out=OUT/'independent_csv';out.mkdir(parents=True,exist_ok=True)
 for key,obj in [('flights',flights),('deliveries',deliveries),('legs',legs),('battery_cycles',cycles),('phases',phases),('metrics',metrics)]:
  (out/(key+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(metrics,ensure_ascii=False,indent=2));return metrics
if __name__=='__main__':run()
