import numpy as np
import pytest
from model.io import load_inputs
from model.geometry import load_dem, geometry, supercover, slab_cells, check_geometry, ProjectedRoute


def test_dem_geometry():
    nodes,_,_=load_inputs()
    dem=load_dem()
    geo,cells=geometry(nodes,dem,'aeqd_o01')
    assert len(check_geometry(nodes,dem,geo,cells)) == 15


@pytest.mark.parametrize('a,b', [((.2,.2),(3.8,3.8)), ((1,0),(1,4)),
                               ((0,2),(4,2)), ((.2,3.8),(3.8,.2)), ((1,1),(1,1))])
def test_boundary_corner_and_reverse(a,b):
    assert supercover(a,b) == slab_cells(a,b) == supercover(b,a)


def test_work_altitude():
    nodes,_,_=load_inputs()
    assert nodes['O01'].work_m == nodes['O01'].ground_m
    geo,_=geometry(nodes,load_dem(),'aeqd_o01')
    for s,g in geo.items():
        assert nodes[s].work_m == nodes[s].ground_m+30
        assert g['back_up_m'] == g['out_down_m'] > 0
        assert g['back_down_m'] == g['out_up_m'] > 0


def thin_bresenham(a,b):
    x0,y0=map(int,np.floor(a));x1,y1=map(int,np.floor(b))
    dx,dy=abs(x1-x0),-abs(y1-y0)
    sx,sy=1 if x0<x1 else -1,1 if y0<y1 else -1
    err=dx+dy;cells=set()
    while True:
        cells.add((y0,x0))
        if (x0,y0)==(x1,y1):break
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy
    return cells


def test_negative_thin_bresenham():
    nodes,_,_=load_inputs();dem=load_dem()
    a=dem.pixel(nodes['O01'].lon,nodes['O01'].lat)
    # A real raw-data route, not a synthetic expected maximum.
    n=nodes['S001'];b=dem.pixel(n.lon,n.lat)
    exact=ProjectedRoute(nodes['O01'],n,dem).cells()
    assert thin_bresenham(a,b) != exact
    with pytest.raises(AssertionError):
        assert thin_bresenham(a,b) == exact
