// Finite, exhaustive resource-DAG pricing. Integer reduced costs + energy units.
// Repeated visits/items are allowed, so this is a RELAXATION, never an incumbent.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>
#include <tuple>
#include <limits>
using namespace std;
struct Lab { long long c; int e,parent,item,w,v,last; };
int main(){
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int Q,V,C,N,BUD;long long mu,prep,per,base;
 if(!(cin>>Q>>V>>C>>N>>BUD>>mu>>prep>>per>>base))return 2;
 vector<int>s(C),w(C),v(C),nb(C);vector<long long>pi(C);
 for(int j=0;j<C;j++)cin>>s[j]>>w[j]>>v[j]>>nb[j]>>pi[j];
 vector<vector<int>>tt(N,vector<int>(N));for(auto &r:tt)for(auto &a:r)cin>>a;
 vector<int>eng((Q+1)*N*N);for(auto &a:eng)cin>>a;
 auto energy=[&](int load,int a,int b){return eng[(load*N+a)*N+b];};
 auto key=[&](int ww,int vv,int a){return (ww*(V+1)+vv)*N+a;};
 vector<vector<int>>f((Q+1)*(V+1)*N);vector<Lab>L;L.reserve(1000000);
 L.push_back({mu*prep,0,-1,-1,0,0,0});f[0].push_back(0);
 long long best=numeric_limits<long long>::max();int best_id=-1;
 vector<pair<long long,int>>finals;
 for(int ww=0;ww<=Q;ww++)for(int vv=0;vv<=V;vv++)for(int a=0;a<N;a++){
  auto ids=f[key(ww,vv,a)];
  for(int id:ids){Lab cur=L[id];
   if(a!=0 && cur.e+energy(ww,0,a)<=BUD){
    long long rc=cur.c+mu*tt[0][a];
    if(rc<best){best=rc;best_id=id;}
    if(rc<0)finals.emplace_back(rc,id);
   }
   for(int j=0;j<C;j++){
    int nw=ww+w[j],nv=vv+v[j],b=s[j];if(nw>Q||nv>V||b==a)continue;
    int ne=cur.e+(a==b?0:energy(ww,b,a));if(ne>BUD)continue;
    long long nc=cur.c+mu*(per*nb[j]+base+tt[b][a])-pi[j]*1000;
    auto &front=f[key(nw,nv,b)];bool dominated=false;
    for(int k:front)if(L[k].e<=ne&&L[k].c<=nc){dominated=true;break;}
    if(dominated)continue;
    front.erase(remove_if(front.begin(),front.end(),[&](int k){return L[k].e>=ne&&L[k].c>=nc;}),front.end());
    int nid=(int)L.size();L.push_back({nc,ne,id,j,nw,nv,b});front.push_back(nid);
   }
  }
 }
 sort(finals.begin(),finals.end());if(finals.empty()&&best_id>=0)finals.emplace_back(best,best_id);
 size_t n=min((size_t)80,finals.size());cout<<best<<" "<<L.size()<<" "<<n<<"\n";
 for(size_t i=0;i<n;i++){
  int p=finals[i].second;vector<int>seq;
  while(p>0){seq.push_back(L[p].item);p=L[p].parent;}
  // Backward extension: walking parents yields forward delivery sequence.
  cout<<finals[i].first<<" "<<seq.size();for(int j:seq)cout<<" "<<j;cout<<"\n";
 }
 return 0;
}
