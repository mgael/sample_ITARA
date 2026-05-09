"""
ITARA ML Intelligence Page
Renders all 4 ML features inside the Streamlit app.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

PL = dict(template='plotly_white', plot_bgcolor='#faf7f2',
          paper_bgcolor='#faf7f2', font_color='#1c1917', title_font_size=13)

def render_ml_page(df_all, user, season):
    from ml_engine import (get_models, predict_injury, predict_match,
                            predict_dev, cluster_players)

    st.markdown("""
    <div style='background:linear-gradient(135deg,#1c1917,#2c2218);border-radius:14px;
    padding:28px 36px;margin-bottom:24px;box-shadow:0 4px 20px rgba(0,0,0,0.15);'>
        <div style='font-family:Fraunces,serif;font-size:2rem;font-weight:800;color:#d97757;'>
            🤖 ITARA ML Intelligence
        </div>
        <div style='color:#a8a29e;font-size:0.85rem;margin-top:6px;letter-spacing:0.07em;
        text-transform:uppercase;'>
            Machine Learning · Injury Prediction · Match Forecasting ·
            Development Forecast · Talent Clustering
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load / train models ──────────────────────────────────────────
    with st.spinner("⚙️  Loading ITARA ML models — first run trains on synthetic data..."):
        models = get_models()

    # Model health bar
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏥 Injury Model",      f"ROC-AUC {models['injury']['metric']}")
    c2.metric("⚽ Match Model",        f"Accuracy {models['match']['metric']}")
    c3.metric("📈 Dev Forecast",       "Ridge Regression")
    c4.metric("🔍 Talent Clusters",    "K-Means (5 archetypes)")

    st.caption(
        "Models trained on synthetic African league data. "
        "Replace synthetic generators in ml_engine.py with real data loaders "
        "to upgrade accuracy as platform data grows."
    )
    st.markdown("---")

    tabs = st.tabs([
        "🏥 Injury Prediction",
        "⚽ Match Result Forecast",
        "📈 Player Development",
        "🔍 Talent Discovery"
    ])

    # ════════════════════════════════════════════
    # TAB 1 — INJURY PREDICTION
    # ════════════════════════════════════════════
    with tabs[0]:
        st.markdown("### 🏥 Injury Risk Prediction")
        st.markdown(
            "The Random Forest model analyses **9 player attributes** — workload, "
            "age, fitness, and physical intensity — to estimate injury probability. "
            "**ROC-AUC: {}**".format(models['injury']['metric'])
        )

        if not df_all.empty:
            # Squad-wide scan
            st.markdown("#### Squad Injury Risk Scan")
            results = []
            for _, row in df_all.iterrows():
                r = predict_injury(models['injury']['model'], row.to_dict())
                results.append({
                    "Player":      row.get("Player", "Unknown"),
                    "Team":        row.get("Team", ""),
                    "Position":    row.get("Position", ""),
                    "Age":         row.get("Age", 0),
                    "Fitness%":    row.get("Health_Score", 0),
                    "Minutes":     row.get("Minutes_Played", 0),
                    "Injury Prob %": round(r["probability"] * 100, 1),
                    "Risk Level":  r["risk_level"],
                    "Top Factor":  r["top_factors"][0] if r["top_factors"] else "",
                })
            rdf = pd.DataFrame(results).sort_values("Injury Prob %", ascending=False)

            # Colour the risk column
            def colour_risk(val):
                if "High" in str(val):   return "color:#ef4444;font-weight:700"
                if "Moderate" in str(val): return "color:#f59e0b;font-weight:700"
                return "color:#22c55e;font-weight:700"

            st.dataframe(
                rdf.style.applymap(colour_risk, subset=["Risk Level"])
                         .background_gradient(subset=["Injury Prob %"], cmap="RdYlGn_r"),
                use_container_width=True
            )

            # Visualisations
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    rdf.head(12), x="Player", y="Injury Prob %",
                    color="Injury Prob %", color_continuous_scale="RdYlGn_r",
                    title="Top Injury Risk Players", text="Injury Prob %"
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(**PL)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                cnt = rdf["Risk Level"].value_counts().reset_index()
                cnt.columns = ["Risk", "Count"]
                fig2 = px.pie(
                    cnt, names="Risk", values="Count",
                    title="Squad Risk Distribution",
                    color_discrete_sequence=["#ef4444","#f59e0b","#22c55e"]
                )
                fig2.update_layout(**PL)
                st.plotly_chart(fig2, use_container_width=True)

            # Scatter: minutes vs fitness, sized by injury prob
            fig3 = px.scatter(
                rdf, x="Fitness%", y="Minutes", color="Injury Prob %",
                size="Injury Prob %", hover_data=["Player","Risk Level","Top Factor"],
                color_continuous_scale="RdYlGn_r",
                title="Fitness vs Minutes Load (size = injury probability)"
            )
            fig3.update_layout(**PL)
            st.plotly_chart(fig3, use_container_width=True)

            # Deep dive for one player
            st.markdown("---")
            st.markdown("#### Deep-Dive: Individual Player Assessment")
            sel = st.selectbox("Select player", df_all["Player"].unique(), key="inj_sel")
            p   = df_all[df_all["Player"] == sel].iloc[0]
            r   = predict_injury(models["injury"]["model"], p.to_dict())
            c1, c2, c3 = st.columns(3)
            c1.metric("Injury Probability", f"{r['probability']*100:.1f}%")
            c2.metric("Risk Level", r["risk_level"])
            c3.metric("Primary Risk Factor", r["top_factors"][0])
            st.progress(r["probability"])
            st.info(
                f"**Top contributing factors:** "
                f"{', '.join(r['top_factors'])}. "
                "Reduce workload or improve fitness to lower risk."
            )
        else:
            st.warning("Add players in Data Management to run injury predictions.")

    # ════════════════════════════════════════════
    # TAB 2 — MATCH RESULT FORECAST
    # ════════════════════════════════════════════
    with tabs[1]:
        st.markdown("### ⚽ Match Result Forecast")
        st.markdown(
            "Gradient Boosting model predicts **Home Win / Draw / Away Win** "
            "using team strength, fitness, form, and head-to-head history. "
            "**CV Accuracy: {}**".format(models["match"]["metric"])
        )

        teams = st.session_state.teams if st.session_state.teams else ["Team A", "Team B"]
        df_data = st.session_state.data.copy()

        def team_stats(team_name):
            t = df_data[df_data["Team"] == team_name] if not df_data.empty else pd.DataFrame()
            return {
                "avg_pi":      float(t["Performance_Index"].mean()) if not t.empty else 5.5,
                "avg_fitness": float(t["Health_Score"].mean()) if not t.empty else 75.0,
            }

        st.markdown("#### Configure a Fixture")
        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("🏠 Home Team", teams, key="mp_home")
            h2h  = st.slider("H2H — home wins in last 5 meetings", 0, 5, 2)
            hform= st.slider("Home team — points from last 5 games", 0, 15, 8)
        with col2:
            away = st.selectbox("✈️  Away Team",
                                [t for t in teams if t != home] or teams, key="mp_away")
            aform= st.slider("Away team — points from last 5 games", 0, 15, 7)

        if st.button("🔮 Generate Prediction", key="mp_btn"):
            ht = team_stats(home); at = team_stats(away)
            res = predict_match(
                models["match"]["model"], ht, at, h2h, hform, aform
            )

            st.markdown("---")
            st.markdown(f"#### {home}  vs  {away}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🏠 Home Win",  f"{res['home_win']}%")
            c2.metric("🤝 Draw",       f"{res['draw']}%")
            c3.metric("✈️  Away Win",  f"{res['away_win']}%")
            c4.metric("🤖 Prediction", res["prediction"],
                      delta=f"{res['confidence']}% confidence")

            # Probability bar chart
            fig = go.Figure(go.Bar(
                x=["Home Win", "Draw", "Away Win"],
                y=[res["home_win"], res["draw"], res["away_win"]],
                marker_color=["#d97757","#a8a29e","#57534e"],
                text=[f"{v}%" for v in [res["home_win"],res["draw"],res["away_win"]]],
                textposition="outside"
            ))
            fig.update_layout(**PL, title=f"Outcome Probabilities — {home} vs {away}",
                              yaxis_range=[0, 105])
            st.plotly_chart(fig, use_container_width=True)

            # Team comparison
            st.markdown("#### Team Strength Comparison")
            comp = pd.DataFrame({
                "Metric":   ["Avg Performance Index", "Avg Fitness %"],
                home:       [round(ht["avg_pi"],2), round(ht["avg_fitness"],1)],
                away:       [round(at["avg_pi"],2), round(at["avg_fitness"],1)],
            })
            st.dataframe(comp.set_index("Metric"), use_container_width=True)

        # Bulk fixture matrix
        if len(teams) >= 2:
            st.markdown("---")
            st.markdown("#### 📊 Full Season Fixture Probability Matrix")
            st.caption("Home Win % for every home vs away combination")
            matrix = {}
            for h in teams:
                matrix[h] = {}
                ht = team_stats(h)
                for a in teams:
                    if h == a:
                        matrix[h][a] = "-"
                    else:
                        at = team_stats(a)
                        r2 = predict_match(models["match"]["model"],ht,at)
                        matrix[h][a] = f"{r2['home_win']}%"
            mdf = pd.DataFrame(matrix).T
            st.dataframe(mdf, use_container_width=True)

    # ════════════════════════════════════════════
    # TAB 3 — PLAYER DEVELOPMENT FORECAST
    # ════════════════════════════════════════════
    with tabs[2]:
        st.markdown("### 📈 Player Development Forecast (6-Month Horizon)")
        st.markdown(
            "Ridge regression model projects each player's **Performance Index "
            "and Market Value** 6 months forward based on age, current form, "
            "workload and fitness trajectory."
        )

        if not df_all.empty:
            # Squad-wide forecast
            st.markdown("#### Full Squad Development Projections")
            devs = []
            for _, row in df_all.iterrows():
                d = predict_dev(
                    models["dev"]["scaler"], models["dev"]["m_pi"],
                    models["dev"]["m_mv"], row.to_dict()
                )
                devs.append({
                    "Player":          row.get("Player",""),
                    "Team":            row.get("Team",""),
                    "Position":        row.get("Position",""),
                    "Age":             row.get("Age",0),
                    "Current PI":      d["current_pi"],
                    "Forecast PI (6M)":d["forecast_pi"],
                    "PI Change":       d["delta_pi"],
                    "Forecast Value":  int(d["forecast_mv"]),
                    "Trajectory":      d["trajectory"],
                })
            ddf = pd.DataFrame(devs).sort_values("Forecast PI (6M)", ascending=False)

            def colour_traj(val):
                if "Growth" in str(val):  return "color:#22c55e;font-weight:700"
                if "Steady" in str(val):  return "color:#3b82f6;font-weight:700"
                if "Plateau" in str(val): return "color:#a8a29e"
                return "color:#ef4444"

            st.dataframe(
                ddf.style.applymap(colour_traj, subset=["Trajectory"])
                         .background_gradient(subset=["Forecast PI (6M)"], cmap="Oranges"),
                use_container_width=True
            )

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    ddf.head(12), x="Player", y=["Current PI","Forecast PI (6M)"],
                    barmode="group", title="Current vs Forecast PI",
                    color_discrete_sequence=["#a8a29e","#d97757"]
                )
                fig.update_layout(**PL)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                tc = ddf["Trajectory"].value_counts().reset_index()
                tc.columns = ["Trajectory","Count"]
                fig2 = px.pie(
                    tc, names="Trajectory", values="Count",
                    title="Squad Development Trajectory Mix",
                    color_discrete_sequence=["#22c55e","#3b82f6","#d97757","#ef4444","#a8a29e"]
                )
                fig2.update_layout(**PL)
                st.plotly_chart(fig2, use_container_width=True)

            # Scatter: age vs PI change
            fig3 = px.scatter(
                ddf, x="Age", y="PI Change", color="Trajectory",
                size="Forecast Value", hover_data=["Player","Team"],
                title="Age vs Projected PI Growth (size = forecast value)",
                color_discrete_map={
                    "📈 Strong Growth":"#22c55e","📊 Steady Progress":"#3b82f6",
                    "➡️  Plateau":"#a8a29e","📉 Declining":"#ef4444"
                }
            )
            fig3.add_hline(y=0, line_dash="dash", line_color="#d97757",
                           annotation_text="No change")
            fig3.update_layout(**PL)
            st.plotly_chart(fig3, use_container_width=True)

            # Individual deep dive
            st.markdown("---")
            st.markdown("#### Individual Player Forecast")
            sel2 = st.selectbox("Select player", df_all["Player"].unique(), key="dev_sel")
            p2   = df_all[df_all["Player"] == sel2].iloc[0]
            d2   = predict_dev(models["dev"]["scaler"], models["dev"]["m_pi"],
                               models["dev"]["m_mv"], p2.to_dict())
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Current PI",    f"{d2['current_pi']:.2f}")
            c2.metric("Forecast PI",   f"{d2['forecast_pi']:.2f}",
                      delta=f"{d2['delta_pi']:+.2f}")
            c3.metric("Forecast Value",f"{d2['forecast_mv']:,.0f} RWF")
            c4.metric("Trajectory",    d2["trajectory"])

            # Gauge
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=d2["forecast_pi"],
                delta={"reference": d2["current_pi"]},
                gauge=dict(
                    axis=dict(range=[0,10]),
                    bar=dict(color="#d97757"),
                    steps=[
                        dict(range=[0,5],  color="#fef3c7"),
                        dict(range=[5,7],  color="#fed7aa"),
                        dict(range=[7,10], color="#fecaca"),
                    ],
                    threshold=dict(line=dict(color="#1c1917",width=3),
                                   thickness=0.75, value=d2["current_pi"])
                ),
                title=dict(text=f"6-Month PI Forecast — {sel2}")
            ))
            fig_g.update_layout(paper_bgcolor="#faf7f2", font_color="#1c1917", height=300)
            st.plotly_chart(fig_g, use_container_width=True)
        else:
            st.warning("Add players in Data Management to run development forecasts.")

    # ════════════════════════════════════════════
    # TAB 4 — TALENT DISCOVERY / CLUSTERING
    # ════════════════════════════════════════════
    with tabs[3]:
        st.markdown("### 🔍 Talent Discovery — Player Archetype Clustering")
        st.markdown(
            "K-Means clustering (k=5) groups players into **performance archetypes** "
            "using 9 statistical dimensions, reduced to 2D via PCA for visualisation. "
            "Use this to find players matching a target profile or uncover hidden gems."
        )

        if not df_all.empty:
            cdf = cluster_players(models["cluster"]["model"], df_all.copy())
            cdf["CPR"] = cdf.apply(lambda r: round(min(
                r.get("Performance_Index",5)*0.40
                +min(r.get("Goals",0)/max(r.get("Matches",1),1)*10,10)*0.20
                +min(r.get("Assists",0)/max(r.get("Matches",1),1)*10,10)*0.15
                +r.get("Pass_Accuracy",75)/10*0.10
                +r.get("Health_Score",100)/10*0.10
                +min(((r.get("Dribbles_Completed",0)/max(r.get("Matches",1),1))*0.6
                      +(r.get("Tackles_Won",0)/max(r.get("Matches",1),1))*0.4)*1.5,10)*0.05
            ,10),2), axis=1)

            # 2-D archetype scatter
            st.markdown("#### 🗺️ Player Archetype Map (PCA 2D Projection)")
            fig = px.scatter(
                cdf, x="PCA_X", y="PCA_Y",
                color="Archetype", symbol="Archetype",
                hover_data=["Player","Team","Position","CPR"],
                color_discrete_map={row[0]:row[1] for row in [
                    ("🌟 Elite Creator","#d97757"),("⚔️  Goal Threat","#b85e3a"),
                    ("🛡️  Defensive Anchor","#57534e"),("🔧 Engine Room","#92400e"),
                    ("🌱 Rising Prospect","#c9a84c")]},
                title="Player Archetypes in 2D Feature Space"
            )
            fig.update_traces(marker=dict(size=11, opacity=0.85,
                              line=dict(width=1, color="#ffffff")))
            fig.update_layout(**PL, height=480,
                legend=dict(bgcolor="#faf7f2",bordercolor="#e7e0d5",borderwidth=1))
            st.plotly_chart(fig, use_container_width=True)

            # Archetype summary table
            st.markdown("#### Archetype Breakdown")
            arch_sum = (cdf.groupby("Archetype")
                          .agg(Count=("Player","count"),
                               Avg_CPR=("CPR","mean"),
                               Avg_PI=("Performance_Index","mean"),
                               Avg_Goals=("Goals","mean"),
                               Avg_Fitness=("Health_Score","mean"))
                          .round(2).reset_index())
            st.dataframe(arch_sum, use_container_width=True)

            # Player roster per archetype
            st.markdown("---")
            st.markdown("#### Browse Players by Archetype")
            sel_arch = st.selectbox("Select Archetype",
                                    sorted(cdf["Archetype"].unique()), key="arch_sel")
            arch_players = cdf[cdf["Archetype"]==sel_arch].sort_values("CPR",ascending=False)
            show_cols = ["Player","Team","Position","Age","CPR",
                         "Performance_Index","Goals","Assists","Health_Score"]
            st.dataframe(
                arch_players[[c for c in show_cols if c in arch_players.columns]]
                .style.background_gradient(subset=["CPR"], cmap="Oranges"),
                use_container_width=True
            )

            # Profile match: find similar players to a target
            st.markdown("---")
            st.markdown("#### 🎯 Find Similar Players (Talent Matching)")
            target = st.selectbox("Select target player to match",
                                  df_all["Player"].unique(), key="sim_sel")
            tp     = cdf[cdf["Player"]==target].iloc[0]
            same   = cdf[(cdf["Archetype"]==tp["Archetype"]) &
                         (cdf["Player"]!=target)].sort_values("CPR",ascending=False)
            if not same.empty:
                st.markdown(
                    f"**{target}** is a **{tp['Archetype']}**. "
                    f"Here are the most similar players in the league:"
                )
                st.dataframe(
                    same[[c for c in show_cols if c in same.columns]].head(8)
                    .style.background_gradient(subset=["CPR"], cmap="Oranges"),
                    use_container_width=True
                )
            else:
                st.info("No similar players found in the current dataset for this archetype.")

            # Distribution charts
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                fig2 = px.bar(
                    arch_sum, x="Archetype", y="Count",
                    color="Archetype", title="Players per Archetype",
                    color_discrete_sequence=["#d97757","#b85e3a","#57534e","#92400e","#c9a84c"]
                )
                fig2.update_layout(**PL, showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            with col2:
                fig3 = px.box(
                    cdf, x="Archetype", y="CPR", color="Archetype",
                    title="CPR Distribution by Archetype",
                    color_discrete_sequence=["#d97757","#b85e3a","#57534e","#92400e","#c9a84c"]
                )
                fig3.update_layout(**PL, showlegend=False)
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.warning("Add players in Data Management to run talent clustering.")

    # ── Footer note ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='background:#faf7f2;border:1px solid #e7e0d5;border-radius:10px;padding:16px 20px;'>
        <div style='font-family:Fraunces,serif;font-size:0.95rem;font-weight:700;
        color:#d97757;margin-bottom:6px;'>🔬 About the ML Models</div>
        <div style='font-size:0.82rem;color:#57534e;line-height:1.7;'>
            <b>Injury Model</b>: Random Forest (200 trees) trained on 400 synthetic player-seasons.
            Features: age, minutes, fitness, PI, goals, assists, dribbles, tackles. ROC-AUC measures
            ability to distinguish high vs low risk players.<br>
            <b>Match Model</b>: Gradient Boosting (250 estimators) trained on 600 synthetic fixtures.
            Features: team PI, fitness, H2H record, recent form. 5-fold CV accuracy reported.<br>
            <b>Development Model</b>: Ridge Regression forecasting PI and market value
            at a 6-month horizon. Age peak curve baked into training labels.<br>
            <b>Talent Clustering</b>: K-Means (k=5) with StandardScaler + PCA(2D).
            Five archetypes discovered from 9 performance dimensions.<br><br>
            <i>To upgrade to real data: replace the synthetic generators in
            <code>ml_engine.py</code> with loaders from <code>st.session_state.data</code>
            once sufficient historical records are collected.</i>
        </div>
    </div>
    """, unsafe_allow_html=True)
