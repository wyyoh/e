"""Local exact dominance enhancement; no changes to published source kernels.
Compared labels must have the same load/volume/location and matching pair memory.
For each SRI parity difference a=1,b=0, pay an upper bound pen on any common
continuation. If no odd-contribution stop can fit remaining capacities, pay zero.
Visited-set subset and energy ordering remain unchanged. Penalties are >=0.
"""
from pathlib import Path
import argparse,subprocess

def build(srcroot,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for name in ['cut_pricer','elementary_pricer','memory_pricer']:
  text=(Path(srcroot)/f'{name}.cpp').read_text()
  anchor=' L.push_back('
  assert anchor in text
  extra='''
 // Necessary-capacity reachability. We do not use deadlines or original-route
 // constraints that are absent in this relaxation. Includes the current site.
 vector<int> live((Q+1)*(V+1),0);
 for(int j=0;j<C;j++) if(w[j]<=Q&&v[j]<=V) live[w[j]*(V+1)+v[j]]|=flip[j];
 for(int w0=0;w0<=Q;w0++)for(int v0=0;v0<=V;v0++){
   int &m=live[w0*(V+1)+v0];
   if(w0)m|=live[(w0-1)*(V+1)+v0];
   if(v0)m|=live[w0*(V+1)+v0-1];
 }
 vector<I> penalty(1<<K,0);
 for(int m=1;m<(1<<K);m++) {int b=__builtin_ctz((unsigned)m);penalty[m]=penalty[m&(m-1)]+1000*pen[b];}
 auto dc=[&](I ca,int pa,I cb,int pb,int usedw,int usedv){
   return ca+penalty[(pa&~pb)&live[(Q-usedw)*(V+1)+(V-usedv)]]<=cb;
 };
'''
  text=text.replace(anchor,extra+anchor,1)
  parity='parity' if name=='memory_pricer' else 'mask'
  text=text.replace(f'L[k].{parity}==nm&&','')
  # Replace cost comparisons only in dominance loops, preserving all other guards.
  text=text.replace('L[k].c<=nc',f'dc(L[k].c,L[k].{parity},nc,nm,nw,nv)')
  text=text.replace('L[k].c>=nc',f'dc(nc,nm,L[k].c,L[k].{parity},nw,nv)')
  dst=out/f'{name}_accelerated.cpp';dst.write_text(text)
  subprocess.run(['g++','-O3','-std=c++17',str(dst),'-o',str(out/f'{name}_accelerated')],check=True)
  subprocess.run(['g++','-O3','-std=c++17',str(Path(srcroot)/f'{name}.cpp'),'-o',str(out/f'{name}_baseline')],check=True)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');a=p.parse_args();build(a.source,a.out)
