"""Reconstruct attachment parameters and continuous AEQD raster geometry.

Event traversal and independent strip-interval intersection use different inverse
implementations (PROJ / GeographicLib). No Bresenham or sampled DEM maxima.
"""
from common import *
import math,itertools
import numpy as np
import openpyxl,tifffile
from scipy.io import loadmat
from scipy.optimize import brentq
from pyproj import CRS,Transformer
from geographiclib.geodesic import Geodesic

def spreadsheet_inputs():
    raw=ROOT/'data/raw'
    def rows(name,sheet=0):
        w=openpyxl.load_workbook(raw/name,read_only=True,data_only=True);out=list(w.worksheets[sheet].values);w.close();return out
    nodes={r[0]:dict(id=r[0],name=r[1],lon=r[2],lat=r[3],elevation_m=r[4],work_z=r[4]+(0 if r[0]=='O01' else 30)) for r in rows('调度中心与服务区.xlsx') if isinstance(r[0],str) and (r[0]=='O01' or r[0].startswith('S0'))}
    fields=['id','name','empty_mass_kg','max_payload_kg','max_volume_m3','cruise_mps','empty_range_m','full_range_m','battery_kwh','reserve_pct','prep_s','load_per_box_s','handover_base_s','handover_per_box_s','up_mps','down_mps','up_efficiency','down_efficiency']
    ar=rows('运输无人机数据.xlsx');head=next(i for i,r in enumerate(ar) if r[0]=='机型编号' and r[2]=='含电池空载总质量（kg）')
    types={r[0]:dict(zip(fields,r[:18])) for r in ar[head+1:head+4]}
    bh=next(i for i,r in enumerate(ar) if r[0]=='机型编号' and r[1]=='共享电池组总数（组）')
    for g,t in types.items():
        t['aircraft']=[r[0] for r in ar if isinstance(r[0],str) and r[0].startswith('U0') and r[1]==g]
        br=next(r for r in ar[bh+1:] if r[0]==g);t['battery_count']=br[1];t['charge_full_s']=br[2]
    boxes={}
    for r in rows('物资需求与配送时限.xlsx',1)[1:]:
        if not r[0]:continue
        b=dict(zip(['id','site','kind','mass_kg','volume_m3','first_batch','first_deadline_s','expected_delivery_s','priority'],r[:9]))
        hard=([b['expected_delivery_s']] if b['kind']=='医疗物资' else [])+([b['first_deadline_s']] if b['first_batch']=='是' else [])
        b['hard_deadline_s']=min(hard) if hard else None;boxes[b['id']]=b
    assert len(boxes)==80 and len(nodes)==16
    return dict(nodes=nodes,types=types,boxes=boxes)

class Raster:
    def __init__(self):
        raw=ROOT/'data/raw'
        with tifffile.TiffFile(raw/'镇龙乡及周边30米DEM.tif') as f:self.z=f.asarray();meta=f.geotiff_metadata
        mat=loadmat(raw/'镇龙乡及周边30米DEM.mat');assert np.array_equal(self.z,mat['dem'])
        assert meta['GeographicTypeGeoKey']==4326 and meta['GTRasterTypeGeoKey']==2
        self.dx,self.sy,_=meta['ModelPixelScale'];tie=meta['ModelTiepoint'];self.x0=tie[3]-self.dx/2;self.y0=tie[4]+self.sy/2
        assert np.allclose(mat['transform'].ravel(),[self.dx,0,self.x0,0,-self.sy,self.y0],atol=1e-11,rtol=0)
        self.nodata=float(mat['nodata'][0,0])
    def pixel(self,lon,lat):return np.stack(((np.asarray(lon)-self.x0)/self.dx,(self.y0-np.asarray(lat))/self.sy),axis=-1)
    def max(self,cells):
        assert all(0<=r<self.z.shape[0] and 0<=c<self.z.shape[1] for r,c in cells)
        h=[float(self.z[r,c]) for r,c in cells];assert all(v!=self.nodata and math.isfinite(v) for v in h)
        return max(h)

def touching(xy):
    def inds(v):
        k=round(v);return [k-1,k] if abs(v-k)<1e-8 else [math.floor(v)]
    return {(r,c) for c in inds(xy[0]) for r in inds(xy[1])}

class Curve:
    def __init__(self,a,b,origin,raster,forward,inverse):
        self.raster=raster;self.origin=origin;self.inverse=inverse
        self.a=np.array(forward.transform(a['lon'],a['lat']));self.b=np.array(forward.transform(b['lon'],b['lat']))
        self.delta=self.b-self.a;self.distance=float(np.linalg.norm(self.delta));self.ends=[self.pixel(0),self.pixel(1)]
        # Refuse nearly axis-aligned curves: these need explicit extrema splitting.
        # On this local (<10 km, |lat|<24 deg) AEQD patch, a conservative bound on
        # the inverse differential's EN-frame deviation is 4*r/(Rmin*cos(24deg)).
        # Rmin=6e6 m is below all WGS84 curvature radii. Frame rotation is first
        # order; radial scale error is second order. Positive diagonal conversion
        # to lon/lat does not change signs. Endpoint radius bounds the whole line.
        radius=max(np.linalg.norm(self.a),np.linalg.norm(self.b))
        bound=4*radius/(6e6*math.cos(math.radians(24)))
        self.monotonic_margin=float(min(abs(self.delta))/self.distance-bound)
        if radius>10000 or max(abs(a['lat']),abs(b['lat']))>=24 or self.monotonic_margin<=0:
            raise ValueError('Outside certified monotone local-patch scope; split at extrema first')
    def pixel(self,t):
        xy=self.a+np.asarray(t)[...,None]*self.delta;lon,lat=self.inverse.transform(xy[...,0],xy[...,1]);return self.raster.pixel(lon,lat)
    def independent(self,t):
        x,y=self.a+t*self.delta
        g=Geodesic.WGS84.Direct(self.origin['lat'],self.origin['lon'],math.degrees(math.atan2(x,y)),math.hypot(x,y))
        return self.raster.pixel(g['lon2'],g['lat2'])
    def cells(self):
        ts={0.,1.}
        for k in range(2):
            lo,hi=sorted([a[k] for a in self.ends])
            for edge in range(math.ceil(lo),math.floor(hi)+1):ts.add(brentq(lambda t:self.pixel(t)[k]-edge,0,1,xtol=5e-15))
        ts=sorted(ts);cells=set()
        for t in ts+[(u+v)/2 for u,v in zip(ts,ts[1:])]:cells.update(touching(self.pixel(t)))
        return cells
    def strip_cells(self):
        ends=[self.independent(0),self.independent(1)];strips=[]
        for k in range(2):
            low,high=sorted([x[k] for x in ends]);roots={}
            for edge in range(math.floor(low),math.floor(high)+2):
                if edge<=low:root=0. if ends[0][k]<ends[1][k] else 1.
                elif edge>=high:root=1. if ends[0][k]<ends[1][k] else 0.
                else:root=brentq(lambda t:self.independent(t)[k]-edge,0,1,xtol=5e-15)
                roots[edge]=root
            strips.append({j:sorted([roots[j],roots[j+1]]) for j in range(math.floor(low),math.floor(high)+1)})
        return {(r,c) for c,(l,h) in strips[0].items() for r,(u,v) in strips[1].items() if max(l,u)<=min(h,v)+1e-12}

def main():
    original=inputs();d=spreadsheet_inputs();checks=0
    for kind in ['types','boxes','nodes']:
        for key,r in d[kind].items():
            for field,value in r.items():
                assert original[kind][key][field]==value,(kind,key,field,value,original[kind][key][field]);checks+=1
    origin=d['nodes']['O01'];crs=CRS.from_proj4(f"+proj=aeqd +lat_0={origin['lat']} +lon_0={origin['lon']} +datum=WGS84 +units=m")
    forward=Transformer.from_crs(4326,crs,always_xy=True);inverse=Transformer.from_crs(crs,4326,always_xy=True);dem=Raster();rows=[];traversals={}
    for node in d['nodes'].values():node['x'],node['y']=forward.transform(node['lon'],node['lat'])
    for index,(a,b) in enumerate(itertools.combinations(d['nodes'],2)):
        curve=Curve(d['nodes'][a],d['nodes'][b],origin,dem,forward,inverse);cells=curve.cells();other=curve.strip_cells()
        assert cells==other,(a,b,'independent traversal mismatch',cells^other)
        sample=curve.pixel(np.linspace(0,1,math.ceil(curve.distance/.25)+1));samplecells={(int(r),int(c)) for c,r in np.floor(sample)}
        assert samplecells<=cells
        z=dem.max(cells);old_dist,old_z=original['geo'][a,b]
        rows.append(dict(origin=a,destination=b,distance_m=curve.distance,max_dem_m=z,traversed_cells=len(cells),sample_missed_cells=len(cells-samplecells),snapshot_distance_difference_m=curve.distance-old_dist,snapshot_max_dem_difference_m=z-old_z,monotonic_margin=curve.monotonic_margin))
        traversals[a+'|'+b]=sorted(cells)
        if index%20==0:print('raw geometry',index+1,120,flush=True)
    save(ROOT/'data/raw_instance.json',d);save(ROOT/'results/raw_geometry_cells.json',traversals);table(ROOT/'results/raw_geometry.csv',rows)
    report=dict(attachment_field_checks=checks,undirected_legs=120,directed_legs=240,independent_full_cell_agreement=True,max_snapshot_distance_difference_m=max(abs(r['snapshot_distance_difference_m']) for r in rows),changed_max_dem_legs=[r for r in rows if r['snapshot_max_dem_difference_m']!=0],minimum_monotonic_margin=min(r['monotonic_margin'] for r in rows),raw_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data/raw').iterdir()})
    save(ROOT/'results/raw_input_audit.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
