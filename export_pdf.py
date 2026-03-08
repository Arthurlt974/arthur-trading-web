"""
export_pdf.py — AM-Trading | Export PDF
Génère un rapport PDF complet :
  - Fiche analyse (prix, valorisation, ratios)
  - Screenshot-like chart (Plotly → image)
  - Rapport de portefeuille
  - Résumé des alertes actives
Utilisation : depuis Analyseur Pro et Portfolio
"""

import io
import base64
from datetime import datetime

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ══════════════════════════════════════════
#  PALETTE AM-TRADING
# ══════════════════════════════════════════
C_BG       = colors.HexColor("#0d0d0d")
C_ORANGE   = colors.HexColor("#ff9800")
C_ORANGE2  = colors.HexColor("#ffb84d")
C_GREEN    = colors.HexColor("#00ff88")
C_RED      = colors.HexColor("#ff4444")
C_WHITE    = colors.HexColor("#ffffff")
C_GREY     = colors.HexColor("#aaaaaa")
C_DARK     = colors.HexColor("#1a1a1a")
C_BORDER   = colors.HexColor("#333333")

# ══════════════════════════════════════════
#  STYLES
# ══════════════════════════════════════════
def _styles():
    return {
        "title": ParagraphStyle("title",
            fontName="Helvetica-Bold", fontSize=26, textColor=C_ORANGE,
            alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle",
            fontName="Helvetica", fontSize=11, textColor=C_GREY,
            alignment=TA_CENTER, spaceAfter=8),
        "section": ParagraphStyle("section",
            fontName="Helvetica-Bold", fontSize=13, textColor=C_ORANGE,
            spaceBefore=14, spaceAfter=6),
        "label": ParagraphStyle("label",
            fontName="Helvetica-Bold", fontSize=9, textColor=C_GREY),
        "value": ParagraphStyle("value",
            fontName="Helvetica-Bold", fontSize=14, textColor=C_WHITE),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9, textColor=C_GREY,
            spaceAfter=4),
        "footer": ParagraphStyle("footer",
            fontName="Helvetica", fontSize=8, textColor=C_BORDER,
            alignment=TA_CENTER),
    }

# ══════════════════════════════════════════
#  CHART PLOTLY → IMAGE PNG en mémoire
# ══════════════════════════════════════════
def _chart_image(ticker: str, width_mm=170, height_mm=70) -> RLImage | None:
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        fig = go.Figure(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"],  close=df["Close"],
            increasing_line_color="#00ff88", decreasing_line_color="#ff4444",
            increasing_fillcolor="#00ff88", decreasing_fillcolor="#ff4444",
            name=ticker,
        ))
        # MA 20 & 50
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"].rolling(20).mean(),
            line=dict(color="#ff9800", width=1.2), name="MA20"))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"].rolling(50).mean(),
            line=dict(color="#2196F3", width=1.2), name="MA50"))

        fig.update_layout(
            paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
            font=dict(color="#aaa", family="monospace"),
            xaxis=dict(gridcolor="#1a1a1a", showgrid=True, rangeslider_visible=False),
            yaxis=dict(gridcolor="#1a1a1a", showgrid=True),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            margin=dict(l=40, r=20, t=20, b=30),
            height=300,
        )

        img_bytes = fig.to_image(format="png", width=900, height=300, scale=2)
        buf = io.BytesIO(img_bytes)
        return RLImage(buf, width=width_mm*mm, height=height_mm*mm)
    except Exception:
        return None

# ══════════════════════════════════════════
#  SECTION — EN-TÊTE
# ══════════════════════════════════════════
def _header(story, S, subtitle="RAPPORT D'ANALYSE"):
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("AM-TRADING", S["title"]))
    story.append(Paragraph(subtitle, S["subtitle"]))
    story.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}  •  Bloomberg Terminal",
        S["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ORANGE, spaceAfter=10))

# ══════════════════════════════════════════
#  SECTION — ANALYSE ACTION
# ══════════════════════════════════════════
def _section_analyse(story, S, ticker: str, info: dict, valuation: dict):
    story.append(Paragraph("» FICHE ANALYSE", S["section"]))

    nom    = info.get("longName") or info.get("shortName") or ticker
    prix   = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    devise = info.get("currency", "USD")
    prev   = info.get("previousClose") or prix
    chg    = ((prix - prev) / prev * 100) if prev else 0
    chg_c  = C_GREEN if chg >= 0 else C_RED

    # Ligne prix
    kpi_data = [
        ["TICKER", "NOM", "PRIX", "VAR. 24H", "DEVISE"],
        [ticker,
         Paragraph(nom[:35], ParagraphStyle("n", fontName="Helvetica", fontSize=8, textColor=C_WHITE)),
         f"{prix:,.2f}",
         f"{chg:+.2f}%",
         devise],
    ]
    kpi_tbl = Table(kpi_data, colWidths=[25*mm, 55*mm, 30*mm, 30*mm, 25*mm])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",    (0,0), (-1,0), C_ORANGE),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0), 8),
        ("BACKGROUND",   (0,1), (-1,1), C_BG),
        ("TEXTCOLOR",    (0,1), (-1,1), C_WHITE),
        ("FONTNAME",     (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,1), (-1,1), 11),
        ("TEXTCOLOR",    (3,1), (3,1),  chg_c),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_DARK, C_BG]),
        ("GRID",         (0,0), (-1,-1), 0.5, C_BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 4*mm))

    # Ratios fondamentaux
    ratios = [
        ("Market Cap",    f"{info.get('marketCap',0)/1e9:.1f} Md" if info.get('marketCap') else "N/A"),
        ("P/E Trailing",  f"{info.get('trailingPE',0):.1f}x" if info.get('trailingPE') else "N/A"),
        ("P/E Forward",   f"{info.get('forwardPE',0):.1f}x" if info.get('forwardPE') else "N/A"),
        ("EPS (TTM)",     f"{info.get('trailingEps',0):.2f}" if info.get('trailingEps') else "N/A"),
        ("Div. Yield",    f"{info.get('dividendYield',0)*100:.2f}%" if info.get('dividendYield') else "N/A"),
        ("Beta",          f"{info.get('beta',0):.2f}" if info.get('beta') else "N/A"),
        ("52W High",      f"{info.get('fiftyTwoWeekHigh',0):.2f}" if info.get('fiftyTwoWeekHigh') else "N/A"),
        ("52W Low",       f"{info.get('fiftyTwoWeekLow',0):.2f}" if info.get('fiftyTwoWeekLow') else "N/A"),
        ("Secteur",       info.get("sector", "N/A")),
        ("Industrie",     (info.get("industry","N/A") or "N/A")[:30]),
    ]
    r_rows = [["INDICATEUR", "VALEUR", "INDICATEUR", "VALEUR"]]
    for i in range(0, len(ratios), 2):
        r1 = ratios[i]
        r2 = ratios[i+1] if i+1 < len(ratios) else ("", "")
        r_rows.append([r1[0], r1[1], r2[0], r2[1]])

    r_tbl = Table(r_rows, colWidths=[40*mm, 40*mm, 40*mm, 40*mm])
    r_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), C_ORANGE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_GREY),
        ("TEXTCOLOR",     (1,1), (1,-1), C_WHITE),
        ("TEXTCOLOR",     (3,1), (3,-1), C_WHITE),
        ("FONTNAME",      (1,1), (1,-1), "Helvetica-Bold"),
        ("FONTNAME",      (3,1), (3,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_DARK]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(r_tbl)
    story.append(Spacer(1, 4*mm))

    # Valorisation
    consensus = valuation.get("consensus", {})
    if consensus:
        story.append(Paragraph("» VALORISATION & CONSENSUS", S["section"]))
        rec   = consensus.get("recommendation", "N/A")
        cv    = consensus.get("fair_value", 0)
        up    = consensus.get("upside_pct", 0)
        up_c  = C_GREEN if up >= 0 else C_RED
        rec_c = C_GREEN if "ACHAT" in str(rec) else (C_RED if "VENTE" in str(rec) else C_ORANGE2)
        nmeth = consensus.get("methods_used", 0)

        cons_data = [
            ["RECOMMANDATION", "VALEUR CONSENSUS", "POTENTIEL", "MÉTHODES"],
            [Paragraph(f'<font color="#{rec_c.hexval()[1:]}"><b>{rec}</b></font>', ParagraphStyle("x", fontSize=11, alignment=TA_CENTER)),
             f"{cv:,.2f} {devise}",
             Paragraph(f'<font color="#{up_c.hexval()[1:]}"><b>{up:+.1f}%</b></font>', ParagraphStyle("x", fontSize=11, alignment=TA_CENTER)),
             str(nmeth)],
        ]
        cons_tbl = Table(cons_data, colWidths=[45*mm, 45*mm, 45*mm, 30*mm])
        cons_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), C_DARK),
            ("TEXTCOLOR",     (0,0), (-1,0), C_ORANGE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("BACKGROUND",    (0,1), (-1,1), C_BG),
            ("TEXTCOLOR",     (0,1), (-1,1), C_WHITE),
            ("FONTNAME",      (0,1), (-1,1), "Helvetica-Bold"),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("GRID",          (0,0), (-1,-1), 0.5, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))
        story.append(cons_tbl)

        # Détail méthodes
        methods = [(k,v) for k,v in valuation.items() if k != "consensus" and isinstance(v, dict) and "fair_value" in v]
        if methods:
            story.append(Spacer(1, 3*mm))
            m_rows = [["MÉTHODE", "VALEUR JUSTE", "POTENTIEL", "NOTE"]]
            for name, data in methods:
                fv  = data.get("fair_value", 0)
                upc = data.get("upside_pct", 0)
                note = ""
                if data.get("excluded_from_consensus"):
                    note = data.get("exclusion_reason","")[:40]
                m_rows.append([
                    name.upper(),
                    f"{fv:,.2f} {devise}",
                    f"{upc:+.1f}%",
                    Paragraph(note, ParagraphStyle("n2", fontSize=7, textColor=C_GREY)),
                ])
            m_tbl = Table(m_rows, colWidths=[25*mm, 35*mm, 25*mm, 80*mm])
            m_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0), C_DARK),
                ("TEXTCOLOR",     (0,0), (-1,0), C_ORANGE),
                ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,-1), 8),
                ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_DARK]),
                ("TEXTCOLOR",     (0,1), (-1,-1), C_WHITE),
                ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
                ("ALIGN",         (0,0), (2,-1),  "CENTER"),
                ("LEFTPADDING",   (0,0), (-1,-1), 5),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(m_tbl)

# ══════════════════════════════════════════
#  SECTION — PORTEFEUILLE
# ══════════════════════════════════════════
def _section_portfolio(story, S, positions: list):
    if not positions:
        return
    story.append(Paragraph("» PORTEFEUILLE", S["section"]))

    total_value = sum(p.get("market_value", 0) for p in positions)
    total_cost  = sum(p.get("cost_basis", 0)   for p in positions)
    total_pnl   = total_value - total_cost
    total_pnl_p = (total_pnl / total_cost * 100) if total_cost else 0
    pnl_c = C_GREEN if total_pnl >= 0 else C_RED

    # KPIs portefeuille
    kpi_d = [
        ["VALEUR TOTALE", "COÛT TOTAL", "P&L TOTAL", "P&L %"],
        [f"{total_value:,.2f} $", f"{total_cost:,.2f} $",
         f"{total_pnl:+,.2f} $", f"{total_pnl_p:+.2f}%"],
    ]
    kpi_t = Table(kpi_d, colWidths=[42*mm]*4)
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), C_ORANGE),
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("BACKGROUND",    (0,1), (-1,1), C_BG),
        ("TEXTCOLOR",     (0,1), (1,1),  C_WHITE),
        ("TEXTCOLOR",     (2,1), (3,1),  pnl_c),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("GRID",          (0,0), (-1,-1), 0.5, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 3*mm))

    # Tableau positions
    p_rows = [["SYMBOLE", "TYPE", "QTÉ", "PRX ACHAT", "PRX ACTUEL", "VALEUR", "P&L", "P&L %"]]
    for p in sorted(positions, key=lambda x: x.get("market_value", 0), reverse=True):
        pnl_abs = p.get("pnl_abs", 0)
        pnl_pct = p.get("pnl_pct", 0)
        p_c = C_GREEN if pnl_abs >= 0 else C_RED
        p_rows.append([
            p.get("symbol",""),
            p.get("asset_type","")[:8],
            f"{p.get('quantity',0):.4f}".rstrip("0").rstrip("."),
            f"{p.get('buy_price',0):.2f}",
            f"{p.get('current_price',0):.2f}",
            f"{p.get('market_value',0):,.2f}",
            Paragraph(f'<font color="#{p_c.hexval()[1:]}">{pnl_abs:+,.2f}</font>',
                      ParagraphStyle("pnl", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f'<font color="#{p_c.hexval()[1:]}">{pnl_pct:+.1f}%</font>',
                      ParagraphStyle("pnlp", fontSize=8, alignment=TA_CENTER)),
        ])
    p_tbl = Table(p_rows, colWidths=[22*mm, 20*mm, 18*mm, 22*mm, 22*mm, 22*mm, 22*mm, 18*mm])
    p_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), C_ORANGE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_DARK]),
        ("TEXTCOLOR",     (0,1), (-1,-1), C_WHITE),
        ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(p_tbl)

# ══════════════════════════════════════════
#  SECTION — ALERTES
# ══════════════════════════════════════════
def _section_alertes(story, S, alerts: list, triggered: list):
    active = [a for a in alerts if a.get("active", True)]
    if not active and not triggered:
        return

    story.append(Paragraph("» ALERTES", S["section"]))

    if active:
        story.append(Paragraph(f"Alertes actives ({len(active)})", S["body"]))
        a_rows = [["NOM", "TICKER", "TYPE", "SEUIL", "EMAIL", "CRÉÉE LE"]]
        for a in active:
            val = (f"MA{a.get('ma_fast',20)}/MA{a.get('ma_slow',50)}"
                   if "MA" in a.get("type","")
                   else str(a.get("value","")))
            a_rows.append([
                Paragraph(a.get("name","")[:30], ParagraphStyle("an", fontSize=7, textColor=C_WHITE)),
                a.get("ticker",""),
                a.get("type","")[:22],
                val,
                "✓" if a.get("notify_email") else "–",
                str(a.get("created_at",""))[:16],
            ])
        a_tbl = Table(a_rows, colWidths=[45*mm, 18*mm, 38*mm, 22*mm, 12*mm, 30*mm])
        a_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), C_DARK),
            ("TEXTCOLOR",     (0,0), (-1,0), C_ORANGE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 7),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_DARK]),
            ("TEXTCOLOR",     (0,1), (-1,-1), C_WHITE),
            ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
            ("ALIGN",         (0,0), (-1,-1), "LEFT"),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(a_tbl)

    if triggered:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(f"Dernières alertes déclenchées ({min(len(triggered),5)})", S["body"]))
        t_rows = [["NOM", "TICKER", "PRIX", "VAR 24H", "INFO", "DÉCLENCHÉ"]]
        for item in triggered[:5]:
            a = item.get("alert", {})
            t_rows.append([
                Paragraph(a.get("name","")[:28], ParagraphStyle("tn", fontSize=7, textColor=C_WHITE)),
                a.get("ticker",""),
                f"{item.get('current_price',0):.2f}",
                f"{item.get('change_pct',0):+.2f}%",
                item.get("extra","–")[:20],
                str(item.get("triggered_at",""))[:16],
            ])
        t_tbl = Table(t_rows, colWidths=[42*mm, 18*mm, 20*mm, 18*mm, 35*mm, 32*mm])
        t_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), C_DARK),
            ("TEXTCOLOR",     (0,0), (-1,0), C_GREEN),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 7),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BG, C_DARK]),
            ("TEXTCOLOR",     (0,1), (-1,-1), C_WHITE),
            ("GRID",          (0,0), (-1,-1), 0.4, C_BORDER),
            ("ALIGN",         (0,0), (-1,-1), "LEFT"),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(t_tbl)

# ══════════════════════════════════════════
#  BUILDER PRINCIPAL
# ══════════════════════════════════════════
def generate_pdf(
    ticker:    str  = None,
    info:      dict = None,
    valuation: dict = None,
    positions: list = None,
    mode:      str  = "full",   # "analyse" | "portfolio" | "full"
) -> bytes:
    """
    Génère le PDF et retourne les bytes.
    mode="analyse"   → fiche action + chart
    mode="portfolio" → portefeuille + alertes
    mode="full"      → tout
    """
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm,  bottomMargin=15*mm,
        title="AM-Trading — Rapport d'Analyse",
        author="AM-Trading Bloomberg Terminal",
    )
    S     = _styles()
    story = []

    # En-tête
    subtitle = {
        "analyse":   f"ANALYSE — {(ticker or '').upper()}",
        "portfolio": "RAPPORT DE PORTEFEUILLE",
        "full":      f"RAPPORT COMPLET — {(ticker or '').upper()}",
    }.get(mode, "RAPPORT D'ANALYSE")
    _header(story, S, subtitle)

    # Fiche analyse
    if mode in ("analyse", "full") and ticker and info:
        _section_analyse(story, S, ticker, info or {}, valuation or {})
        story.append(Spacer(1, 4*mm))

        # Chart
        story.append(Paragraph("» GRAPHIQUE 6 MOIS (Chandeliers + MA20/50)", S["section"]))
        chart = _chart_image(ticker)
        if chart:
            story.append(chart)
        else:
            story.append(Paragraph("Graphique non disponible.", S["body"]))
        story.append(Spacer(1, 4*mm))

    # Portefeuille
    if mode in ("portfolio", "full"):
        positions = positions or st.session_state.get("positions_computed",
                    st.session_state.get("portfolio", []))
        if positions:
            if mode == "full":
                story.append(PageBreak())
                _header(story, S, "RAPPORT DE PORTEFEUILLE")
            _section_portfolio(story, S, positions)
            story.append(Spacer(1, 4*mm))

    # Alertes (toujours incluses)
    alerts    = st.session_state.get("alerts", [])
    triggered = st.session_state.get("triggered_alerts", [])
    if alerts or triggered:
        _section_alertes(story, S, alerts, triggered)

    # Footer
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "AM-Trading Bloomberg Terminal  •  Document généré automatiquement  •  Ne constitue pas un conseil en investissement",
        S["footer"]))

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════
#  BOUTON STREAMLIT RÉUTILISABLE
# ══════════════════════════════════════════
def download_button_analyse(ticker: str, info: dict, valuation: dict, key: str = "dl_pdf_analyse"):
    """Bouton à insérer dans l'Analyseur Pro."""
    if st.button("📄 EXPORTER EN PDF", key=key, use_container_width=True):
        with st.spinner("Génération du PDF..."):
            try:
                pdf_bytes = generate_pdf(ticker=ticker, info=info, valuation=valuation, mode="analyse")
                fname = f"AM-Trading_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.download_button(
                    label="⬇️ Télécharger le rapport",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    key=f"{key}_dl",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Erreur génération PDF : {e}")


def download_button_portfolio(positions: list, key: str = "dl_pdf_portfolio"):
    """Bouton à insérer dans le Portfolio."""
    if st.button("📄 EXPORTER EN PDF", key=key, use_container_width=True):
        with st.spinner("Génération du rapport..."):
            try:
                pdf_bytes = generate_pdf(positions=positions, mode="portfolio")
                fname = f"AM-Trading_Portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.download_button(
                    label="⬇️ Télécharger le rapport",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    key=f"{key}_dl",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Erreur génération PDF : {e}")
