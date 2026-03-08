"""
interface_forex.py
Section FOREX pour AM-Trading Terminal
Outils : Classement monnaies, Top hausse/baisse, Corrélation, Heat map, Carry Trade, etc.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import requests
from datetime import datetime, timedelta

# ══════════════════════════════════════════════
#  CONFIG PAIRES FOREX
# ══════════════════════════════════════════════

MAJOR_PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X", "USD/CNY": "USDCNY=X",
}

MINOR_PAIRS = {
    "EUR/GBP": "EURGBP=X", "EUR/JPY": "EURJPY=X", "EUR/CHF": "EURCHF=X",
    "GBP/JPY": "GBPJPY=X", "AUD/JPY": "AUDJPY=X", "EUR/AUD": "EURAUD=X",
    "GBP/CHF": "GBPCHF=X", "EUR/CAD": "EURCAD=X",
}

EXOTIC_PAIRS = {
    "USD/TRY": "USDTRY=X", "USD/MXN": "USDMXN=X", "USD/ZAR": "USDZAR=X",
    "USD/BRL": "USDBRL=X", "USD/SGD": "USDSGD=X", "USD/HKD": "USDHKD=X",
}

ALL_PAIRS = {**MAJOR_PAIRS, **MINOR_PAIRS, **EXOTIC_PAIRS}

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "CNY"]

CURRENCY_FLAGS = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵",
    "CHF": "🇨🇭", "AUD": "🇦🇺", "CAD": "🇨🇦", "NZD": "🇳🇿",
    "CNY": "🇨🇳", "TRY": "🇹🇷", "MXN": "🇲🇽", "ZAR": "🇿🇦",
    "BRL": "🇧🇷", "SGD": "🇸🇬", "HKD": "🇭🇰",
}

# Taux directeurs — fallback mars 2026 (sources officielles banques centrales)
_INTEREST_RATES_FALLBACK = {
    "USD": 4.50,  # FED — mars 2026
    "EUR": 2.65,  # BCE — mars 2026
    "GBP": 4.50,  # BOE — mars 2026
    "JPY": 0.50,  # BOJ — mars 2026
    "CHF": 0.50,  # BNS — mars 2026
    "AUD": 4.10,  # RBA — mars 2026
    "CAD": 3.00,  # BOC — mars 2026
    "NZD": 3.75,  # RBNZ — mars 2026
    "CNY": 3.10,  # PBOC — mars 2026
    "TRY": 42.50, "MXN": 9.50, "ZAR": 7.50,
    "BRL": 14.75, "SGD": 3.50, "HKD": 4.75,
}

@st.cache_data(ttl=3600)
def get_interest_rates() -> dict:
    """
    Taux directeurs en temps réel via FRED (FED, BCE) + fallback officiel.
    Refresh toutes les heures.
    """
    rates = dict(_INTEREST_RATES_FALLBACK)
    try:
        # FED — FRED FEDFUNDS (CSV sans clé)
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS",
                         timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            lines = [l for l in r.text.strip().split("\n") if l and not l.startswith("DATE")]
            for line in reversed(lines):
                parts = line.split(",")
                if len(parts) == 2 and parts[1].strip() not in ("", "."):
                    rates["USD"] = round(float(parts[1].strip()), 2)
                    break
    except Exception:
        pass
    try:
        # BCE — MRR
        r = requests.get(
            "https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.MRR_FR.LEV"
            "?format=csvdata&lastNObservations=1",
            timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            for line in reversed(r.text.strip().split("\n")):
                if line and not line.startswith("KEY") and "," in line:
                    parts = line.split(",")
                    val = float(parts[-1].strip())
                    if val > 0.1:  # guard zéro
                        rates["EUR"] = round(val, 2)
                    break
    except Exception:
        pass
    return rates

# Variable globale mise en cache (chargée une seule fois par session)
INTEREST_RATES = _INTEREST_RATES_FALLBACK  # sera rafraîchi via get_interest_rates()

CURRENCY_NAMES = {
    "USD": "Dollar Américain", "EUR": "Euro", "GBP": "Livre Sterling",
    "JPY": "Yen Japonais", "CHF": "Franc Suisse", "AUD": "Dollar Australien",
    "CAD": "Dollar Canadien", "NZD": "Dollar Néo-Zélandais", "CNY": "Yuan Chinois",
}

# ══════════════════════════════════════════════
#  FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════

@st.cache_data(ttl=300)
def get_forex_data(ticker, period="1mo"):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_current_price(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        return float(info["last_price"])
    except:
        return None

@st.cache_data(ttl=300)
def get_pair_change(ticker, period="1d"):
    try:
        df = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if len(df) >= 2:
            close = df["Close"].dropna()
            current = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            change_pct = ((current - previous) / previous) * 100
            return current, change_pct
        return None, None
    except:
        return None, None

def couleur_variation(val):
    if val > 0: return "#00ff00"
    elif val < 0: return "#ff4b4b"
    return "#888"

def badge_variation(val, unite="%"):
    c = couleur_variation(val)
    signe = "▲" if val > 0 else "▼" if val < 0 else "→"
    return f"<span style='color:{c}; font-weight:bold;'>{signe} {abs(val):.2f}{unite}</span>"


# ══════════════════════════════════════════════
#  INTERFACE PRINCIPALE
# ══════════════════════════════════════════════

def show_forex():
    st.markdown("""
        <div style='text-align:center; padding:25px; background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #ff9800; border-radius:12px; margin-bottom:20px;'>
            <h1 style='color:#ff9800; margin:0; font-size:36px;'>💱 FOREX TERMINAL</h1>
            <p style='color:#ffb84d; margin:8px 0 0 0; font-size:14px;'>
                Marchés des Changes — Majeurs · Mineurs · Exotiques
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 TABLEAU DE BORD",
        "🏆 CLASSEMENT MONNAIES",
        "🚀 TOP HAUSSE / BAISSE",
        "🔥 HEATMAP FOREX",
        "📈 GRAPHIQUES",
        "🔗 CORRÉLATION",
        "💰 CARRY TRADE",
        "⚖️ CONVERTISSEUR"
    ])

    # ══════════════════════════════════════════
    #  ONGLET 1 — TABLEAU DE BORD
    # ══════════════════════════════════════════
    with tab1:
        st.markdown("### 📊 TABLEAU DE BORD FOREX — PAIRES MAJEURES")
        st.caption("Données en temps réel via Yahoo Finance")

        if st.button("🔄 ACTUALISER LES DONNÉES", key="refresh_dashboard"):
            st.cache_data.clear()
            st.rerun()

        # Métriques rapides
        col1, col2, col3, col4 = st.columns(4)
        paires_quick = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"]
        for i, paire in enumerate(paires_quick):
            ticker = MAJOR_PAIRS[paire]
            prix, chg = get_pair_change(ticker)
            with [col1, col2, col3, col4][i]:
                if prix and chg is not None:
                    st.metric(paire, f"{prix:.4f}", f"{chg:+.2f}%",
                              delta_color="normal" if chg >= 0 else "inverse")
                else:
                    st.metric(paire, "N/A")

        st.markdown("---")
        st.markdown("### 📋 TOUTES LES PAIRES MAJEURES")

        rows = []
        progress = st.progress(0)
        pairs_list = list(MAJOR_PAIRS.items())
        for i, (paire, ticker) in enumerate(pairs_list):
            prix, chg = get_pair_change(ticker)
            progress.progress((i + 1) / len(pairs_list))
            if prix and chg is not None:
                df_1w = get_forex_data(ticker, "5d")
                df_1m = get_forex_data(ticker, "1mo")
                chg_1w = chg_1m = 0
                if not df_1w.empty and len(df_1w) >= 5:
                    c = df_1w["Close"].dropna()
                    chg_1w = ((float(c.iloc[-1]) - float(c.iloc[0])) / float(c.iloc[0])) * 100
                if not df_1m.empty:
                    c = df_1m["Close"].dropna()
                    chg_1m = ((float(c.iloc[-1]) - float(c.iloc[0])) / float(c.iloc[0])) * 100
                rows.append({
                    "Paire": paire,
                    "Prix": f"{prix:.4f}",
                    "1 Jour": f"{chg:+.2f}%",
                    "1 Semaine": f"{chg_1w:+.2f}%",
                    "1 Mois": f"{chg_1m:+.2f}%",
                    "Tendance": "📈" if chg >= 0 else "📉"
                })
        progress.empty()

        if rows:
            df_display = pd.DataFrame(rows)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        # TradingView widget overview
        st.markdown("---")
        st.markdown("### 📺 FOREX OVERVIEW — TRADINGVIEW")
        tv_html = """
        <div class="tradingview-widget-container">
            <div class="tradingview-widget-container__widget"></div>
            <script type="text/javascript"
                src="https://s3.tradingview.com/external-embedding/embed-widget-forex-cross-rates.js" async>
            {
                "width": "100%", "height": "450", "currencies": ["EUR","USD","JPY","GBP","CHF","AUD","CAD","NZD"],
                "isTransparent": true, "colorTheme": "dark", "locale": "fr"
            }
            </script>
        </div>
        """
        st.components.v1.html(tv_html, height=460)

    # ══════════════════════════════════════════
    #  ONGLET 2 — CLASSEMENT MONNAIES
    # ══════════════════════════════════════════
    with tab2:
        st.markdown("### 🏆 CLASSEMENT DE FORCE DES MONNAIES")
        st.info("Calcul basé sur la performance moyenne de chaque monnaie contre toutes les autres.")

        period_rank = st.selectbox("Période", ["1d", "5d", "1mo", "3mo"], index=1, key="rank_period")

        if st.button("🚀 CALCULER LE CLASSEMENT", key="calc_rank"):
            with st.spinner("Analyse de toutes les paires en cours..."):
                currency_scores = {c: [] for c in CURRENCIES}

                for paire, ticker in MAJOR_PAIRS.items():
                    base, quote = paire.split("/")
                    df = get_forex_data(ticker, period_rank)
                    if not df.empty:
                        c = df["Close"].dropna()
                        if len(c) >= 2:
                            chg = ((float(c.iloc[-1]) - float(c.iloc[0])) / float(c.iloc[0])) * 100
                            if base in currency_scores:
                                currency_scores[base].append(chg)
                            if quote in currency_scores:
                                currency_scores[quote].append(-chg)

                results = []
                for currency, scores in currency_scores.items():
                    if scores:
                        avg_score = np.mean(scores)
                        results.append({
                            "Rang": 0,
                            "Monnaie": f"{CURRENCY_FLAGS.get(currency, '')} {currency}",
                            "Nom": CURRENCY_NAMES.get(currency, currency),
                            "Score Moyen": round(avg_score, 3),
                            "Taux Intérêt": f"{INTEREST_RATES.get(currency, 0)}%",
                        })

                results = sorted(results, key=lambda x: x["Score Moyen"], reverse=True)
                for i, r in enumerate(results):
                    r["Rang"] = i + 1
                    r["Statut"] = "💪 FORT" if r["Score Moyen"] > 0 else "😔 FAIBLE"

                df_rank = pd.DataFrame(results)

                # Podium top 3
                st.markdown("### 🥇 PODIUM")
                c1, c2, c3 = st.columns(3)
                podium = [(c1, 0, "🥇", "#FFD700"), (c2, 1, "🥈", "#C0C0C0"), (c3, 2, "🥉", "#CD7F32")]
                for col, idx, medal, color in podium:
                    if idx < len(results):
                        r = results[idx]
                        with col:
                            st.markdown(f"""
                                <div style='text-align:center; padding:20px; border:2px solid {color};
                                     border-radius:10px; background:#0d0d0d;'>
                                    <div style='font-size:36px;'>{medal}</div>
                                    <div style='color:{color}; font-size:24px; font-weight:bold;'>
                                        {r['Monnaie']}
                                    </div>
                                    <div style='color:#ccc; font-size:14px;'>{r['Nom']}</div>
                                    <div style='color:{"#00ff00" if r["Score Moyen"] > 0 else "#ff4b4b"};
                                         font-size:18px; margin-top:8px;'>
                                        {r['Score Moyen']:+.3f}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                st.markdown("---")

                # Graphique barres
                fig = go.Figure(go.Bar(
                    x=[r["Monnaie"] for r in results],
                    y=[r["Score Moyen"] for r in results],
                    marker_color=["#00ff00" if r["Score Moyen"] > 0 else "#ff4b4b" for r in results],
                    text=[f"{r['Score Moyen']:+.3f}%" for r in results],
                    textposition="auto"
                ))
                fig.update_layout(
                    template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                    title=dict(text="Force Relative des Monnaies", font=dict(color="#ff9800", size=16)),
                    height=400, margin=dict(l=40, r=20, t=50, b=40),
                    yaxis=dict(gridcolor="#222", ticksuffix="%"),
                    xaxis=dict(gridcolor="#222"),
                    showlegend=False
                )
                fig.add_hline(y=0, line_color="#888", line_width=1)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### 📋 CLASSEMENT COMPLET")
                st.dataframe(df_rank, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════
    #  ONGLET 3 — TOP HAUSSE / BAISSE
    # ══════════════════════════════════════════
    with tab3:
        st.markdown("### 🚀 TOP HAUSSE & BAISSE DU JOUR")

        type_pairs = st.selectbox("Type de paires", ["Majeures", "Mineures", "Exotiques", "Toutes"], key="top_type")
        period_top = st.selectbox("Période", ["1d", "5d", "1mo"], index=0, key="top_period")

        pairs_to_scan = {
            "Majeures": MAJOR_PAIRS,
            "Mineures": MINOR_PAIRS,
            "Exotiques": EXOTIC_PAIRS,
            "Toutes": ALL_PAIRS
        }[type_pairs]

        if st.button("🔍 SCANNER LES MARCHÉS", key="scan_top"):
            with st.spinner("Scan en cours..."):
                mouvements = []
                prog = st.progress(0)
                pairs_list = list(pairs_to_scan.items())
                for i, (paire, ticker) in enumerate(pairs_list):
                    prog.progress((i + 1) / len(pairs_list))
                    df = get_forex_data(ticker, period_top if period_top != "1d" else "5d")
                    if not df.empty and len(df) >= 2:
                        c = df["Close"].dropna()
                        current = float(c.iloc[-1])
                        start = float(c.iloc[-2] if period_top == "1d" else c.iloc[0])
                        chg = ((current - start) / start) * 100
                        high = float(df["High"].max())
                        low = float(df["Low"].min())
                        mouvements.append({
                            "Paire": paire, "Prix": current,
                            "Variation": chg, "Plus Haut": high, "Plus Bas": low,
                            "Range": ((high - low) / low) * 100
                        })
                prog.empty()

                if mouvements:
                    mouvements_sorted = sorted(mouvements, key=lambda x: x["Variation"], reverse=True)
                    top_hausse = mouvements_sorted[:5]
                    top_baisse = mouvements_sorted[-5:][::-1]

                    col_h, col_b = st.columns(2)
                    with col_h:
                        st.markdown("### 🟢 TOP 5 HAUSSES")
                        for r in top_hausse:
                            st.markdown(f"""
                                <div style='padding:15px; background:#00ff0011;
                                     border-left:4px solid #00ff00; border-radius:5px; margin:8px 0;'>
                                    <div style='display:flex; justify-content:space-between;'>
                                        <b style='color:#00ff00; font-size:18px;'>{r['Paire']}</b>
                                        <b style='color:#00ff00; font-size:18px;'>+{r['Variation']:.2f}%</b>
                                    </div>
                                    <div style='color:#ccc; font-size:13px; margin-top:5px;'>
                                        Prix: {r['Prix']:.4f} | Range: {r['Range']:.2f}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                    with col_b:
                        st.markdown("### 🔴 TOP 5 BAISSES")
                        for r in top_baisse:
                            st.markdown(f"""
                                <div style='padding:15px; background:#ff4b4b11;
                                     border-left:4px solid #ff4b4b; border-radius:5px; margin:8px 0;'>
                                    <div style='display:flex; justify-content:space-between;'>
                                        <b style='color:#ff4b4b; font-size:18px;'>{r['Paire']}</b>
                                        <b style='color:#ff4b4b; font-size:18px;'>{r['Variation']:.2f}%</b>
                                    </div>
                                    <div style='color:#ccc; font-size:13px; margin-top:5px;'>
                                        Prix: {r['Prix']:.4f} | Range: {r['Range']:.2f}%
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                    st.markdown("---")
                    # Graphique waterfall
                    mouvements_sorted_all = sorted(mouvements, key=lambda x: x["Variation"])
                    fig = go.Figure(go.Bar(
                        x=[m["Paire"] for m in mouvements_sorted_all],
                        y=[m["Variation"] for m in mouvements_sorted_all],
                        marker_color=["#00ff00" if m["Variation"] >= 0 else "#ff4b4b"
                                      for m in mouvements_sorted_all],
                        text=[f"{m['Variation']:+.2f}%" for m in mouvements_sorted_all],
                        textposition="auto"
                    ))
                    fig.update_layout(
                        template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                        title=dict(text=f"Variations Forex ({period_top})",
                                   font=dict(color="#ff9800", size=16)),
                        height=450, xaxis=dict(tickangle=-45, gridcolor="#222"),
                        yaxis=dict(gridcolor="#222", ticksuffix="%"), showlegend=False
                    )
                    fig.add_hline(y=0, line_color="#888", line_width=1)
                    st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════
    #  ONGLET 4 — HEATMAP FOREX
    # ══════════════════════════════════════════
    with tab4:
        st.markdown("### 🔥 HEATMAP FOREX")
        st.info("Visualisation de la performance de chaque paire sur la période sélectionnée.")

        period_heat = st.selectbox("Période", ["1d", "5d", "1mo", "3mo"], index=1, key="heat_period")

        if st.button("🎨 GÉNÉRER LA HEATMAP", key="gen_heat"):
            with st.spinner("Chargement des données..."):
                heat_data = {}
                pairs_list = list(MAJOR_PAIRS.items()) + list(MINOR_PAIRS.items())
                prog = st.progress(0)
                for i, (paire, ticker) in enumerate(pairs_list):
                    prog.progress((i + 1) / len(pairs_list))
                    df = get_forex_data(ticker, period_heat if period_heat != "1d" else "5d")
                    if not df.empty and len(df) >= 2:
                        c = df["Close"].dropna()
                        start = float(c.iloc[-2] if period_heat == "1d" else c.iloc[0])
                        end = float(c.iloc[-1])
                        heat_data[paire] = ((end - start) / start) * 100
                prog.empty()

                if heat_data:
                    # Heatmap Treemap
                    labels = list(heat_data.keys())
                    values = list(heat_data.values())
                    colors = values

                    fig = go.Figure(go.Treemap(
                        labels=labels,
                        parents=[""] * len(labels),
                        values=[abs(v) + 0.01 for v in values],
                        customdata=[[f"{v:+.2f}%"] for v in values],
                        text=[f"{l}<br>{v:+.2f}%" for l, v in zip(labels, values)],
                        textinfo="text",
                        marker=dict(
                            colors=colors,
                            colorscale=[[0, "#ff0000"], [0.5, "#1a1a1a"], [1, "#00ff00"]],
                            cmid=0,
                            showscale=True,
                            colorbar=dict(title="Var %", ticksuffix="%")
                        ),
                        hovertemplate="<b>%{label}</b><br>Variation: %{customdata[0]}<extra></extra>"
                    ))
                    fig.update_layout(
                        template="plotly_dark", paper_bgcolor="#0d0d0d",
                        title=dict(text=f"Heatmap Forex — {period_heat}",
                                   font=dict(color="#ff9800", size=16)),
                        height=600, margin=dict(l=10, r=10, t=60, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Stats rapides
                    st.markdown("### 📊 STATISTIQUES")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("Variation Moyenne", f"{np.mean(values):+.2f}%")
                    with c2: st.metric("Meilleure Paire 🚀",
                                       max(heat_data, key=heat_data.get),
                                       f"{max(values):+.2f}%")
                    with c3: st.metric("Pire Paire 📉",
                                       min(heat_data, key=heat_data.get),
                                       f"{min(values):+.2f}%")
                    with c4:
                        pos = len([v for v in values if v > 0])
                        st.metric("Paires en hausse", f"{pos}/{len(values)}")

    # ══════════════════════════════════════════
    #  ONGLET 5 — GRAPHIQUES
    # ══════════════════════════════════════════
    with tab5:
        st.markdown("### 📈 GRAPHIQUES FOREX")

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            paire_chart = st.selectbox("Paire", list(ALL_PAIRS.keys()), key="chart_pair")
        with col_g2:
            period_chart = st.selectbox("Période",
                ["5d", "1mo", "3mo", "6mo", "1y", "2y"], index=2, key="chart_period")
        with col_g3:
            chart_type = st.selectbox("Type", ["Chandeliers", "Ligne", "Aire"], key="chart_type")

        if st.button("📊 AFFICHER LE GRAPHIQUE", key="show_chart"):
            with st.spinner("Chargement..."):
                ticker = ALL_PAIRS[paire_chart]
                df = get_forex_data(ticker, period_chart)

                if not df.empty:
                    df["SMA20"] = df["Close"].rolling(20).mean()
                    df["SMA50"] = df["Close"].rolling(50).mean()
                    df["EMA12"] = df["Close"].ewm(span=12).mean()
                    df["BB_mid"] = df["Close"].rolling(20).mean()
                    df["BB_std"] = df["Close"].rolling(20).std()
                    df["BB_up"] = df["BB_mid"] + 2 * df["BB_std"]
                    df["BB_low"] = df["BB_mid"] - 2 * df["BB_std"]

                    # RSI
                    delta = df["Close"].diff()
                    gain = delta.clip(lower=0)
                    loss = -delta.clip(upper=0)
                    avg_gain = gain.rolling(14).mean()
                    avg_loss = loss.rolling(14).mean().replace(0, 0.0001)
                    rs = avg_gain / avg_loss
                    df["RSI"] = 100 - (100 / (1 + rs))

                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                        vertical_spacing=0.05, row_heights=[0.7, 0.3],
                                        subplot_titles=(paire_chart, "RSI"))

                    if chart_type == "Chandeliers":
                        fig.add_trace(go.Candlestick(
                            x=df.index, open=df["Open"], high=df["High"],
                            low=df["Low"], close=df["Close"], name=paire_chart
                        ), row=1, col=1)
                    elif chart_type == "Ligne":
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df["Close"], name=paire_chart,
                            line=dict(color="#ff9800", width=2)
                        ), row=1, col=1)
                    else:
                        fig.add_trace(go.Scatter(
                            x=df.index, y=df["Close"], name=paire_chart,
                            fill="tozeroy", line=dict(color="#ff9800", width=2),
                            fillcolor="rgba(255,152,0,0.1)"
                        ), row=1, col=1)

                    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA20",
                                             line=dict(color="cyan", width=1.5, dash="dot")), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50",
                                             line=dict(color="magenta", width=1.5, dash="dot")), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["BB_up"], name="BB+",
                                             line=dict(color="rgba(255,152,0,0.3)", dash="dash")), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["BB_low"], name="BB-",
                                             line=dict(color="rgba(255,152,0,0.3)", dash="dash"),
                                             fill="tonexty", fillcolor="rgba(255,152,0,0.05)"), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                                             line=dict(color="purple", width=2)), row=2, col=1)
                    fig.add_hline(y=70, line_color="red", line_dash="dash", row=2, col=1)
                    fig.add_hline(y=30, line_color="green", line_dash="dash", row=2, col=1)

                    fig.update_layout(
                        template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                        height=700, xaxis_rangeslider_visible=False,
                        legend=dict(bgcolor="rgba(0,0,0,0.5)"),
                        margin=dict(l=40, r=20, t=60, b=40)
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Stats clés
                    last = df.iloc[-1]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Prix Actuel", f"{float(last['Close']):.4f}")
                    c2.metric("RSI", f"{float(last['RSI']):.1f}")
                    c3.metric("SMA 20", f"{float(last['SMA20']):.4f}" if not pd.isna(last['SMA20']) else "N/A")
                    c4.metric("SMA 50", f"{float(last['SMA50']):.4f}" if not pd.isna(last['SMA50']) else "N/A")

    # ══════════════════════════════════════════
    #  ONGLET 6 — CORRÉLATION
    # ══════════════════════════════════════════
    with tab6:
        st.markdown("### 🔗 MATRICE DE CORRÉLATION FOREX")
        st.info("Corrélation = +1 : paires identiques | 0 : indépendantes | -1 : opposées")

        period_corr = st.selectbox("Période", ["1mo", "3mo", "6mo"], index=0, key="corr_period")

        if st.button("🔗 CALCULER LA CORRÉLATION", key="calc_corr"):
            with st.spinner("Calcul des corrélations..."):
                paires_corr = list(MAJOR_PAIRS.keys()) + list(MINOR_PAIRS.keys())[:4]
                tickers_corr = [ALL_PAIRS[p] for p in paires_corr]

                price_data = {}
                prog = st.progress(0)
                for i, (paire, ticker) in enumerate(zip(paires_corr, tickers_corr)):
                    prog.progress((i + 1) / len(paires_corr))
                    df = get_forex_data(ticker, period_corr)
                    if not df.empty:
                        price_data[paire] = df["Close"].dropna()
                prog.empty()

                if len(price_data) >= 3:
                    df_prices = pd.DataFrame(price_data).dropna()
                    returns = df_prices.pct_change().dropna()
                    corr_matrix = returns.corr()

                    fig = go.Figure(go.Heatmap(
                        z=corr_matrix.values,
                        x=corr_matrix.columns.tolist(),
                        y=corr_matrix.index.tolist(),
                        colorscale=[[0, "#ff0000"], [0.5, "#1a1a1a"], [1, "#00ff00"]],
                        zmin=-1, zmax=1,
                        text=[[f"{v:.2f}" for v in row] for row in corr_matrix.values],
                        texttemplate="%{text}",
                        textfont=dict(size=11, color="white"),
                        hovertemplate="<b>%{x} / %{y}</b><br>Corrélation: %{z:.3f}<extra></extra>"
                    ))
                    fig.update_layout(
                        template="plotly_dark", paper_bgcolor="#0d0d0d",
                        title=dict(text=f"Corrélation Forex ({period_corr})",
                                   font=dict(color="#ff9800", size=16)),
                        height=600, margin=dict(l=120, r=20, t=60, b=120),
                        xaxis=dict(tickangle=-45),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Insights corrélation
                    st.markdown("### 💡 INSIGHTS CLÉS")
                    strong_pos, strong_neg = [], []
                    for i in range(len(corr_matrix.columns)):
                        for j in range(i + 1, len(corr_matrix.columns)):
                            val = corr_matrix.iloc[i, j]
                            pair_str = f"{corr_matrix.columns[i]} / {corr_matrix.columns[j]}"
                            if val > 0.85:
                                strong_pos.append((pair_str, val))
                            elif val < -0.85:
                                strong_neg.append((pair_str, val))

                    col_p, col_n = st.columns(2)
                    with col_p:
                        st.markdown("#### 🟢 Très corrélées (+)")
                        if strong_pos:
                            for p, v in sorted(strong_pos, key=lambda x: -x[1])[:5]:
                                st.markdown(f"<span style='color:#00ff00;'>✅ {p}: **{v:.2f}**</span>",
                                            unsafe_allow_html=True)
                        else:
                            st.info("Aucune corrélation forte positive")
                    with col_n:
                        st.markdown("#### 🔴 Inversement corrélées (-)")
                        if strong_neg:
                            for p, v in sorted(strong_neg, key=lambda x: x[1])[:5]:
                                st.markdown(f"<span style='color:#ff4b4b;'>⚠️ {p}: **{v:.2f}**</span>",
                                            unsafe_allow_html=True)
                        else:
                            st.info("Aucune corrélation forte négative")

    # ══════════════════════════════════════════
    #  ONGLET 7 — CARRY TRADE
    # ══════════════════════════════════════════
    with tab7:
        st.markdown("### 💰 CARRY TRADE ANALYZER")
        st.info("Le carry trade consiste à emprunter dans une monnaie à faible taux et investir dans une monnaie à taux élevé.")

        st.markdown("### 📊 TAUX D'INTÉRÊT DES BANQUES CENTRALES")
        rates_sorted = sorted(INTEREST_RATES.items(), key=lambda x: -x[1])

        fig_rates = go.Figure(go.Bar(
            x=[f"{CURRENCY_FLAGS.get(c, '')} {c}" for c, r in rates_sorted],
            y=[r for c, r in rates_sorted],
            marker_color=["#00ff00" if r > 3 else "#ff9800" if r > 1 else "#ff4b4b"
                          for c, r in rates_sorted],
            text=[f"{r}%" for c, r in rates_sorted],
            textposition="auto"
        ))
        fig_rates.update_layout(
            template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
            title=dict(text="Taux Directeurs par Banque Centrale",
                       font=dict(color="#ff9800", size=16)),
            height=400, yaxis=dict(gridcolor="#222", ticksuffix="%"),
            xaxis=dict(gridcolor="#222"), showlegend=False
        )
        st.plotly_chart(fig_rates, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🎯 MEILLEURES OPPORTUNITÉS CARRY TRADE")

        opportunities = []
        for base, base_rate in INTEREST_RATES.items():
            for quote, quote_rate in INTEREST_RATES.items():
                if base != quote:
                    carry = base_rate - quote_rate
                    if carry > 2:
                        opportunities.append({
                            "Position": f"Long {CURRENCY_FLAGS.get(base,'')} {base} / Short {CURRENCY_FLAGS.get(quote,'')} {quote}",
                            "Taux Base": f"{base_rate}%",
                            "Taux Quote": f"{quote_rate}%",
                            "Carry Annuel": f"{carry:.2f}%",
                            "Score": carry
                        })

        opportunities = sorted(opportunities, key=lambda x: -x["Score"])[:10]
        for i, opp in enumerate(opportunities):
            score = opp["Score"]
            color = "#00ff00" if score > 10 else "#ff9800" if score > 5 else "#ffff00"
            st.markdown(f"""
                <div style='padding:12px; background:{color}11; border-left:4px solid {color};
                     border-radius:5px; margin:8px 0;'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <b style='color:{color}; font-size:15px;'>{opp['Position']}</b>
                        <b style='color:{color}; font-size:18px;'>+{opp['Carry Annuel']}/an</b>
                    </div>
                    <div style='color:#888; font-size:12px; margin-top:4px;'>
                        Base: {opp['Taux Base']} | Quote: {opp['Taux Quote']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🧮 SIMULATEUR CARRY TRADE")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            curr_long = st.selectbox("Monnaie LONG (taux élevé)",
                                     [c for c, r in sorted(INTEREST_RATES.items(), key=lambda x: -x[1])],
                                     key="carry_long")
        with col_s2:
            curr_short = st.selectbox("Monnaie SHORT (taux faible)",
                                      [c for c, r in sorted(INTEREST_RATES.items(), key=lambda x: x[1])],
                                      key="carry_short")
        with col_s3:
            capital_carry = st.number_input("Capital ($)", value=10000, step=1000, key="carry_capital")

        leverage = st.slider("Levier", 1, 20, 1, key="carry_leverage")
        carry_rate = INTEREST_RATES.get(curr_long, 0) - INTEREST_RATES.get(curr_short, 0)
        gain_annuel = capital_carry * leverage * (carry_rate / 100)
        gain_mensuel = gain_annuel / 12

        if carry_rate > 0:
            st.success(f"✅ Carry positif : **{carry_rate:.2f}%/an**")
        else:
            st.error(f"❌ Carry négatif : **{carry_rate:.2f}%/an** — Cette position coûte de l'argent !")

        c1, c2, c3 = st.columns(3)
        c1.metric("Gain Annuel Estimé", f"${gain_annuel:,.0f}")
        c2.metric("Gain Mensuel Estimé", f"${gain_mensuel:,.0f}")
        c3.metric("Carry Rate", f"{carry_rate:+.2f}%/an")
        st.caption("⚠️ Le carry trade comporte des risques de change. Les gains peuvent être annulés par les variations de cours.")

    # ══════════════════════════════════════════
    #  ONGLET 8 — CONVERTISSEUR
    # ══════════════════════════════════════════
    with tab8:
        st.markdown("### ⚖️ CONVERTISSEUR DE DEVISES")

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            montant = st.number_input("Montant", value=1000.0, step=100.0, key="conv_amount")
            devise_from = st.selectbox("De", list(CURRENCY_FLAGS.keys()), key="conv_from")
        with col_c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align:center; color:#ff9800;'>➡️</h2>", unsafe_allow_html=True)
        with col_c3:
            devise_to = st.selectbox("Vers", list(CURRENCY_FLAGS.keys()), index=1, key="conv_to")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💱 CONVERTIR", key="conv_btn", use_container_width=True):
                try:
                    if devise_from == devise_to:
                        st.info(f"Résultat : **{montant:,.2f} {devise_to}**")
                    else:
                        ticker_conv = f"{devise_from}{devise_to}=X"
                        rate = get_current_price(ticker_conv)
                        if rate:
                            result = montant * rate
                            st.markdown(f"""
                                <div style='text-align:center; padding:25px; border:2px solid #ff9800;
                                     border-radius:10px; background:#0d0d0d; margin-top:10px;'>
                                    <div style='color:#888; font-size:14px;'>RÉSULTAT</div>
                                    <div style='color:#ff9800; font-size:42px; font-weight:bold;'>
                                        {CURRENCY_FLAGS.get(devise_to,'')} {result:,.2f}
                                    </div>
                                    <div style='color:#ccc; font-size:14px; margin-top:8px;'>
                                        {montant:,.2f} {devise_from} = {result:,.2f} {devise_to}
                                    </div>
                                    <div style='color:#555; font-size:12px; margin-top:5px;'>
                                        Taux : 1 {devise_from} = {rate:.4f} {devise_to}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error("Paire non disponible")
                except Exception as e:
                    st.error(f"Erreur : {e}")

        st.markdown("---")
        st.markdown("### 📋 TABLE DE CONVERSION RAPIDE")
        montant_table = st.number_input("Montant à convertir", value=100.0, key="table_amount")
        base_curr = st.selectbox("Devise de base", list(CURRENCY_FLAGS.keys()), key="table_base")

        if st.button("📊 GÉNÉRER LA TABLE", key="gen_table"):
            with st.spinner("Calcul en cours..."):
                table_rows = []
                for target in CURRENCY_FLAGS.keys():
                    if target == base_curr:
                        continue
                    try:
                        ticker_t = f"{base_curr}{target}=X"
                        rate = get_current_price(ticker_t)
                        if rate:
                            table_rows.append({
                                "Devise": f"{CURRENCY_FLAGS[target]} {target}",
                                "Taux": f"{rate:.4f}",
                                f"{montant_table:.0f} {base_curr} =": f"{montant_table * rate:,.2f} {target}"
                            })
                    except:
                        continue

                if table_rows:
                    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("⚠️ Données via Yahoo Finance. Délai possible de quelques minutes. Ne constitue pas un conseil financier.")
