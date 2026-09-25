"""Exact bounding-box pruning of terrain cells, unchanged radio/DEM constants.
Only skips cells that cannot pass the ORIGINAL full-array rectangle test.
The final verifier can run unpatched in a separate process.
"""
from functools import lru_cache
import numpy as np

def enable():
    import terrain_events as te
    import coverage_v2 as cov
    orig=te.obstacles
    xmin_col=te.XLO.min(axis=0);xmax_col=te.XHI.max(axis=0)
    ymin_row=te.YLO.min(axis=1);ymax_row=te.YHI.max(axis=1)
    def candidates(src,a,b,pad):
        x0=min(src[0],a[0],b[0])-pad;x1=max(src[0],a[0],b[0])+pad
        y0=min(src[1],a[1],b[1])-pad;y1=max(src[1],a[1],b[1])+pad
        cs=np.flatnonzero((xmax_col>=x0)&(xmin_col<=x1));rs=np.flatnonzero((ymax_row>=y0)&(ymin_row<=y1))
        if not len(cs) or not len(rs):return np.empty(0,dtype=np.int64),np.empty(0,dtype=np.int64)
        c0,c1=int(cs[0]),int(cs[-1])+1;r0,r1=int(rs[0]),int(rs[-1])+1
        sl=np.s_[r0:r1,c0:c1]
        rr,cc=np.nonzero((te.XHI[sl]>=x0)&(te.XLO[sl]<=x1)&(te.YHI[sl]>=y0)&(te.YLO[sl]<=y1))
        return rr+r0,cc+c0
    @lru_cache(maxsize=30000)
    def obstacles(src0,a0,b0,rect=False,pad=0.):
        src=np.array(src0);a=np.array(a0);b=np.array(b0)
        rows,cols=candidates(src,a,b,pad)
        iv=te.all_blocks(src,a,b,rows,cols,te.DEM,te.XX,te.YY,pad,rect)
        return te.merge(iv.tolist())
    te.obstacles=obstacles
    return {'original':orig,'accelerated':obstacles,'candidate_cells':candidates}
