"""Closed-cell supercover in the original affine raster, without resampling DEM.

Every grid boundary crossing splits the continuous segment. The cell membership
is constant on each open interval; its midpoint plus all boundary points covers
every intersected closed cell, including corner touches and boundary-aligned legs.
"""
from dataclasses import dataclass, asdict
from math import floor, ceil, hypot
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy.optimize import brentq
from pyproj import CRS, Transformer
from geographiclib.geodesic import Geodesic
import tifffile
from .io import ROOT

GRID_TOL = 1e-9  # raster-coordinate roundoff, never a physical clearance margin


@dataclass
class DEM:
    values: np.ndarray
    x0: float  # upper-left corner, not the PixelIsPoint tiepoint centre
    y0: float
    dx: float
    dy: float
    nodata: float

    def pixel(self, lon, lat):
        return ((lon - self.x0) / self.dx, (lat - self.y0) / self.dy)


def load_dem(raw=None):
    raw = Path(raw or ROOT / 'data/raw')
    with tifffile.TiffFile(raw / '镇龙乡及周边30米DEM.tif') as tif:
        values = tif.asarray()
        meta = tif.geotiff_metadata
    mat = loadmat(raw / '镇龙乡及周边30米DEM.mat')
    if not np.array_equal(values, mat['dem']):
        raise ValueError('TIF/MAT elevation mismatch')
    if int(meta['GeographicTypeGeoKey']) != 4326 or int(meta['GTRasterTypeGeoKey']) != 2:
        raise ValueError('Expected WGS84 PixelIsPoint DEM')
    dx, sy, _ = meta['ModelPixelScale']
    tie = meta['ModelTiepoint']
    if tie[:3] != [0.0, 0.0, 0.0]:
        raise ValueError('Unsupported tiepoint')
    dem = DEM(values, tie[3] - dx / 2, tie[4] + sy / 2, dx, -sy, float(mat['nodata'][0, 0]))
    if not np.allclose(mat['transform'].ravel(), [dx, 0, dem.x0, 0, -sy, dem.y0], atol=1e-11, rtol=0):
        raise ValueError('Half-pixel transform mismatch')
    if not (np.allclose(mat['longitude'].ravel(), dem.x0 + (np.arange(values.shape[1]) + .5)*dx, atol=1e-11, rtol=0)
            and np.allclose(mat['latitude'].ravel(), dem.y0 - (np.arange(values.shape[0]) + .5)*sy, atol=1e-11, rtol=0)):
        raise ValueError('MAT cell centres disagree with GeoTIFF')
    return dem


def point_cells(x, y):
    def indices(v):
        n = round(v)
        return (n-1, n) if abs(v-n) <= GRID_TOL else (floor(v),)
    return {(r, c) for c in indices(x) for r in indices(y)}


def supercover(a, b):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    delta = b-a
    ts = {0.0, 1.0}
    for k in range(2):
        if delta[k] != 0:
            for edge in range(ceil(min(a[k], b[k])), floor(max(a[k], b[k]))+1):
                t = (edge-a[k])/delta[k]
                if 0 <= t <= 1:
                    ts.add(float(t))
    ts = sorted(ts)
    cells = set()
    for t in ts + [(u+v)/2 for u, v in zip(ts, ts[1:])]:
        cells.update(point_cells(*(a+t*delta)))
    return cells


def slab_cells(a, b):
    """Independent exhaustive segment/rectangle intersection (validation only)."""
    found = set()
    for r in range(floor(min(a[1], b[1]))-1, floor(max(a[1], b[1]))+1):
        for c in range(floor(min(a[0], b[0]))-1, floor(max(a[0], b[0]))+1):
            lo, hi = 0., 1.
            for v, w, lower in zip(a, b, (c, r)):
                dv = w-v
                if dv == 0:
                    if not lower-GRID_TOL <= v <= lower+1+GRID_TOL:
                        lo, hi = 1., 0.
                        break
                else:
                    s, t = (lower-v)/dv, (lower+1-v)/dv
                    lo, hi = max(lo, min(s,t)), min(hi, max(s,t))
            if lo <= hi + 1e-13:
                found.add((r,c))
    return found


def sampled_cells(a, b, distance_m, step_m=.25):
    n = max(1, ceil(distance_m/step_m))
    xy = np.asarray(a) + np.linspace(0,1,n+1)[:,None]*(np.asarray(b)-np.asarray(a))
    return {(int(r),int(c)) for c,r in np.floor(xy).astype(int)}


def horizontal_distance(a, b, method):
    if method == 'aeqd_o01':
        crs = CRS.from_proj4(f'+proj=aeqd +lat_0={a.lat} +lon_0={a.lon} +datum=WGS84 +units=m')
        forward = Transformer.from_crs(4326, crs, always_xy=True)
        x0,y0 = forward.transform(a.lon,a.lat)
        x1,y1 = forward.transform(b.lon,b.lat)
        return hypot(x1-x0,y1-y0)
    if method == 'wgs84_geodesic':
        from geographiclib.geodesic import Geodesic
        return Geodesic.WGS84.Inverse(a.lat, a.lon, b.lat, b.lon)['s12']
    if method == 'haversine_6371000':
        # Only for explicit model-convention comparison; not selected by regression.
        lon1,lat1,lon2,lat2 = np.radians([a.lon,a.lat,b.lon,b.lat])
        v = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
        return float(2*6371000*np.arcsin(np.sqrt(v)))
    raise ValueError('A documented distance convention is required')


class ProjectedRoute:
    """Exact AEQD radial segment; nonlinear curve in geographic raster coords.

    Q1 only: every route starts at the projection centre. Its inverse is a WGS84
    geodesic. Longitude is monotone (Clairaut); latitude is monotone on these
    short legs when endpoint northward azimuth components have the same sign.
    We verify that condition and refuse unsupported nonmonotone legs.
    """
    def __init__(self, a, b, dem):
        self.a,self.b,self.dem=a,b,dem
        crs=CRS.from_proj4(f'+proj=aeqd +lat_0={a.lat} +lon_0={a.lon} +datum=WGS84 +units=m')
        self.forward=Transformer.from_crs(4326,crs,always_xy=True)
        self.inverse=Transformer.from_crs(crs,4326,always_xy=True)
        self.xy0=np.array(self.forward.transform(a.lon,a.lat))
        self.xy1=np.array(self.forward.transform(b.lon,b.lat))
        self.distance=float(np.linalg.norm(self.xy1-self.xy0))
        self.geod=Geodesic.WGS84.Inverse(a.lat,a.lon,b.lat,b.lon)
        if not (self.geod['a12'] < 90 and
                np.cos(np.radians(self.geod['azi1'])) * np.cos(np.radians(self.geod['azi2'])) > 0):
            raise ValueError('Nonmonotone latitude requires splitting at the geodesic vertex')
        self.ends=(self.pixel(0.),self.pixel(1.))

    def pixel(self,t):
        xy=self.xy0+np.asarray(t)[...,None]*(self.xy1-self.xy0)
        lon,lat=self.inverse.transform(xy[...,0],xy[...,1])
        return np.stack(self.dem.pixel(lon,lat),axis=-1)

    def independent_pixel(self,t):
        g=Geodesic.WGS84.Direct(self.a.lat,self.a.lon,self.geod['azi1'],t*self.geod['s12'])
        return self.dem.pixel(g['lon2'],g['lat2'])

    def cells(self):
        a,b=self.ends
        ts={0.,1.}
        for k in range(2):
            for edge in range(ceil(min(a[k],b[k])),floor(max(a[k],b[k]))+1):
                if a[k] != b[k]:
                    ts.add(brentq(lambda t:self.pixel(t)[k]-edge,0,1,xtol=5e-15))
        ts=sorted(ts)
        cells=set()
        for t in ts+[(u+v)/2 for u,v in zip(ts,ts[1:])]:
            cells.update(point_cells(*self.pixel(t)))
        return cells

    def independent_cells(self):
        """Rectangle/time-interval intersection, GeographicLib + bisection.

        For a monotone coordinate, each pixel strip pulls back to a closed
        interval of path time. Row and column intervals intersect iff the
        continuous geodesic intersects the pixel. No polyline or sampling.
        """
        a,b=self.independent_pixel(0.),self.independent_pixel(1.)
        strips=[]
        for k in range(2):
            def inverse(value):
                if value <= min(a[k],b[k]):return 0. if a[k]<b[k] else 1.
                if value >= max(a[k],b[k]):return 1. if a[k]<b[k] else 0.
                lo,hi=0.,1.
                for _ in range(48):
                    mid=(lo+hi)/2
                    if (self.independent_pixel(mid)[k]<value)==(a[k]<b[k]):lo=mid
                    else:hi=mid
                return (lo+hi)/2
            low,high=floor(min(a[k],b[k])),floor(max(a[k],b[k]))
            crossings={j:inverse(j) for j in range(low,high+2)}
            strips.append({j:sorted((crossings[j],crossings[j+1])) for j in range(low,high+1)})
        return {(r,c) for c,(cl,ch) in strips[0].items() for r,(rl,rh) in strips[1].items()
                if max(cl,rl) <= min(ch,rh)+1e-13}

    def sample(self,step_m=.25):
        n=ceil(self.distance/step_m)
        xy=self.pixel(np.linspace(0,1,n+1))
        return {(int(r),int(c)) for c,r in np.floor(xy).astype(int)}


def geometry(nodes, dem, method):
    origin = nodes['O01']
    start = dem.pixel(origin.lon, origin.lat)
    result = {}
    traversals = {}
    for name, node in sorted(nodes.items()):
        if name == 'O01':
            continue
        route = ProjectedRoute(origin,node,dem)
        cells = route.cells()
        if any(r < 0 or c < 0 or r >= dem.values.shape[0] or c >= dem.values.shape[1] for r,c in cells):
            raise ValueError(f'{name}: segment outside DEM')
        heights = [float(dem.values[r,c]) for r,c in cells]
        if any(h == dem.nodata or not np.isfinite(h) for h in heights):
            raise ValueError(f'{name}: NoData on segment')
        zmax = max(heights)
        H = zmax+50
        if H < max(origin.work_m, node.work_m):
            raise ValueError(f'{name}: cruise altitude below work altitude; requires clarification')
        result[name] = dict(service_area=name, distance_m=horizontal_distance(origin,node,method),
                            max_dem_m=zmax, cruise_altitude_m=H,
                            out_up_m=H-origin.work_m, out_down_m=H-node.work_m,
                            back_up_m=H-node.work_m, back_down_m=H-origin.work_m,
                            traversed_cells_count=len(cells))
        traversals[name] = sorted(cells)
    return result, traversals


def check_geometry(nodes, dem, records, traversals):
    a = dem.pixel(nodes['O01'].lon,nodes['O01'].lat)
    report = []
    for name,g in records.items():
        n = nodes[name]
        b = dem.pixel(n.lon,n.lat)
        route=ProjectedRoute(nodes['O01'],n,dem)
        exact = set(map(tuple,traversals[name]))
        slab = route.independent_cells()
        sampled = route.sample()
        if exact != slab or not sampled <= exact:
            raise AssertionError(f'Independent geometric validation failed: {name}')
        report.append(dict(service_area=name, exact_cells=len(exact), slab_cells=len(slab),
                           sample_cells=len(sampled), sample_missed_cells=len(exact-sampled),
                           max_dem_sample_m=max(float(dem.values[r,c]) for r,c in sampled),
                           max_dem_exact_m=g['max_dem_m'], sample_step_m=.25,
                           aeqd_distance_m=route.distance, geodesic_distance_m=route.geod['s12'],
                           distance_abs_difference_m=abs(route.distance-route.geod['s12']),
                           distance_relative_difference=abs(route.distance-route.geod['s12'])/route.distance))
    return report
