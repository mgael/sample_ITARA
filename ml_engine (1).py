"""
ITARA ML Engine — 4 models, synthetic training, real-data swap path.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import Ridge
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import warnings
warnings.filterwarnings("ignore")

RNG = np.random.default_rng(42)

# ── SYNTHETIC DATA ──────────────────────────────────────────────────────────

def _players(n=400):
    age=RNG.integers(17,36,n); matches=RNG.integers(5,38,n)
    minutes=matches*RNG.integers(60,90,n); pi=RNG.uniform(3.0,9.5,n)
    fitness=RNG.integers(50,100,n); goals=(RNG.poisson(pi/5,n)).clip(0,30)
    assists=(RNG.poisson(pi/7,n)).clip(0,20); pass_acc=RNG.uniform(60,95,n)
    dribbles=RNG.integers(0,80,n); tackles=RNG.integers(0,80,n)
    shots=(goals*RNG.uniform(2.5,4.5,n)).astype(int)
    inj_prob=((age/35)*0.25+((100-fitness)/100)*0.40+(minutes/3420)*0.20
              +((10-pi)/10)*0.15+RNG.normal(0,0.04,n))
    injured=(inj_prob>0.42).astype(int)
    age_growth=np.where(age<24,1.06,np.where(age<28,1.02,0.97))
    future_pi=(pi*age_growth+RNG.normal(0,0.3,n)).clip(1,10)
    future_mv=(future_pi*1_250_000*(1+matches*0.05)*np.where(age<30,1.0,0.85)
               +RNG.normal(0,50_000,n)).clip(500_000,25_000_000)
    return pd.DataFrame(dict(age=age,matches=matches,minutes=minutes,pi=pi,
        fitness=fitness,goals=goals,assists=assists,pass_acc=pass_acc,
        dribbles=dribbles,tackles=tackles,shots=shots,injured=injured,
        future_pi=future_pi,future_mv=future_mv))

def _matches(n=600):
    hp=RNG.uniform(4,9,n); ap=RNG.uniform(4,9,n)
    hf=RNG.integers(60,100,n); af=RNG.integers(60,100,n)
    h2h=RNG.integers(0,10,n); hform=RNG.uniform(0,15,n); aform=RNG.uniform(0,15,n)
    score=((hp-ap)*0.35+(hf-af)/100*0.20+(hform-aform)/15*0.25
           +(h2h/10)*0.10+0.10+RNG.normal(0,0.15,n))
    result=np.where(score>0.18,2,np.where(score<-0.18,0,1))
    return pd.DataFrame(dict(home_pi=hp,away_pi=ap,home_fit=hf,away_fit=af,
        h2h_wins=h2h,home_form=hform,away_form=aform,result=result))

# ── MODEL 1: INJURY ─────────────────────────────────────────────────────────

INJ_FEATS=["age","minutes","fitness","pi","matches","goals","assists","dribbles","tackles"]

def train_injury():
    df=_players(); X=df[INJ_FEATS].values; y=df["injured"].values
    p=Pipeline([("sc",StandardScaler()),
                ("clf",RandomForestClassifier(n_estimators=200,max_depth=6,
                    class_weight="balanced",random_state=42))])
    p.fit(X,y)
    auc=cross_val_score(p,X,y,cv=5,scoring="roc_auc").mean()
    return p,round(auc,3)

def predict_injury(model,row):
    vals=np.array([[row.get("Age",24),row.get("Minutes_Played",900),
        row.get("Health_Score",80),row.get("Performance_Index",5),
        row.get("Matches",10),row.get("Goals",2),row.get("Assists",2),
        row.get("Dribbles_Completed",10),row.get("Tackles_Won",10)]])
    prob=float(model.predict_proba(vals)[0][1])
    risk=("🔴 High Risk" if prob>=0.65 else "🟠 Moderate Risk" if prob>=0.40 else "🟢 Low Risk")
    imp=model.named_steps["clf"].feature_importances_
    labels={"age":"Player Age","minutes":"Minutes Load","fitness":"Fitness Score",
            "pi":"Performance Index","matches":"Matches Played",
            "goals":"Goal Workload","assists":"Creative Load",
            "dribbles":"Dribble Intensity","tackles":"Tackle Intensity"}
    top3=[labels[k] for k,_ in sorted(zip(INJ_FEATS,imp),key=lambda x:-x[1])[:3]]
    return dict(probability=prob,risk_level=risk,top_factors=top3)

# ── MODEL 2: MATCH RESULT ───────────────────────────────────────────────────

MTH_FEATS=["home_pi","away_pi","home_fit","away_fit","h2h_wins","home_form","away_form"]

def train_match():
    df=_matches(); X=df[MTH_FEATS].values; y=df["result"].values
    p=Pipeline([("sc",StandardScaler()),
                ("clf",GradientBoostingClassifier(n_estimators=250,max_depth=4,
                    learning_rate=0.08,random_state=42))])
    p.fit(X,y)
    acc=cross_val_score(p,X,y,cv=5,scoring="accuracy").mean()
    return p,round(acc,3)

def predict_match(model,ht,at,h2h=3,hform=7.0,aform=7.0):
    vals=np.array([[ht.get("avg_pi",5.5),at.get("avg_pi",5.5),
        ht.get("avg_fitness",80),at.get("avg_fitness",80),h2h,hform,aform]])
    probs=model.predict_proba(vals)[0]  # 0=Away,1=Draw,2=Home
    idx=int(np.argmax(probs))
    labels={0:"Away Win",1:"Draw",2:"Home Win"}
    return dict(home_win=round(float(probs[2])*100,1),draw=round(float(probs[1])*100,1),
                away_win=round(float(probs[0])*100,1),prediction=labels[idx],
                confidence=round(float(probs[idx])*100,1))

# ── MODEL 3: DEVELOPMENT FORECAST ──────────────────────────────────────────

DEV_FEATS=["age","pi","matches","goals","assists","pass_acc","fitness","minutes"]

def train_dev():
    df=_players(); X=df[DEV_FEATS].values
    sc=StandardScaler(); Xs=sc.fit_transform(X)
    mpi=Ridge(alpha=1.0); mmv=Ridge(alpha=1.0)
    mpi.fit(Xs,df["future_pi"].values); mmv.fit(Xs,df["future_mv"].values)
    return sc,mpi,mmv

def predict_dev(sc,mpi,mmv,row):
    vals=np.array([[row.get("Age",24),row.get("Performance_Index",5),
        row.get("Matches",10),row.get("Goals",2),row.get("Assists",2),
        row.get("Pass_Accuracy",75),row.get("Health_Score",80),row.get("Minutes_Played",900)]])
    Xs=sc.transform(vals)
    fpi=float(np.clip(mpi.predict(Xs)[0],1,10))
    fmv=float(np.clip(mmv.predict(Xs)[0],500_000,30_000_000))
    cur=row.get("Performance_Index",5); delta=round(fpi-cur,2)
    traj=("📈 Strong Growth" if delta>0.5 else "📊 Steady Progress" if delta>0.1
          else "➡️  Plateau" if delta>-0.2 else "📉 Declining")
    return dict(current_pi=round(cur,2),forecast_pi=round(fpi,2),
                delta_pi=delta,forecast_mv=round(fmv,-3),trajectory=traj)

# ── MODEL 4: TALENT CLUSTER ─────────────────────────────────────────────────

CLU_FEATS=["Performance_Index","Goals","Assists","Pass_Accuracy",
           "Dribbles_Completed","Tackles_Won","Health_Score",
           "Minutes_Played","Shots_on_Target"]

ARCHETYPES={
    0:("🌟 Elite Creator",   "#d97757"),
    1:("⚔️  Goal Threat",     "#b85e3a"),
    2:("🛡️  Defensive Anchor","#57534e"),
    3:("🔧 Engine Room",      "#92400e"),
    4:("🌱 Rising Prospect",  "#c9a84c"),
}

def train_cluster(n=5):
    df=_players(500)
    rename={"pi":"Performance_Index","goals":"Goals","assists":"Assists",
            "pass_acc":"Pass_Accuracy","dribbles":"Dribbles_Completed",
            "tackles":"Tackles_Won","fitness":"Health_Score",
            "minutes":"Minutes_Played","shots":"Shots_on_Target"}
    df=df.rename(columns=rename)
    X=df[CLU_FEATS].values
    p=Pipeline([("sc",StandardScaler()),("pca",PCA(n_components=2,random_state=42)),
                ("km",KMeans(n_clusters=n,n_init=20,random_state=42))])
    p.fit(X); return p

def cluster_players(model,pdf):
    df=pdf.copy()
    for c in CLU_FEATS:
        if c not in df.columns: df[c]=0
    X=df[CLU_FEATS].fillna(0).values
    labels=model.predict(X)
    sc=model.named_steps["sc"]; pca=model.named_steps["pca"]
    xy=pca.transform(sc.transform(X))
    df["Cluster"]=labels
    df["Archetype"]=df["Cluster"].map(lambda c:ARCHETYPES.get(c,(f"Group {c}","#999"))[0])
    df["Arch_Color"]=df["Cluster"].map(lambda c:ARCHETYPES.get(c,(f"Group {c}","#999"))[1])
    df["PCA_X"]=xy[:,0]; df["PCA_Y"]=xy[:,1]
    return df

# ── REGISTRY ────────────────────────────────────────────────────────────────

_reg={}

def get_models():
    global _reg
    if not _reg:
        im,ia=train_injury()
        mm,ma=train_match()
        ds,dp,dv=train_dev()
        cm=train_cluster()
        _reg=dict(
            injury=dict(model=im,metric=ia,label="ROC-AUC"),
            match=dict(model=mm,metric=ma,label="CV Accuracy"),
            dev=dict(scaler=ds,m_pi=dp,m_mv=dv),
            cluster=dict(model=cm),
        )
    return _reg
