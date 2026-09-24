// Exact pricing of a stated LOWER-BOUND relaxation, not an executable schedule.
// Costs/energy are integer lower ticks. Mode 0 permits repeats, 1 is elementary.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>
#include <limits>
#include <new>
using namespace std;
using I=long long;
struct Lab {I c; int e,parent,item,mask;};
int main(){try {
 ios::sync_with_stdio(false);cin.tie(nullptr);
 int Q,V,C,N,BUD,elem,K;I mu,prep,per,base;
 if(!(cin>>Q>>V>>C>>N>>BUD>>mu>>prep>>per>>base>>elem>>K))return 2;
 vector<int>s(C),w(C),v(C),nb(C);vector<I>pi(C);
 for(int j=0;j<C;j++)cin>>s[j]>>w[j]>>v[j]>>nb[j]>>pi[j];
 vector<int> cm(K);vector<I>cp(K);for(int k=0;k<K;k++)cin>>cm[k]>>cp[k];
 vector<vector<int>>tt(N,vector<int>(N));for(auto&r:tt)for(auto&a:r)cin>>a;
 vector<int>eng((Q+1)*N*N);for(auto&a:eng)cin>>a;
 auto energy=[&](int q,int a,int b){return eng[(q*N+a)*N+b];};
 auto key=[&](int ww,int vv,int a){return (ww*(V+1)+vv)*N+a;};
 vector<vector<int>>front((Q+1)*(V+1)*N);vector<Lab>L;L.reserve(200000);
 L.push_back({mu*prep,0,-1,-1,0});front[0].push_back(0);
 vector<I>bonus((1<<(N-1))*N,0);
 for(int mask=0;mask<(1<<(N-1));mask++) for(int k=0;k<K;k++)if(!(mask&cm[k]))
  for(int b=1;b<N;b++)if(cm[k]&(1<<(b-1)))bonus[mask*N+b]+=cp[k]*1000;
 I best=numeric_limits<I>::max();int bestid=-1;vector<pair<I,int>>finals;
 for(int ww=0;ww<=Q;ww++)for(int vv=0;vv<=V;vv++)for(int a=0;a<N;a++){
  auto ids=front[key(ww,vv,a)];
  for(int id:ids){Lab cur=L[id];
   if(a!=0&&cur.e+energy(ww,0,a)<=BUD){
    I rc=cur.c+mu*tt[0][a];if(rc<best){best=rc;bestid=id;}if(rc<0)finals.emplace_back(rc,id);
   }
   for(int j=0;j<C;j++){
    int nw=ww+w[j],nv=vv+v[j],b=s[j],bit=1<<(b-1);
    if(nw>Q||nv>V||b==a||(elem&&(cur.mask&bit)))continue;
    int ne=cur.e+energy(ww,b,a);if(ne>BUD)continue;
    int mask=(elem||K)?cur.mask|bit:0;
    I nc=cur.c+mu*(per*nb[j]+base+tt[b][a])-pi[j]*1000-bonus[cur.mask*N+b];
    auto&f=front[key(nw,nv,b)];bool dominated=false;
    // Subset-mask dominance is safe for nonnegative hit-cut rewards and future feasibility.
    for(int k:f)if(L[k].e<=ne&&L[k].c<=nc&&((L[k].mask&mask)==L[k].mask)){dominated=true;break;}
    if(dominated)continue;
    f.erase(remove_if(f.begin(),f.end(),[&](int k){return L[k].e>=ne&&L[k].c>=nc&&((L[k].mask&mask)==mask);}),f.end());
    int ni=(int)L.size();L.push_back({nc,ne,id,j,mask});f.push_back(ni);
   }
  }
 }
 sort(finals.begin(),finals.end());if(finals.empty()&&bestid>=0)finals.emplace_back(best,bestid);
 size_t n=min((size_t)100,finals.size());cout<<best<<" "<<L.size()<<" "<<n<<"\n";
 for(size_t k=0;k<n;k++){int id=finals[k].second;vector<int>seq;while(id>0){seq.push_back(L[id].item);id=L[id].parent;}cout<<finals[k].first<<" "<<seq.size();for(int j:seq)cout<<" "<<j;cout<<"\n";}
 return 0;
}catch(const bad_alloc&){cerr<<"memory_limit_no_certificate\n";return 3;}}
