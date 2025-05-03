#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
#define pb push_back
#define ff first
#define ss second
const ll MOD = 998244353;

struct my {
    ll x,y,z;
};

my makemy(ll a,ll b, ll c) {
    my temp;
    temp.x = a;
    temp.y = b;
    temp.z = c;
    return temp;
}

ll powp(ll a, ll b) {
    ll ans = 1; while( b ) { if(b&1) ans = (ans * a % MOD); a = ( a * a % MOD); b >>= 1; } return ans;
}

ll inv (ll a) { return powp(a,MOD-2); }

ll mydiv(ll a, ll b) {
    return a*inv(b) % MOD;
}

void solve() {
    int n; cin>>n;
    vector <int> adj[n];
    for(int i=0;i<n-1;++i) {
        int x,y; cin>>x>>y;
        x--;y--;
        adj[x].pb(y);
        adj[y].pb(x);
    }
    function <my(int,int)> dfs = [&](int v, int par) -> my {
        int sz = adj[v].size();
        // if(sz == 1) return makemy(1,1,0);
        vector <ll> A(sz),B(sz),C(sz);
        int i = 0;
        ll prod = 1, sum = 0, sumsq = 0, sumc = 0;
        for(int x: adj[v]) {
            if(x == par) continue;
            my chld = dfs(x,v);
            cout<<x<<" "<<v<<" "<<chld.x<<" "<<chld.y<<" "<<chld.z<<endl;
            A[i] = chld.x;
            prod = (prod * A[i] % MOD);
            B[i] = mydiv(chld.y,A[i]);
            sum += B[i]; if(sum >= MOD) sum -= MOD;
            sumsq += B[i] * B[i] % MOD; if(sumsq >= MOD) sumsq -= MOD;
            C[i] = mydiv(chld.z,A[i]);
            sumc += C[i]; if(sumc >= MOD) sumc -= MOD;
            ++i;
        }
        my ans =  makemy(prod, (1 + sum) * prod % MOD, (mydiv(((sum * sum % MOD - sumsq) + MOD) % MOD,2) + sum + sumc) % MOD * prod % MOD );
        cout<<v<<" "<<ans.x<<" "<<ans.y<<" "<<ans.z<<endl;
        return ans;
    };
    my ans = dfs(0,-1);
    cout << (ans.x + ans.y + ans.z)%MOD <<endl;
    cout<<endl;
}

int main() 
{
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    int t = 1;
    cin >> t;
    while(t--) solve();
    return 0;
}