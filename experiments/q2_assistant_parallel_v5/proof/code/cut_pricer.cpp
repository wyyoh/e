// Exact repeated-walk pricing with <=10 rank-1 subset-row cuts.
// Each cut is sum_r floor(number of boxes in subset on r / 2) x_r <= floor(total / 2).
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>
#include <limits>
#include <new>
using namespace std; using I=long long;
struct Lab {I c; int e,parent,item,mask;};
int main(){try{
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int Q,V,C,N,BUD,K;I mu,prep,per,base;
 if(!(cin>>Q>>V>>C>>N>>BUD>>mu>>prep>>per>>base>>K))return 2;
 if(K<0||K>10||mu<0)return 2;
 vector<int>s(C),w(C),v(C),nb(C);vector<I>pi(C);
 vector<vector<int>>cn(C,vector<int>(K));
 for(int j=0;j<C;j++){cin>>s[j]>>w[j]>>v[j]>>nb[j]>>pi[j];for(int k=0;k<K;k++)cin>>cn[j][k];}
 vector<I>pen(K);for(auto &a:pen){cin>>a;if(a<0)return 2;}
 vector<vector<int>>tt(N,vector<int>(N));for(auto&r:tt)for(auto&a:r)cin>>a;
 vector<int>eng((Q+1)*N*N);for(auto&a:eng)cin>>a;
 auto energy=[&](int q,int a,int b){return eng[(q*N+a)*N+b];};
 auto key=[&](int ww,int vv,int a){return (ww*(V+1)+vv)*N+a;};
 vector<vector<int>>front((Q+1)*(V+1)*N);vector<Lab>L;L.reserve(300000);
 vector<vector<I>>add(C,vector<I>(1<<K));vector<int>flip(C,0);
 for(int j=0;j<C;j++){
  for(int k=0;k<K;k++)if(cn[j][k]%2)flip[j]|=1<<k;
  for(int mask=0;mask<(1<<K);mask++)for(int k=0;k<K;k++)add[j][mask]+=1000*pen[k]*((cn[j][k]+((mask>>k)&1))/2);
 }
 L.push_back({mu*prep,0,-1,-1,0});front[0].push_back(0);
 I best=numeric_limits<I>::max();int bestid=-1;vector<pair<I,int>>finals;
 for(int ww=0;ww<=Q;ww++)for(int vv=0;vv<=V;vv++)for(int a=0;a<N;a++){
  auto ids=front[key(ww,vv,a)];
  for(int id:ids){Lab cur=L[id];
   if(a!=0&&cur.e+energy(ww,0,a)<=BUD){I rc=cur.c+mu*tt[0][a];if(rc<best){best=rc;bestid=id;}if(rc<0)finals.emplace_back(rc,id);}
   for(int j=0;j<C;j++){
    int nw=ww+w[j],nv=vv+v[j],b=s[j];if(nw>Q||nv>V||b==a)continue;
    int ne=cur.e+energy(ww,b,a);if(ne>BUD)continue;int nm=cur.mask^flip[j];
    I nc=cur.c+mu*(per*nb[j]+base+tt[b][a])-pi[j]*1000+add[j][cur.mask];
    auto&f=front[key(nw,nv,b)];bool dominated=false;
    for(int k:f)if(L[k].mask==nm&&L[k].e<=ne&&L[k].c<=nc){dominated=true;break;}
    if(dominated)continue;
    f.erase(remove_if(f.begin(),f.end(),[&](int k){return L[k].mask==nm&&L[k].e>=ne&&L[k].c>=nc;}),f.end());
    int ni=(int)L.size();L.push_back({nc,ne,id,j,nm});f.push_back(ni);
   }
  }
 }
 sort(finals.begin(),finals.end());if(finals.empty()&&bestid>=0)finals.emplace_back(best,bestid);
 size_t n=min((size_t)100,finals.size());cout<<best<<" "<<L.size()<<" "<<n<<"\n";
 for(size_t k=0;k<n;k++){int id=finals[k].second;vector<int>seq;while(id>0){seq.push_back(L[id].item);id=L[id].parent;}cout<<finals[k].first<<" "<<seq.size();for(int j:seq)cout<<" "<<j;cout<<"\n";}
 return 0;
}catch(const bad_alloc&){cerr<<"memory_limit_no_certificate\n";return 3;}}
