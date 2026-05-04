# =============================
# ITARA CLUB-READY VERSION
# Streamlit App Structure + PDF Generator + Demo Pitch
# =============================

import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =============================
# 🎨 THEME COLORS
# =============================
PRIMARY = "#1c1917"
ACCENT = "#d97757"
BG = "#faf7f2"

# =============================
# ⚽ MATCH CENTER
# =============================

def render_match_center(df):
    st.markdown(f"""
    <div style='background:{PRIMARY};padding:20px;border-radius:12px;color:white;'>
        <h2>⚽ Match Intelligence</h2>
        <p>Key insights to improve match performance</p>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.warning("No data available")
        return

    # Simple stats
    st.subheader("📊 Match Summary")
    st.dataframe(df.head(10))

    # Coach recommendations (example logic)
    st.subheader("🧠 Coach Recommendations")

    recs = []

    if df["Minutes_Played"].mean() > 75:
        recs.append("⚠️ Squad fatigue is high — consider rotation")

    if df["Goals"].sum() < 1:
        recs.append("🎯 Low scoring — improve attacking efficiency")

    if not recs:
        recs.append("✅ Team performance is balanced")

    for r in recs:
        st.markdown(f"- {r}")

    # Prediction (simplified)
    st.subheader("🔮 Match Prediction")
    st.metric("Home Win", "52%")
    st.metric("Draw", "25%")
    st.metric("Away Win", "23%")

# =============================
# 🏥 PLAYER HEALTH
# =============================

def render_health(df):
    st.subheader("🏥 Player Fitness & Risk")

    if df.empty:
        return

    df["Risk"] = df["Minutes_Played"].apply(
        lambda x: "High" if x > 80 else "Moderate" if x > 60 else "Low"
    )

    st.dataframe(df[["Player","Minutes_Played","Risk"]])

    st.subheader("🚨 Alerts")
    high = df[df["Risk"] == "High"]
    for _, row in high.iterrows():
        st.error(f"{row['Player']} — HIGH fatigue risk")

# =============================
# 📊 SQUAD OVERVIEW
# =============================

def render_squad(df):
    st.subheader("📊 Squad Overview")

    if df.empty:
        return

    top = df.sort_values("Performance_Index", ascending=False).head(5)
    st.write("Top Performers")
    st.dataframe(top[["Player","Performance_Index"]])

# =============================
# 📄 PDF GENERATOR
# =============================

def generate_pdf(df, filename="report.pdf"):
    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("Match Report", styles['Title']))
    content.append(Spacer(1, 12))

    for _, row in df.head(10).iterrows():
        content.append(Paragraph(str(row.to_dict()), styles['Normal']))
        content.append(Spacer(1, 8))

    doc.build(content)
    return filename

# =============================
# 🚀 MAIN APP
# =============================

def main():
    st.set_page_config(page_title="ITARA", layout="wide")

    st.title("⚽ ITARA — Football Performance System")

    # Dummy data
    df = pd.DataFrame({
        "Player": ["Player A","Player B","Player C"],
        "Minutes_Played": [90, 70, 50],
        "Goals": [0,1,0],
        "Performance_Index": [6.5,7.2,6.0]
    })

    menu = st.sidebar.selectbox("Navigation", [
        "Match Center",
        "Player Health",
        "Squad Overview",
        "Reports"
    ])

    if menu == "Match Center":
        render_match_center(df)

    elif menu == "Player Health":
        render_health(df)

    elif menu == "Squad Overview":
        render_squad(df)

    elif menu == "Reports":
        if st.button("Download Report"):
            file = generate_pdf(df)
            st.success(f"Report generated: {file}")

if __name__ == "__main__":
    main()

# =============================
# 🎤 DEMO PITCH SCRIPT
# =============================

"""
Hello Coach,

I built a system that helps you understand exactly why your team wins or loses.

After every match, you get:
- A performance report
- Key player ratings
- Clear recommendations on what to improve

For example:
- Which players are at risk of fatigue
- Where your team is losing chances
- How to prepare against your next opponent

This is not complicated analytics — it's simple insights to help you win more matches.

I’d like to analyze your next match for free and show you the value.

If it helps your team, we can continue working together.
"""
