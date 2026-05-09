"""
ITARA Sports Analytics Platform  v5.0
======================================
New in v5:
  • Developer portal: full activity dashboard, traceability, reports,
    players DB, feedback replies, subscription reminders, team/match edit/delete
  • Auto-logout after 5 minutes of inactivity (JS heartbeat)
  • Match log: date, venue, scorers + minutes, logo upload, edit/delete
  • Team registration: edit/delete
  • Coach Decision Center: opponent analysis + tactical recommendations
  • Charts in all portals (Plotly)
  • Role-based data confidentiality (league table shared, all else private)
  • Daily / Weekly / Monthly automated reports
  • Player delete requires password confirmation
"""

import streamlit as st
import pandas as pd
import numpy as np
import io, base64, hashlib, datetime, warnings, json
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable)
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
warnings.filterwarnings("ignore")

try:
    from ml_page import render_ml_page
    ML_OK = True
except ImportError:
    ML_OK = False

try:
    from itara_reports import (generate_agent_report,
                                generate_journalist_report,
                                generate_manager_report)
    REPORTS_OK = True
except ImportError:
    REPORTS_OK = False

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(page_title="ITARA Sports Analytics", page_icon="⚽",
                   layout="wide", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════════════════════
# AUTO-LOGOUT  — 5-minute inactivity timer via JS
# Every click resets the timer. After 300s with no click → reload.
# ══════════════════════════════════════════════════════════════
AUTO_LOGOUT_JS = """
<script>
(function(){
  var TIMEOUT = 300000; // 5 minutes in ms
  var timer;
  function resetTimer(){
    clearTimeout(timer);
    timer = setTimeout(function(){
      // Set a flag in sessionStorage then force reload
      sessionStorage.setItem('itara_autologout','1');
      window.location.reload();
    }, TIMEOUT);
  }
  // Reset on any click or keypress
  document.addEventListener('click', resetTimer, true);
  document.addEventListener('keypress', resetTimer, true);
  resetTimer();

  // On load, check if we were auto-logged out
  if(sessionStorage.getItem('itara_autologout') === '1'){
    sessionStorage.removeItem('itara_autologout');
    // Post message to Streamlit to trigger logout
    window.parent.postMessage({type:'streamlit:setComponentValue', value:'autologout'}, '*');
  }
})();
</script>
"""

# ══════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;0,9..144,800&display=swap');
:root{--bg:#f5f0e8;--bg-card:#faf7f2;--bg-dark:#1c1917;
  --accent:#d97757;--accent-dk:#b85e3a;--accent-lt:#f5e6dc;
  --text-pri:#1c1917;--text-sec:#57534e;--text-muted:#a8a29e;
  --border:#e7e0d5;--gold:#c9a84c;
  --agent:#7c3aed;--journalist:#0369a1;--manager:#065f46;--admin:#92400e;}
html,body,[class*="css"]{font-family:'Sora',sans-serif;color:var(--text-pri);}
h1,h2,h3{font-family:'Fraunces',serif!important;font-weight:800!important;
  color:var(--text-pri)!important;letter-spacing:-0.01em!important;}
.main,.stApp{background-color:var(--bg)!important;}
.block-container{padding-top:1rem!important;background-color:var(--bg)!important;}
section[data-testid="stSidebar"]{background:var(--bg-dark)!important;border-right:1px solid #2c2825;}
section[data-testid="stSidebar"] *{color:#d6d3d1!important;}
section[data-testid="stSidebar"] [data-testid="stMetricValue"]{color:var(--accent)!important;font-weight:700!important;}
section[data-testid="stSidebar"] div[data-baseweb="select"]>div{background:#2c2825!important;border-color:#3d3530!important;}
div[data-testid="metric-container"]{background:var(--bg-card);border:1px solid var(--border);
  border-radius:10px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:var(--accent)!important;font-weight:700;}
div[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;border:1px solid var(--border);}
.stButton>button{background:var(--accent);color:#fff;border:none;border-radius:8px;
  font-family:'Sora',sans-serif;font-weight:600;font-size:.88rem;padding:.5rem 1.2rem;
  transition:all .18s;box-shadow:0 2px 8px rgba(217,119,87,.25);}
.stButton>button:hover{background:var(--accent-dk);transform:translateY(-1px);}
.stDownloadButton>button{background:var(--text-pri)!important;color:var(--bg)!important;
  border:none!important;border-radius:8px!important;font-weight:600!important;}
div[data-testid="stForm"]{background:var(--bg-card);border:1px solid var(--border);
  border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.05);}
.stTabs [data-baseweb="tab-list"]{background:var(--bg-card);border:1px solid var(--border);
  border-radius:10px;gap:2px;padding:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;color:var(--text-sec);
  font-family:'Sora',sans-serif;font-weight:600;font-size:.85rem;border-radius:7px;}
.stTabs [aria-selected="true"]{background:var(--accent)!important;color:#fff!important;border-radius:7px;}
div[data-baseweb="select"]>div{background:var(--bg-card)!important;border-color:var(--border)!important;}
input,textarea{background:var(--bg-card)!important;color:var(--text-pri)!important;border-color:var(--border)!important;}
div[data-testid="stAlert"]{border-radius:10px!important;border-left:4px solid var(--accent)!important;background:var(--bg-card)!important;}
hr{border-color:var(--border)!important;}
.stCaption,small{color:var(--text-muted)!important;}
label{color:var(--text-sec)!important;font-size:.85rem!important;}
div[data-testid="stProgress"]>div>div{background:linear-gradient(90deg,var(--accent),var(--accent-dk))!important;border-radius:4px;}
.notification-banner{background:linear-gradient(135deg,#fff8f4,var(--bg-card));
  border:2px solid var(--accent);border-radius:12px;padding:16px 20px;margin-bottom:16px;}
.portal-banner{border-radius:14px;padding:26px 36px;margin-bottom:22px;
  position:relative;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.12);}
.portal-banner::before{content:'⚽';position:absolute;right:28px;top:50%;
  transform:translateY(-50%);font-size:72px;opacity:.1;}
.portal-title{font-family:'Fraunces',serif;font-size:2rem;font-weight:800;
  color:#fff;line-height:1.1;margin:0;}
.portal-sub{color:rgba(255,255,255,.75);font-size:.88rem;margin-top:8px;
  letter-spacing:.05em;text-transform:uppercase;}
.home-hero{background:linear-gradient(135deg,#1c1917 0%,#2c2218 60%,#1c1917 100%);
  border-radius:20px;padding:52px 48px;margin-bottom:32px;position:relative;
  overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.18);}
.home-tagline{font-family:'Fraunces',serif;font-size:2.5rem;font-weight:800;
  color:#fff;line-height:1.15;margin:0 0 12px;}
.home-tagline span{color:var(--accent);}
.badge-rw{display:inline-flex;align-items:center;gap:6px;background:rgba(217,119,87,.15);
  border:1px solid rgba(217,119,87,.35);border-radius:20px;padding:5px 14px;
  font-size:.78rem;color:var(--accent);font-weight:600;}
.plan-card{background:var(--bg-card);border:2px solid var(--border);border-radius:16px;
  padding:28px 20px;text-align:center;transition:all .2s;}
.plan-card.featured{border-color:var(--accent);box-shadow:0 6px 24px rgba(217,119,87,.18);}
.paywall-box{background:linear-gradient(135deg,#fff8f4,var(--bg-card));border:2px solid var(--accent);
  border-radius:16px;padding:40px 32px;text-align:center;max-width:540px;margin:0 auto;}
.mtn-badge{background:#ffcc00;color:#1c1917;font-weight:700;font-size:.9rem;
  border-radius:8px;padding:7px 18px;display:inline-block;margin-bottom:16px;}
.rb{display:inline-block;padding:3px 12px;border-radius:20px;font-size:.75rem;font-weight:700;}
.rb-agent{background:#ede9fe;color:#6d28d9;}
.rb-journalist{background:#e0f2fe;color:#0369a1;}
.rb-manager{background:#d1fae5;color:#065f46;}
.rb-teamadmin{background:#fef3c7;color:#92400e;}
.rb-developer{background:#fce7f3;color:#9d174d;}
.chip{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:700;}
.chip-green{background:#d1fae5;color:#065f46;}
.chip-yellow{background:#fef9c3;color:#854d0e;}
.chip-red{background:#fee2e2;color:#991b1b;}
.info-box{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:26px;margin-bottom:16px;}
.info-box h4{font-family:'Fraunces',serif;font-size:1.1rem;font-weight:700;color:var(--accent);margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════
ROLES         = ["Football Agent","Journalist","Team Manager/Coach","Team Administration"]
ROLE_PRICES   = {"Football Agent":"500,000","Journalist":"100,000",
                 "Team Manager/Coach":"1,000,000","Team Administration":"1,000,000"}
ROLE_COLORS   = {"Football Agent":"#7c3aed","Journalist":"#0369a1",
                 "Team Manager/Coach":"#065f46","Team Administration":"#92400e",
                 "Developer":"#d97757"}
ROLE_BADGE_CL = {"Football Agent":"rb-agent","Journalist":"rb-journalist",
                 "Team Manager/Coach":"rb-manager","Team Administration":"rb-teamadmin",
                 "Developer":"rb-developer"}
TEAM_MAX_USERS = 2
PL = dict(template='plotly_white',plot_bgcolor='#faf7f2',
          paper_bgcolor='#faf7f2',font_color='#1c1917',title_font_size=13)
CL = ['#d97757','#b85e3a','#92400e','#f0c4b0','#78716c','#c9a84c','#6b7280']
FC = {'Elite':'#d97757','Strong':'#b85e3a','Developing':'#f59e0b','Underperforming':'#ef4444'}

DEV_EMAIL    = "dev@itara.rw"
DEV_PASSWORD_HASH = None   # set after h() is defined

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def h(pw): return hashlib.sha256(pw.encode()).hexdigest()
DEV_PASSWORD_HASH = h("itara@dev2025")

def img_b64():
    try:
        with open("logo.png","rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

LOGO = img_b64()

def logo_html(w=160):
    if LOGO: return f'<img src="data:image/png;base64,{LOGO}" width="{w}" style="display:block;">'
    return '<span style="font-family:Fraunces,serif;font-size:1.6rem;font-weight:800;color:#d97757;">⚽ ITARA</span>'

def role_badge(role):
    cls = ROLE_BADGE_CL.get(role,"rb-agent")
    return f'<span class="rb {cls}">{role}</span>'

def subscribed(u): return u.get("subscribed",False)

def team_user_count(role, team):
    return sum(1 for u in st.session_state.users_db.values()
               if u.get("role")==role and u.get("team")==team)

def portal_banner(title, subtitle, color):
    st.markdown(f"""<div class="portal-banner"
        style="background:linear-gradient(135deg,{color} 0%,{color}cc 100%);">
        <div class="portal-title">{title}</div>
        <div class="portal-sub">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def now_str(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def today_str(): return datetime.date.today().strftime("%Y-%m-%d")

# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════
def _seed_users_db():
    return {
        "agent@itara.rw":{"name":"Demo Agent","role":"Football Agent","team":None,
            "pw":h("demo1234"),"subscribed":True,"sub_expires":"2026-12-31","notifications":[]},
        "journalist@itara.rw":{"name":"Demo Journalist","role":"Journalist","team":None,
            "pw":h("demo1234"),"subscribed":True,"sub_expires":"2026-12-31","notifications":[]},
        "coach@aprfc.rw":{"name":"APR FC Coach","role":"Team Manager/Coach","team":"APR FC",
            "pw":h("demo1234"),"subscribed":True,"sub_expires":"2026-12-31","notifications":[]},
        "admin@aprfc.rw":{"name":"APR FC Admin","role":"Team Administration","team":"APR FC",
            "pw":h("demo1234"),"subscribed":True,"sub_expires":"2026-12-31","notifications":[]},
        "coach2@rayonsports.rw":{"name":"Rayon Sports Coach","role":"Team Manager/Coach","team":"Rayon Sports",
            "pw":h("demo1234"),"subscribed":True,"sub_expires":"2026-12-31","notifications":[]},
        "admin2@rayonsports.rw":{"name":"Rayon Sports Admin","role":"Team Administration","team":"Rayon Sports",
            "pw":h("demo1234"),"subscribed":True,"sub_expires":"2026-12-31","notifications":[]},
    }

def init():
    defaults = {
        "page":"home","logged_in":False,"user":None,
        "selected_season":"2024/25",
        "seasons":["2022/23","2023/24","2024/25","2025/26"],
        "teams":["APR FC","Rayon Sports","Police FC","Kiyovu Sports","Mukura VS"],
        "team_logos":{},   # team_name -> base64 logo
        "feedback":[],"login_log":[],"activity_log":[],"issues_log":[],
        "last_activity": datetime.datetime.now().isoformat(),
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
    if "users_db" not in st.session_state:
        st.session_state.users_db = _seed_users_db()
    if "data" not in st.session_state:
        st.session_state.data = pd.DataFrame(columns=[
            "Player","Team","Position","Age","Goals","Assists","Matches",
            "Minutes_Played","Shots_on_Target","Pass_Accuracy",
            "Dribbles_Completed","Tackles_Won","Health_Score","Performance_Index","Season"])
    if "match_results" not in st.session_state:
        st.session_state.match_results = pd.DataFrame(columns=[
            "Home_Team","Away_Team","Home_Goals","Away_Goals","Matchday",
            "Match_Date","Venue","Home_Scorers","Away_Scorers","Season"])
    if "contracts" not in st.session_state:
        st.session_state.contracts = pd.DataFrame(columns=[
            "Player","Team","Position","Contract_Start","Contract_End","Season","Notes"])

def log_login(email, name, role, action="login"):
    st.session_state.login_log.append({
        "email":email,"name":name,"role":role,"action":action,"time":now_str()})

def log_activity(email, role, page):
    st.session_state.activity_log.append({
        "email":email,"role":role,"page":page,"time":now_str()})
    st.session_state.last_activity = datetime.datetime.now().isoformat()

def add_notification(email, message, notif_type="info"):
    """Add in-app notification to a user's queue."""
    if email in st.session_state.users_db:
        if "notifications" not in st.session_state.users_db[email]:
            st.session_state.users_db[email]["notifications"] = []
        st.session_state.users_db[email]["notifications"].append({
            "message": message, "type": notif_type,
            "time": now_str(), "read": False
        })

def check_sub_expiry_reminders():
    """Auto-send reminders to users whose subscription expires within 7 days."""
    today = datetime.date.today()
    for email, u in st.session_state.users_db.items():
        if not u.get("sub_expires"): continue
        try:
            exp = datetime.datetime.strptime(u["sub_expires"],"%Y-%m-%d").date()
            diff = (exp - today).days
            if 0 < diff <= 7:
                # Only send once per day
                notifs = u.get("notifications",[])
                already_sent = any("subscription" in n.get("message","").lower()
                                   and n.get("time","")[:10] == str(today)
                                   for n in notifs)
                if not already_sent:
                    add_notification(email,
                        f"⏰ Your ITARA subscription expires in {diff} day(s) "
                        f"({u['sub_expires']}). Please renew via MTN Mobile Money "
                        f"to maintain access. Contact dev@itara.rw if you need help.",
                        "warning")
        except: pass

init()
check_sub_expiry_reminders()

# Inject auto-logout JS
st.markdown(AUTO_LOGOUT_JS, unsafe_allow_html=True)

# Check auto-logout flag
if st.session_state.get("logged_in") and st.session_state.get("user"):
    last = datetime.datetime.fromisoformat(
        st.session_state.get("last_activity", datetime.datetime.now().isoformat()))
    if (datetime.datetime.now() - last).total_seconds() > 310:
        u_out = st.session_state.user
        if u_out:
            log_login(u_out.get("email",""), u_out.get("name",""),
                      u_out.get("role",""), "auto-logout")
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.page = "home"
        st.warning("⏱️ You were automatically logged out after 5 minutes of inactivity.")
        st.rerun()

# ══════════════════════════════════════════════════════════════
# ANALYTICS ENGINE
# ══════════════════════════════════════════════════════════════
def xG(r):
    s=max(r.get("Shots_on_Target",0),0);m=max(r.get("Matches",1),1)
    return round(s/m*0.32*m,2)
def xA(r):
    a=r.get("Assists",0);p=r.get("Pass_Accuracy",75)/100
    return round(max(a*(1+(p-0.75)),0),2)
def prog(r):
    d=r.get("Dribbles_Completed",0);t=r.get("Tackles_Won",0);m=max(r.get("Matches",1),1)
    return round(min(((d/m)*0.6+(t/m)*0.4)*1.5,10),2)
def market_val(r):
    pi=r["Performance_Index"];m=max(r.get("Matches",1),1);age=r.get("Age",25)
    af=max(0.6,1.0-abs(age-25)*0.015)
    return round((pi*1_250_000)*(1+(m*0.05))*af,-3)
def cpr(r):
    m=max(r.get("Matches",1),1)
    g=min(r.get("Goals",0)/m*10,10);a=min(r.get("Assists",0)/m*10,10)
    pa=r.get("Pass_Accuracy",75)/10;hs=r.get("Health_Score",100)/10
    pr=prog(r);pi=r.get("Performance_Index",5)
    return round(min(pi*.40+g*.20+a*.15+pa*.10+hs*.10+pr*.05,10),2)
def form_label(pi):
    if pi>=8.5:return "Elite"
    if pi>=7.0:return "Strong"
    if pi>=5.0:return "Developing"
    return "Underperforming"
def avail(hs):
    if hs>=85:return "✅ Match Ready"
    if hs>=70:return "⚠️ Light Training"
    if hs>=50:return "🟠 Monitored"
    return "🔴 Unavailable"
def contract_status(end_str):
    try:
        end=datetime.datetime.strptime(str(end_str),"%Y-%m-%d").date()
        diff=(end-datetime.date.today()).days
        if diff<0:    return "Expired","chip chip-red"
        if diff<=90:  return f"Expiring ({diff}d)","chip chip-red"
        if diff<=180: return f"Due Soon ({diff}d)","chip chip-yellow"
        return f"Active ({diff}d left)","chip chip-green"
    except: return "Unknown","chip"

def league_table(mr, teams):
    tbl={t:{"MP":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"Pts":0} for t in teams}
    for _,row in mr.iterrows():
        ht,at=row["Home_Team"],row["Away_Team"]
        hg,ag=int(row["Home_Goals"]),int(row["Away_Goals"])
        for t in [ht,at]:
            if t not in tbl: tbl[t]={"MP":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"Pts":0}
        tbl[ht]["MP"]+=1;tbl[at]["MP"]+=1
        tbl[ht]["GF"]+=hg;tbl[ht]["GA"]+=ag;tbl[at]["GF"]+=ag;tbl[at]["GA"]+=hg
        if hg>ag:   tbl[ht]["W"]+=1;tbl[ht]["Pts"]+=3;tbl[at]["L"]+=1
        elif hg==ag:tbl[ht]["D"]+=1;tbl[ht]["Pts"]+=1;tbl[at]["D"]+=1;tbl[at]["Pts"]+=1
        else:       tbl[at]["W"]+=1;tbl[at]["Pts"]+=3;tbl[ht]["L"]+=1
    for t in tbl:tbl[t]["GD"]=tbl[t]["GF"]-tbl[t]["GA"]
    df=pd.DataFrame(tbl).T.reset_index().rename(columns={"index":"Club"})
    df=df.sort_values(["Pts","GD","GF"],ascending=False).reset_index(drop=True)
    df.index=df.index+1;df.index.name="Pos";return df

def season_df(season):
    df=st.session_state.data.copy()
    if "Season" in df.columns and season!="All Seasons":df=df[df["Season"]==season]
    return df
def team_df(season,team):
    df=season_df(season)
    if team:df=df[df["Team"]==team]
    return df
def season_mr(season):
    mr=st.session_state.match_results.copy()
    if "Season" in mr.columns and season!="All Seasons":mr=mr[mr["Season"]==season]
    return mr
def get_ldf(season):
    mr=season_mr(season)
    if not mr.empty:return league_table(mr,st.session_state.teams).reset_index()
    return None

# ══════════════════════════════════════════════════════════════
# NOTIFICATION BANNER — shown at top of every portal page
# ══════════════════════════════════════════════════════════════
def show_notifications(user_email):
    if user_email not in st.session_state.users_db: return
    notifs = st.session_state.users_db[user_email].get("notifications",[])
    unread = [n for n in notifs if not n.get("read")]
    if not unread: return
    for i,n in enumerate(unread):
        icon = "⚠️" if n["type"]=="warning" else "📩" if n["type"]=="reply" else "ℹ️"
        bg = "#fff8f4" if n["type"]=="warning" else "#e0f2fe" if n["type"]=="reply" else "#faf7f2"
        border = "#d97757" if n["type"]=="warning" else "#0369a1" if n["type"]=="reply" else "#e7e0d5"
        st.markdown(f"""<div style='background:{bg};border:2px solid {border};
            border-radius:10px;padding:12px 16px;margin-bottom:8px;'>
            {icon} {n['message']}<br>
            <span style='font-size:.72rem;color:#a8a29e;'>{n['time']}</span>
        </div>""", unsafe_allow_html=True)
        # Mark as read
        st.session_state.users_db[user_email]["notifications"][
            notifs.index(n)]["read"] = True

# ══════════════════════════════════════════════════════════════
# SHARED SIDEBAR
# ══════════════════════════════════════════════════════════════
def render_sidebar(u, nav_opts):
    role=u["role"]
    with st.sidebar:
        st.markdown(f"<div style='text-align:center;padding:6px 0 4px;'>{logo_html(120)}</div>",
                    unsafe_allow_html=True)
        st.markdown(f"""<div style='text-align:center;padding-bottom:12px;border-bottom:1px solid #2c2825;'>
          <div style='color:#d6d3d1;font-size:.85rem;font-weight:600;margin-top:6px;'>{u['name']}</div>
          <div style='margin-top:4px;'>{role_badge(role)}</div>
          {'<div style="color:#78716c;font-size:.72rem;margin-top:3px;">'+str(u.get('team',''))+'</div>' if u.get('team') else ''}
        </div>""", unsafe_allow_html=True)
        season=st.selectbox("📅 Season",
            ["All Seasons"]+st.session_state.seasons,
            index=(["All Seasons"]+st.session_state.seasons).index(
                st.session_state.selected_season)
            if st.session_state.selected_season in ["All Seasons"]+st.session_state.seasons else 0)
        st.session_state.selected_season=season
        nav=st.selectbox("Navigation",nav_opts)
        st.markdown("---")
        st.metric("Players",len(st.session_state.data))
        st.metric("Teams",len(st.session_state.teams))
        st.metric("Matches",len(st.session_state.match_results))
        st.caption(f"Sub expires: {u.get('sub_expires','N/A')}")
        st.markdown("---")
        if st.button("🚪 Sign Out"):
            log_login(u.get("email",""),u.get("name",""),u.get("role",""),"logout")
            st.session_state.logged_in=False;st.session_state.user=None
            st.session_state.page="home";st.rerun()
        st.caption("ITARA · African Football Intelligence · 🇷🇼")
    # Track activity
    log_activity(u.get("email",""),role,nav)
    st.session_state.last_activity = datetime.datetime.now().isoformat()
    return nav, season

# ══════════════════════════════════════════════════════════════
# SHARED LEAGUE TABLE VIEW (read-only for all users)
# ══════════════════════════════════════════════════════════════
def render_league_table(season):
    mr=season_mr(season)
    if not mr.empty:
        ldf=league_table(mr,st.session_state.teams)
        st.markdown("**W=3 · D=1 · L=0 · Sorted by Pts → GD → GF**")
        def slt(df):
            return df.style.apply(lambda r:[
                "background-color:#fff3ee;color:#d97757;font-weight:bold" if r.name==1
                else "background-color:#fff5f5;color:#ef4444" if r.name>=len(df)-1
                else "" for _ in r],axis=1)
        st.dataframe(slt(ldf),use_container_width=True,height=280)
        col1,col2=st.columns(2)
        with col1:
            fig=px.bar(ldf.reset_index(),x="Club",y="Pts",color="Pts",
                color_continuous_scale="Oranges",title="Points Tally",text="Pts")
            fig.update_traces(textposition="outside");fig.update_layout(**PL,showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
        with col2:
            fig2=px.bar(ldf.reset_index(),x="Club",y="GD",color="GD",
                color_continuous_scale="RdYlGn",title="Goal Difference",text="GD")
            fig2.update_traces(textposition="outside");fig2.update_layout(**PL,showlegend=False)
            st.plotly_chart(fig2,use_container_width=True)
    else:
        st.info("No match results for this season.")

# ══════════════════════════════════════════════════════════════
# MATCH LOG — enhanced with date, venue, scorers, edit/delete
# ══════════════════════════════════════════════════════════════
def render_match_log(season, allow_edit=False):
    """Full match log with enhanced fields. allow_edit=True for Manager/Dev."""
    with st.expander("➕ Log New Match Result", expanded=False):
        with st.form("match_form_v2"):
            r1=st.columns(3)
            hm=r1[0].selectbox("🏠 Home Team",st.session_state.teams,key="mf_hm")
            md=r1[1].number_input("Matchday",1,50,1)
            aw=r1[2].selectbox("✈️ Away Team",
                [t for t in st.session_state.teams if t!=hm]+[hm],key="mf_aw")
            r2=st.columns(4)
            hg=r2[0].number_input("Home Goals",0,20,0)
            ag=r2[1].number_input("Away Goals",0,20,0)
            match_date=r2[2].date_input("Match Date",value=datetime.date.today())
            venue=r2[3].text_input("Venue / Stadium","")
            r3=st.columns(2)
            home_scorers=r3[0].text_area("Home Scorers (Name - Min, ...)",
                placeholder="e.g. Hakizimana - 23', Nshuti - 67'",height=60)
            away_scorers=r3[1].text_area("Away Scorers (Name - Min, ...)",
                placeholder="e.g. Mugisha - 45'",height=60)
            if st.form_submit_button("📝 Log Result"):
                if hm!=aw:
                    new_match={"Home_Team":hm,"Away_Team":aw,
                        "Home_Goals":hg,"Away_Goals":ag,"Matchday":md,
                        "Match_Date":str(match_date),"Venue":venue,
                        "Home_Scorers":home_scorers,"Away_Scorers":away_scorers,
                        "Season":season}
                    st.session_state.match_results=pd.concat(
                        [st.session_state.match_results,pd.DataFrame([new_match])],
                        ignore_index=True)
                    log_activity(st.session_state.user.get("email",""),
                        st.session_state.user.get("role",""),
                        f"Logged match: {hm} {hg}-{ag} {aw}")
                    st.success(f"✅ {hm} {hg}–{ag} {aw} on {match_date} @ {venue or 'TBD'}")
                    st.rerun()
                else:
                    st.error("Home and Away teams must differ.")

    mr=season_mr(season)
    if not mr.empty:
        st.markdown(f"**{len(mr)} matches logged**")
        # Display with edit/delete
        for i,row in mr.iterrows():
            with st.container():
                c1,c2,c3=st.columns([5,1,1])
                date_str=row.get("Match_Date","") or ""
                venue_str=row.get("Venue","") or ""
                hsc=row.get("Home_Scorers","") or ""
                asc=row.get("Away_Scorers","") or ""
                c1.markdown(
                    f"**MD{row.get('Matchday','')}** · {date_str} · "
                    f"**{row['Home_Team']}** {row['Home_Goals']} – {row['Away_Goals']} "
                    f"**{row['Away_Team']}**"
                    f"{(' · 📍 '+venue_str) if venue_str else ''}"
                    f"{(' · ⚽ '+hsc) if hsc else ''}"
                    f"{(' / '+asc) if asc else ''}")
                if allow_edit:
                    if c2.button("✏️",key=f"edit_m_{i}",help="Edit"):
                        st.session_state[f"editing_match_{i}"] = True
                    if c3.button("🗑️",key=f"del_m_{i}",help="Delete"):
                        st.session_state.match_results=st.session_state.match_results.drop(i).reset_index(drop=True)
                        log_activity(st.session_state.user.get("email",""),
                            st.session_state.user.get("role",""),f"Deleted match row {i}")
                        st.rerun()
                # Inline edit form
                if allow_edit and st.session_state.get(f"editing_match_{i}"):
                    with st.form(f"edit_match_{i}"):
                        ec=st.columns(4)
                        new_hg=ec[0].number_input("Home Goals",0,20,int(row["Home_Goals"]))
                        new_ag=ec[1].number_input("Away Goals",0,20,int(row["Away_Goals"]))
                        new_date=ec[2].text_input("Date",str(date_str))
                        new_venue=ec[3].text_input("Venue",str(venue_str))
                        new_hsc=st.text_input("Home Scorers",str(hsc))
                        new_asc=st.text_input("Away Scorers",str(asc))
                        if st.form_submit_button("💾 Save"):
                            st.session_state.match_results.at[i,"Home_Goals"]=new_hg
                            st.session_state.match_results.at[i,"Away_Goals"]=new_ag
                            st.session_state.match_results.at[i,"Match_Date"]=new_date
                            st.session_state.match_results.at[i,"Venue"]=new_venue
                            st.session_state.match_results.at[i,"Home_Scorers"]=new_hsc
                            st.session_state.match_results.at[i,"Away_Scorers"]=new_asc
                            del st.session_state[f"editing_match_{i}"]
                            st.rerun()
    else:
        st.info("No match results yet.")

# ══════════════════════════════════════════════════════════════
# TEAM MANAGEMENT (for developer — edit/delete teams + logos)
# ══════════════════════════════════════════════════════════════
def render_team_management():
    st.markdown("#### Team Registry")
    c1,c2=st.columns(2)
    with c1:
        with st.form("add_team_form"):
            nt=st.text_input("New Team Name")
            logo_file=st.file_uploader("Upload Team Logo (PNG)",type=["png","jpg","jpeg"])
            if st.form_submit_button("➕ Register Team"):
                if nt and nt not in st.session_state.teams:
                    st.session_state.teams.append(nt)
                    if logo_file:
                        st.session_state.team_logos[nt]=base64.b64encode(
                            logo_file.read()).decode()
                    log_activity(st.session_state.user.get("email",""),
                        "Developer",f"Added team: {nt}")
                    st.success(f"✅ {nt} registered!")
                    st.rerun()
                elif nt in st.session_state.teams:
                    st.warning("Team already exists.")

    st.markdown("**Registered Teams:**")
    for t in st.session_state.teams:
        tc1,tc2,tc3,tc4=st.columns([3,1,1,1])
        logo_b64=st.session_state.team_logos.get(t)
        if logo_b64:
            tc1.markdown(
                f'<img src="data:image/png;base64,{logo_b64}" height="28" style="vertical-align:middle;margin-right:8px;">'
                f'**{t}**',unsafe_allow_html=True)
        else:
            tc1.markdown(f"🏟️ **{t}**")
        # Upload/update logo
        logo_up=tc2.file_uploader("Logo",type=["png","jpg","jpeg"],
            key=f"logo_{t}",label_visibility="collapsed")
        if logo_up:
            st.session_state.team_logos[t]=base64.b64encode(logo_up.read()).decode()
            st.rerun()
        if tc3.button("✏️",key=f"ren_{t}",help="Rename"):
            st.session_state[f"renaming_{t}"]=True
        if tc4.button("🗑️",key=f"del_t_{t}",help="Delete"):
            st.session_state.teams.remove(t)
            if t in st.session_state.team_logos:
                del st.session_state.team_logos[t]
            log_activity(st.session_state.user.get("email",""),
                "Developer",f"Deleted team: {t}")
            st.rerun()
        if st.session_state.get(f"renaming_{t}"):
            with st.form(f"ren_form_{t}"):
                new_name=st.text_input("New name",value=t)
                if st.form_submit_button("Save"):
                    idx=st.session_state.teams.index(t)
                    st.session_state.teams[idx]=new_name
                    if t in st.session_state.team_logos:
                        st.session_state.team_logos[new_name]=st.session_state.team_logos.pop(t)
                    del st.session_state[f"renaming_{t}"]
                    st.rerun()

# ══════════════════════════════════════════════════════════════
# AUTOMATED REPORT GENERATOR (Daily / Weekly / Monthly)
# ══════════════════════════════════════════════════════════════
def generate_system_report(period="daily"):
    """Generates a PDF system activity report for the developer."""
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=0.7*inch,rightMargin=0.7*inch,
                          topMargin=0.65*inch,bottomMargin=0.65*inch)
    styles=getSampleStyleSheet()
    T=ParagraphStyle("T",parent=styles["Title"],fontSize=16,alignment=TA_CENTER,
                     textColor=rl_colors.HexColor("#d97757"),spaceAfter=4)
    S=ParagraphStyle("S",parent=styles["Normal"],fontSize=8,alignment=TA_CENTER,
                     textColor=rl_colors.HexColor("#57534e"),spaceAfter=6)
    H=ParagraphStyle("H",parent=styles["Heading2"],fontSize=11,
                     textColor=rl_colors.HexColor("#b85e3a"),spaceBefore=10,spaceAfter=5)
    N=ParagraphStyle("N",parent=styles["Normal"],fontSize=7.5,
                     textColor=rl_colors.HexColor("#57534e"),leading=11)
    els=[]

    # Determine date range
    today=datetime.date.today()
    if period=="daily":
        since=today; label="Daily Report"
    elif period=="weekly":
        since=today-datetime.timedelta(days=7); label="Weekly Report"
    else:
        since=today-datetime.timedelta(days=30); label="Monthly Report"

    els.append(Paragraph("ITARA SPORTS ANALYTICS",T))
    els.append(Paragraph(f"Developer System {label} — {since} to {today}",S))
    els.append(Paragraph("🇷🇼 Made in Rwanda · Confidential — Developer Use Only",S))
    els.append(Spacer(1,0.15*inch))

    def ts_table(data,hdr):
        t=Table([hdr]+data,repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),rl_colors.HexColor("#d97757")),
            ("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),7.5),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("GRID",(0,0),(-1,-1),0.3,rl_colors.HexColor("#e7e0d5")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[rl_colors.white,rl_colors.HexColor("#faf7f2")]),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ]))
        return t

    # User stats
    db=st.session_state.users_db
    els.append(Paragraph("Platform User Summary",H))
    roles={}
    for u in db.values(): roles[u.get("role","?")] = roles.get(u.get("role","?"),0)+1
    ud=[[r,str(c),str(sum(1 for x in db.values()
        if x.get("role")==r and x.get("subscribed")))] for r,c in roles.items()]
    els.append(ts_table(ud,["Role","Total Users","Subscribed"]))
    els.append(Spacer(1,0.1*inch))

    # Login activity
    els.append(Paragraph(f"Login Activity ({label})",H))
    ll=st.session_state.login_log
    filtered_ll=[x for x in ll if x.get("time","")[:10]>=str(since)]
    if filtered_ll:
        ld=[[x["time"],x.get("email",""),x.get("role",""),x.get("action","")]
            for x in filtered_ll[-30:]]
        els.append(ts_table(ld,["Time","Email","Role","Action"]))
    else:
        els.append(Paragraph("No login events in this period.",N))
    els.append(Spacer(1,0.1*inch))

    # Activity log
    els.append(Paragraph(f"System Activity ({label})",H))
    al=st.session_state.activity_log
    filtered_al=[x for x in al if x.get("time","")[:10]>=str(since)]
    if filtered_al:
        ad=[[x["time"],x.get("email",""),x.get("role",""),x.get("page","")]
            for x in filtered_al[-30:]]
        els.append(ts_table(ad,["Time","Email","Role","Action / Page"]))
    else:
        els.append(Paragraph("No activity in this period.",N))
    els.append(Spacer(1,0.1*inch))

    # Player database
    els.append(Paragraph("Players Database",H))
    df=st.session_state.data
    els.append(Paragraph(
        f"Total players: {len(df)} | "
        f"Teams represented: {df['Team'].nunique() if not df.empty else 0} | "
        f"Seasons: {', '.join(df['Season'].unique()) if not df.empty and 'Season' in df.columns else 'N/A'}",N))
    els.append(Spacer(1,0.1*inch))

    # Match results
    els.append(Paragraph("Match Results",H))
    mr=st.session_state.match_results
    els.append(Paragraph(f"Total matches logged: {len(mr)}",N))
    if not mr.empty:
        md=[[str(r.get("Matchday","")),str(r.get("Match_Date","")),
             r["Home_Team"],f"{r['Home_Goals']}-{r['Away_Goals']}",
             r["Away_Team"],str(r.get("Venue",""))]
            for _,r in mr.tail(10).iterrows()]
        els.append(ts_table(md,["MD","Date","Home","Score","Away","Venue"]))
    els.append(Spacer(1,0.1*inch))

    # Feedback
    els.append(Paragraph("Feedback Received",H))
    fb=st.session_state.feedback
    if fb:
        fbd=[[x.get("name",""),x.get("role",""),
              str(x.get("rating",""))+" ⭐",
              (x.get("message","")[:60]+"...") if len(x.get("message",""))>60
              else x.get("message",""),x.get("time","")]
             for x in fb[-10:]]
        els.append(ts_table(fbd,["Name","Role","Rating","Message","Time"]))
    else:
        els.append(Paragraph("No feedback received.",N))

    doc.build(els)
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════
# PDF HELPERS
# ══════════════════════════════════════════════════════════════
def _pdf_styles():
    s=getSampleStyleSheet()
    T=ParagraphStyle("T",parent=s["Title"],fontSize=16,alignment=TA_CENTER,
                     textColor=rl_colors.HexColor("#d97757"),spaceAfter=4)
    S=ParagraphStyle("S",parent=s["Normal"],fontSize=8,alignment=TA_CENTER,
                     textColor=rl_colors.HexColor("#57534e"),spaceAfter=6)
    H=ParagraphStyle("H",parent=s["Heading2"],fontSize=11,
                     textColor=rl_colors.HexColor("#b85e3a"),spaceBefore=10,spaceAfter=5)
    N=ParagraphStyle("N",parent=s["Normal"],fontSize=7,textColor=rl_colors.HexColor("#78716c"))
    return T,S,H,N
def _ts():
    return TableStyle([
        ("BACKGROUND",(0,0),(-1,0),rl_colors.HexColor("#d97757")),
        ("TEXTCOLOR",(0,0),(-1,0),rl_colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),8),("FONTSIZE",(0,1),(-1,-1),7.5),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),.4,rl_colors.HexColor("#e7e0d5")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[rl_colors.white,rl_colors.HexColor("#faf7f2")]),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ])
def make_pdf_agent(df,season):
    if REPORTS_OK:
        return generate_agent_report(df.to_dict("records"),
            st.session_state.user.get("name","Agent"),season)
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=0.6*inch,rightMargin=0.6*inch,
                          topMargin=0.6*inch,bottomMargin=0.6*inch)
    T,S,H,N=_pdf_styles();els=[]
    els.append(Paragraph("ITARA SPORTS ANALYTICS",T))
    els.append(Paragraph(f"Football Agent Report | Season {season}",S))
    df2=df.copy();df2["CPR"]=df2.apply(cpr,axis=1);df2["MV"]=df2.apply(market_val,axis=1)
    df2["Form"]=df2["Performance_Index"].apply(form_label);df2=df2.sort_values("CPR",ascending=False)
    els.append(Paragraph("Player Intelligence",H))
    hdr=["Player","Team","Pos","CPR","PI","Goals","Assists","Fitness","Form","Value(RWF)"]
    data=[hdr]+[[r.get("Player",""),r.get("Team",""),r.get("Position",""),
        f"{r['CPR']:.1f}",f"{r['Performance_Index']:.1f}",
        int(r.get("Goals",0)),int(r.get("Assists",0)),
        f"{r.get('Health_Score',0):.0f}%",r["Form"],f"{int(r['MV']):,}"]
        for _,r in df2.iterrows()]
    t=Table(data,repeatRows=1);t.setStyle(_ts());els.append(t)
    doc.build(els);return buf.getvalue()

def make_pdf_journalist(df,mr,season):
    if REPORTS_OK:
        return generate_journalist_report(df.to_dict("records"),
            mr.to_dict("records") if not mr.empty else [],
            st.session_state.user.get("name","Journalist"),season)
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=0.6*inch,rightMargin=0.6*inch,
                          topMargin=0.6*inch,bottomMargin=0.6*inch)
    T,S,H,N=_pdf_styles();els=[]
    els.append(Paragraph("ITARA SPORTS ANALYTICS",T))
    els.append(Paragraph(f"Media Intelligence Pack | Season {season}",S))
    ldf=get_ldf(season)
    if ldf is not None:
        els.append(Paragraph("League Standings",H))
        lt=Table([list(ldf.columns)]+[[str(v) for v in r] for _,r in ldf.iterrows()],repeatRows=1)
        lt.setStyle(_ts());els.append(lt)
    doc.build(els);return buf.getvalue()

def make_pdf_manager(df,team,season):
    if REPORTS_OK:
        ldf=get_ldf(season)
        mr=season_mr(season)
        ct=st.session_state.contracts
        ct_team=ct[ct["Team"]==team].to_dict("records") if not ct.empty else []
        return generate_manager_report(df.to_dict("records"),
            mr.to_dict("records") if not mr.empty else [],
            ct_team,st.session_state.user.get("name","Coach"),team,season)
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=0.6*inch,rightMargin=0.6*inch,
                          topMargin=0.6*inch,bottomMargin=0.6*inch)
    T,S,H,N=_pdf_styles();els=[]
    els.append(Paragraph("ITARA SPORTS ANALYTICS",T))
    els.append(Paragraph(f"Team Tactical Dossier — {team} | Season {season}",S))
    df2=df.copy();df2["CPR"]=df2.apply(cpr,axis=1)
    hdr=["Player","Pos","Age","CPR","PI","Goals","Assists","Fitness","Form"]
    data=[hdr]+[[r.get("Player",""),r.get("Position",""),int(r.get("Age",0)),
        f"{r['CPR']:.1f}",f"{r['Performance_Index']:.1f}",
        int(r.get("Goals",0)),int(r.get("Assists",0)),
        f"{r.get('Health_Score',0):.0f}%",form_label(r["Performance_Index"])]
        for _,r in df2.iterrows()]
    t=Table(data,repeatRows=1);t.setStyle(_ts());els.append(t)
    doc.build(els);return buf.getvalue()

# ══════════════════════════════════════════════════════════════
# ████  DEVELOPER PORTAL  ████
# ══════════════════════════════════════════════════════════════
def pg_developer():
    u=st.session_state.user
    with st.sidebar:
        st.markdown(f"<div style='text-align:center;padding:6px 0 4px;'>{logo_html(120)}</div>",
                    unsafe_allow_html=True)
        st.markdown("""<div style='text-align:center;padding-bottom:12px;border-bottom:1px solid #2c2825;'>
            <div style='color:#d97757;font-size:.9rem;font-weight:700;margin-top:8px;'>🛠️ DEVELOPER</div>
            <div style='color:#78716c;font-size:.72rem;'>ITARA Internal</div>
        </div>""",unsafe_allow_html=True)
        dev_nav=st.selectbox("Section",[
            "📊 Dashboard",
            "👥 User Management",
            "🏈 Players Database",
            "📅 Data Management",
            "🏆 League Table",
            "📤 Export Center",
        ])
        st.markdown("---")
        st.metric("Users",len(st.session_state.users_db))
        st.metric("Players",len(st.session_state.data))
        st.metric("Matches",len(st.session_state.match_results))
        st.metric("Feedbacks",len(st.session_state.feedback))
        st.markdown("---")
        if st.button("🚪 Sign Out"):
            log_login(DEV_EMAIL,"ITARA Developer","Developer","logout")
            st.session_state.logged_in=False;st.session_state.user=None
            st.session_state.page="home";st.rerun()
        st.caption("ITARA Developer · 🇷🇼")
    log_activity(DEV_EMAIL,"Developer",dev_nav)
    st.session_state.last_activity=datetime.datetime.now().isoformat()

    # ── DASHBOARD ──────────────────────────────────────────────
    if dev_nav=="📊 Dashboard":
        st.markdown("""<div style='background:linear-gradient(135deg,#1c1917,#2c2218);
            border-radius:14px;padding:28px 36px;margin-bottom:24px;'>
            <div style='font-family:Fraunces,serif;font-size:2rem;font-weight:800;color:#d97757;'>
                🛠️ Developer Dashboard — ITARA Platform</div>
            <div style='color:#a8a29e;font-size:.85rem;margin-top:6px;'>
                Full system visibility · Activity traceability · Real-time monitoring</div>
        </div>""",unsafe_allow_html=True)

        db=st.session_state.users_db
        sub_count=sum(1 for u2 in db.values() if u2.get("subscribed"))
        expiring=sum(1 for u2 in db.values()
            if u2.get("sub_expires") and
            0 < (datetime.datetime.strptime(u2["sub_expires"],"%Y-%m-%d").date()
                 -datetime.date.today()).days <= 7)

        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("👥 Total Users",len(db))
        c2.metric("✅ Subscribed",sub_count)
        c3.metric("⚠️ Expiring Soon",expiring)
        c4.metric("👤 Players",len(st.session_state.data))
        c5.metric("📅 Matches",len(st.session_state.match_results))
        c6.metric("💬 Feedbacks",len(st.session_state.feedback))
        st.markdown("---")

        tab1,tab2,tab3,tab4,tab5=st.tabs([
            "📈 Activity Charts","🔐 Login Trace",
            "🗂️ Action Log","💬 Feedback","🐛 Issues"])

        with tab1:
            col1,col2=st.columns(2)
            with col1:
                # Users by role pie
                roles={}
                for u2 in db.values():
                    roles[u2.get("role","?")] = roles.get(u2.get("role","?"),0)+1
                if roles:
                    fig=px.pie(values=list(roles.values()),names=list(roles.keys()),
                        title="Users by Role",color_discrete_sequence=CL)
                    fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with col2:
                # Subscription status bar
                sub_data={"Active":sub_count,"Inactive":len(db)-sub_count}
                fig2=px.bar(x=list(sub_data.keys()),y=list(sub_data.values()),
                    title="Subscription Status",
                    color=list(sub_data.keys()),
                    color_discrete_map={"Active":"#22c55e","Inactive":"#ef4444"})
                fig2.update_layout(**PL,showlegend=False);st.plotly_chart(fig2,use_container_width=True)
            col3,col4=st.columns(2)
            with col3:
                # Login activity over time
                ll=st.session_state.login_log
                if ll:
                    ldf=pd.DataFrame(ll)
                    ldf["date"]=ldf["time"].str[:10]
                    daily=ldf.groupby("date").size().reset_index(name="count")
                    fig3=px.line(daily,x="date",y="count",
                        title="Daily Login Activity",markers=True,
                        color_discrete_sequence=["#d97757"])
                    fig3.update_layout(**PL);st.plotly_chart(fig3,use_container_width=True)
                else:
                    st.info("No login data yet.")
            with col4:
                # Activity by role
                al=st.session_state.activity_log
                if al:
                    adf=pd.DataFrame(al)
                    role_act=adf["role"].value_counts().reset_index()
                    role_act.columns=["Role","Actions"]
                    fig4=px.bar(role_act,x="Role",y="Actions",
                        title="Actions by Role",color="Role",
                        color_discrete_sequence=CL)
                    fig4.update_layout(**PL,showlegend=False)
                    st.plotly_chart(fig4,use_container_width=True)
                else:
                    st.info("No activity data yet.")

        with tab2:
            st.markdown("**🔐 Full Login & Logout Trace**")
            ll=st.session_state.login_log
            if ll:
                ldf=pd.DataFrame(ll).sort_values("time",ascending=False)
                # Filter options
                fc1,fc2=st.columns(2)
                role_f=fc1.selectbox("Filter by Role",["All"]+list(ldf["role"].unique()))
                action_f=fc2.selectbox("Filter by Action",["All","login","logout","auto-logout","register"])
                fdf=ldf.copy()
                if role_f!="All":fdf=fdf[fdf["role"]==role_f]
                if action_f!="All":fdf=fdf[fdf["action"]==action_f]
                st.markdown(f"**{len(fdf)} events**")
                st.dataframe(fdf,use_container_width=True,height=400)
                st.download_button("📥 Export Login Log",fdf.to_csv(index=False).encode(),
                    "ITARA_Login_Log.csv","text/csv")
            else:
                st.info("No login events yet.")

        with tab3:
            st.markdown("**🗂️ Full Activity Trace — Who Did What & When**")
            al=st.session_state.activity_log
            if al:
                adf=pd.DataFrame(al).sort_values("time",ascending=False)
                fc1,fc2=st.columns(2)
                role_f=fc1.selectbox("Filter",["All"]+list(adf["role"].unique()),key="af_r")
                email_f=fc2.selectbox("User",["All"]+list(adf["email"].unique()),key="af_e")
                fdf=adf.copy()
                if role_f!="All":fdf=fdf[fdf["role"]==role_f]
                if email_f!="All":fdf=fdf[fdf["email"]==email_f]
                st.dataframe(fdf,use_container_width=True,height=400)
                st.download_button("📥 Export Activity Log",fdf.to_csv(index=False).encode(),
                    "ITARA_Activity_Log.csv","text/csv")
            else:
                st.info("No activity recorded yet.")

        with tab4:
            st.markdown("**💬 Feedback Inbox**")
            fb=st.session_state.feedback
            if fb:
                fdf=pd.DataFrame(fb).sort_values("time",ascending=False)
                c1,c2=st.columns(2)
                c1.metric("Total",len(fdf))
                if "rating" in fdf.columns:
                    c2.metric("Avg Rating",f"{fdf['rating'].mean():.1f}/5")
                # Rating chart
                if "rating" in fdf.columns:
                    fig=px.histogram(fdf,x="rating",nbins=5,
                        title="Rating Distribution",
                        color_discrete_sequence=["#d97757"])
                    fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
                # Reply to feedback
                for i,row in fdf.iterrows():
                    stars="⭐"*int(row.get("rating",0))
                    with st.expander(
                        f"{row.get('name','?')} — {row.get('role','')} — {row.get('time','')} {stars}"):
                        st.markdown(f"**Email:** {row.get('email','—')}")
                        st.markdown(f"**Message:** {row.get('message','')}")
                        # Reply form
                        reply=st.text_area("Reply to this user",key=f"reply_{i}",height=80)
                        if st.button("📩 Send Reply",key=f"send_reply_{i}"):
                            if reply and row.get("email") and row["email"] in st.session_state.users_db:
                                add_notification(row["email"],
                                    f"📩 Reply from ITARA Developer: {reply}","reply")
                                st.success(f"✅ Reply sent to {row['email']}")
                            elif reply:
                                st.warning("User email not in system — reply not deliverable in-app.")
            else:
                st.info("No feedback yet.")

        with tab5:
            st.markdown("**🐛 Issues Tracker**")
            with st.expander("➕ Log a New Issue"):
                with st.form("dev_issue"):
                    it=st.text_input("Issue Title")
                    id_=st.text_area("Description",height=80)
                    isev=st.selectbox("Severity",["🟢 Low","🟡 Medium","🔴 High","🚨 Critical"])
                    if st.form_submit_button("Log Issue"):
                        if it:
                            st.session_state.issues_log.append({
                                "email":DEV_EMAIL,"role":"Developer",
                                "title":it,"description":id_,
                                "severity":isev,"status":"Open","time":now_str()})
                            st.success("Issue logged.")
            if st.session_state.issues_log:
                idf=pd.DataFrame(st.session_state.issues_log).sort_values("time",ascending=False)
                def cs(v):
                    if "Critical" in str(v):return "background-color:#fee2e2;color:#991b1b;font-weight:700"
                    if "High" in str(v):return "background-color:#fed7aa;color:#9a3412;font-weight:700"
                    if "Medium" in str(v):return "background-color:#fef9c3;color:#854d0e"
                    return "background-color:#d1fae5;color:#065f46"
                def css2(v):
                    if v=="Resolved":return "background-color:#d1fae5;color:#065f46;font-weight:700"
                    if v=="In Progress":return "background-color:#dbeafe;color:#1e40af"
                    return "color:#ef4444;font-weight:700"
                cols_show=["title","role","severity","status","time"]
                cols_show=[c for c in cols_show if c in idf.columns]
                st.dataframe(idf[cols_show].style
                    .applymap(cs,subset=["severity"] if "severity" in idf.columns else [])
                    .applymap(css2,subset=["status"] if "status" in idf.columns else []),
                    use_container_width=True)
                with st.form("issue_update"):
                    idx=st.number_input("Issue index to update",0,max(len(idf)-1,0),0)
                    new_st=st.selectbox("New Status",["Open","In Progress","Resolved","Won't Fix"])
                    if st.form_submit_button("Update"):
                        if 0<=idx<len(st.session_state.issues_log):
                            st.session_state.issues_log[int(idx)]["status"]=new_st
                            st.success("Updated.");st.rerun()

    # ── USER MANAGEMENT ────────────────────────────────────────
    elif dev_nav=="👥 User Management":
        st.subheader("👥 User Management")
        db=st.session_state.users_db
        rows=[{"Email":e,"Name":u2.get("name",""),"Role":u2.get("role",""),
               "Team":u2.get("team","—"),"Subscribed":"✅" if u2.get("subscribed") else "❌",
               "Expires":u2.get("sub_expires","—")}
              for e,u2 in db.items()]
        st.markdown(f"**{len(rows)} accounts**")
        st.dataframe(pd.DataFrame(rows),use_container_width=True)
        st.markdown("---")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("**Toggle Subscription**")
            with st.form("sub_toggle"):
                te=st.selectbox("User",list(db.keys()))
                ns=st.radio("Status",["Active ✅","Inactive ❌"])
                ed=st.date_input("Expiry",value=datetime.date.today()+datetime.timedelta(days=30))
                if st.form_submit_button("Apply"):
                    is_sub="Active" in ns
                    db[te]["subscribed"]=is_sub
                    db[te]["sub_expires"]=str(ed)
                    if is_sub:
                        add_notification(te,
                            f"✅ Your ITARA subscription is now active until {ed}. Welcome back!","info")
                    st.success(f"Updated {te}");st.rerun()
        with c2:
            st.markdown("**Reset Password**")
            with st.form("reset_pw"):
                re_e=st.selectbox("User",list(db.keys()),key="rpe")
                np_=st.text_input("New Password",type="password")
                np2=st.text_input("Confirm",type="password")
                if st.form_submit_button("Reset"):
                    if np_ and np_==np2:
                        db[re_e]["pw"]=h(np_)
                        st.success(f"Password reset for {re_e}")
                    else:st.error("Passwords must match.")
        with c3:
            st.markdown("**Delete Account**")
            with st.form("del_acc"):
                de=st.selectbox("Account",[e for e in db.keys() if e!=DEV_EMAIL],key="da")
                conf=st.text_input("Type DELETE")
                if st.form_submit_button("🗑️ Delete"):
                    if conf=="DELETE":
                        del db[de];st.success(f"Deleted {de}");st.rerun()
                    else:st.error("Type DELETE to confirm.")
        st.markdown("---")
        st.markdown("**Send Notification to User**")
        with st.form("send_notif"):
            notif_e=st.selectbox("Recipient",list(db.keys()),key="sne")
            notif_msg=st.text_area("Message")
            notif_type=st.selectbox("Type",["info","warning","reply"])
            if st.form_submit_button("📩 Send"):
                if notif_msg:
                    add_notification(notif_e,notif_msg,notif_type)
                    st.success(f"Notification sent to {notif_e}")

    # ── PLAYERS DATABASE ───────────────────────────────────────
    elif dev_nav=="🏈 Players Database":
        st.subheader("🏈 Players Database")
        st.caption("All players added by team managers across all teams and seasons. Delete requires your developer password.")
        df=st.session_state.data
        if not df.empty:
            df2=df.copy()
            df2["CPR"]=df2.apply(cpr,axis=1)
            df2["MV"]=df2.apply(market_val,axis=1)

            # Filters
            fc1,fc2,fc3=st.columns(3)
            f_team=fc1.selectbox("Team",["All"]+sorted(df2["Team"].unique().tolist()))
            f_season=fc2.selectbox("Season",["All"]+sorted(df2["Season"].unique().tolist()) if "Season" in df2.columns else ["All"])
            f_pos=fc3.selectbox("Position",["All"]+sorted(df2["Position"].dropna().unique().tolist()) if "Position" in df2.columns else ["All"])
            fdf=df2.copy()
            if f_team!="All":fdf=fdf[fdf["Team"]==f_team]
            if f_season!="All" and "Season" in fdf.columns:fdf=fdf[fdf["Season"]==f_season]
            if f_pos!="All" and "Position" in fdf.columns:fdf=fdf[fdf["Position"]==f_pos]

            c1,c2,c3=st.columns(3)
            c1.metric("Players Shown",len(fdf))
            c2.metric("Teams",fdf["Team"].nunique())
            c3.metric("Avg CPR",f"{fdf['CPR'].mean():.2f}" if not fdf.empty else "—")
            st.markdown("---")

            # Charts
            ch1,ch2=st.columns(2)
            with ch1:
                fig=px.bar(fdf.sort_values("CPR",ascending=False).head(15),
                    x="Player",y="CPR",color="Team",title="Top 15 Players by CPR",
                    color_discrete_sequence=CL)
                fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with ch2:
                if "Position" in fdf.columns:
                    pos_count=fdf["Position"].value_counts().reset_index()
                    pos_count.columns=["Position","Count"]
                    fig2=px.pie(pos_count,names="Position",values="Count",
                        title="Players by Position",color_discrete_sequence=CL)
                    fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)

            st.markdown("**Full Player Database**")
            view_cols=[c for c in ["Player","Team","Position","Age","Goals","Assists",
                "Matches","Health_Score","Performance_Index","CPR","MV","Season"]
                if c in fdf.columns]
            st.dataframe(fdf[view_cols].style.background_gradient(subset=["CPR"],cmap="Oranges"),
                use_container_width=True)

            # Delete player (requires dev password)
            st.markdown("---")
            st.markdown("**🗑️ Delete Player** *(requires developer password)*")
            with st.form("del_player_form"):
                if not fdf.empty:
                    del_player=st.selectbox("Select Player to Delete",fdf["Player"].unique())
                    del_team=st.selectbox("From Team",fdf[fdf["Player"]==del_player]["Team"].unique() if del_player else [])
                    del_pw=st.text_input("Developer Password",type="password")
                    if st.form_submit_button("🗑️ Delete Player"):
                        if h(del_pw)==DEV_PASSWORD_HASH:
                            mask=~((st.session_state.data["Player"]==del_player)&
                                   (st.session_state.data["Team"]==del_team))
                            st.session_state.data=st.session_state.data[mask].reset_index(drop=True)
                            log_activity(DEV_EMAIL,"Developer",
                                f"Deleted player: {del_player} ({del_team})")
                            st.success(f"✅ {del_player} deleted from {del_team}.")
                            st.rerun()
                        else:
                            st.error("❌ Incorrect developer password.")
        else:
            st.info("No players in the database yet. Team managers add players via their portals.")

    # ── DATA MANAGEMENT ────────────────────────────────────────
    elif dev_nav=="📅 Data Management":
        st.subheader("📅 Data Management")
        tab1,tab2=st.tabs(["⚽ Match Results","🏟️ Teams"])
        with tab1:
            render_match_log(st.session_state.selected_season, allow_edit=True)
        with tab2:
            render_team_management()

    # ── LEAGUE TABLE ───────────────────────────────────────────
    elif dev_nav=="🏆 League Table":
        st.subheader("🏆 League Table")
        render_league_table(st.session_state.selected_season)

    # ── EXPORT CENTER ──────────────────────────────────────────
    elif dev_nav=="📤 Export Center":
        st.subheader("📤 Export Center — Developer Reports")
        st.markdown("Generate daily, weekly and monthly system intelligence reports.")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("**📅 Daily Report**")
            st.caption(f"Covers today: {today_str()}")
            if st.button("Generate Daily Report",key="gen_daily"):
                pdf=generate_system_report("daily")
                st.download_button("📥 Download Daily PDF",pdf,
                    f"ITARA_Daily_Report_{today_str()}.pdf","application/pdf")
        with c2:
            st.markdown("**📆 Weekly Report**")
            st.caption(f"Last 7 days")
            if st.button("Generate Weekly Report",key="gen_weekly"):
                pdf=generate_system_report("weekly")
                st.download_button("📥 Download Weekly PDF",pdf,
                    f"ITARA_Weekly_Report_{today_str()}.pdf","application/pdf")
        with c3:
            st.markdown("**🗓️ Monthly Report**")
            st.caption("Last 30 days")
            if st.button("Generate Monthly Report",key="gen_monthly"):
                pdf=generate_system_report("monthly")
                st.download_button("📥 Download Monthly PDF",pdf,
                    f"ITARA_Monthly_Report_{today_str()}.pdf","application/pdf")
        st.markdown("---")
        st.markdown("**📊 Raw Data Exports**")
        ec1,ec2,ec3=st.columns(3)
        if not st.session_state.data.empty:
            ec1.download_button("📥 All Players CSV",
                st.session_state.data.to_csv(index=False).encode(),
                "ITARA_All_Players.csv","text/csv")
        if not st.session_state.match_results.empty:
            ec2.download_button("📥 All Matches CSV",
                st.session_state.match_results.to_csv(index=False).encode(),
                "ITARA_All_Matches.csv","text/csv")
        if st.session_state.login_log:
            ec3.download_button("📥 Login Log CSV",
                pd.DataFrame(st.session_state.login_log).to_csv(index=False).encode(),
                "ITARA_Login_Log.csv","text/csv")

# ══════════════════════════════════════════════════════════════
# OPPONENT ANALYSIS — Coach Decision Center feature
# ══════════════════════════════════════════════════════════════
def render_opponent_analysis(team, season):
    """Analyse opponent team strengths/weaknesses and suggest tactics."""
    st.markdown("### 🔍 Opponent Analysis & Tactical Recommendations")
    st.caption("Select an opponent to analyse their squad and generate tactical suggestions.")

    all_df=season_df(season)
    opponents=[t for t in st.session_state.teams if t!=team]
    if not opponents:
        st.warning("No other teams registered.");return

    opp=st.selectbox("Select Opponent",opponents,key="opp_sel")
    opp_df=all_df[all_df["Team"]==opp].copy() if not all_df.empty else pd.DataFrame()
    my_df=all_df[all_df["Team"]==team].copy() if not all_df.empty else pd.DataFrame()

    if opp_df.empty:
        st.info(f"No player data available for {opp} in this season yet.")
        return

    opp_df["CPR"]=opp_df.apply(cpr,axis=1)
    opp_df["Form"]=opp_df["Performance_Index"].apply(form_label)

    if not my_df.empty:
        my_df["CPR"]=my_df.apply(cpr,axis=1)

    st.markdown("---")
    col1,col2=st.columns(2)

    with col1:
        st.markdown(f"**{opp} — Squad Overview**")
        avg_opp_cpr=opp_df["CPR"].mean()
        avg_opp_fit=opp_df["Health_Score"].mean()
        avg_opp_goals=opp_df["Goals"].mean()
        mc1,mc2,mc3=st.columns(3)
        mc1.metric("Avg CPR",f"{avg_opp_cpr:.2f}")
        mc2.metric("Avg Fitness",f"{avg_opp_fit:.0f}%")
        mc3.metric("Avg Goals/Player",f"{avg_opp_goals:.1f}")

        fig=px.bar(opp_df.sort_values("CPR",ascending=False),
            x="Player",y="CPR",color="Position",
            title=f"{opp} — Player CPR Rankings",
            color_discrete_sequence=CL)
        fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)

    with col2:
        if not my_df.empty:
            st.markdown(f"**{team} vs {opp} — Head-to-Head Team Stats**")
            my_avg_cpr=my_df["CPR"].mean()
            diff=my_avg_cpr-avg_opp_cpr
            st.metric("Your Avg CPR",f"{my_avg_cpr:.2f}",
                delta=f"{diff:+.2f} vs {opp}")
            fig2=px.bar(
                pd.DataFrame({
                    "Metric":["Avg CPR","Avg Goals","Avg Assists","Avg Fitness"],
                    team:[my_df["CPR"].mean(),my_df["Goals"].mean(),
                          my_df["Assists"].mean(),my_df["Health_Score"].mean()],
                    opp:[opp_df["CPR"].mean(),opp_df["Goals"].mean(),
                         opp_df["Assists"].mean(),opp_df["Health_Score"].mean()]
                }),
                x="Metric",y=[team,opp],barmode="group",
                title="Team Comparison",color_discrete_sequence=["#065f46","#d97757"])
            fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)

    # Strength/Weakness Analysis
    st.markdown("---")
    st.markdown(f"#### 💡 {opp} — Strengths & Weaknesses")

    # Position analysis
    if "Position" in opp_df.columns:
        pos_stats=opp_df.groupby("Position").agg(
            Count=("Player","count"),
            Avg_CPR=("CPR","mean"),
            Avg_Fitness=("Health_Score","mean"),
            Total_Goals=("Goals","sum")
        ).round(2).reset_index()

        strongest_pos=pos_stats.loc[pos_stats["Avg_CPR"].idxmax()] if not pos_stats.empty else None
        weakest_pos=pos_stats.loc[pos_stats["Avg_CPR"].idxmin()] if not pos_stats.empty else None

        c1,c2=st.columns(2)
        with c1:
            st.markdown("**💪 Strengths**")
            if strongest_pos is not None:
                st.success(f"**Strong position:** {strongest_pos['Position']} "
                    f"(Avg CPR: {strongest_pos['Avg_CPR']:.2f})")
            top_scorer=opp_df.loc[opp_df["Goals"].idxmax()] if not opp_df.empty else None
            if top_scorer is not None:
                st.info(f"**Key scorer:** {top_scorer['Player']} "
                    f"({int(top_scorer['Goals'])} goals, CPR {top_scorer['CPR']:.2f})")
            elite=opp_df[opp_df["Performance_Index"]>=8.0]
            if not elite.empty:
                st.warning(f"**Elite players:** {', '.join(elite['Player'].tolist())} — "
                    "mark these tightly")

        with c2:
            st.markdown("**⚠️ Weaknesses**")
            if weakest_pos is not None:
                st.error(f"**Weak position:** {weakest_pos['Position']} "
                    f"(Avg CPR: {weakest_pos['Avg_CPR']:.2f}) — exploit this area")
            low_fitness=opp_df[opp_df["Health_Score"]<70]
            if not low_fitness.empty:
                st.info(f"**Fitness concerns:** {', '.join(low_fitness['Player'].tolist())} "
                    f"— press these players hard")
            low_pass=opp_df[opp_df["Pass_Accuracy"]<72] if "Pass_Accuracy" in opp_df.columns else pd.DataFrame()
            if not low_pass.empty:
                st.info(f"**Poor passers:** {', '.join(low_pass['Player'].tolist())} "
                    f"— apply pressing to force errors")

    # Tactical Recommendations
    st.markdown("---")
    st.markdown(f"#### 🧠 ITARA Tactical Recommendations vs {opp}")

    if not my_df.empty:
        my_avg=my_df["CPR"].mean()
        opp_avg=opp_df["CPR"].mean()
        diff=my_avg-opp_avg

        # Determine recommended tactic
        if diff>1.0:
            tactic="ATTACKING — High Press & Possession"
            tactic_desc=(f"Your squad is significantly stronger (CPR advantage: {diff:.2f}). "
                "Play high pressing football, dominate possession and commit numbers forward. "
                "Your quality should overcome defensive resistance.")
            formation="4-3-3 or 4-2-3-1"
        elif diff>0:
            tactic="CONTROLLED — Balanced with Quick Transitions"
            tactic_desc=(f"You have a slight advantage (CPR +{diff:.2f}). "
                "Maintain shape, be patient in build-up, and use quick counter-attacks "
                "when the opponent loses possession.")
            formation="4-4-2 or 4-1-4-1"
        elif diff>-1.0:
            tactic="DEFENSIVE — Compact Block & Counter"
            tactic_desc=(f"Opponent has slight edge (CPR {abs(diff):.2f} stronger). "
                "Defend deep in a compact shape, limit spaces, and rely on fast "
                "counter-attacks through your quickest forwards.")
            formation="5-3-2 or 4-5-1"
        else:
            tactic="DEFENSIVE — Low Block & Set Pieces"
            tactic_desc=(f"Opponent significantly stronger (CPR gap: {abs(diff):.2f}). "
                "Protect the goal with a low block, limit shots, and focus energy "
                "on set pieces as your best scoring opportunities.")
            formation="5-4-1 or 4-4-2 flat"

        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#0a3d0a15,var(--bg-card));
        border:2px solid #065f46;border-radius:12px;padding:20px 24px;'>
            <div style='font-family:Fraunces,serif;font-size:1.2rem;font-weight:800;
            color:#065f46;margin-bottom:8px;'>🎯 Recommended Tactic: {tactic}</div>
            <div style='font-size:.9rem;color:#1c1917;line-height:1.7;margin-bottom:10px;'>{tactic_desc}</div>
            <div style='font-size:.85rem;color:#57534e;'>
            <b>Suggested Formation:</b> {formation}<br>
            <b>Key Focus:</b> Target {weakest_pos['Position'] if weakest_pos is not None else 'opponent\'s defence'} 
            as their weakest area · Watch {top_scorer['Player'] if top_scorer is not None else 'key players'}
            </div>
        </div>""",unsafe_allow_html=True)
    else:
        st.info("Add your team's players to receive personalised tactical recommendations.")

    # Position heatmap comparison
    if not my_df.empty and "Position" in opp_df.columns and "Position" in my_df.columns:
        st.markdown("---")
        st.markdown("**📊 Position-by-Position Comparison**")
        my_pos=my_df.groupby("Position")["CPR"].mean().reset_index().rename(columns={"CPR":f"{team} CPR"})
        opp_pos=opp_df.groupby("Position")["CPR"].mean().reset_index().rename(columns={"CPR":f"{opp} CPR"})
        merged=my_pos.merge(opp_pos,on="Position",how="outer").fillna(0)
        fig_pos=px.bar(merged,x="Position",
            y=[f"{team} CPR",f"{opp} CPR"],
            barmode="group",title=f"Position Strength: {team} vs {opp}",
            color_discrete_sequence=["#065f46","#d97757"])
        fig_pos.update_layout(**PL);st.plotly_chart(fig_pos,use_container_width=True)

# ══════════════════════════════════════════════════════════════
# ████  PORTAL: FOOTBALL AGENT  ████
# ══════════════════════════════════════════════════════════════
def portal_agent(u):
    nav,season=render_sidebar(u,["🏠 Dashboard","💪 Physical Status",
        "⚖️ Player Comparison","💰 Market Valuations",
        "🏆 League Table","📤 Export Report"])
    show_notifications(u.get("email",""))
    color=ROLE_COLORS["Football Agent"]

    # Only league table data is shared — agent sees all players (public stats only)
    df=season_df(season)
    if not df.empty:
        df["CPR"]=df.apply(cpr,axis=1);df["MV"]=df.apply(market_val,axis=1)
        df["xG_v"]=df.apply(xG,axis=1);df["xA_v"]=df.apply(xA,axis=1)
        df["Form"]=df["Performance_Index"].apply(form_label)

    if nav=="🏠 Dashboard":
        portal_banner("Football Agent Portal",f"League-wide intelligence · {season}",color)
        if not df.empty:
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("👥 Players",len(df))
            c2.metric("⚽ Total Goals",int(df["Goals"].sum()))
            c3.metric("🎯 Avg CPR",f"{df['CPR'].mean():.2f}")
            c4.metric("📈 Top xG",f"{df['xG_v'].max():.1f}")
            c5.metric("💰 Top Value",f"{df['MV'].max():,.0f} RWF")
            st.markdown("---")
            t1,t2,t3=st.tabs(["📊 Player Stats","🏅 Top Performers","🌐 Radar"])
            with t1:
                st.dataframe(df[["Player","Team","Position","Age","CPR","Performance_Index",
                    "xG_v","xA_v","Goals","Assists","Matches","Form","MV"]].rename(
                    columns={"xG_v":"xG","xA_v":"xA","MV":"Value(RWF)"})
                    .style.background_gradient(subset=["CPR","Performance_Index"],cmap="Oranges"),
                    use_container_width=True)
            with t2:
                col1,col2=st.columns(2)
                with col1:
                    fig=px.bar(df.sort_values("CPR",ascending=False).head(12),
                        x="Player",y="CPR",color="Team",title="Top 12 by CPR",
                        color_discrete_sequence=CL)
                    fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
                with col2:
                    fig2=px.scatter(df,x="Performance_Index",y="MV",color="Form",
                        size="Matches",hover_data=["Player","Team"],
                        title="Market Value vs PI",color_discrete_map=FC)
                    fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
                col3,col4=st.columns(2)
                with col3:
                    fig3=px.bar(df.sort_values("Goals",ascending=False).head(10),
                        x="Player",y="Goals",color="Team",title="Top Scorers",
                        color_discrete_sequence=CL)
                    fig3.update_layout(**PL);st.plotly_chart(fig3,use_container_width=True)
                with col4:
                    fig4=px.bar(df.sort_values("Assists",ascending=False).head(10),
                        x="Player",y="Assists",color="Team",title="Top Assisters",
                        color_discrete_sequence=CL)
                    fig4.update_layout(**PL);st.plotly_chart(fig4,use_container_width=True)
            with t3:
                sel=st.selectbox("Player radar",df["Player"].unique(),key="ag_rad")
                p=df[df["Player"]==sel].iloc[0];m=max(p.get("Matches",1),1)
                cats=["Scoring","Creativity","Passing","Physical","Fitness","Overall"]
                vals=[min(p.get("Goals",0)/m*10,10),min(p.get("Assists",0)/m*10,10),
                    p.get("Pass_Accuracy",75)/10,prog(p),
                    p.get("Health_Score",100)/10,p.get("Performance_Index",5)]
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],
                    fill="toself",fillcolor="rgba(124,58,237,0.15)",
                    line=dict(color="#7c3aed",width=2)))
                fig_r.update_layout(polar=dict(bgcolor="#faf7f2",
                    radialaxis=dict(visible=True,range=[0,10],color="#57534e",gridcolor="#e7e0d5"),
                    angularaxis=dict(color="#1c1917",gridcolor="#e7e0d5")),
                    paper_bgcolor="#faf7f2",font_color="#1c1917",
                    title=dict(text=f"Radar — {sel}",font_size=14),showlegend=False,height=420)
                st.plotly_chart(fig_r,use_container_width=True)
        else:
            st.info("No player data for this season.")

    elif nav=="💪 Physical Status":
        portal_banner("Physical Status",f"Fitness across all squads · {season}",color)
        if not df.empty:
            df["Availability"]=df["Health_Score"].apply(avail)
            c1,c2,c3=st.columns(3)
            c1.metric("✅ Match Ready",len(df[df["Health_Score"]>=85]))
            c2.metric("⚠️ Monitored",len(df[(df["Health_Score"]>=50)&(df["Health_Score"]<85)]))
            c3.metric("🔴 Unavailable",len(df[df["Health_Score"]<50]))
            fig=px.bar(df.sort_values("Health_Score"),x="Player",y="Health_Score",
                color="Health_Score",color_continuous_scale="RdYlGn",
                title="Squad Fitness",hover_data=["Team","Position"])
            fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            st.dataframe(df[["Player","Team","Position","Age","Health_Score","Availability"]]
                .sort_values("Health_Score",ascending=False),use_container_width=True)
        else:st.info("No data.")

    elif nav=="⚖️ Player Comparison":
        portal_banner("Player Comparison","Head-to-head analysis",color)
        if len(df)>=2:
            c1,c2=st.columns(2)
            p1n=c1.selectbox("Player A",df["Player"].unique(),key="ag_p1")
            p2n=c2.selectbox("Player B",[p for p in df["Player"].unique() if p!=p1n],key="ag_p2")
            p1=df[df["Player"]==p1n].iloc[0];p2=df[df["Player"]==p2n].iloc[0]
            st.markdown("---")
            metrics=[("CPR","CPR",2),("Performance Index","Performance_Index",1),
                ("xG","xG_v",2),("xA","xA_v",2),("Goals","Goals",0),
                ("Assists","Assists",0),("Pass Acc%","Pass_Accuracy",1),
                ("Fitness%","Health_Score",0),("Market Value (RWF)","MV",0)]
            c1,cm,c3=st.columns([2,1,2])
            cm.markdown("<div style='text-align:center;padding-top:28px;color:#7c3aed;"
                "font-family:Fraunces,serif;font-size:1.4rem;font-weight:800;'>VS</div>",
                unsafe_allow_html=True)
            for lbl,fld,dec in metrics:
                v1,v2=float(p1.get(fld,0)),float(p2.get(fld,0))
                fmt=f"{{:,.{dec}f}}"
                c1.metric(lbl,fmt.format(v1),f"{'+' if v1-v2>0 else ''}{fmt.format(round(v1-v2,dec))} vs {p2n}")
                c3.metric(lbl,fmt.format(v2),f"{'+' if v2-v1>0 else ''}{fmt.format(round(v2-v1,dec))} vs {p1n}")
            # Radar overlay
            def rv(p):
                m=max(p.get("Matches",1),1)
                return [round(min(p.get("Goals",0)/m*10,10),2),
                    round(min(p.get("Assists",0)/m*10,10),2),
                    round(p.get("Pass_Accuracy",75)/10,2),
                    round(prog(p),2),round(p.get("Health_Score",100)/10,2),
                    round(p.get("Performance_Index",5),2)]
            cats=["Scoring","Creativity","Passing","Physical","Fitness","Overall"]
            fig_c=go.Figure()
            for vals,name,cl in [(rv(p1),p1n,"#7c3aed"),(rv(p2),p2n,"#d97757")]:
                fig_c.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],
                    fill="toself",name=name,line=dict(color=cl,width=2),fillcolor=cl+"26"))
            fig_c.update_layout(polar=dict(bgcolor="#faf7f2",
                radialaxis=dict(visible=True,range=[0,10],color="#57534e",gridcolor="#e7e0d5"),
                angularaxis=dict(color="#1c1917",gridcolor="#e7e0d5")),
                paper_bgcolor="#faf7f2",font_color="#1c1917",
                title=dict(text=f"{p1n} vs {p2n}",font_size=14),height=420,
                legend=dict(bgcolor="#faf7f2",bordercolor="#e7e0d5",borderwidth=1))
            st.plotly_chart(fig_c,use_container_width=True)
            cpr1,cpr2=float(p1["CPR"]),float(p2["CPR"])
            if cpr1>cpr2:st.success(f"**ITARA Verdict:** {p1n} leads by {round(cpr1-cpr2,2)} CPR pts")
            elif cpr2>cpr1:st.success(f"**ITARA Verdict:** {p2n} leads by {round(cpr2-cpr1,2)} CPR pts")
            else:st.info("Both players rated equally.")
        else:st.warning("Need at least 2 players.")

    elif nav=="💰 Market Valuations":
        portal_banner("Market Valuations","Estimated transfer values",color)
        if not df.empty:
            c1,c2,c3=st.columns(3)
            c1.metric("Highest",f"{df['MV'].max():,.0f} RWF")
            c2.metric("Average",f"{df['MV'].mean():,.0f} RWF")
            c3.metric("Total",f"{df['MV'].sum():,.0f} RWF")
            col1,col2=st.columns(2)
            with col1:
                fig=px.bar(df.sort_values("MV",ascending=False).head(15),
                    x="Player",y="MV",color="Team",title="Top 15 Values (RWF)",
                    color_discrete_sequence=CL)
                fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with col2:
                tv=df.groupby("Team")["MV"].sum().reset_index()
                fig2=px.pie(tv,names="Team",values="MV",
                    title="Value by Team",color_discrete_sequence=CL)
                fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
            st.dataframe(df[["Player","Team","Position","Age","CPR","Form","MV"]]
                .rename(columns={"MV":"Value(RWF)"})
                .sort_values("Value(RWF)",ascending=False)
                .style.background_gradient(subset=["CPR"],cmap="Oranges"),
                use_container_width=True)
        else:st.info("No data.")

    elif nav=="🏆 League Table":
        portal_banner("League Standings",f"Season {season}",color)
        render_league_table(season)

    elif nav=="📤 Export Report":
        portal_banner("Export Report","Agent Intelligence Brief",color)
        if not df.empty:
            pdf=make_pdf_agent(df,season)
            st.download_button("📄 Download Agent PDF",pdf,
                f"ITARA_Agent_{season.replace('/','_')}.pdf","application/pdf")
        else:st.error("No data.")

# ══════════════════════════════════════════════════════════════
# ████  PORTAL: JOURNALIST  ████
# ══════════════════════════════════════════════════════════════
def portal_journalist(u):
    nav,season=render_sidebar(u,["🏠 Dashboard","🏆 League Standings",
        "📊 Player Stats","📅 Match Results","📈 Data Visualizer",
        "🧬 ML Predictions","📤 Export Report"])
    show_notifications(u.get("email",""))
    color=ROLE_COLORS["Journalist"]
    df=season_df(season)
    if not df.empty:
        df["CPR"]=df.apply(cpr,axis=1);df["Form"]=df["Performance_Index"].apply(form_label)
    mr=season_mr(season)

    if nav=="🏠 Dashboard":
        portal_banner("Journalist Media Portal",f"League intelligence · {season}",color)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("🏟️ Teams",len(df["Team"].unique()) if not df.empty else 0)
        c2.metric("👥 Players",len(df))
        c3.metric("⚽ Total Goals",int(df["Goals"].sum()) if not df.empty else 0)
        c4.metric("📅 Matches",len(mr))
        if not df.empty:
            col1,col2=st.columns(2)
            with col1:
                fig=px.bar(df.sort_values("Goals",ascending=False).head(10),
                    x="Player",y="Goals",color="Team",title="Top Scorers",
                    color_discrete_sequence=CL)
                fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with col2:
                render_league_table(season)

    elif nav=="🏆 League Standings":
        portal_banner("League Standings",f"Season {season}",color)
        render_league_table(season)

    elif nav=="📊 Player Stats":
        portal_banner("Player Statistics",f"Season {season}",color)
        if not df.empty:
            tf=st.selectbox("Filter by Team",["All Teams"]+list(df["Team"].unique()))
            fdf=df if tf=="All Teams" else df[df["Team"]==tf]
            col1,col2=st.columns(2)
            with col1:
                fig=px.scatter(fdf,x="Performance_Index",y="Goals",color="Team",
                    size="Matches",hover_data=["Player"],
                    title="Goals vs Performance Index",color_discrete_sequence=CL)
                fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with col2:
                fig2=px.box(fdf,x="Team",y="CPR",color="Team",
                    title="CPR Distribution by Team",color_discrete_sequence=CL)
                fig2.update_layout(**PL,showlegend=False);st.plotly_chart(fig2,use_container_width=True)
            st.dataframe(fdf[["Player","Team","Position","CPR","Performance_Index",
                "Goals","Assists","Matches","Form"]]
                .style.background_gradient(subset=["CPR"],cmap="Oranges"),
                use_container_width=True)
        else:st.info("No data.")

    elif nav=="📅 Match Results":
        portal_banner("Match Results",f"Season {season}",color)
        if not mr.empty:
            st.dataframe(mr,use_container_width=True)
        else:st.info("No match results.")

    elif nav=="📈 Data Visualizer":
        portal_banner("Data Visualizer","Interactive charts",color)
        if not df.empty:
            numeric_cols=["Goals","Assists","Matches","Minutes_Played","Shots_on_Target",
                "Pass_Accuracy","Dribbles_Completed","Tackles_Won","Health_Score",
                "Performance_Index","CPR"]
            numeric_cols=[c for c in numeric_cols if c in df.columns]
            cat_cols=["Team","Position","Form"]
            cat_cols=[c for c in cat_cols if c in df.columns]
            c1,c2,c3=st.columns(3)
            chart_type=c1.selectbox("Chart Type",["Bar","Scatter","Box",
                "Histogram","Bubble","Line","Heatmap","Pie","Violin","Treemap"])
            x_col=c2.selectbox("X Axis",numeric_cols+cat_cols)
            y_col=c3.selectbox("Y Axis",numeric_cols,index=min(6,len(numeric_cols)-1))
            c4,c5=st.columns(2)
            color_col=c4.selectbox("Color by",["None"]+cat_cols+numeric_cols)
            size_col=c5.selectbox("Size by",["None"]+numeric_cols)
            ca=color_col if color_col!="None" else None
            sa=size_col if size_col!="None" else None
            if chart_type=="Bar":fig=px.bar(df,x=x_col,y=y_col,color=ca,title=f"{y_col} by {x_col}",color_discrete_sequence=CL)
            elif chart_type=="Scatter":fig=px.scatter(df,x=x_col,y=y_col,color=ca,size=sa,hover_data=["Player","Team"],title=f"{y_col} vs {x_col}",color_discrete_map=FC if ca=="Form" else None)
            elif chart_type=="Box":fig=px.box(df,x=ca or "Team",y=y_col,color=ca or "Team",title=f"{y_col} distribution",color_discrete_sequence=CL)
            elif chart_type=="Histogram":fig=px.histogram(df,x=x_col,color=ca,nbins=15,title=f"Distribution of {x_col}",color_discrete_sequence=CL)
            elif chart_type=="Bubble":fig=px.scatter(df,x=x_col,y=y_col,size=sa or "Matches",color=ca,hover_data=["Player","Team"],title=f"Bubble: {y_col} vs {x_col}",color_discrete_sequence=CL)
            elif chart_type=="Line":fig=px.line(df.sort_values(x_col),x=x_col,y=y_col,color=ca,title=f"{y_col} trend",markers=True,color_discrete_sequence=CL)
            elif chart_type=="Heatmap":
                num_df=df[numeric_cols].corr()
                fig=px.imshow(num_df,title="Correlation Heatmap",color_continuous_scale="RdBu_r",text_auto=".2f")
            elif chart_type=="Pie":
                pie_df=df.groupby(x_col if x_col in cat_cols else "Team")[y_col].sum().reset_index()
                fig=px.pie(pie_df,names=pie_df.columns[0],values=y_col,title=f"{y_col} by {pie_df.columns[0]}",hole=0.35,color_discrete_sequence=CL)
            elif chart_type=="Violin":fig=px.violin(df,x=ca or "Team",y=y_col,color=ca or "Team",box=True,title=f"Violin: {y_col}",color_discrete_sequence=CL)
            elif chart_type=="Treemap":
                tm_df=df.groupby(["Team","Position"])[y_col].sum().reset_index()
                fig=px.treemap(tm_df,path=["Team","Position"],values=y_col,title=f"Treemap: {y_col}",color_discrete_sequence=CL)
            else:fig=px.bar(df,x=x_col,y=y_col)
            fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
        else:st.info("No data.")

    elif nav=="🧬 ML Predictions":
        portal_banner("ML Predictions","AI-powered forecasting",color)
        if ML_OK:render_ml_page(df,u,season)
        else:st.error("ML modules not available.")

    elif nav=="📤 Export Report":
        portal_banner("Export Media Report","Journalist Media Pack",color)
        if not df.empty:
            pdf=make_pdf_journalist(df,mr,season)
            st.download_button("📄 Download Media PDF",pdf,
                f"ITARA_Media_{season.replace('/','_')}.pdf","application/pdf")
        else:st.error("No data.")

# ══════════════════════════════════════════════════════════════
# ████  PORTAL: TEAM MANAGER/COACH  ████
# ══════════════════════════════════════════════════════════════
def portal_manager(u):
    team=u.get("team","");color=ROLE_COLORS["Team Manager/Coach"]
    nav,season=render_sidebar(u,["🏠 Dashboard","📊 Data Management",
        "🧠 Coach Decision Center","🏥 Health Reports",
        "🏆 League Table","📤 Export Report"])
    show_notifications(u.get("email",""))

    df=team_df(season,team)
    if not df.empty:
        df["CPR"]=df.apply(cpr,axis=1);df["MV"]=df.apply(market_val,axis=1)
        df["Form"]=df["Performance_Index"].apply(form_label)
        df["Availability"]=df["Health_Score"].apply(avail)

    if nav=="🏠 Dashboard":
        portal_banner(f"Team Manager — {team}",f"Full squad · {season}",color)
        if not df.empty:
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("👥 Squad",len(df))
            c2.metric("⚽ Goals",int(df["Goals"].sum()))
            c3.metric("🎯 Avg CPR",f"{df['CPR'].mean():.2f}")
            c4.metric("❤️ Avg Fitness",f"{df['Health_Score'].mean():.0f}%")
            c5.metric("💰 Squad Value",f"{df['MV'].sum():,.0f}")
            st.markdown("---")
            t1,t2,t3=st.tabs(["📊 Visuals","🌐 Radar","📋 Squad"])
            with t1:
                col1,col2=st.columns(2)
                with col1:
                    fig=px.bar(df.sort_values("CPR",ascending=False),
                        x="Player",y="CPR",color="Position",
                        title="Squad CPR Ranking",color_discrete_sequence=CL)
                    fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
                with col2:
                    fig2=px.scatter(df,x="Performance_Index",y="MV",color="Form",
                        size="Matches",hover_data=["Player"],
                        title="Value vs Performance",color_discrete_map=FC)
                    fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
                col3,col4=st.columns(2)
                with col3:
                    fig3=px.bar(df,x="Player",y="Health_Score",color="Health_Score",
                        color_continuous_scale="RdYlGn",title="Squad Fitness")
                    fig3.update_layout(**PL);st.plotly_chart(fig3,use_container_width=True)
                with col4:
                    if "Position" in df.columns:
                        pos_cpr=df.groupby("Position")["CPR"].mean().reset_index()
                        fig4=px.bar(pos_cpr,x="Position",y="CPR",
                            title="Avg CPR by Position",color="CPR",
                            color_continuous_scale="Oranges")
                        fig4.update_layout(**PL);st.plotly_chart(fig4,use_container_width=True)
            with t2:
                sel=st.selectbox("Player",df["Player"].unique(),key="mg_rad")
                p=df[df["Player"]==sel].iloc[0];m=max(p.get("Matches",1),1)
                cats=["Scoring","Creativity","Passing","Physical","Fitness","Overall"]
                vals=[min(p.get("Goals",0)/m*10,10),min(p.get("Assists",0)/m*10,10),
                    p.get("Pass_Accuracy",75)/10,prog(p),
                    p.get("Health_Score",100)/10,p.get("Performance_Index",5)]
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],
                    fill="toself",fillcolor="rgba(6,95,70,0.15)",
                    line=dict(color="#065f46",width=2)))
                fig_r.update_layout(polar=dict(bgcolor="#faf7f2",
                    radialaxis=dict(visible=True,range=[0,10],color="#57534e",gridcolor="#e7e0d5"),
                    angularaxis=dict(color="#1c1917",gridcolor="#e7e0d5")),
                    paper_bgcolor="#faf7f2",font_color="#1c1917",
                    title=dict(text=f"Radar — {sel}",font_size=14),showlegend=False,height=420)
                st.plotly_chart(fig_r,use_container_width=True)
            with t3:
                st.dataframe(df[["Player","Position","Age","CPR","Goals","Assists",
                    "Matches","Performance_Index","Form","Health_Score","Availability"]]
                    .style.background_gradient(subset=["CPR"],cmap="Greens"),
                    use_container_width=True)
        else:
            st.info("No squad data. Add players in Data Management.")

    elif nav=="📊 Data Management":
        portal_banner(f"Data Management — {team}","Add players & matches",color)
        tb1,tb2,tb3=st.tabs(["✏️ Add Player","📂 Upload Excel","⚽ Match Log"])
        with tb1:
            with st.form("mg_player"):
                rc=st.columns(2)
                pn=rc[0].text_input("Player Name *")
                pos=rc[1].selectbox("Position",["GK","CB","LB","RB","CDM","CM","CAM","LW","RW","ST"])
                rc2=st.columns(3)
                age=rc2[0].number_input("Age",15,45,24)
                mp=rc2[1].number_input("Matches",1,100,10)
                mins=rc2[2].number_input("Minutes",0,9000,900)
                rc3=st.columns(3)
                g=rc3[0].number_input("Goals",0,100,0)
                a=rc3[1].number_input("Assists",0,100,0)
                sh=rc3[2].number_input("Shots on Target",0,200,5)
                rc4=st.columns(3)
                pa=rc4[0].number_input("Pass Acc%",0,100,75)
                dr=rc4[1].number_input("Dribbles",0,300,10)
                tk=rc4[2].number_input("Tackles",0,300,10)
                rc5=st.columns(2)
                pi=rc5[0].slider("Performance Index",0.0,10.0,5.0,.1)
                hs=rc5[1].slider("Fitness%",0,100,100)
                if st.form_submit_button("💾 Save Player"):
                    if pn:
                        st.session_state.data=pd.concat([st.session_state.data,
                            pd.DataFrame([{"Player":pn,"Team":team,"Position":pos,"Age":age,
                                "Goals":g,"Assists":a,"Matches":mp,"Minutes_Played":mins,
                                "Shots_on_Target":sh,"Pass_Accuracy":pa,
                                "Dribbles_Completed":dr,"Tackles_Won":tk,
                                "Health_Score":hs,"Performance_Index":pi,"Season":season}])],
                            ignore_index=True)
                        log_activity(u.get("email",""),u.get("role",""),
                            f"Added player: {pn} ({team})")
                        st.success(f"✅ {pn} saved!")
                    else:st.error("Name required.")
        with tb2:
            uf=st.file_uploader("Upload Excel (.xlsx)",type=["xlsx"])
            if uf:
                udf=pd.read_excel(uf)
                udf["Team"]=team;udf["Season"]=season
                for col,dfl in [("Position","MF"),("Age",24),("Minutes_Played",0),
                    ("Shots_on_Target",0),("Pass_Accuracy",75),
                    ("Dribbles_Completed",0),("Tackles_Won",0)]:
                    if col not in udf.columns:udf[col]=dfl
                st.session_state.data=pd.concat([st.session_state.data,udf],
                    ignore_index=True).drop_duplicates(subset=["Player","Team","Season"])
                log_activity(u.get("email",""),u.get("role",""),
                    f"Uploaded {len(udf)} players for {team}")
                st.success(f"✅ {len(udf)} players uploaded!")
        with tb3:
            render_match_log(season, allow_edit=True)

    elif nav=="🧠 Coach Decision Center":
        portal_banner(f"Coach Decision Center — {team}","Selection · Analysis · Tactics",color)
        tab1,tab2,tab3,tab4=st.tabs(["📋 Starting XI","📉 Risk Analysis","📊 Positions","🔍 Opponent Analysis"])
        with tab1:
            if not df.empty:
                c1,c2=st.columns(2)
                mf=c1.slider("Min Fitness%",0,100,70)
                mc_val=c2.slider("Min CPR",0.0,10.0,4.0,.1)
                elig=df[(df["Health_Score"]>=mf)&(df["CPR"]>=mc_val)].sort_values("CPR",ascending=False)
                st.markdown(f"**{len(elig)} eligible**")
                if not elig.empty:
                    st.dataframe(elig[["Player","Position","CPR","Performance_Index",
                        "Goals","Assists","Health_Score","Form","Availability"]]
                        .style.background_gradient(subset=["CPR"],cmap="Greens"),
                        use_container_width=True)
                    xi=elig.head(11).reset_index(drop=True);xi.index+=1;xi.index.name="#"
                    st.markdown("**🤖 Auto-Select Best XI**")
                    st.dataframe(xi[["Player","Position","CPR","Form","Availability"]],
                        use_container_width=True)
                    avg_cpr=elig.head(11)["CPR"].mean();avg_fit=elig.head(11)["Health_Score"].mean()
                    st.success(f"Avg CPR {avg_cpr:.2f} | Avg Fitness {avg_fit:.0f}% | "
                        f"{'Strong ✅' if avg_cpr>=6 else 'Developing ⚠️'}")
            else:st.warning("No squad data.")
        with tab2:
            if not df.empty:
                risk=df.copy()
                risk["Risk"]=risk.apply(lambda r:
                    "🔴 HIGH" if r["Health_Score"]<50 or r["Performance_Index"]<3
                    else "🟠 MED" if r["Health_Score"]<70 or r["Performance_Index"]<5
                    else "🟢 LOW",axis=1)
                # Risk pie chart
                col1,col2=st.columns(2)
                with col1:
                    rc=risk["Risk"].value_counts().reset_index()
                    rc.columns=["Risk","Count"]
                    fig=px.pie(rc,names="Risk",values="Count",title="Risk Distribution",
                        color_discrete_sequence=["#22c55e","#f59e0b","#ef4444"])
                    fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
                with col2:
                    fig2=px.bar(risk.sort_values("Health_Score"),x="Player",y="Health_Score",
                        color="Risk",title="Fitness by Risk Level",
                        color_discrete_map={"🟢 LOW":"#22c55e","🟠 MED":"#f59e0b","🔴 HIGH":"#ef4444"})
                    fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
                st.dataframe(risk[["Player","Position","Health_Score","Performance_Index",
                    "CPR","Risk","Availability"]].sort_values("Health_Score"),
                    use_container_width=True)
            else:st.warning("No data.")
        with tab3:
            if not df.empty and "Position" in df.columns:
                pr=df.groupby("Position").agg(
                    Players=("Player","count"),Avg_CPR=("CPR","mean"),
                    Avg_Fitness=("Health_Score","mean"),
                    Goals=("Goals","sum"),Assists=("Assists","sum")).round(2).reset_index()
                col1,col2=st.columns(2)
                with col1:
                    fig=px.bar(pr,x="Position",y="Avg_CPR",color="Avg_Fitness",
                        color_continuous_scale="RdYlGn",title="Avg CPR by Position",text="Avg_CPR")
                    fig.update_traces(textposition="outside");fig.update_layout(**PL)
                    st.plotly_chart(fig,use_container_width=True)
                with col2:
                    fig2=px.scatter(pr,x="Avg_CPR",y="Avg_Fitness",size="Players",
                        color="Position",hover_data=["Goals","Assists"],
                        title="CPR vs Fitness by Position",color_discrete_sequence=CL)
                    fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
                st.dataframe(pr,use_container_width=True)
            else:st.warning("No data.")
        with tab4:
            render_opponent_analysis(team,season)

    elif nav=="🏥 Health Reports":
        portal_banner(f"Health & Fitness — {team}","Clinical status",color)
        if not df.empty:
            sel=st.selectbox("Player",df["Player"].unique())
            pd_=df[df["Player"]==sel].iloc[0]
            cc=st.columns(4)
            cc[0].metric("Fitness",f"{pd_['Health_Score']}%")
            cc[1].metric("PI",f"{pd_['Performance_Index']:.1f}/10")
            cc[2].metric("Matches",int(pd_.get("Matches",0)))
            cc[3].metric("Minutes",int(pd_.get("Minutes_Played",0)))
            s=avail(pd_["Health_Score"])
            if pd_["Health_Score"]>=85:st.success(f"**Status:** {s}")
            elif pd_["Health_Score"]>=70:st.warning(f"**Status:** {s}")
            else:st.error(f"**Status:** {s}")
            st.progress(int(pd_["Health_Score"])/100)
            st.markdown("---")
            fig=px.bar(df.sort_values("Health_Score",ascending=False),
                x="Player",y="Health_Score",color="Health_Score",
                color_continuous_scale="RdYlGn",title="Squad Fitness",text="Health_Score")
            fig.update_traces(textposition="outside")
            fig.add_hline(y=85,line_dash="dash",line_color="green",annotation_text="85%")
            fig.add_hline(y=70,line_dash="dash",line_color="orange",annotation_text="70%")
            fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
        else:st.warning("No data.")

    elif nav=="🏆 League Table":
        portal_banner("League Table",f"Season {season}",color)
        render_league_table(season)

    elif nav=="📤 Export Report":
        portal_banner(f"Export — {team}","Tactical Dossier",color)
        if not df.empty:
            pdf=make_pdf_manager(df,team,season)
            st.download_button("📄 Download Manager PDF",pdf,
                f"ITARA_{team.replace(' ','_')}_{season.replace('/','_')}.pdf","application/pdf")
        else:st.error("No data.")

# ══════════════════════════════════════════════════════════════
# ████  PORTAL: TEAM ADMINISTRATION  ████
# ══════════════════════════════════════════════════════════════
def portal_teamadmin(u):
    team=u.get("team","");color=ROLE_COLORS["Team Administration"]
    nav,season=render_sidebar(u,["🏠 Team Overview","📋 Contract Tracker",
        "📊 Squad Summary","🏆 League Table","📤 Export"])
    show_notifications(u.get("email",""))

    df=team_df(season,team)
    if not df.empty:
        df["CPR"]=df.apply(cpr,axis=1);df["MV"]=df.apply(market_val,axis=1)
        df["Form"]=df["Performance_Index"].apply(form_label)
        df["Availability"]=df["Health_Score"].apply(avail)

    if nav=="🏠 Team Overview":
        portal_banner(f"Team Administration — {team}",f"Club overview · {season}",color)
        if not df.empty:
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("👥 Players",len(df))
            c2.metric("💰 Squad Value",f"{df['MV'].sum():,.0f} RWF")
            c3.metric("🎯 Avg CPR",f"{df['CPR'].mean():.2f}")
            c4.metric("❤️ Avg Fitness",f"{df['Health_Score'].mean():.0f}%")
            c5.metric("✅ Match Ready",len(df[df["Health_Score"]>=85]))
            col1,col2=st.columns(2)
            with col1:
                fig=px.pie(df,"Form",title="Form Distribution",
                    color="Form",color_discrete_map=FC)
                fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with col2:
                fig2=px.bar(df.sort_values("MV",ascending=False),
                    x="Player",y="MV",color="Position",title="Player Values",
                    color_discrete_sequence=CL)
                fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
            st.dataframe(df[["Player","Position","Age","CPR","Goals","Assists",
                "Health_Score","Form","Availability","MV"]]
                .rename(columns={"MV":"Value(RWF)"})
                .style.background_gradient(subset=["CPR"],cmap="Oranges"),
                use_container_width=True)
        else:st.info("No squad data.")

    elif nav=="📋 Contract Tracker":
        portal_banner(f"Contract Tracker — {team}","Colour-coded validity",color)
        cdf=st.session_state.contracts.copy()
        if team:cdf=cdf[cdf["Team"]==team]
        if not cdf.empty:
            cdf2=cdf.copy()
            cdf2["Status_Label"]=cdf2["Contract_End"].apply(lambda x:contract_status(x)[0])
            cdf2["CSS"]=cdf2["Contract_End"].apply(lambda x:contract_status(x)[1])
            c1,c2,c3,c4=st.columns(4)
            c1.metric("📄 Total",len(cdf2))
            c2.metric("🟢 Active",len(cdf2[cdf2["Status_Label"].str.startswith("Active")]))
            c3.metric("🟡 Due Soon",len(cdf2[cdf2["Status_Label"].str.contains("Due|Expiring")]))
            c4.metric("🔴 Expired",len(cdf2[cdf2["Status_Label"].str.startswith("Expired")]))
            def colour_st(val):
                if "Expired" in str(val) or "Expiring" in str(val):
                    return "background-color:#fee2e2;color:#991b1b;font-weight:700"
                if "Due" in str(val):
                    return "background-color:#fef9c3;color:#854d0e;font-weight:700"
                if "Active" in str(val):
                    return "background-color:#d1fae5;color:#065f46;font-weight:700"
                return ""
            st.dataframe(cdf2[["Player","Position","Contract_Start","Contract_End",
                "Status_Label","Notes"]].style.applymap(colour_st,subset=["Status_Label"]),
                use_container_width=True)
            # Timeline chart
            try:
                cdf2["Contract_End_dt"]=pd.to_datetime(cdf2["Contract_End"],errors="coerce")
                cdf_sorted=cdf2.dropna(subset=["Contract_End_dt"]).sort_values("Contract_End_dt")
                if not cdf_sorted.empty:
                    fig=px.bar(cdf_sorted,x="Player",y="Contract_End_dt",
                        color="Status_Label",title="Contract Expiry Timeline",
                        color_discrete_sequence=["#ef4444","#f59e0b","#22c55e","#a8a29e"])
                    fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            except:pass
        else:
            st.info("No contracts logged yet.")
        # Add contract
        with st.expander("➕ Add / Update Contract"):
            with st.form("ct_form"):
                players_in_team=list(df["Player"].unique()) if not df.empty else []
                cp=st.selectbox("Player",players_in_team) if players_in_team else st.text_input("Player Name")
                cp_pos=st.text_input("Position")
                rc2=st.columns(2)
                cs_date=rc2[0].date_input("Start",value=datetime.date.today()-datetime.timedelta(days=365))
                ce_date=rc2[1].date_input("End",value=datetime.date.today()+datetime.timedelta(days=365))
                notes=st.text_input("Notes")
                if st.form_submit_button("💾 Save"):
                    new_c={"Player":cp,"Team":team,"Position":cp_pos,
                        "Contract_Start":str(cs_date),"Contract_End":str(ce_date),
                        "Season":season,"Notes":notes}
                    st.session_state.contracts=st.session_state.contracts[
                        ~((st.session_state.contracts["Player"]==cp)&
                          (st.session_state.contracts["Team"]==team))]
                    st.session_state.contracts=pd.concat(
                        [st.session_state.contracts,pd.DataFrame([new_c])],ignore_index=True)
                    log_activity(u.get("email",""),u.get("role",""),
                        f"Updated contract: {cp} ({team})")
                    st.success(f"✅ Contract saved!");st.rerun()

    elif nav=="📊 Squad Summary":
        portal_banner(f"Squad Summary — {team}","Positional breakdown",color)
        if not df.empty and "Position" in df.columns:
            pos_sum=df.groupby("Position").agg(
                Count=("Player","count"),Avg_Age=("Age","mean"),
                Avg_CPR=("CPR","mean"),Avg_Fitness=("Health_Score","mean"),
                Total_Goals=("Goals","sum"),Squad_Value=("MV","sum")
            ).round(2).reset_index()
            col1,col2=st.columns(2)
            with col1:
                fig=px.pie(pos_sum,names="Position",values="Count",
                    title="Squad Composition",color_discrete_sequence=CL)
                fig.update_layout(**PL);st.plotly_chart(fig,use_container_width=True)
            with col2:
                fig2=px.bar(pos_sum,x="Position",y="Avg_CPR",color="Avg_Fitness",
                    color_continuous_scale="RdYlGn",title="Avg CPR by Position")
                fig2.update_layout(**PL);st.plotly_chart(fig2,use_container_width=True)
            st.dataframe(pos_sum,use_container_width=True)
        else:st.info("No data.")

    elif nav=="🏆 League Table":
        portal_banner("League Table",f"Season {season}",color)
        render_league_table(season)

    elif nav=="📤 Export":
        portal_banner(f"Export — {team}","Administration Report",color)
        if not df.empty:
            cdf=st.session_state.contracts[st.session_state.contracts["Team"]==team] if not st.session_state.contracts.empty else pd.DataFrame()
            buf=io.BytesIO()
            with pd.ExcelWriter(buf,engine="openpyxl") as w:
                df.to_excel(w,sheet_name="Squad",index=False)
                if not cdf.empty:cdf.to_excel(w,sheet_name="Contracts",index=False)
            st.download_button("📥 Export Excel",buf.getvalue(),
                f"ITARA_Admin_{team.replace(' ','_')}_{season.replace('/','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:st.error("No data.")

# ══════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════
def pg_home():
    n1,n2,n3=st.columns([2,4,2])
    with n1:st.markdown(logo_html(155),unsafe_allow_html=True)
    with n3:
        ca,cb=st.columns(2)
        if ca.button("Sign In",key="nav_si"):st.session_state.page="auth";st.rerun()
        if cb.button("Register",key="nav_reg"):st.session_state.page="auth";st.rerun()
    st.markdown("<hr style='margin:10px 0 24px;border-color:#e7e0d5;'>",unsafe_allow_html=True)
    st.markdown(f"""<div class="home-hero">
        <div style="margin-bottom:18px;">{logo_html(190)}</div>
        <div class="home-tagline">African Football<br><span>Intelligence Platform</span></div>
        <p style="color:#a8a29e;font-size:.95rem;line-height:1.8;max-width:580px;margin-bottom:22px;">
            Rwanda's first professional football data platform — a one-stop centre for athlete
            intelligence, scouting, editorial insights, and strategic decision-making across
            the African football ecosystem.</p>
        <div class="badge-rw">🇷🇼 Made in Rwanda · Vision 2050 Sport Industry Initiative</div>
    </div>""",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        st.markdown("""<div class="info-box"><h4>📖 Introduction</h4>
        <p style="color:#57534e;font-size:.9rem;line-height:1.75;">
        ITARA Sports Analytics transforms data into a competitive edge. We partner with teams,
        athletes and organisations to unlock the power of data through advanced analytics,
        cutting-edge technology and deep sports expertise.</p></div>""",unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="info-box"><h4>🎯 Our Vision</h4>
        <p style="color:#57534e;font-size:.9rem;line-height:1.75;">
        To be a global leader in sports analytics, empowering every competitive journey with
        data, insight and impact. Born from Rwanda's government initiative to develop the sports
        industry as a pillar of economic transformation.</p></div>""",unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;margin:32px 0 18px;'>Four Professional Portals</h3>",
        unsafe_allow_html=True)
    portals=[
        ("🕵️ Football Agent","#7c3aed","500,000 RWF/mo",
         ["All-league player database","Physical status","Player comparison","Market values","PDF report"]),
        ("📰 Journalist","#0369a1","100,000 RWF/mo",
         ["League standings","Player stats","Match results","10+ chart types","ML predictions"]),
        ("🧑‍💼 Team Manager/Coach","#065f46","1,000,000 RWF/team/mo",
         ["Full team dashboard","Coach decision center","Opponent analysis","Max 2 users/team"]),
        ("🏢 Team Administration","#92400e","1,000,000 RWF/team/mo",
         ["Team overview","Contract tracker","Squad reports","Max 2 users/team"]),
    ]
    cols=st.columns(4)
    for col,(name,clr,price,perks) in zip(cols,portals):
        with col:
            li="".join(f"<li style='font-size:.78rem;color:#57534e;text-align:left;margin:4px 0;'>✓ {p}</li>" for p in perks)
            st.markdown(f"""<div class="plan-card" style="border-top:3px solid {clr};">
                <div style="font-family:Fraunces,serif;font-weight:800;font-size:1rem;">{name}</div>
                <div style="color:{clr};font-size:1.5rem;font-weight:800;font-family:Fraunces,serif;">{price}</div>
                <ul style="padding-left:14px;margin-top:12px;">{li}</ul>
            </div>""",unsafe_allow_html=True)
            st.markdown("<div style='height:8px;'></div>",unsafe_allow_html=True)
    _,cc,_=st.columns([3,2,3])
    if cc.button("🚀 Create Account",key="cta"):st.session_state.page="auth";st.rerun()
    st.markdown("<hr style='margin:36px 0 24px;'>",unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;margin-bottom:4px;'>💬 Feedback</h3>",unsafe_allow_html=True)
    _,fc2,_=st.columns([1,2,1])
    with fc2:
        with st.form("fb"):
            fb_name=st.text_input("Your Name");fb_email=st.text_input("Email")
            fb_role=st.selectbox("Role",["Fan","Club Official","Agent","Coach","Journalist","Other"])
            fb_rating=st.select_slider("Rating",options=[1,2,3,4,5],value=5)
            fb_msg=st.text_area("Message",height=100)
            if st.form_submit_button("📨 Submit",use_container_width=True):
                if fb_name and fb_msg:
                    st.session_state.feedback.append({"name":fb_name,"email":fb_email,
                        "role":fb_role,"rating":fb_rating,"message":fb_msg,"time":now_str()})
                    st.success("✅ Thank you!")
                else:st.error("Name and message required.")
    st.markdown("""<div style="text-align:center;padding:24px 0 12px;border-top:1px solid #e7e0d5;margin-top:40px;">
        <div style="font-family:Fraunces,serif;font-size:1rem;font-weight:700;color:#d97757;">ITARA Sports Analytics</div>
        <div style="color:#a8a29e;font-size:.76rem;">
        🇷🇼 Kigali, Rwanda · African Football Intelligence · Sport Industry Initiative<br>
        © 2025 ITARA Analytics Ltd.</div></div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# PAGE: AUTH
# ══════════════════════════════════════════════════════════════
def _do_login(email, pw_plain):
    if email==DEV_EMAIL and h(pw_plain)==DEV_PASSWORD_HASH:
        st.session_state.logged_in=True
        st.session_state.user={"email":DEV_EMAIL,"name":"ITARA Developer",
            "role":"Developer","team":None,"subscribed":True,"sub_expires":"2099-12-31"}
        log_login(DEV_EMAIL,"ITARA Developer","Developer","login")
        st.session_state.page="dev";return True
    db=st.session_state.users_db
    if email in db and db[email]["pw"]==h(pw_plain):
        u=db[email].copy();u["email"]=email
        st.session_state.user=u;st.session_state.logged_in=True
        log_login(email,u["name"],u["role"],"login")
        st.session_state.page="subscribe" if not subscribed(u) else "app"
        return True
    return False

def pg_auth():
    if st.button("← Back to Home",key="ab"):st.session_state.page="home";st.rerun()
    _,lc,_=st.columns([2,2,2])
    with lc:st.markdown(f"<div style='text-align:center;margin-bottom:20px;'>{logo_html(150)}</div>",
        unsafe_allow_html=True)
    # Quick demo buttons
    st.markdown("""<div style='background:#faf7f2;border:1px solid #e7e0d5;border-radius:12px;
        padding:18px 22px;margin-bottom:20px;max-width:700px;margin-left:auto;margin-right:auto;'>
        <div style='font-family:Fraunces,serif;font-size:1rem;font-weight:700;
        color:#d97757;margin-bottom:6px;'>🚀 Quick Demo Access</div>
        <div style='font-size:.82rem;color:#57534e;margin-bottom:14px;'>
        Click any button to sign in instantly.</div></div>""",unsafe_allow_html=True)
    demo_accounts=[
        ("🕵️ Football Agent","agent@itara.rw","demo1234"),
        ("📰 Journalist","journalist@itara.rw","demo1234"),
        ("🧑‍💼 APR FC Coach","coach@aprfc.rw","demo1234"),
        ("🏢 APR FC Admin","admin@aprfc.rw","demo1234"),
        ("🧑‍💼 Rayon Coach","coach2@rayonsports.rw","demo1234"),
        ("🏢 Rayon Admin","admin2@rayonsports.rw","demo1234"),
        ("🛠️ Developer","dev@itara.rw","itara@dev2025"),
    ]
    _,rc,_=st.columns([1,6,1])
    with rc:
        c1,c2,c3,c4=st.columns(4)
        for col,(label,email,pw) in zip([c1,c2,c3,c4],demo_accounts[:4]):
            if col.button(label,key=f"qd_{email}",use_container_width=True):
                _do_login(email,pw);st.rerun()
        _,cc2,cc3,cc4,_=st.columns([1,2,2,2,1])
        for col,(label,email,pw) in zip([cc2,cc3,cc4],demo_accounts[4:]):
            if col.button(label,key=f"qd_{email}",use_container_width=True):
                _do_login(email,pw);st.rerun()
    _,fc,_=st.columns([1,2,1])
    with fc:
        tab_si,tab_reg=st.tabs(["🔐 Sign In","📝 Create Account"])
        with tab_si:
            with st.form("sf"):
                email_in=st.text_input("Email",placeholder="you@example.com")
                pw_in=st.text_input("Password",type="password")
                if st.form_submit_button("Sign In →",use_container_width=True):
                    if not email_in or not pw_in:st.error("Enter email and password.")
                    elif _do_login(email_in.strip().lower(),pw_in):st.rerun()
                    else:st.error("❌ Incorrect email or password.")
        with tab_reg:
            st.markdown("""<div style='background:#fff8f4;border:1px solid #f0c4b0;
                border-radius:8px;padding:10px 14px;margin:8px 0 12px;
                font-size:.8rem;color:#57534e;'>🔒 Minimum 6 characters.</div>""",
                unsafe_allow_html=True)
            with st.form("rf"):
                rn=st.text_input("Full Name *");re=st.text_input("Email *")
                rr=st.selectbox("Role *",ROLES)
                rt=st.text_input("Team (required for Manager & Admin)",placeholder="e.g. APR FC")
                rp=st.text_input("Password *",type="password")
                rp2=st.text_input("Confirm *",type="password")
                rtms=st.checkbox("I agree to the Terms of Service")
                if st.form_submit_button("Create Account →",use_container_width=True):
                    errors=[]
                    if not rn.strip():errors.append("Full name required.")
                    if not re.strip():errors.append("Email required.")
                    if len(rp)<6:errors.append("Password min 6 chars.")
                    if rp!=rp2:errors.append("Passwords don't match.")
                    if not rtms:errors.append("Accept terms.")
                    if re.strip().lower() in st.session_state.users_db:errors.append("Account exists.")
                    if rr in ["Team Manager/Coach","Team Administration"]:
                        if not rt.strip():errors.append("Team name required.")
                        elif team_user_count(rr,rt.strip())>=TEAM_MAX_USERS:
                            errors.append(f"⛔ {rt} already has {TEAM_MAX_USERS} {rr} accounts.")
                    if errors:
                        for e in errors:st.error(e)
                    else:
                        ec=re.strip().lower()
                        nu={"name":rn.strip(),"role":rr,
                            "team":rt.strip() if rr in ["Team Manager/Coach","Team Administration"] else None,
                            "pw":h(rp),"subscribed":False,"sub_expires":None,"notifications":[]}
                        st.session_state.users_db[ec]=nu;nu["email"]=ec
                        st.session_state.user=nu;st.session_state.logged_in=True
                        log_login(ec,nu["name"],nu["role"],"register")
                        st.session_state.page="subscribe";st.rerun()

# ══════════════════════════════════════════════════════════════
# PAGE: SUBSCRIBE
# ══════════════════════════════════════════════════════════════
def pg_subscribe():
    u=st.session_state.user;role=u["role"]
    price=ROLE_PRICES.get(role,"100,000")
    team_note=f" for **{u.get('team','')}**" if role in ["Team Manager/Coach","Team Administration"] else ""
    _,cc,_=st.columns([1,2,1])
    with cc:
        st.markdown(f"<div style='text-align:center;margin-bottom:18px;'>{logo_html(140)}</div>",
            unsafe_allow_html=True)
        st.markdown(f"""<div class="paywall-box">
            <div style="font-size:2.2rem;margin-bottom:8px;">🔒</div>
            <div style="font-family:Fraunces,serif;font-size:1.7rem;font-weight:800;margin-bottom:8px;">
                Activate Subscription</div>
            <p style="color:#57534e;font-size:.9rem;line-height:1.65;margin-bottom:20px;">
                Welcome, <strong>{u['name']}</strong>!<br>
                Portal: <strong>{role}</strong>{team_note}<br>
                Monthly: <strong>{price} RWF</strong>
            </p>
            <div class="mtn-badge">📱 MTN Mobile Money Rwanda</div>
        </div>""",unsafe_allow_html=True)
        st.markdown("---")
        st.info(f"""**Step 1:** Dial `*182*8*1*0788ITARA01*{price.replace(',','')}#`
**Step 2:** Merchant code: **ITARA2025**  
**Step 3:** Confirm on phone, wait for SMS  
**Step 4:** Enter number + reference below""")
        with st.form("mtn"):
            mtn=st.text_input("MTN Number",placeholder="0788123456")
            ref=st.text_input("Transaction Reference",placeholder="TXN-2025-XXXXXX")
            if st.form_submit_button("✅ Verify & Activate",use_container_width=True):
                if mtn and ref:
                    exp=(datetime.datetime.now()+datetime.timedelta(days=30)).strftime("%Y-%m-%d")
                    st.session_state.user["subscribed"]=True
                    st.session_state.user["sub_expires"]=exp
                    st.session_state.users_db[u["email"]]["subscribed"]=True
                    st.session_state.users_db[u["email"]]["sub_expires"]=exp
                    add_notification(u["email"],
                        f"🎉 Welcome to ITARA! Your subscription is active until {exp}. "
                        f"Enjoy full access to your {role} portal.","info")
                    st.success("🎉 Activated! Loading your portal...");st.session_state.page="app";st.rerun()
                else:st.error("Enter MTN number and reference.")
        st.caption("💡 Demo: any number + 'DEMO-2025'")
        if st.button("← Sign Out"):
            st.session_state.logged_in=False;st.session_state.user=None
            st.session_state.page="home";st.rerun()

# ══════════════════════════════════════════════════════════════
# APP ROUTER
# ══════════════════════════════════════════════════════════════
def pg_app():
    u=st.session_state.user;role=u["role"]
    if role=="Football Agent":       portal_agent(u)
    elif role=="Journalist":         portal_journalist(u)
    elif role=="Team Manager/Coach": portal_manager(u)
    elif role=="Team Administration":portal_teamadmin(u)
    else:st.error(f"Unknown role: {role}")

# ══════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════
pg=st.session_state.page
if pg=="home":      pg_home()
elif pg=="auth":    pg_auth()
elif pg=="dev":
    if st.session_state.logged_in and st.session_state.user and \
       st.session_state.user.get("role")=="Developer":
        pg_developer()
    else:
        st.session_state.page="home";st.rerun()
elif pg=="subscribe":
    if st.session_state.logged_in and st.session_state.user:pg_subscribe()
    else:st.session_state.page="home";st.rerun()
elif pg=="app":
    if st.session_state.logged_in and st.session_state.user and subscribed(st.session_state.user):
        pg_app()
    elif st.session_state.logged_in and st.session_state.user:
        st.session_state.page="subscribe";st.rerun()
    else:
        st.session_state.page="home";st.rerun()
else:
    st.session_state.page="home";st.rerun()
