"""Unmodified Q1/Q2 physics, applied to remaining load on every route leg."""
import math

class Model:
    def __init__(self,data):
        self.data=data;self.boxes=data['boxes'];self.types=data['types'];self.geo=data['geo'];self.nodes=data['nodes']
    def job(self,typ,ids,route,fid='candidate'):
        ids=sorted(ids);route=list(route)
        if route and route[0]=='O01':route=route[1:-1]
        if len(ids)!=len(set(ids)) or set(route)!={self.boxes[b]['site'] for b in ids} or len(set(route))!=len(route):
            raise ValueError('Invalid boxes/route')
        t=self.types[typ];mass=sum(self.boxes[b]['mass_kg'] for b in ids)
        vl=sum(round(self.boxes[b]['volume_m3']*1000) for b in ids)
        failures=[]
        if mass>t['max_payload_kg']:failures.append('mass')
        if vl>round(t['max_volume_m3']*1000):failures.append('volume')
        if failures:return dict(type=typ,box_ids=ids,route=route,feasible=False,failures=failures)
        now=t['prep_s']+len(ids)*t['load_per_box_s'];prep=now;energy=0.;q=mass;legs=[];deliveries={};flight=0.;handover=0.
        full=['O01']+route+['O01']
        for a,b in zip(full,full[1:]):
            dist,z=self.geo[a,b];up=z+50-self.nodes[a]['work_z'];down=z+50-self.nodes[b]['work_z']
            if up<0 or down<0:raise ValueError('Cruise altitude below work altitude')
            length=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
            horizontal=t['battery_kwh']*dist/length
            climb=(t['empty_mass_kg']+q)*9.81*up/(t['up_efficiency']*3.6e6)
            dt=up/t['up_mps']+dist/t['cruise_mps']+down/t['down_mps']
            legs.append(dict(origin=a,destination=b,distance_m=dist,max_dem_m=z,up_m=up,down_m=down,payload_kg=q,flight_s=dt,departure_offset_s=now,arrival_offset_s=now+dt,energy_kwh=horizontal+climb))
            now+=dt;flight+=dt;energy+=horizontal+climb
            if b!='O01':
                bs=[i for i in ids if self.boxes[i]['site']==b]
                hand=t['handover_base_s']+len(bs)*t['handover_per_box_s'];handover+=hand;now+=hand
                for bid in bs:deliveries[bid]=now
                q-=sum(self.boxes[i]['mass_kg'] for i in bs)
        assert q==0 and legs[-1]['payload_kg']==0
        soc=1-energy/t['battery_kwh'];budget=(1-t['reserve_pct']/100)*t['battery_kwh']
        if energy>budget+1e-10:failures.append('energy')
        latest=min(min(self.boxes[b]['expected_delivery_s'],self.boxes[b]['hard_deadline_s'] or math.inf)-off for b,off in deliveries.items())
        if latest < -1e-7:failures.append('deadline_necessary')
        charge=t['charge_full_s']*(.65*max(0.,.9-soc)/.9+.35*(1-max(.9,soc))/.1)
        return dict(flight_id=fid,type=typ,box_ids=ids,route=route,payload_kg=mass,volume_m3=vl/1000,energy_kwh=energy,return_soc=soc,energy_budget_kwh=budget,duration_s=now,prep_load_s=prep,flight_s=flight,handover_s=handover,charge_s=charge,latest_start_s=latest,delivery_offsets=deliveries,legs=legs,feasible=not failures,failures=failures)

def workloads(jobs,types):
    return {g:sum(j['duration_s'] for j in jobs if j['type']==g) for g in types}

def partition_bound(jobs,types,cap=None):
    """Exact identical-machine partition bound; ignores batteries and deadlines.
    Branch pruning only by incumbent maximum load and identical-machine symmetry.
    """
    ans={}
    for g,t in types.items():
        ds=sorted([j['duration_s'] for j in jobs if j['type']==g],reverse=True)
        loads=[0.]*len(t['aircraft'])
        for p in ds:loads[loads.index(min(loads))]+=p
        best=max(loads,default=0.)
        loads=[0.]*len(loads)
        def visit(k):
            nonlocal best
            if k==len(ds):best=min(best,max(loads));return
            seen=[]
            for i,v in enumerate(loads):
                if any(abs(v-w)<1e-9 for w in seen):continue
                seen.append(v)
                if v+ds[k]>=best-1e-9:continue
                loads[i]+=ds[k];visit(k+1);loads[i]-=ds[k]
        visit(0);ans[g]=best
    return ans
