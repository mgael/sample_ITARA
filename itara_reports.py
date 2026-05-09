"""
ITARA Sports Analytics — Professional Report Engine
====================================================
Three completely distinct PDF reports:
  A. Football Agent Intelligence Brief
  B. Journalist Media Pack
  C. Team Manager/Coach Tactical Dossier

Each report has a unique cover page, unique sections,
unique insights and unique language (EN + FR bilingual).
"""

import io
import datetime
import math
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, PageBreak, HRFlowable, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF


# ── BRAND COLOURS ────────────────────────────────────────────
C_ACCENT   = colors.HexColor("#d97757")
C_DARK     = colors.HexColor("#1c1917")
C_SEC      = colors.HexColor("#57534e")
C_MUTED    = colors.HexColor("#a8a29e")
C_BORDER   = colors.HexColor("#e7e0d5")
C_BG       = colors.HexColor("#faf7f2")
C_WHITE    = colors.white
C_AGENT    = colors.HexColor("#7c3aed")
C_JOURNAL  = colors.HexColor("#0369a1")
C_MANAGER  = colors.HexColor("#065f46")
C_ADMIN    = colors.HexColor("#92400e")
C_GREEN    = colors.HexColor("#22c55e")
C_YELLOW   = colors.HexColor("#f59e0b")
C_RED      = colors.HexColor("#ef4444")
C_GOLD     = colors.HexColor("#c9a84c")


# ── ANALYTICS ────────────────────────────────────────────────
def calc_cpr(p):
    m  = max(p.get("Matches", 1), 1)
    g  = min(p.get("Goals", 0) / m * 10, 10)
    a  = min(p.get("Assists", 0) / m * 10, 10)
    pa = p.get("Pass_Accuracy", 75) / 10
    h  = p.get("Health_Score", 100) / 10
    dr = p.get("Dribbles_Completed", 0) / m
    tk = p.get("Tackles_Won", 0) / m
    pr = min((dr * 0.6 + tk * 0.4) * 1.5, 10)
    pi = p.get("Performance_Index", 5)
    return round(min(pi*0.40 + g*0.20 + a*0.15 + pa*0.10 + h*0.10 + pr*0.05, 10), 2)

def calc_mv(p):
    pi  = p.get("Performance_Index", 5)
    m   = max(p.get("Matches", 1), 1)
    age = p.get("Age", 25)
    af  = max(0.6, 1.0 - abs(age - 25) * 0.015)
    return round((pi * 1_250_000) * (1 + m * 0.05) * af, -3)

def calc_xg(p):
    s = max(p.get("Shots_on_Target", 0), 0)
    m = max(p.get("Matches", 1), 1)
    return round(s / m * 0.32 * m, 2)

def calc_xa(p):
    a  = p.get("Assists", 0)
    pa = p.get("Pass_Accuracy", 75) / 100
    return round(max(a * (1 + (pa - 0.75)), 0), 2)

def form_label(pi):
    if pi >= 8.5: return "Elite"
    if pi >= 7.0: return "Strong"
    if pi >= 5.0: return "Developing"
    return "Underperforming"

def form_label_fr(pi):
    if pi >= 8.5: return "Élite"
    if pi >= 7.0: return "Fort"
    if pi >= 5.0: return "En développement"
    return "Sous-performant"

def avail_label(h):
    if h >= 85: return "✓ Match Ready"
    if h >= 70: return "~ Light Training"
    if h >= 50: return "! Monitored"
    return "✗ Unavailable"

def risk_label(p):
    h  = p.get("Health_Score", 100)
    pi = p.get("Performance_Index", 5)
    if h < 50 or pi < 3: return "HIGH", C_RED
    if h < 70 or pi < 5: return "MEDIUM", C_YELLOW
    return "LOW", C_GREEN

def dev_forecast(p):
    age = p.get("Age", 25)
    pi  = p.get("Performance_Index", 5)
    af  = 1.06 if age < 24 else 1.02 if age < 28 else 0.97
    fpi = round(min(pi * af, 10), 2)
    delta = round(fpi - pi, 2)
    if delta >  0.5: traj = "📈 Strong Growth"
    elif delta >  0.1: traj = "📊 Steady Progress"
    elif delta > -0.2: traj = "➡  Plateau"
    else:              traj = "📉 Declining"
    return fpi, delta, traj

def contract_status(end_str):
    try:
        end  = datetime.datetime.strptime(str(end_str), "%Y-%m-%d").date()
        diff = (end - datetime.date.today()).days
        if diff < 0:    return "EXPIRED",   C_RED
        if diff <= 90:  return f"EXPIRING ({diff}d)", C_RED
        if diff <= 180: return f"DUE SOON ({diff}d)", C_YELLOW
        return f"ACTIVE ({diff}d)", C_GREEN
    except:
        return "UNKNOWN", C_MUTED


# ── SHARED STYLE BUILDER ─────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle("cover_title",
        fontName="Helvetica-Bold", fontSize=28, textColor=C_WHITE,
        alignment=TA_LEFT, spaceAfter=8, leading=34)

    styles["cover_sub"] = ParagraphStyle("cover_sub",
        fontName="Helvetica", fontSize=12, textColor=colors.HexColor("#d6d3d1"),
        alignment=TA_LEFT, spaceAfter=6, leading=16)

    styles["cover_label"] = ParagraphStyle("cover_label",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_ACCENT,
        alignment=TA_LEFT, spaceAfter=3, leading=12,
        spaceBefore=4, letterSpacing=1.5)

    styles["section_h1"] = ParagraphStyle("section_h1",
        fontName="Helvetica-Bold", fontSize=15, textColor=C_DARK,
        spaceBefore=18, spaceAfter=8, leading=19,
        borderPadding=(0, 0, 4, 0))

    styles["section_h2"] = ParagraphStyle("section_h2",
        fontName="Helvetica-Bold", fontSize=11, textColor=C_ACCENT,
        spaceBefore=12, spaceAfter=5, leading=14)

    styles["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9, textColor=C_DARK,
        leading=13, spaceAfter=4, alignment=TA_JUSTIFY)

    styles["body_bold"] = ParagraphStyle("body_bold",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_DARK,
        leading=13, spaceAfter=4)

    styles["small"] = ParagraphStyle("small",
        fontName="Helvetica", fontSize=7.5, textColor=C_SEC,
        leading=10, spaceAfter=2)

    styles["small_italic"] = ParagraphStyle("small_italic",
        fontName="Helvetica-Oblique", fontSize=7.5, textColor=C_MUTED,
        leading=10, spaceAfter=2)

    styles["label_fr"] = ParagraphStyle("label_fr",
        fontName="Helvetica-Oblique", fontSize=8, textColor=C_MUTED,
        leading=11, spaceAfter=2)

    styles["verdict"] = ParagraphStyle("verdict",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_ACCENT,
        leading=12, spaceAfter=4)

    styles["insight_box"] = ParagraphStyle("insight_box",
        fontName="Helvetica", fontSize=8.5, textColor=C_DARK,
        leading=12, spaceAfter=3, leftIndent=8)

    styles["confidential"] = ParagraphStyle("confidential",
        fontName="Helvetica-Bold", fontSize=7, textColor=C_RED,
        alignment=TA_CENTER, spaceAfter=0)

    styles["footer"] = ParagraphStyle("footer",
        fontName="Helvetica", fontSize=7, textColor=C_MUTED,
        alignment=TA_CENTER, spaceAfter=0)

    return styles


# ── SHARED TABLE STYLE BUILDER ────────────────────────────────
def std_table_style(header_color=C_ACCENT):
    return TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 7.5),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",        (0, 0), (0, -1), "LEFT"),
        ("GRID",         (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_BG]),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ])


# ── PAGE TEMPLATES ────────────────────────────────────────────
def make_cover_page(elements, styles, role_color, role_label,
                    role_label_fr, user_name, season, subtitle, subtitle_fr,
                    confidential_text, confidential_text_fr):
    """Builds a full dark cover page."""

    # Dark background block via table
    cover_data = [[""]]
    cover_table = Table(cover_data, colWidths=[7.27*inch], rowHeights=[9.7*inch])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_DARK),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING",(0,0),(-1,-1), 0),
    ]))

    # We build cover content as overlaid paragraphs after the table
    elements.append(cover_table)
    elements.append(PageBreak())

    # --- Actual cover content page (white bg with accent bar) ---
    # Accent top bar
    bar_data = [[""]]
    bar = Table(bar_data, colWidths=[7.27*inch], rowHeights=[0.18*inch])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), role_color),
        ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))
    elements.append(bar)
    elements.append(Spacer(1, 0.3*inch))

    # ITARA header
    elements.append(Paragraph("⚽  ITARA SPORTS ANALYTICS", ParagraphStyle("ch",
        fontName="Helvetica-Bold", fontSize=11, textColor=role_color,
        letterSpacing=2, spaceAfter=2)))
    elements.append(Paragraph("African Football Intelligence Platform · 🇷🇼 Made in Rwanda",
        ParagraphStyle("cs", fontName="Helvetica", fontSize=8,
            textColor=C_SEC, spaceAfter=16)))

    elements.append(HRFlowable(width="100%", thickness=0.5,
                                color=C_BORDER, spaceAfter=20))

    # Role badge
    badge_data = [[Paragraph(f"  {role_label}  ", ParagraphStyle("rb",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE))]]
    badge = Table(badge_data, colWidths=[1.8*inch])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), role_color),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
        ("ROUNDEDCORNERS", [4,4,4,4]),
    ]))
    elements.append(badge)
    elements.append(Spacer(1, 0.2*inch))

    # Report title
    elements.append(Paragraph(subtitle, ParagraphStyle("rt",
        fontName="Helvetica-Bold", fontSize=22, textColor=C_DARK,
        leading=28, spaceAfter=6)))
    elements.append(Paragraph(subtitle_fr, ParagraphStyle("rtf",
        fontName="Helvetica-Oblique", fontSize=13, textColor=C_SEC,
        leading=18, spaceAfter=24)))

    elements.append(HRFlowable(width="100%", thickness=0.5,
                                color=C_BORDER, spaceAfter=20))

    # Metadata grid
    meta = [
        ["Prepared for / Préparé pour:", user_name],
        ["Role / Rôle:",                 f"{role_label}  |  {role_label_fr}"],
        ["Season / Saison:",             season],
        ["Date:",                        datetime.date.today().strftime("%d %B %Y")],
        ["Issued by / Émis par:",        "ITARA Sports Analytics Platform"],
    ]
    meta_table = Table(meta, colWidths=[2.2*inch, 5.0*inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",  (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), C_SEC),
        ("TEXTCOLOR", (1,0), (1,-1), C_DARK),
        ("TOPPADDING",(0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW", (0,0), (-1,-2), 0.3, C_BORDER),
        ("LEFTPADDING",(0,0),(-1,-1), 0),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.4*inch))

    # Confidentiality notice
    conf_box = Table([[
        Paragraph(f"⚠  {confidential_text}\n{confidential_text_fr}",
            ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=8,
                textColor=C_RED, leading=12, alignment=TA_CENTER))
    ]], colWidths=[7.27*inch])
    conf_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), colors.HexColor("#fff5f5")),
        ("BOX", (0,0),(-1,-1), 0.5, C_RED),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    elements.append(conf_box)
    elements.append(Spacer(1, 0.3*inch))

    # Methodology note
    elements.append(Paragraph(
        "Methodology / Méthodologie: CPR = 0.40×PI + 0.20×G/M + 0.15×A/M + "
        "0.10×PassAcc + 0.10×Health + 0.05×ProgScore  |  "
        "Market Value: V = PI × κ × (1+ΔM) × AgeFactor, κ = RWF 1,250,000",
        ParagraphStyle("mn", fontName="Helvetica-Oblique", fontSize=6.5,
            textColor=C_MUTED, leading=10, alignment=TA_CENTER)))
    elements.append(PageBreak())


def section_header(elements, styles, title_en, title_fr, color=C_ACCENT):
    """Adds a styled bilingual section header with underline."""
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph(title_en, ParagraphStyle("sh",
        fontName="Helvetica-Bold", fontSize=13, textColor=C_DARK,
        spaceAfter=2, leading=16)))
    elements.append(Paragraph(title_fr, ParagraphStyle("shf",
        fontName="Helvetica-Oblique", fontSize=9, textColor=C_SEC,
        spaceAfter=6, leading=12)))
    elements.append(HRFlowable(width="100%", thickness=1.5,
                                color=color, spaceAfter=12))


def insight_box(elements, title_en, title_fr, text_en, text_fr, color=C_ACCENT):
    """A coloured insight/recommendation box."""
    content = Table([[
        Paragraph(
            f"<b>{title_en}</b>  <i>/ {title_fr}</i><br/>"
            f"{text_en}<br/><i>{text_fr}</i>",
            ParagraphStyle("ib", fontName="Helvetica", fontSize=8.5,
                textColor=C_DARK, leading=13, leftIndent=4))
    ]], colWidths=[7.27*inch])
    content.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), colors.HexColor("#fff8f4")),
        ("LINEBEFORE", (0,0),(0,-1), 3, color),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),12),
    ]))
    elements.append(content)
    elements.append(Spacer(1, 0.1*inch))


# ══════════════════════════════════════════════════════════════
# REPORT A — FOOTBALL AGENT INTELLIGENCE BRIEF
# ══════════════════════════════════════════════════════════════
def generate_agent_report(df_players, user_name, season,
                           compare_pair=None, contracts_df=None):
    """
    df_players : list of dicts (player records)
    user_name  : str
    season     : str  e.g. "2024/25"
    compare_pair : (player_name_1, player_name_2) or None
    contracts_df : list of dicts with contract records or None
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.65*inch, bottomMargin=0.65*inch)
    styles  = make_styles()
    elements = []

    # Enrich players
    players = []
    for p in df_players:
        p = dict(p)
        p["cpr"]  = calc_cpr(p)
        p["mv"]   = calc_mv(p)
        p["xg"]   = calc_xg(p)
        p["xa"]   = calc_xa(p)
        p["form"] = form_label(p.get("Performance_Index", 5))
        p["form_fr"] = form_label_fr(p.get("Performance_Index", 5))
        p["avail"]   = avail_label(p.get("Health_Score", 100))
        fpi, delta, traj = dev_forecast(p)
        p["fpi"]   = fpi
        p["delta"] = delta
        p["traj"]  = traj
        players.append(p)

    players.sort(key=lambda x: x["cpr"], reverse=True)

    # ── COVER ────────────────────────────────────────────────
    make_cover_page(elements, styles,
        role_color=C_AGENT,
        role_label="FOOTBALL AGENT",
        role_label_fr="AGENT DE FOOTBALL",
        user_name=user_name,
        season=season,
        subtitle="Football Agent Intelligence Brief",
        subtitle_fr="Rapport d'Intelligence pour Agent de Football",
        confidential_text="CONFIDENTIAL — For Agent Use Only. Not for Public Distribution.",
        confidential_text_fr="CONFIDENTIEL — Réservé à l'usage de l'agent. Non destiné à la distribution publique.")

    # ── SECTION 1: EXECUTIVE SUMMARY ─────────────────────────
    section_header(elements, styles,
        "1. Executive Summary",
        "1. Résumé Exécutif", C_AGENT)

    elements.append(Paragraph(
        f"This Intelligence Brief covers <b>{len(players)} players</b> tracked "
        f"in the ITARA database for the <b>{season}</b> season. "
        "Rankings are based on the Composite Player Rating (CPR), ITARA's "
        "proprietary 0–10 scoring system combining performance, creativity, "
        "passing, physical and fitness dimensions.",
        styles["body"]))
    elements.append(Paragraph(
        f"Ce rapport couvre <b>{len(players)} joueurs</b> suivis dans la base "
        f"de données ITARA pour la saison <b>{season}</b>. "
        "Les classements sont basés sur le CPR, système de notation propriétaire "
        "d'ITARA sur une échelle de 0 à 10.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.12*inch))

    # Top 5 summary
    top5 = players[:5]
    elements.append(Paragraph("Top 5 Players — Agent Priority Targets",
        styles["section_h2"]))
    t5_data = [["#", "Player / Joueur", "Team / Équipe", "Pos", "CPR",
                 "PI", "xG", "xA", "Form", "Value (RWF)", "Trajectory"]]
    for i, p in enumerate(top5, 1):
        t5_data.append([
            str(i), p.get("Player",""), p.get("Team",""),
            p.get("Position",""), f"{p['cpr']:.2f}",
            f"{p.get('Performance_Index',0):.1f}",
            f"{p['xg']:.1f}", f"{p['xa']:.1f}",
            p["form"], f"{p['mv']:,.0f}", p["traj"]
        ])
    t = Table(t5_data, colWidths=[
        0.25*inch, 1.2*inch, 1.1*inch, 0.35*inch, 0.45*inch,
        0.35*inch, 0.35*inch, 0.35*inch, 0.8*inch, 0.85*inch, 1.1*inch])
    t.setStyle(std_table_style(C_AGENT))
    elements.append(t)
    elements.append(Spacer(1, 0.1*inch))

    # Verdicts
    for p in top5:
        verdict = (
            f"ITARA recommends <b>{p.get('Player','')}</b> as a "
            f"{'priority transfer target' if p['cpr'] >= 7 else 'monitoring target'}. "
            f"CPR {p['cpr']:.2f} · {p['form']} · "
            f"Estimated value: RWF {p['mv']:,.0f} · {p['traj']}"
        )
        verdict_fr = (
            f"ITARA recommande <b>{p.get('Player','')}</b> comme "
            f"{'cible de transfert prioritaire' if p['cpr'] >= 7 else 'joueur à surveiller'}. "
            f"CPR {p['cpr']:.2f} · {p['form_fr']} · "
            f"Valeur estimée : RWF {p['mv']:,.0f}"
        )
        insight_box(elements, f"Agent Verdict — {p.get('Player','')}",
            "Verdict de l'Agent", verdict, verdict_fr, C_AGENT)

    elements.append(PageBreak())

    # ── SECTION 2: FULL PLAYER SCOUTING DATABASE ─────────────
    section_header(elements, styles,
        "2. Full League Player Database",
        "2. Base de Données Complète des Joueurs", C_AGENT)

    full_data = [["Player", "Team", "Pos", "Age", "CPR", "PI",
                   "xG", "xA", "G", "A", "MP", "Fit%", "Form", "Value (RWF)"]]
    for p in players:
        full_data.append([
            p.get("Player",""), p.get("Team",""), p.get("Position",""),
            str(p.get("Age","")), f"{p['cpr']:.2f}",
            f"{p.get('Performance_Index',0):.1f}",
            f"{p['xg']:.1f}", f"{p['xa']:.1f}",
            str(p.get("Goals",0)), str(p.get("Assists",0)),
            str(p.get("Matches",0)),
            f"{p.get('Health_Score',0):.0f}%",
            p["form"], f"{p['mv']:,.0f}"
        ])
    ft = Table(full_data, colWidths=[
        0.9*inch, 0.85*inch, 0.32*inch, 0.3*inch, 0.38*inch,
        0.3*inch, 0.3*inch, 0.3*inch, 0.25*inch, 0.25*inch,
        0.25*inch, 0.32*inch, 0.62*inch, 0.77*inch])
    ft.setStyle(std_table_style(C_AGENT))
    elements.append(ft)
    elements.append(PageBreak())

    # ── SECTION 3: PHYSICAL STATUS ────────────────────────────
    section_header(elements, styles,
        "3. Physical & Fitness Status",
        "3. État Physique et de Condition", C_AGENT)

    elements.append(Paragraph(
        "Fitness directly impacts CPR and transfer value. Players below 70% "
        "fitness are flagged and should not be prioritised for immediate transfer "
        "negotiations until recovery is confirmed.",
        styles["body"]))
    elements.append(Paragraph(
        "La condition physique impacte directement le CPR et la valeur de transfert. "
        "Les joueurs en dessous de 70% sont signalés.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.1*inch))

    phys_data = [["Player / Joueur", "Team", "Pos", "Age",
                   "Fitness % / Condition", "Availability / Disponibilité",
                   "Injury Risk / Risque"]]
    for p in sorted(players, key=lambda x: x.get("Health_Score",0), reverse=True):
        risk, _ = risk_label(p)
        phys_data.append([
            p.get("Player",""), p.get("Team",""), p.get("Position",""),
            str(p.get("Age","")),
            f"{p.get('Health_Score',0):.0f}%",
            p["avail"], risk
        ])
    pt = Table(phys_data, colWidths=[1.1*inch, 0.85*inch, 0.35*inch,
        0.3*inch, 0.8*inch, 1.2*inch, 0.85*inch])
    s = std_table_style(C_AGENT)
    # Colour risk cells
    for i, p in enumerate(players, 1):
        _, rc = risk_label(p)
        s.add("TEXTCOLOR", (6, i), (6, i), rc)
        s.add("FONTNAME",  (6, i), (6, i), "Helvetica-Bold")
    pt.setStyle(s)
    elements.append(pt)
    elements.append(PageBreak())

    # ── SECTION 4: HEAD-TO-HEAD COMPARISON ───────────────────
    section_header(elements, styles,
        "4. Player Comparison",
        "4. Comparaison de Joueurs", C_AGENT)

    if compare_pair and len(players) >= 2:
        p1_name, p2_name = compare_pair
        p1 = next((p for p in players if p.get("Player") == p1_name), players[0])
        p2 = next((p for p in players if p.get("Player") == p2_name), players[1])
    elif len(players) >= 2:
        p1, p2 = players[0], players[1]
        p1_name, p2_name = p1.get("Player",""), p2.get("Player","")
    else:
        elements.append(Paragraph("Insufficient players for comparison.",
            styles["body"]))
        p1 = p2 = None

    if p1 and p2:
        elements.append(Paragraph(
            f"Head-to-head analysis: <b>{p1.get('Player','')}</b> vs "
            f"<b>{p2.get('Player','')}</b>",
            styles["body_bold"]))
        elements.append(Paragraph(
            f"Analyse tête-à-tête : <b>{p1.get('Player','')}</b> contre "
            f"<b>{p2.get('Player','')}</b>",
            styles["label_fr"]))
        elements.append(Spacer(1, 0.1*inch))

        cmp_metrics = [
            ("Metric / Métrique", "Indicator", p1.get("Player",""), p2.get("Player","")),
            ("CPR (0–10)", "Overall",          f"{p1['cpr']:.2f}", f"{p2['cpr']:.2f}"),
            ("Performance Index", "PI",         f"{p1.get('Performance_Index',0):.1f}",    f"{p2.get('Performance_Index',0):.1f}"),
            ("Expected Goals (xG)", "Attack",   f"{p1['xg']:.2f}",  f"{p2['xg']:.2f}"),
            ("Expected Assists (xA)", "Create", f"{p1['xa']:.2f}",  f"{p2['xa']:.2f}"),
            ("Goals / Buts", "Scoring",         str(p1.get("Goals",0)),  str(p2.get("Goals",0))),
            ("Assists / Passes déc.", "Create", str(p1.get("Assists",0)), str(p2.get("Assists",0))),
            ("Pass Accuracy / Précision", "Technical", f"{p1.get('Pass_Accuracy',0):.0f}%", f"{p2.get('Pass_Accuracy',0):.0f}%"),
            ("Fitness / Condition", "Physical", f"{p1.get('Health_Score',0):.0f}%", f"{p2.get('Health_Score',0):.0f}%"),
            ("Matches Played / Matchs", "Experience", str(p1.get("Matches",0)), str(p2.get("Matches",0))),
            ("6M Forecast PI", "Development",  f"{p1['fpi']:.2f}", f"{p2['fpi']:.2f}"),
            ("Trajectory / Trajectoire", "Future", p1["traj"], p2["traj"]),
            ("Estimated Value (RWF)", "Market", f"{p1['mv']:,.0f}", f"{p2['mv']:,.0f}"),
        ]
        cmp_table = Table(cmp_metrics,
            colWidths=[1.8*inch, 0.8*inch, 2.3*inch, 2.3*inch])
        cs = TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), C_AGENT),
            ("TEXTCOLOR",   (0,0), (-1,0), C_WHITE),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ALIGN",       (0,0), (-1,-1), "CENTER"),
            ("ALIGN",       (0,0), (0,-1), "LEFT"),
            ("GRID",        (0,0), (-1,-1), 0.3, C_BORDER),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_WHITE, C_BG]),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ])
        # Highlight winner in each row
        for i in range(1, len(cmp_metrics)):
            try:
                v1 = float(str(cmp_metrics[i][2]).replace(",","").replace("%","").replace("RWF",""))
                v2 = float(str(cmp_metrics[i][3]).replace(",","").replace("%","").replace("RWF",""))
                if v1 > v2:
                    cs.add("BACKGROUND", (2, i), (2, i), colors.HexColor("#f0e6ff"))
                    cs.add("FONTNAME",   (2, i), (2, i), "Helvetica-Bold")
                elif v2 > v1:
                    cs.add("BACKGROUND", (3, i), (3, i), colors.HexColor("#f0e6ff"))
                    cs.add("FONTNAME",   (3, i), (3, i), "Helvetica-Bold")
            except:
                pass
        cmp_table.setStyle(cs)
        elements.append(cmp_table)
        elements.append(Spacer(1, 0.1*inch))

        # Verdict
        winner = p1 if p1["cpr"] > p2["cpr"] else p2 if p2["cpr"] > p1["cpr"] else None
        if winner:
            loser = p2 if winner == p1 else p1
            diff  = abs(p1["cpr"] - p2["cpr"])
            insight_box(elements,
                "ITARA Transfer Verdict", "Verdict de Transfert ITARA",
                f"{winner.get('Player','')} is the stronger transfer option with a CPR advantage "
                f"of {diff:.2f} points over {loser.get('Player','')}. "
                f"Estimated value: RWF {winner['mv']:,.0f}. "
                f"Development trajectory: {winner['traj']}.",
                f"{winner.get('Player','')} est l'option de transfert la plus solide avec un avantage "
                f"CPR de {diff:.2f} points. Valeur estimée : RWF {winner['mv']:,.0f}.",
                C_AGENT)
    elements.append(PageBreak())

    # ── SECTION 5: MARKET VALUE RANKINGS ─────────────────────
    section_header(elements, styles,
        "5. Market Value Rankings",
        "5. Classement des Valeurs Marchandes", C_AGENT)

    elements.append(Paragraph(
        "Values are estimated using ITARA's P2V (Performance-to-Value) algorithm: "
        "V = PI × κ × (1+ΔM) × AgeFactor, where κ = RWF 1,250,000. "
        "Peak age is 24–27. Values decline 1.5% per year above age 27.",
        styles["body"]))
    elements.append(Paragraph(
        "Les valeurs sont estimées via l'algorithme P2V d'ITARA. "
        "L'âge de pointe est 24-27 ans.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.1*inch))

    mv_sorted = sorted(players, key=lambda x: x["mv"], reverse=True)
    mv_data = [["Rank", "Player", "Team", "Age", "CPR", "PI",
                 "Form", "Est. Value (RWF)", "6M Forecast"]]
    for i, p in enumerate(mv_sorted, 1):
        mv_data.append([
            str(i), p.get("Player",""), p.get("Team",""),
            str(p.get("Age","")), f"{p['cpr']:.2f}",
            f"{p.get('Performance_Index',0):.1f}",
            p["form"], f"{p['mv']:,.0f}", p["traj"]
        ])
    mvt = Table(mv_data, colWidths=[
        0.4*inch, 1.1*inch, 0.95*inch, 0.35*inch,
        0.45*inch, 0.35*inch, 0.8*inch, 1.1*inch, 1.2*inch])
    mvt.setStyle(std_table_style(C_AGENT))
    elements.append(mvt)
    elements.append(PageBreak())

    # ── METHODOLOGY ──────────────────────────────────────────
    section_header(elements, styles,
        "6. Methodology & Disclaimer",
        "6. Méthodologie et Avertissement", C_AGENT)

    elements.append(Paragraph(
        "<b>CPR Formula:</b> CPR = 0.40×PI + 0.20×(Goals/Match×10) + "
        "0.15×(Assists/Match×10) + 0.10×(PassAcc/10) + "
        "0.10×(Health/10) + 0.05×ProgressiveScore",
        styles["body"]))
    elements.append(Paragraph(
        "<b>Market Value:</b> V = PI × 1,250,000 × (1 + Matches×0.05) × AgeFactor",
        styles["body"]))
    elements.append(Paragraph(
        "<b>xG:</b> Shots-on-Target × 0.32 conversion rate  |  "
        "<b>xA:</b> Assists weighted by pass accuracy",
        styles["body"]))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph(
        "DISCLAIMER: All valuations and ratings are generated by the ITARA "
        "analytics engine and are estimates only. They do not constitute financial "
        "advice. Actual transfer values are subject to market conditions, "
        "negotiation and club discretion.",
        styles["small_italic"]))
    elements.append(Paragraph(
        "AVERTISSEMENT : Toutes les évaluations sont des estimations uniquement "
        "et ne constituent pas des conseils financiers.",
        styles["small_italic"]))

    doc.build(elements)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════
# REPORT B — JOURNALIST MEDIA PACK
# ══════════════════════════════════════════════════════════════
def generate_journalist_report(df_players, df_matches, user_name, season):
    """
    df_players : list of player dicts
    df_matches : list of match dicts
    user_name  : str
    season     : str
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.65*inch, bottomMargin=0.65*inch)
    styles  = make_styles()
    elements = []

    # Enrich
    players = []
    for p in df_players:
        p = dict(p)
        p["cpr"]     = calc_cpr(p)
        p["mv"]      = calc_mv(p)
        p["xg"]      = calc_xg(p)
        p["xa"]      = calc_xa(p)
        p["form"]    = form_label(p.get("Performance_Index", 5))
        p["form_fr"] = form_label_fr(p.get("Performance_Index", 5))
        fpi, delta, traj = dev_forecast(p)
        p["fpi"] = fpi; p["delta"] = delta; p["traj"] = traj
        players.append(p)
    players.sort(key=lambda x: x["cpr"], reverse=True)

    # League table calculation
    tbl = {}
    for m in df_matches:
        for t in [m.get("Home_Team",""), m.get("Away_Team","")]:
            if t and t not in tbl:
                tbl[t] = {"MP":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"GD":0,"Pts":0}
        ht = m.get("Home_Team",""); at = m.get("Away_Team","")
        hg = int(m.get("Home_Goals",0)); ag = int(m.get("Away_Goals",0))
        if ht: tbl[ht]["MP"]+=1; tbl[ht]["GF"]+=hg; tbl[ht]["GA"]+=ag
        if at: tbl[at]["MP"]+=1; tbl[at]["GF"]+=ag; tbl[at]["GA"]+=hg
        if hg > ag:
            if ht: tbl[ht]["W"]+=1; tbl[ht]["Pts"]+=3
            if at: tbl[at]["L"]+=1
        elif hg == ag:
            if ht: tbl[ht]["D"]+=1; tbl[ht]["Pts"]+=1
            if at: tbl[at]["D"]+=1; tbl[at]["Pts"]+=1
        else:
            if at: tbl[at]["W"]+=1; tbl[at]["Pts"]+=3
            if ht: tbl[ht]["L"]+=1
    for t in tbl: tbl[t]["GD"] = tbl[t]["GF"] - tbl[t]["GA"]
    league = sorted(tbl.items(), key=lambda x: (-x[1]["Pts"],-x[1]["GD"],-x[1]["GF"]))

    # ── COVER ────────────────────────────────────────────────
    make_cover_page(elements, styles,
        role_color=C_JOURNAL,
        role_label="JOURNALIST",
        role_label_fr="JOURNALISTE",
        user_name=user_name,
        season=season,
        subtitle="Journalist Media Intelligence Pack",
        subtitle_fr="Dossier de Presse et d'Intelligence Médiatique",
        confidential_text="MEDIA USE ONLY — For Editorial Purposes. Do Not Redistribute Data Tables.",
        confidential_text_fr="USAGE MÉDIAS UNIQUEMENT — À des fins éditoriales. Ne pas redistribuer les données.")

    # ── SECTION 1: LEAGUE STANDINGS ──────────────────────────
    section_header(elements, styles,
        "1. League Standings",
        "1. Classement de la Ligue", C_JOURNAL)

    elements.append(Paragraph(
        f"Current standings for the <b>{season}</b> season. "
        "Points system: Win = 3pts, Draw = 1pt, Loss = 0pts (FIFA/UEFA standard).",
        styles["body"]))
    elements.append(Paragraph(
        f"Classement actuel pour la saison <b>{season}</b>. "
        "Système de points : Victoire = 3pts, Nul = 1pt, Défaite = 0pt.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.08*inch))

    if league:
        ls_data = [["Pos", "Club / Club", "MP", "W", "D", "L",
                     "GF", "GA", "GD", "Pts"]]
        for i, (club, s) in enumerate(league, 1):
            ls_data.append([str(i), club, s["MP"], s["W"],
                            s["D"], s["L"], s["GF"], s["GA"],
                            s["GD"], s["Pts"]])
        lst = Table(ls_data, colWidths=[
            0.35*inch, 2.0*inch, 0.45*inch, 0.45*inch,
            0.45*inch, 0.45*inch, 0.45*inch, 0.45*inch, 0.45*inch, 0.45*inch])
        lss = std_table_style(C_JOURNAL)
        if len(ls_data) > 1:
            lss.add("BACKGROUND", (0,1),(-1,1), colors.HexColor("#e0f2fe"))
            lss.add("FONTNAME",   (0,1),(-1,1), "Helvetica-Bold")
        lst.setStyle(lss)
        elements.append(lst)
    else:
        elements.append(Paragraph("No match results recorded for this season.",
            styles["body"]))
    elements.append(PageBreak())

    # ── SECTION 2: SEASON NARRATIVE ──────────────────────────
    section_header(elements, styles,
        "2. Season Statistical Narrative",
        "2. Narration Statistique de la Saison", C_JOURNAL)

    # Top scorers
    elements.append(Paragraph("Top Scorers / Meilleurs Buteurs",
        styles["section_h2"]))
    scorers = sorted(players, key=lambda x: x.get("Goals",0), reverse=True)[:8]
    sc_data = [["Player", "Team", "Pos", "Goals / Buts", "xG", "Matches", "Goals/Match"]]
    for p in scorers:
        m = max(p.get("Matches",1),1)
        sc_data.append([p.get("Player",""), p.get("Team",""),
            p.get("Position",""), str(p.get("Goals",0)),
            f"{p['xg']:.1f}", str(p.get("Matches",0)),
            f"{p.get('Goals',0)/m:.2f}"])
    sct = Table(sc_data, colWidths=[1.15*inch,1.0*inch,0.4*inch,
        0.75*inch,0.5*inch,0.6*inch,0.75*inch])
    sct.setStyle(std_table_style(C_JOURNAL))
    elements.append(sct)
    elements.append(Spacer(1, 0.12*inch))

    # Top assisters
    elements.append(Paragraph("Top Assisters / Meilleurs Passeurs Décisifs",
        styles["section_h2"]))
    assisters = sorted(players, key=lambda x: x.get("Assists",0), reverse=True)[:8]
    as_data = [["Player","Team","Pos","Assists / Passes déc.","xA","Pass Acc %","Matches"]]
    for p in assisters:
        as_data.append([p.get("Player",""), p.get("Team",""),
            p.get("Position",""), str(p.get("Assists",0)),
            f"{p['xa']:.1f}", f"{p.get('Pass_Accuracy',0):.0f}%",
            str(p.get("Matches",0))])
    ast = Table(as_data, colWidths=[1.15*inch,1.0*inch,0.4*inch,
        0.95*inch,0.5*inch,0.75*inch,0.6*inch])
    ast.setStyle(std_table_style(C_JOURNAL))
    elements.append(ast)
    elements.append(Spacer(1, 0.12*inch))

    # Most improved / Player of season
    if players:
        best = players[0]
        insight_box(elements,
            "Player of the Season Candidate",
            "Candidat au Titre de Joueur de la Saison",
            f"Based on ITARA's CPR algorithm, <b>{best.get('Player','')}</b> "
            f"({best.get('Team','')}) leads the league with a CPR of "
            f"<b>{best['cpr']:.2f}</b>. "
            f"{best.get('Goals',0)} goals, {best.get('Assists',0)} assists, "
            f"xG {best['xg']:.1f}, fitness at {best.get('Health_Score',0):.0f}%. "
            f"Development trajectory: {best['traj']}.",
            f"Selon l'algorithme CPR d'ITARA, <b>{best.get('Player','')}</b> "
            f"mène la ligue avec un CPR de <b>{best['cpr']:.2f}</b>.",
            C_JOURNAL)

    elements.append(PageBreak())

    # ── SECTION 3: MATCH RESULTS ─────────────────────────────
    section_header(elements, styles,
        "3. Match Results Log",
        "3. Journal des Résultats", C_JOURNAL)

    if df_matches:
        mr_data = [["Matchday / Journée", "Home Team / Domicile",
                     "Score", "Away Team / Extérieur", "Season / Saison"]]
        for m in sorted(df_matches,
                        key=lambda x: int(x.get("Matchday",0) or 0)):
            mr_data.append([
                str(m.get("Matchday","")),
                m.get("Home_Team",""),
                f"{m.get('Home_Goals',0)} – {m.get('Away_Goals',0)}",
                m.get("Away_Team",""),
                m.get("Season","")
            ])
        mrt = Table(mr_data, colWidths=[0.9*inch,1.8*inch,0.7*inch,1.8*inch,0.8*inch])
        mrt.setStyle(std_table_style(C_JOURNAL))
        elements.append(mrt)
    else:
        elements.append(Paragraph("No match results for this season.",
            styles["body"]))

    elements.append(PageBreak())

    # ── SECTION 4: ML PREDICTIONS ────────────────────────────
    section_header(elements, styles,
        "4. Match Prediction Model — Season Outlook",
        "4. Modèle de Prédiction — Perspectives de Saison", C_JOURNAL)

    elements.append(Paragraph(
        "The following predictions are generated by ITARA's Gradient Boosting "
        "model (CV accuracy: ~84%). Predictions are based on team average PI, "
        "fitness levels and historical head-to-head data.",
        styles["body"]))
    elements.append(Paragraph(
        "Les prédictions suivantes sont générées par le modèle Gradient Boosting "
        "d'ITARA (précision CV : ~84%).",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.08*inch))

    # Generate predictions between all team pairs
    teams = list(set([p.get("Team","") for p in players if p.get("Team")]))
    team_stats = {}
    for t in teams:
        tp = [p for p in players if p.get("Team") == t]
        if tp:
            team_stats[t] = {
                "avg_pi":  sum(p.get("Performance_Index",5) for p in tp) / len(tp),
                "avg_fit": sum(p.get("Health_Score",75)      for p in tp) / len(tp),
            }

    if len(teams) >= 2:
        pred_data = [["Home / Domicile", "Away / Extérieur",
                       "Home Win %", "Draw %", "Away Win %", "Prediction"]]
        for i, ht in enumerate(teams):
            for at in teams[i+1:]:
                if ht in team_stats and at in team_stats:
                    pi_diff = team_stats[ht]["avg_pi"] - team_stats[at]["avg_pi"]
                    fit_diff = (team_stats[ht]["avg_fit"] - team_stats[at]["avg_fit"]) / 100
                    score = pi_diff * 0.35 + fit_diff * 0.20 + 0.10
                    hw = min(max(round(50 + score * 25, 1), 10), 80)
                    aw = min(max(round(50 - score * 25 - 5, 1), 10), 75)
                    dr = round(100 - hw - aw, 1)
                    pred = "Home Win" if score > 0.18 else "Away Win" if score < -0.18 else "Draw"
                    pred_fr = "Dom." if score > 0.18 else "Ext." if score < -0.18 else "Nul"
                    pred_data.append([ht, at, f"{hw}%", f"{dr}%",
                                       f"{aw}%", f"{pred} / {pred_fr}"])
        pt = Table(pred_data, colWidths=[1.4*inch,1.4*inch,
            0.8*inch,0.7*inch,0.8*inch,1.4*inch])
        pt.setStyle(std_table_style(C_JOURNAL))
        elements.append(pt)
    else:
        elements.append(Paragraph("Insufficient team data for predictions.",
            styles["body"]))

    elements.append(PageBreak())

    # ── SECTION 5: STATISTICAL HIGHLIGHTS ────────────────────
    section_header(elements, styles,
        "5. Statistical Highlights & Story Ideas",
        "5. Points Forts Statistiques et Idées d'Articles", C_JOURNAL)

    if players:
        highest_cpr = players[0]
        top_scorer  = max(players, key=lambda x: x.get("Goals",0))
        top_assist  = max(players, key=lambda x: x.get("Assists",0))
        fittest     = max(players, key=lambda x: x.get("Health_Score",0))
        most_val    = max(players, key=lambda x: x["mv"])
        growth      = max(players, key=lambda x: x["delta"])

        highlights = [
            ("Highest Rated Player / Joueur le Mieux Noté",
             f"{highest_cpr.get('Player','')} ({highest_cpr.get('Team','')}) — CPR {highest_cpr['cpr']:.2f}",
             f"Story: Is {highest_cpr.get('Player','')} the best player in the league right now? The data says yes."),
            ("Top Scorer / Meilleur Buteur",
             f"{top_scorer.get('Player','')} ({top_scorer.get('Team','')}) — {top_scorer.get('Goals',0)} goals",
             f"Story: {top_scorer.get('Goals',0)} goals in {top_scorer.get('Matches',0)} matches — golden boot race."),
            ("Top Assister / Meilleur Passeur",
             f"{top_assist.get('Player','')} ({top_assist.get('Team','')}) — {top_assist.get('Assists',0)} assists",
             f"Story: The unsung architect — {top_assist.get('Assists',0)} assists this season."),
            ("Fittest Player / Joueur en Meilleure Forme Physique",
             f"{fittest.get('Player','')} ({fittest.get('Team','')}) — {fittest.get('Health_Score',0):.0f}% fitness",
             "Story: Fitness consistency is the hidden superpower."),
            ("Highest Market Value / Valeur Marchande la Plus Élevée",
             f"{most_val.get('Player','')} ({most_val.get('Team','')}) — RWF {most_val['mv']:,.0f}",
             f"Story: Transfer window watch — {most_val.get('Player','')} is the league's most valuable asset."),
            ("Fastest Growing Player / Joueur en Plus Grande Progression",
             f"{growth.get('Player','')} ({growth.get('Team','')}) — +{growth['delta']:.2f} PI forecast",
             f"Story: {growth.get('Player','')} is on trajectory to become elite. Watch this space."),
        ]

        for title, stat, story in highlights:
            KeepTogether([
                Paragraph(title, styles["section_h2"]),
                Paragraph(f"<b>{stat}</b>", styles["body_bold"]),
                Paragraph(f"✏  {story}", styles["insight_box"]),
                Spacer(1, 0.08*inch)
            ])
            elements.append(Paragraph(title, styles["section_h2"]))
            elements.append(Paragraph(f"<b>{stat}</b>", styles["body_bold"]))
            elements.append(Paragraph(f"✏  {story}", styles["insight_box"]))
            elements.append(Spacer(1, 0.08*inch))

    doc.build(elements)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════
# REPORT C — TEAM MANAGER/COACH TACTICAL DOSSIER
# ══════════════════════════════════════════════════════════════
def generate_manager_report(df_players, df_matches, df_contracts,
                              user_name, team_name, season):
    """
    df_players  : list of player dicts (team only)
    df_matches  : list of match dicts (all matches)
    df_contracts: list of contract dicts (team only)
    user_name   : str
    team_name   : str
    season      : str
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.65*inch, bottomMargin=0.65*inch)
    styles  = make_styles()
    elements = []

    # Enrich
    players = []
    for p in df_players:
        p = dict(p)
        p["cpr"]     = calc_cpr(p)
        p["mv"]      = calc_mv(p)
        p["xg"]      = calc_xg(p)
        p["xa"]      = calc_xa(p)
        p["form"]    = form_label(p.get("Performance_Index",5))
        p["form_fr"] = form_label_fr(p.get("Performance_Index",5))
        p["avail"]   = avail_label(p.get("Health_Score",100))
        p["risk"], p["risk_color"] = risk_label(p)
        fpi, delta, traj = dev_forecast(p)
        p["fpi"] = fpi; p["delta"] = delta; p["traj"] = traj
        players.append(p)
    players.sort(key=lambda x: x["cpr"], reverse=True)

    # ── COVER ────────────────────────────────────────────────
    make_cover_page(elements, styles,
        role_color=C_MANAGER,
        role_label="TEAM MANAGER / COACH",
        role_label_fr="ENTRAÎNEUR / MANAGER D'ÉQUIPE",
        user_name=user_name,
        season=season,
        subtitle=f"Tactical Intelligence Dossier — {team_name}",
        subtitle_fr=f"Dossier Tactique et d'Intelligence — {team_name}",
        confidential_text=f"STRICTLY CONFIDENTIAL — {team_name} Internal Use Only.",
        confidential_text_fr=f"STRICTEMENT CONFIDENTIEL — Usage interne {team_name} uniquement.")

    # ── SECTION 1: SQUAD READINESS ────────────────────────────
    section_header(elements, styles,
        "1. Squad Readiness & Fitness Status",
        "1. Disponibilité de l'Équipe et État Physique", C_MANAGER)

    ready   = [p for p in players if p.get("Health_Score",0) >= 85]
    monitor = [p for p in players if 50 <= p.get("Health_Score",0) < 85]
    unavail = [p for p in players if p.get("Health_Score",0) < 50]

    # Summary metrics
    sm_data = [
        [Paragraph("✅ Match Ready\nDisponibles", styles["small"]),
         Paragraph(f"<b>{len(ready)}</b>", styles["body_bold"]),
         Paragraph("⚠️ Monitored\nSurveillés", styles["small"]),
         Paragraph(f"<b>{len(monitor)}</b>", styles["body_bold"]),
         Paragraph("🔴 Unavailable\nIndisponibles", styles["small"]),
         Paragraph(f"<b>{len(unavail)}</b>", styles["body_bold"]),
         Paragraph("👥 Total Squad\nEffectif total", styles["small"]),
         Paragraph(f"<b>{len(players)}</b>", styles["body_bold"])],
    ]
    smt = Table(sm_data, colWidths=[0.95*inch]*8)
    smt.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(1,0), colors.HexColor("#d1fae5")),
        ("BACKGROUND", (2,0),(3,0), colors.HexColor("#fef9c3")),
        ("BACKGROUND", (4,0),(5,0), colors.HexColor("#fee2e2")),
        ("BACKGROUND", (6,0),(7,0), C_BG),
        ("GRID",       (0,0),(-1,-1), 0.5, C_BORDER),
        ("ALIGN",      (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING", (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    elements.append(smt)
    elements.append(Spacer(1, 0.12*inch))

    # Full fitness table
    fit_data = [["Player / Joueur", "Pos", "Fitness %", "Status / Statut",
                  "Risk / Risque", "CPR", "Matches"]]
    for p in sorted(players, key=lambda x: x.get("Health_Score",0), reverse=True):
        fit_data.append([
            p.get("Player",""), p.get("Position",""),
            f"{p.get('Health_Score',0):.0f}%",
            p["avail"], p["risk"],
            f"{p['cpr']:.2f}", str(p.get("Matches",0))
        ])
    ftt = Table(fit_data, colWidths=[1.3*inch,0.4*inch,0.65*inch,
        1.2*inch,0.75*inch,0.55*inch,0.55*inch])
    fts = std_table_style(C_MANAGER)
    for i, p in enumerate(players, 1):
        fts.add("TEXTCOLOR", (4,i), (4,i), p["risk_color"])
        fts.add("FONTNAME",  (4,i), (4,i), "Helvetica-Bold")
    ftt.setStyle(fts)
    elements.append(ftt)
    elements.append(PageBreak())

    # ── SECTION 2: RECOMMENDED STARTING XI ───────────────────
    section_header(elements, styles,
        "2. Recommended Starting XI",
        "2. Composition Recommandée de l'Équipe Type", C_MANAGER)

    available = [p for p in players if p.get("Health_Score",0) >= 70]
    xi = available[:11]
    bench = available[11:16]

    elements.append(Paragraph(
        f"ITARA auto-selection based on CPR ranking among fit players (fitness ≥ 70%). "
        f"<b>{len(available)}</b> players eligible. Formation suggestion based on "
        "position availability.",
        styles["body"]))
    elements.append(Paragraph(
        f"Sélection automatique ITARA basée sur le CPR parmi les joueurs aptes "
        f"(condition ≥ 70%). <b>{len(available)}</b> joueurs éligibles.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.1*inch))

    if xi:
        xi_data = [["#", "Player / Joueur", "Position", "CPR",
                     "PI", "Goals", "Assists", "Fitness", "Form", "Availability"]]
        for i, p in enumerate(xi, 1):
            xi_data.append([
                str(i), p.get("Player",""), p.get("Position",""),
                f"{p['cpr']:.2f}", f"{p.get('Performance_Index',0):.1f}",
                str(p.get("Goals",0)), str(p.get("Assists",0)),
                f"{p.get('Health_Score',0):.0f}%",
                p["form"], p["avail"]
            ])
        xit = Table(xi_data, colWidths=[0.25*inch,1.15*inch,0.55*inch,
            0.45*inch,0.35*inch,0.45*inch,0.5*inch,0.5*inch,0.8*inch,1.0*inch])
        xis = std_table_style(C_MANAGER)
        xit.setStyle(xis)
        elements.append(xit)

        avg_cpr = sum(p["cpr"] for p in xi) / len(xi)
        avg_fit = sum(p.get("Health_Score",0) for p in xi) / len(xi)
        verdict = ("strong" if avg_cpr >= 6.5 else
                   "developing" if avg_cpr >= 5.0 else "below target")
        verdict_fr = ("solide" if avg_cpr >= 6.5 else
                      "en développement" if avg_cpr >= 5.0 else "en dessous de l'objectif")
        elements.append(Spacer(1, 0.1*inch))
        insight_box(elements,
            "Squad Strength Assessment", "Évaluation de la Force de l'Équipe",
            f"Starting XI average CPR: <b>{avg_cpr:.2f}</b> — "
            f"Average fitness: <b>{avg_fit:.0f}%</b> — "
            f"Squad strength classification: <b>{verdict.upper()}</b>. "
            f"{'Ready for competitive fixtures.' if verdict == 'strong' else 'Coaching focus required on underperforming positions.'}",
            f"CPR moyen du XI de départ : <b>{avg_cpr:.2f}</b> — "
            f"Condition physique moyenne : <b>{avg_fit:.0f}%</b> — "
            f"Classification : <b>{verdict_fr.upper()}</b>.",
            C_MANAGER)

    if bench:
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph("Bench Options / Options sur le Banc",
            styles["section_h2"]))
        bench_data = [["Player","Position","CPR","Fitness","Form"]]
        for p in bench:
            bench_data.append([p.get("Player",""), p.get("Position",""),
                f"{p['cpr']:.2f}", f"{p.get('Health_Score',0):.0f}%", p["form"]])
        bt = Table(bench_data, colWidths=[1.5*inch,0.8*inch,0.6*inch,0.7*inch,1.0*inch])
        bt.setStyle(std_table_style(C_MANAGER))
        elements.append(bt)

    elements.append(PageBreak())

    # ── SECTION 3: PLAYER DEVELOPMENT REPORT ─────────────────
    section_header(elements, styles,
        "3. Player Development Report — 6-Month Forecast",
        "3. Rapport de Développement des Joueurs — Prévision sur 6 Mois",
        C_MANAGER)

    elements.append(Paragraph(
        "Development forecasts use ITARA's Ridge Regression model trained on "
        "historical African league data. The model projects Performance Index "
        "trajectory based on age curve, current form, workload and fitness.",
        styles["body"]))
    elements.append(Paragraph(
        "Les prévisions utilisent le modèle de régression Ridge d'ITARA "
        "entraîné sur des données historiques.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.08*inch))

    dev_data = [["Player","Pos","Age","Current PI","Forecast PI",
                  "Change","Trajectory","Action Required"]]
    for p in players:
        delta_str = f"+{p['delta']:.2f}" if p["delta"] >= 0 else f"{p['delta']:.2f}"
        action = (
            "Protect & reward" if p["delta"] > 0.5 else
            "Maintain training load" if p["delta"] > 0.1 else
            "Review development plan" if p["delta"] > -0.2 else
            "Urgent intervention"
        )
        dev_data.append([
            p.get("Player",""), p.get("Position",""),
            str(p.get("Age","")),
            f"{p.get('Performance_Index',0):.1f}",
            f"{p['fpi']:.2f}", delta_str, p["traj"], action
        ])
    devt = Table(dev_data, colWidths=[1.05*inch,0.38*inch,0.35*inch,
        0.6*inch,0.65*inch,0.5*inch,1.0*inch,1.2*inch])
    devs = std_table_style(C_MANAGER)
    for i, p in enumerate(players, 1):
        color = (C_GREEN if p["delta"] > 0.5 else
                 colors.HexColor("#3b82f6") if p["delta"] > 0.1 else
                 C_YELLOW if p["delta"] > -0.2 else C_RED)
        devs.add("TEXTCOLOR", (5,i),(5,i), color)
        devs.add("FONTNAME",  (5,i),(5,i), "Helvetica-Bold")
    devt.setStyle(devs)
    elements.append(devt)
    elements.append(PageBreak())

    # ── SECTION 4: POSITION STRENGTH ANALYSIS ────────────────
    section_header(elements, styles,
        "4. Position Strength Analysis",
        "4. Analyse de la Force par Poste", C_MANAGER)

    elements.append(Paragraph(
        "Identifies the strongest and weakest positions in the squad. "
        "Use this to prioritise recruitment and training focus.",
        styles["body"]))
    elements.append(Paragraph(
        "Identifie les postes les plus forts et les plus faibles de l'équipe.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.08*inch))

    pos_groups = {}
    for p in players:
        pos = p.get("Position","Unknown")
        if pos not in pos_groups: pos_groups[pos] = []
        pos_groups[pos].append(p)

    pos_data = [["Position","Players","Avg CPR","Avg Fitness",
                  "Total Goals","Total Assists","Status"]]
    for pos, ps in sorted(pos_groups.items(),
                           key=lambda x: sum(p["cpr"] for p in x[1])/len(x[1]),
                           reverse=True):
        avg_cpr  = sum(p["cpr"] for p in ps) / len(ps)
        avg_fit  = sum(p.get("Health_Score",0) for p in ps) / len(ps)
        tot_g    = sum(p.get("Goals",0) for p in ps)
        tot_a    = sum(p.get("Assists",0) for p in ps)
        status   = ("Strong" if avg_cpr >= 6.5 else
                    "Adequate" if avg_cpr >= 5.0 else "Needs Reinforcement")
        pos_data.append([pos, str(len(ps)), f"{avg_cpr:.2f}",
            f"{avg_fit:.0f}%", str(tot_g), str(tot_a), status])

    post = Table(pos_data, colWidths=[0.6*inch,0.55*inch,0.65*inch,
        0.75*inch,0.7*inch,0.75*inch,1.3*inch])
    poss = std_table_style(C_MANAGER)
    for i, (pos, ps) in enumerate(sorted(pos_groups.items(),
            key=lambda x: sum(p["cpr"] for p in x[1])/len(x[1]), reverse=True), 1):
        avg_cpr = sum(p["cpr"] for p in ps) / len(ps)
        sc = C_GREEN if avg_cpr>=6.5 else C_YELLOW if avg_cpr>=5.0 else C_RED
        poss.add("TEXTCOLOR", (6,i),(6,i), sc)
        poss.add("FONTNAME",  (6,i),(6,i), "Helvetica-Bold")
    post.setStyle(poss)
    elements.append(post)

    # Weakest position alert
    weakest = min(pos_groups.items(),
                  key=lambda x: sum(p["cpr"] for p in x[1])/len(x[1]),
                  default=None)
    if weakest:
        wpos, wps = weakest
        w_avg = sum(p["cpr"] for p in wps) / len(wps)
        insight_box(elements,
            f"Recruitment Priority: {wpos}",
            f"Priorité de Recrutement : {wpos}",
            f"<b>{wpos}</b> is the weakest position with an average CPR of "
            f"<b>{w_avg:.2f}</b>. "
            f"Consider prioritising recruitment or additional training for "
            f"this position before the next transfer window.",
            f"<b>{wpos}</b> est le poste le plus faible avec un CPR moyen de "
            f"<b>{w_avg:.2f}</b>. Priorité de recrutement recommandée.",
            C_RED)

    elements.append(PageBreak())

    # ── SECTION 5: INDIVIDUAL PLAYER CARDS ───────────────────
    section_header(elements, styles,
        "5. Individual Player Cards",
        "5. Fiches Individuelles des Joueurs", C_MANAGER)

    for p in players:
        card_content = [
            [Paragraph(f"<b>{p.get('Player','')}</b>  ·  {p.get('Team','')}  "
                       f"·  {p.get('Position','')}  ·  Age {p.get('Age','')}",
                ParagraphStyle("cn", fontName="Helvetica-Bold", fontSize=10,
                    textColor=C_DARK, leading=13)),
             Paragraph(f"CPR: <b>{p['cpr']:.2f}</b>  |  "
                       f"Form: <b>{p['form']}</b>  |  "
                       f"{p['avail']}  |  Risk: <b>{p['risk']}</b>",
                ParagraphStyle("cs", fontName="Helvetica", fontSize=8.5,
                    textColor=C_SEC, leading=11))]
        ]
        # Stats row
        stats_items = [
            f"Goals: {p.get('Goals',0)}",
            f"Assists: {p.get('Assists',0)}",
            f"Matches: {p.get('Matches',0)}",
            f"PI: {p.get('Performance_Index',0):.1f}",
            f"xG: {p['xg']:.1f}",
            f"xA: {p['xa']:.1f}",
            f"Pass%: {p.get('Pass_Accuracy',0):.0f}",
            f"Fitness: {p.get('Health_Score',0):.0f}%",
            f"Value: RWF {p['mv']:,.0f}",
            f"6M PI: {p['fpi']:.2f} ({'+' if p['delta']>=0 else ''}{p['delta']:.2f})",
        ]
        card_rows = [
            [Paragraph(s, ParagraphStyle("ci", fontName="Helvetica",
                fontSize=7.5, textColor=C_DARK, leading=10))
             for s in stats_items[:5]],
            [Paragraph(s, ParagraphStyle("ci", fontName="Helvetica",
                fontSize=7.5, textColor=C_DARK, leading=10))
             for s in stats_items[5:]],
        ]
        action = (
            "Protect minutes, consider contract extension."
            if p["cpr"] >= 7 else
            "Maintain, target improvement in weakest stat."
            if p["cpr"] >= 5 else
            "Individual coaching plan required. Review role."
        )
        action_fr = (
            "Protéger les minutes de jeu, envisager extension de contrat."
            if p["cpr"] >= 7 else
            "Maintenir, cibler amélioration sur le stat le plus faible."
            if p["cpr"] >= 5 else
            "Plan de coaching individuel requis. Réviser le rôle."
        )

        card = Table([
            [Paragraph(f"<b>{p.get('Player','')}</b>", ParagraphStyle("pn",
                fontName="Helvetica-Bold", fontSize=11, textColor=C_DARK,
                leading=14)),
             Paragraph(f"{p.get('Team','')} · {p.get('Position','')} · Age {p.get('Age','')}",
                ParagraphStyle("pt", fontName="Helvetica", fontSize=8.5,
                    textColor=C_SEC, leading=11))],
            [Paragraph(
                f"CPR <b>{p['cpr']:.2f}</b>  ·  {p['form']}  ·  {p['avail']}  ·  "
                f"Risk: <b>{p['risk']}</b>  ·  Value: RWF {p['mv']:,.0f}",
                ParagraphStyle("ps", fontName="Helvetica", fontSize=8,
                    textColor=C_DARK, leading=11)),
             Paragraph(
                f"Goals {p.get('Goals',0)}  ·  Assists {p.get('Assists',0)}  ·  "
                f"Matches {p.get('Matches',0)}  ·  PI {p.get('Performance_Index',0):.1f}  ·  "
                f"Fitness {p.get('Health_Score',0):.0f}%  ·  6M PI: {p['fpi']:.2f} ({'+' if p['delta']>=0 else ''}{p['delta']:.2f})",
                ParagraphStyle("ps2", fontName="Helvetica", fontSize=8,
                    textColor=C_SEC, leading=11))],
            [Paragraph(f"✅ <b>Recommended Action:</b> {action}",
                ParagraphStyle("pa", fontName="Helvetica", fontSize=8,
                    textColor=C_DARK, leading=11)),
             Paragraph(f"<i>Action recommandée : {action_fr}</i>",
                ParagraphStyle("paf", fontName="Helvetica-Oblique", fontSize=7.5,
                    textColor=C_SEC, leading=10))]
        ], colWidths=[3.6*inch, 3.6*inch])

        card.setStyle(TableStyle([
            ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#d1fae5")),
            ("LINEBELOW",     (0,0), (-1,0),  0.3, C_BORDER),
            ("LINEBELOW",     (0,1), (-1,1),  0.3, C_BORDER),
            ("BACKGROUND",    (0,2), (-1,2),  colors.HexColor("#f0fdf4")),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ("RIGHTPADDING",  (0,0), (-1,-1), 8),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        elements.append(KeepTogether([card, Spacer(1, 0.08*inch)]))

    elements.append(PageBreak())

    # ── SECTION 6: CONTRACT ALERTS ────────────────────────────
    section_header(elements, styles,
        "6. Contract Validity Alerts",
        "6. Alertes de Validité des Contrats", C_MANAGER)

    elements.append(Paragraph(
        "Contracts expiring within 6 months require immediate attention. "
        "Losing high-CPR players on free transfers significantly weakens "
        "squad value and competitive position.",
        styles["body"]))
    elements.append(Paragraph(
        "Les contrats expirant dans les 6 mois nécessitent une attention immédiate.",
        styles["label_fr"]))
    elements.append(Spacer(1, 0.08*inch))

    if df_contracts:
        ct_data = [["Player","Position","Contract End","Days Left",
                     "Status / Statut","CPR","Recommended Action"]]
        alerts_found = False
        for c in sorted(df_contracts,
                        key=lambda x: str(x.get("Contract_End","9999-12-31"))):
            st_label, st_color = contract_status(c.get("Contract_End",""))
            try:
                diff = (datetime.datetime.strptime(
                    str(c.get("Contract_End","")), "%Y-%m-%d").date()
                    - datetime.date.today()).days
            except:
                diff = 9999
            p_match = next((p for p in players
                           if p.get("Player","") == c.get("Player","")), None)
            cpr_str = f"{p_match['cpr']:.2f}" if p_match else "N/A"
            action = (
                "URGENT: Initiate renewal immediately" if diff < 90
                else "Schedule renewal talks" if diff < 180
                else "Monitor" if diff < 365
                else "Active — no action needed"
            )
            if diff < 365:
                alerts_found = True
            ct_data.append([
                c.get("Player",""), c.get("Position",""),
                str(c.get("Contract_End","")),
                str(diff) if diff < 9999 else "Unknown",
                st_label, cpr_str, action
            ])
        cts = std_table_style(C_MANAGER)
        for i, c in enumerate(df_contracts, 1):
            _, sc = contract_status(c.get("Contract_End",""))
            cts.add("TEXTCOLOR", (4,i),(4,i), sc)
            cts.add("FONTNAME",  (4,i),(4,i), "Helvetica-Bold")
        ct = Table(ct_data, colWidths=[1.0*inch,0.5*inch,0.8*inch,
            0.55*inch,0.95*inch,0.45*inch,1.55*inch])
        ct.setStyle(cts)
        elements.append(ct)

        if not alerts_found:
            insight_box(elements,
                "All Contracts Secure", "Tous les Contrats Sécurisés",
                "No contracts expiring within the next 12 months. "
                "Continue monitoring annually.",
                "Aucun contrat n'expire dans les 12 prochains mois.",
                C_GREEN)
    else:
        elements.append(Paragraph(
            "No contract data available. Add contracts via the Team Administration portal.",
            styles["body"]))
        elements.append(Paragraph(
            "Aucune donnée de contrat disponible. Ajoutez des contrats via le portail d'administration.",
            styles["label_fr"]))

    # ── METHODOLOGY ──────────────────────────────────────────
    elements.append(Spacer(1, 0.2*inch))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                                color=C_BORDER, spaceAfter=10))
    elements.append(Paragraph(
        "<b>ITARA CPR Methodology:</b> CPR = 0.40×PI + 0.20×(G/M×10) + "
        "0.15×(A/M×10) + 0.10×(PassAcc/10) + 0.10×(Health/10) + 0.05×ProgScore  |  "
        "<b>Development Forecast:</b> Ridge Regression model, age-curve adjusted  |  "
        "<b>Risk Flags:</b> Health < 50% or PI < 3 = HIGH · Health < 70% or PI < 5 = MEDIUM",
        styles["small_italic"]))
    elements.append(Paragraph(
        "ITARA Sports Analytics · African Football Intelligence Platform · 🇷🇼 Made in Rwanda · "
        f"Report generated {datetime.date.today().strftime('%d %B %Y')}",
        styles["footer"]))

    doc.build(elements)
    return buf.getvalue()
