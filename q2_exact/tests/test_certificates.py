from pathlib import Path
import sys,unittest,json,copy
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from certify_bound import min_price_int,run as verify_lower
from certify_upper import ceil_grid,energy_upper,run as verify_upper
from fractions import Fraction as F
class Tests(unittest.TestCase):
 def test_price_against_exhaustive_small(self):
  edge=np.array([[0,7,9],[6,0,3],[9,4,0]],np.int64);ps=np.array([1,1,2]);pm=np.array([3,6,3]);pv=np.array([12,24,12]);score=np.array([-35,-60,-37]);Q,V=12,48
  allv=[]
  def dfs(j,q,v,cost):
   if j:allv.append(cost+edge[0,j]+15)
   for h,i in enumerate(ps):
    if i!=j and q+pm[h]<=Q and v+pv[h]<=V:dfs(i,q+pm[h],v+pv[h],cost+edge[i,j]+score[h])
  dfs(0,0,0,0);self.assertEqual(min(allv),int(min_price_int(Q,V,edge,ps,pm,pv,score,15)))
 def test_rational_rounds_outward(self):
  self.assertEqual(ceil_grid(F(1,3),1000),F(334,1000));self.assertGreaterEqual(ceil_grid(F(7,10),1000),F(7,10))
 def test_current_certificates(self):
  self.assertTrue(verify_lower(True,True)['certificate_valid']);self.assertTrue(verify_upper()['valid'])
 def test_certificate_tampering_rejected(self):
  p=ROOT/'results/rational_certificate_cuts.json';raw=p.read_bytes();c=json.loads(raw);c['pi_integer'][0]+=100*10**8;p.write_text(json.dumps(c))
  try:
   with self.assertRaises(AssertionError):verify_lower(True,True)
  finally:p.write_bytes(raw)
 def test_wrong_snapshot_rejected(self):
  p=ROOT/'inputs/legs.json';raw=p.read_bytes();p.write_bytes(raw+b' ')
  try:
   with self.assertRaises(AssertionError):verify_lower(True,True)
  finally:p.write_bytes(raw)
 def test_duplicate_box_rejected(self):
  p=ROOT/'inputs/incumbent_flights.json';raw=p.read_bytes();f=json.loads(raw);f[0]['box_ids'][0]=f[1]['box_ids'][0];p.write_text(json.dumps(f))
  try:
   with self.assertRaises(AssertionError):verify_upper()
  finally:p.write_bytes(raw)
if __name__=='__main__':unittest.main()
