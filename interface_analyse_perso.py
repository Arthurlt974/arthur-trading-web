"""
interface_analyse_perso.py
Module : MON ESPACE ANALYSE PERSONNEL
- Recherche actions / crypto
- Graphique TradingView interactif
- Indicateurs techniques (RSI, MACD, Bollinger)
- Notes texte libres
- Score / rating personnel (/10)
- Tags (watchlist, portefeuille, surveillance...)
- Alertes sur l'actif
- Historique de toutes les analyses
- Tableau de bord résumé
- Export PDF
- Partager une analyse
Stockage : Firebase Firestore (collection "analyses/{uid}/items")
"""

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import json
from fpdf import FPDF

# ══════════════════════════════════════════════
#  CONFIG FIREBASE (réutilise les secrets)
# ══════════════════════════════════════════════

FIREBASE_PROJECT_ID = st.secrets["FIREBASE_PROJECT_ID"]
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"

PLOTLY_BASE = dict(
    template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#0a0a0a",
    font=dict(color="#cccccc", family="Courier New"),
    legend=dict(bgcolor="rgba(0,0,0,0.7)", bordercolor="#333", borderwidth=1),
    margin=dict(l=50, r=20, t=50, b=40),
)

def _axis():
    return dict(gridcolor="#1a1a1a", showgrid=True, zeroline=False)

# ══════════════════════════════════════════════
#  HELPERS FIRESTORE
# ══════════════════════════════════════════════

def _headers():
    token = st.session_state.get("user_id_token", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def _to_fs(value):
    if isinstance(value, bool):   return {"booleanValue": value}
    if isinstance(value, int):    return {"integerValue": str(value)}
    if isinstance(value, float):  return {"doubleValue": value}
    if isinstance(value, str):    return {"stringValue": value}
    if isinstance(value, list):   return {"arrayValue": {"values": [_to_fs(v) for v in value]}}
    if isinstance(value, dict):   return {"mapValue": {"fields": {k: _to_fs(v) for k, v in value.items()}}}
    return {"stringValue": str(value)}

def _from_fs(field):
    if not field: return None
    if "stringValue"  in field: return field["stringValue"]
    if "integerValue" in field: return int(field["integerValue"])
    if "doubleValue"  in field: return float(field["doubleValue"])
    if "booleanValue" in field: return field["booleanValue"]
    if "arrayValue"   in field: return [_from_fs(v) for v in field["arrayValue"].get("values", [])]
    if "mapValue"     in field: return {k: _from_fs(v) for k, v in field["mapValue"].get("fields", {}).items()}
    return None

def _doc_to_dict(doc):
    fields = doc.get("fields", {})
    return {k: _from_fs(v) for k, v in fields.items()}

# ══════════════════════════════════════════════
#  CRUD ANALYSES — FIRESTORE
# ══════════════════════════════════════════════

def _collection_path(uid):
    return f"{FIRESTORE_URL}/analyses_{uid}"

def save_analyse(uid, analyse_id, data):
    """Sauvegarde / met à jour une analyse dans Firestore."""
    url = f"{_collection_path(uid)}/{analyse_id}"
    fields = {k: _to_fs(v) for k, v in data.items()}
    try:
        r = requests.patch(url, headers=_headers(), json={"fields": fields}, timeout=8)
        return r.status_code in [200, 201]
    except:
        return False

def load_analyses(uid):
    """Charge toutes les analyses de l'utilisateur."""
    url = f"{_collection_path(uid)}"
    try:
        r = requests.get(url, headers=_headers(), timeout=8)
        if r.status_code == 200:
            docs = r.json().get("documents", [])
            results = []
            for doc in docs:
                d = _doc_to_dict(doc)
                # Récupère l'ID depuis le nom du document
                d["_id"] = doc["name"].split("/")[-1]
                results.append(d)
            return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)
    except:
        pass
    return []

def delete_analyse(uid, analyse_id):
    """Supprime une analyse."""
    url = f"{_collection_path(uid)}/{analyse_id}"
    try:
        r = requests.delete(url, headers=_headers(), timeout=8)
        return r.status_code == 200
    except:
        return False

# ══════════════════════════════════════════════
#  RECHERCHE TICKER
# ══════════════════════════════════════════════

def rechercher_ticker(query):
    """Recherche un ticker via Yahoo Finance."""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=6"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5).json()
        quotes = r.get("quotes", [])
        return [(q["symbol"], q.get("longname") or q.get("shortname", q["symbol"]),
                 q.get("typeDisp", ""), q.get("exchDisp", ""))
                for q in quotes if "symbol" in q]
    except:
        return []

def get_tv_symbol(ticker):
    """Convertit un ticker Yahoo en symbole TradingView."""
    mapping = {
        "^FCHI": "EURONEXT:FCI", "^GSPC": "VANTAGE:SP500",
        "^IXIC": "NASDAQ:COMP",  "BTC-USD": "BINANCE:BTCUSDT",
        "ETH-USD": "BINANCE:ETHUSDT", "SOL-USD": "BINANCE:SOLUSDT",
        "BNB-USD": "BINANCE:BNBUSDT",
    }
    if ticker in mapping:
        return mapping[ticker]
    if "-USD" in ticker:
        base = ticker.replace("-USD", "")
        return f"BINANCE:{base}USDT"
    if ".PA" in ticker:
        return f"EURONEXT:{ticker.replace('.PA', '')}"
    if ".L" in ticker:
        return f"LSE:{ticker.replace('.L', '')}"
    return ticker

# ══════════════════════════════════════════════
#  INDICATEURS TECHNIQUES
# ══════════════════════════════════════════════

def calculer_indicateurs(df):
    """Calcule RSI, MACD, Bollinger Bands."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    loss = loss.replace(0, 0.0001)
    df["RSI"] = 100 - (100 / (1 + gain / loss))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]   = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_H"] = df["MACD"] - df["Signal"]

    # Bollinger Bands
    df["BB_MA"]    = df["Close"].rolling(20).mean()
    df["BB_std"]   = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["BB_MA"] + 2 * df["BB_std"]
    df["BB_Lower"] = df["BB_MA"] - 2 * df["BB_std"]

    # MA 50
    df["MA50"] = df["Close"].rolling(50).mean()

    return df.dropna()

def score_technique(df):
    """Calcule un score technique automatique /10."""
    if df.empty or len(df) < 2:
        return 5, "NEUTRE ⚖️", "#ff9800"

    last = df.iloc[-1]
    score = 5  # Base neutre

    rsi = float(last.get("RSI", 50))
    macd = float(last.get("MACD", 0))
    signal = float(last.get("Signal", 0))
    close = float(last.get("Close", 0))
    bb_upper = float(last.get("BB_Upper", close * 1.05))
    bb_lower = float(last.get("BB_Lower", close * 0.95))
    ma50 = float(last.get("MA50", close))

    # RSI
    if rsi < 30:   score += 2
    elif rsi < 45: score += 1
    elif rsi > 70: score -= 2
    elif rsi > 55: score -= 1

    # MACD
    if macd > signal: score += 1
    else:             score -= 1

    # Bollinger
    bb_pos = (close - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
    if bb_pos < 0.2:   score += 2
    elif bb_pos > 0.8: score -= 2

    # MA50
    if close > ma50: score += 1
    else:            score -= 1

    score = max(0, min(10, score))

    if score >= 8:   label, color = "HAUSSIER 🚀", "#00ff88"
    elif score >= 6: label, color = "LÉGÈREMENT HAUSSIER 📈", "#7fff00"
    elif score >= 5: label, color = "NEUTRE ⚖️", "#ff9800"
    elif score >= 3: label, color = "LÉGÈREMENT BAISSIER 📉", "#ff6347"
    else:            label, color = "BAISSIER 🔴", "#ff4b4b"

    return score, label, color

# ══════════════════════════════════════════════
#  GRAPHIQUE ANALYSE
# ══════════════════════════════════════════════

def afficher_graphique_analyse(ticker, period="6mo"):
    """Affiche le graphique technique complet."""
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            st.warning("Données indisponibles pour ce ticker.")
            return None

        df = calculer_indicateurs(df)
        if df.empty:
            st.warning("Pas assez de données pour calculer les indicateurs.")
            return None

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            vertical_spacing=0.04, row_heights=[0.6, 0.2, 0.2],
            subplot_titles=("Prix & Bollinger Bands", "RSI", "MACD")
        )

        # Chandeliers
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Prix",
            increasing_line_color="#00ff88", decreasing_line_color="#ff4b4b"
        ), row=1, col=1)

        # Bollinger
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
            line=dict(color="rgba(255,152,0,0.4)", dash="dash", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
            line=dict(color="rgba(255,152,0,0.4)", dash="dash", width=1),
            fill="tonexty", fillcolor="rgba(255,152,0,0.05)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_MA"], name="BB MA",
            line=dict(color="#ff9800", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50",
            line=dict(color="#4fc3f7", width=1.5)), row=1, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#9c27b0", width=2)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,75,75,0.5)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,255,136,0.5)", row=2, col=1)

        # MACD
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
            line=dict(color="#2196f3", width=2)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal",
            line=dict(color="#ff9800", width=2)), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_H"], name="Histogramme",
            marker_color=["#00ff88" if v >= 0 else "#ff4b4b" for v in df["MACD_H"]]), row=3, col=1)

        fig.update_layout(
            **PLOTLY_BASE, height=650,
            xaxis_rangeslider_visible=False,
            hovermode="x unified"
        )
        fig.update_xaxes(**_axis())
        fig.update_yaxes(**_axis())
        st.plotly_chart(fig, use_container_width=True)
        return df

    except Exception as e:
        st.error(f"Erreur graphique : {str(e)}")
        return None

# ══════════════════════════════════════════════
#  EXPORT PDF
# ══════════════════════════════════════════════

def _clean(text):
    """Nettoie le texte pour fpdf latin-1 : remplace les caractères unicode problématiques."""
    if not text:
        return ""
    replacements = {
        "—": "-", "–": "-", "’": "'", "‘": "'",
        "“": """, "”": """, "…": "...", "€": "EUR",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ô": "o", "ö": "o", "ù": "u", "û": "u",
        "ü": "u", "î": "i", "ï": "i", "ç": "c",
        "É": "E", "È": "E", "À": "A", "Ç": "C",
        "⚠": "!", "️": "", "📊": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")

def generer_pdf_analyse(analyse):
    """Génère un PDF d'une analyse personnelle."""
    pdf = FPDF()
    pdf.add_page()

    ticker = _clean(analyse.get("ticker", ""))
    nom    = _clean(analyse.get("nom", ""))

    # Header
    pdf.set_fill_color(10, 10, 10)
    pdf.rect(0, 0, 210, 40, "F")
    pdf.set_text_color(255, 152, 0)
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 15, "AM-TRADING | MON ANALYSE PERSONNELLE", ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Actif : {ticker} - {nom}", ln=True, align="C")
    pdf.ln(5)

    # Infos générales
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "INFORMATIONS GENERALES", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(90, 7, f"Date : {_clean(analyse.get('updated_at', 'N/A')[:10])}", ln=False)
    pdf.cell(90, 7, f"Type : {_clean(analyse.get('type_actif', 'N/A'))}", ln=True)
    pdf.cell(90, 7, f"Score personnel : {analyse.get('score_perso', 'N/A')}/10", ln=False)
    pdf.cell(90, 7, f"Score technique : {analyse.get('score_technique', 'N/A')}/10", ln=True)
    sentiment = _clean(analyse.get('sentiment_perso', 'NEUTRE'))
    pdf.cell(90, 7, f"Sentiment : {sentiment}", ln=False)
    tags_raw = analyse.get("tags", [])
    tags = _clean(", ".join(tags_raw) if tags_raw else "Aucun")
    pdf.cell(90, 7, f"Tags : {tags}", ln=True)
    pdf.ln(5)

    # Notes
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "MES NOTES D'ANALYSE", ln=True)
    pdf.set_font("Arial", "", 10)
    notes_clean = _clean(analyse.get("notes", "Aucune note."))
    pdf.multi_cell(0, 6, notes_clean)
    pdf.ln(5)

    # These
    if analyse.get("these"):
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, "THESE D'INVESTISSEMENT", ln=True)
        pdf.set_font("Arial", "", 10)
        these_clean = _clean(analyse.get("these", ""))
        pdf.multi_cell(0, 6, these_clean)
        pdf.ln(5)

    # Niveaux cles
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "NIVEAUX CLES", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(60, 7, f"Prix entree : {_clean(str(analyse.get('prix_entree', 'N/A')))}", ln=False)
    pdf.cell(60, 7, f"Stop Loss : {_clean(str(analyse.get('stop_loss', 'N/A')))}", ln=False)
    pdf.cell(60, 7, f"Take Profit : {_clean(str(analyse.get('take_profit', 'N/A')))}", ln=True)
    pdf.ln(8)

    # Footer
    pdf.set_text_color(150, 150, 150)
    pdf.set_font("Arial", "I", 8)
    date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    pdf.cell(0, 5, f"Rapport genere le {date_str} - AM-Trading Terminal", ln=True, align="C")
    pdf.cell(0, 5, "Ce document ne constitue pas un conseil financier.", ln=True, align="C")

    return bytes(pdf.output(dest="S"))

# ══════════════════════════════════════════════
#  INTERFACE PRINCIPALE
# ══════════════════════════════════════════════

def show_analyse_perso():
    uid       = st.session_state.get("user_uid", "")
    is_guest  = st.session_state.get("guest_mode", False)
    is_logged = st.session_state.get("user_logged_in", False)

    # ── Header ──────────────────────────────────────────────
    st.markdown("""
        <div style='text-align:center;padding:20px;
             background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #ff9800;border-radius:12px;margin-bottom:20px;'>
            <h2 style='color:#ff9800;margin:0;'>📊 MON ESPACE ANALYSE PERSONNEL</h2>
            <p style='color:#ffb84d;margin:5px 0 0;font-size:13px;'>
                Recherchez, analysez et sauvegardez vos analyses — Actions · Crypto · ETF · Forex
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Avertissement invité ─────────────────────────────────
    if is_guest:
        st.warning("👤 Mode invité — vos analyses ne seront pas sauvegardées. Créez un compte gratuit pour tout conserver.")

    # ── Tabs ────────────────────────────────────────────────
    tab_nouvelle, tab_historique, tab_dashboard = st.tabs([
        "🔍 NOUVELLE ANALYSE", "📚 MES ANALYSES", "📊 TABLEAU DE BORD"
    ])

    # ══════════════════════════════════════════════
    #  TAB 1 — NOUVELLE ANALYSE
    # ══════════════════════════════════════════════
    with tab_nouvelle:
        st.markdown("### 🔍 RECHERCHER UN ACTIF")

        col_search, col_btn = st.columns([4, 1])
        with col_search:
            query = st.text_input(
                "Nom ou ticker (ex: Apple, BTC, LVMH, AAPL, BTC-USD...)",
                key="analyse_search_query",
                placeholder="Tapez un nom ou ticker..."
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            search_btn = st.button("🔍 RECHERCHER", key="btn_search_actif", use_container_width=True)

        # Lancer la recherche — stocker en session_state pour persister entre reruns
        if search_btn and query:
            with st.spinner("Recherche en cours..."):
                resultats = rechercher_ticker(query)
            st.session_state["analyse_resultats_recherche"] = resultats
            st.session_state["analyse_query_en_cours"]      = query

        # Afficher les résultats (persistants entre reruns grâce au session_state)
        resultats_affiches = st.session_state.get("analyse_resultats_recherche", [])
        query_en_cours     = st.session_state.get("analyse_query_en_cours", "")

        if resultats_affiches:
            st.markdown("**Sélectionnez un actif :**")
            cols = st.columns(min(3, len(resultats_affiches)))
            for i, (symbol, name, type_actif, exchange) in enumerate(resultats_affiches[:6]):
                with cols[i % 3]:
                    suffix = "..." if len(name) > 30 else ""
                    display_label = f"{symbol} — {name[:30]}{suffix}"
                    if st.button(display_label, key=f"select_{symbol}_{i}", use_container_width=True):
                        st.session_state["analyse_ticker_selectionne"]   = symbol
                        st.session_state["analyse_nom_selectionne"]      = name
                        st.session_state["analyse_type_selectionne"]     = type_actif
                        st.session_state["analyse_resultats_recherche"]  = []
                        st.rerun()

        elif query_en_cours and search_btn and not resultats_affiches:
            st.error("Aucun résultat. Utilisez le ticker direct (ex: AAPL, BTC-USD).")
            if st.button(f"✅ Utiliser '{query_en_cours}' directement", key="use_direct_ticker"):
                st.session_state["analyse_ticker_selectionne"]  = query_en_cours.upper()
                st.session_state["analyse_nom_selectionne"]     = query_en_cours.upper()
                st.session_state["analyse_type_selectionne"]    = "Inconnu"
                st.session_state["analyse_resultats_recherche"] = []
                st.rerun()

        # ── Zone d'analyse ───────────────────────────────────
        ticker_sel = st.session_state.get("analyse_ticker_selectionne", "")
        nom_sel    = st.session_state.get("analyse_nom_selectionne", "")
        type_sel   = st.session_state.get("analyse_type_selectionne", "")

        if ticker_sel:
            st.markdown("---")
            st.markdown(f"### 📈 ANALYSE : {nom_sel} ({ticker_sel})")

            # Période graphique
            col_p1, col_p2, col_p3 = st.columns([2, 2, 4])
            with col_p1:
                period_choix = st.selectbox(
                    "Période", ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
                    index=2, key="analyse_period"
                )
            with col_p2:
                vue_choix = st.selectbox(
                    "Vue", ["Technique (local)", "TradingView (interactif)"],
                    key="analyse_vue"
                )

            # ── Vue TradingView ──
            if vue_choix == "TradingView (interactif)":
                tv_symbol = get_tv_symbol(ticker_sel)
                tv_html = f"""
                    <div id="tv_analyse" style="height:600px;"></div>
                    <script src="https://s3.tradingview.com/tv.js"></script>
                    <script>
                    new TradingView.widget({{
                        "autosize": true, "symbol": "{tv_symbol}",
                        "interval": "D", "timezone": "Europe/Paris",
                        "theme": "dark", "style": "1", "locale": "fr",
                        "toolbar_bg": "#000000", "enable_publishing": false,
                        "hide_side_toolbar": false, "allow_symbol_change": true,
                        "details": true, "hotlist": true, "calendar": true,
                        "container_id": "tv_analyse"
                    }});
                    </script>
                """
                components.html(tv_html, height=610)
                df_analyse = None
                score_auto, label_auto, color_auto = 5, "N/A (vue TradingView)", "#ff9800"
            else:
                # ── Vue technique locale ──
                with st.spinner("Chargement des données..."):
                    df_analyse = afficher_graphique_analyse(ticker_sel, period_choix)

                if df_analyse is not None and not df_analyse.empty:
                    score_auto, label_auto, color_auto = score_technique(df_analyse)

                    # KPIs techniques
                    last = df_analyse.iloc[-1]
                    prev = df_analyse.iloc[-2]
                    prix_actuel = float(last["Close"])
                    variation   = ((prix_actuel - float(prev["Close"])) / float(prev["Close"])) * 100
                    rsi_val     = float(last["RSI"])
                    macd_val    = float(last["MACD"])
                    signal_val  = float(last["Signal"])

                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("Prix", f"${prix_actuel:,.2f}", f"{variation:+.2f}%")
                    k2.metric("RSI", f"{rsi_val:.1f}",
                              "Survente" if rsi_val < 30 else ("Surachat" if rsi_val > 70 else "Neutre"))
                    k3.metric("MACD", f"{macd_val:.4f}",
                              "Haussier" if macd_val > signal_val else "Baissier")
                    k4.metric("Score Auto", f"{score_auto}/10")
                    k5.metric("Signal", label_auto)
                else:
                    score_auto, label_auto, color_auto = 5, "NEUTRE", "#ff9800"
                    df_analyse = None

            st.markdown("---")

            # ══════════════════════════════════════════════
            #  FORMULAIRE D'ANALYSE PERSONNELLE
            # ══════════════════════════════════════════════
            st.markdown("### ✍️ MON ANALYSE PERSONNELLE")

            col_form1, col_form2 = st.columns([3, 2])

            with col_form1:
                notes = st.text_area(
                    "📝 Mes notes",
                    height=150,
                    key="analyse_notes",
                    placeholder="Décrivez votre analyse, les raisons de votre intérêt, les risques identifiés..."
                )
                these = st.text_area(
                    "💡 Thèse d'investissement",
                    height=100,
                    key="analyse_these",
                    placeholder="Pourquoi investir (ou non) dans cet actif ? Catalyseurs, horizon de temps..."
                )

            with col_form2:
                score_perso = st.slider(
                    "⭐ Mon score personnel /10",
                    0, 10, 5, key="analyse_score_perso"
                )
                sentiment_perso = st.selectbox(
                    "📊 Mon sentiment",
                    ["TRÈS HAUSSIER 🚀", "HAUSSIER 📈", "NEUTRE ⚖️", "BAISSIER 📉", "TRÈS BAISSIER 🔴"],
                    index=2, key="analyse_sentiment"
                )
                tags_choix = st.multiselect(
                    "🏷️ Tags",
                    ["💼 Portefeuille", "👀 Surveillance", "⭐ Watchlist",
                     "🎯 Position ouverte", "✅ Analysé", "🔴 À éviter",
                     "📅 Long terme", "⚡ Court terme", "💰 Dividendes"],
                    key="analyse_tags"
                )

            # Niveaux de prix
            st.markdown("**📏 Niveaux de prix**")
            col_n1, col_n2, col_n3 = st.columns(3)
            with col_n1:
                prix_entree = st.text_input("💚 Prix d'entrée cible", key="analyse_entree", placeholder="Ex: 150.00")
            with col_n2:
                stop_loss = st.text_input("🔴 Stop Loss", key="analyse_sl", placeholder="Ex: 140.00")
            with col_n3:
                take_profit = st.text_input("🎯 Take Profit", key="analyse_tp", placeholder="Ex: 175.00")

            # ── Bouton sauvegarder ───────────────────────────
            st.markdown("---")
            col_save1, col_save2, col_save3 = st.columns([2, 2, 1])

            with col_save1:
                if st.button("💾 SAUVEGARDER L'ANALYSE", key="btn_save_analyse",
                             use_container_width=True, type="primary"):
                    if is_guest:
                        st.error("❌ Créez un compte gratuit pour sauvegarder vos analyses.")
                    else:
                        analyse_data = {
                            "ticker":          ticker_sel,
                            "nom":             nom_sel,
                            "type_actif":      type_sel,
                            "notes":           notes,
                            "these":           these,
                            "score_perso":     score_perso,
                            "score_technique": score_auto,
                            "sentiment_perso": sentiment_perso,
                            "tags":            tags_choix,
                            "prix_entree":     prix_entree,
                            "stop_loss":       stop_loss,
                            "take_profit":     take_profit,
                            "period":          period_choix,
                            "updated_at":      datetime.now().isoformat(),
                            "created_at":      datetime.now().isoformat(),
                        }
                        analyse_id = f"{ticker_sel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        with st.spinner("Sauvegarde..."):
                            ok = save_analyse(uid, analyse_id, analyse_data)
                        if ok:
                            st.success(f"✅ Analyse {ticker_sel} sauvegardée !")
                            st.balloons()
                        else:
                            st.error("❌ Erreur lors de la sauvegarde. Réessayez.")

            with col_save2:
                # Export PDF direct
                if st.button("📥 EXPORTER EN PDF", key="btn_pdf_analyse", use_container_width=True):
                    analyse_temp = {
                        "ticker": ticker_sel, "nom": nom_sel, "type_actif": type_sel,
                        "notes": notes, "these": these, "score_perso": score_perso,
                        "score_technique": score_auto, "sentiment_perso": sentiment_perso,
                        "tags": tags_choix, "prix_entree": prix_entree,
                        "stop_loss": stop_loss, "take_profit": take_profit,
                        "updated_at": datetime.now().isoformat(),
                    }
                    pdf_bytes = generer_pdf_analyse(analyse_temp)
                    st.download_button(
                        label="📄 Télécharger le PDF",
                        data=pdf_bytes,
                        file_name=f"Analyse_{ticker_sel}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        key="dl_pdf_analyse"
                    )

    # ══════════════════════════════════════════════
    #  TAB 2 — HISTORIQUE DES ANALYSES
    # ══════════════════════════════════════════════
    with tab_historique:
        st.markdown("### 📚 MES ANALYSES SAUVEGARDÉES")

        if is_guest:
            st.info("👤 Mode invité — créez un compte gratuit pour accéder à votre historique.")
            st.stop()

        col_refresh, col_filtre = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Actualiser", key="btn_refresh_analyses"):
                st.rerun()
        with col_filtre:
            filtre_tag = st.selectbox(
                "Filtrer par tag",
                ["Tous", "💼 Portefeuille", "👀 Surveillance", "⭐ Watchlist",
                 "🎯 Position ouverte", "✅ Analysé", "🔴 À éviter"],
                key="filtre_historique"
            )

        with st.spinner("Chargement de vos analyses..."):
            analyses = load_analyses(uid)

        if not analyses:
            st.info("📭 Aucune analyse sauvegardée. Créez votre première analyse dans l'onglet 🔍.")
            st.stop()

        # Filtrage
        if filtre_tag != "Tous":
            analyses = [a for a in analyses if filtre_tag in a.get("tags", [])]

        st.caption(f"{len(analyses)} analyse(s) trouvée(s)")

        for analyse in analyses:
            ticker   = analyse.get("ticker", "?")
            nom      = analyse.get("nom", ticker)
            score_p  = analyse.get("score_perso", 0)
            score_t  = analyse.get("score_technique", 0)
            sentiment= analyse.get("sentiment_perso", "NEUTRE")
            tags     = analyse.get("tags", [])
            date_upd = analyse.get("updated_at", "")[:10]
            notes    = analyse.get("notes", "")
            these    = analyse.get("these", "")
            a_id     = analyse.get("_id", "")

            # Couleur selon sentiment
            if "HAUSSIER" in sentiment and "TRÈS" in sentiment: card_color = "#00ff88"
            elif "HAUSSIER" in sentiment: card_color = "#7fff00"
            elif "BAISSIER" in sentiment and "TRÈS" in sentiment: card_color = "#ff4b4b"
            elif "BAISSIER" in sentiment: card_color = "#ff6347"
            else: card_color = "#ff9800"

            with st.expander(f"**{ticker}** — {nom[:30]} | Score: {score_p}/10 | {sentiment} | {date_upd}"):
                col_a1, col_a2, col_a3 = st.columns([2, 2, 1])

                with col_a1:
                    st.markdown(f"**📝 Notes :**")
                    st.write(notes if notes else "_Aucune note_")
                    if these:
                        st.markdown(f"**💡 Thèse :**")
                        st.write(these)

                with col_a2:
                    st.markdown("**📊 Scores & Niveaux :**")
                    st.markdown(f"- Score personnel : **{score_p}/10**")
                    st.markdown(f"- Score technique auto : **{score_t}/10**")
                    st.markdown(f"- Sentiment : **{sentiment}**")
                    if analyse.get("prix_entree"):
                        st.markdown(f"- 💚 Entrée : **{analyse.get('prix_entree')}**")
                    if analyse.get("stop_loss"):
                        st.markdown(f"- 🔴 Stop : **{analyse.get('stop_loss')}**")
                    if analyse.get("take_profit"):
                        st.markdown(f"- 🎯 TP : **{analyse.get('take_profit')}**")
                    if tags:
                        st.markdown("**🏷️ Tags :** " + " · ".join(tags))

                with col_a3:
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Recharger dans l'éditeur
                    if st.button("✏️ Modifier", key=f"edit_{a_id}", use_container_width=True):
                        st.session_state["analyse_ticker_selectionne"] = ticker
                        st.session_state["analyse_nom_selectionne"]    = nom
                        st.session_state["analyse_type_selectionne"]   = analyse.get("type_actif", "")
                        st.info("Retournez dans l'onglet 🔍 pour modifier.")

                    # Export PDF
                    pdf_bytes = generer_pdf_analyse(analyse)
                    st.download_button(
                        "📥 PDF", data=pdf_bytes,
                        file_name=f"Analyse_{ticker}_{date_upd}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{a_id}",
                        use_container_width=True
                    )

                    # Partager
                    lien_partage = f"Analyse {ticker} ({date_upd}) — Score: {score_p}/10 — {sentiment}\n\nVia AM-Trading Terminal"
                    st.text_area("📤 Partager", value=lien_partage, height=80, key=f"share_{a_id}")

                    # Supprimer
                    if st.button("🗑️ Supprimer", key=f"del_{a_id}", use_container_width=True):
                        if delete_analyse(uid, a_id):
                            st.success("✅ Analyse supprimée.")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression.")

    # ══════════════════════════════════════════════
    #  TAB 3 — TABLEAU DE BORD
    # ══════════════════════════════════════════════
    with tab_dashboard:
        st.markdown("### 📊 TABLEAU DE BORD DE MES ANALYSES")

        if is_guest:
            st.info("👤 Mode invité — créez un compte gratuit pour accéder au tableau de bord.")
            st.stop()

        with st.spinner("Chargement..."):
            analyses = load_analyses(uid)

        if not analyses:
            st.info("📭 Aucune analyse. Commencez par analyser un actif !")
            st.stop()

        # ── KPIs ────────────────────────────────────────────
        total = len(analyses)
        score_moyen = sum(a.get("score_perso", 0) for a in analyses) / total if total else 0
        haussiers   = len([a for a in analyses if "HAUSSIER" in a.get("sentiment_perso", "")])
        baissiers   = len([a for a in analyses if "BAISSIER" in a.get("sentiment_perso", "")])
        tags_flat   = [t for a in analyses for t in a.get("tags", [])]
        en_portfolio= len([a for a in analyses if "💼 Portefeuille" in a.get("tags", [])])

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total analyses", total)
        k2.metric("Score moyen", f"{score_moyen:.1f}/10")
        k3.metric("Haussiers 📈", haussiers)
        k4.metric("Baissiers 📉", baissiers)
        k5.metric("En portefeuille 💼", en_portfolio)

        st.markdown("---")

        col_dash1, col_dash2 = st.columns(2)

        with col_dash1:
            # Répartition sentiment
            sentiments = {}
            for a in analyses:
                s = a.get("sentiment_perso", "NEUTRE ⚖️")
                sentiments[s] = sentiments.get(s, 0) + 1

            fig_sent = go.Figure(go.Pie(
                labels=list(sentiments.keys()),
                values=list(sentiments.values()),
                marker_colors=["#00ff88", "#7fff00", "#ff9800", "#ff6347", "#ff4b4b"],
                hole=0.5
            ))
            fig_sent.update_layout(
                **{k: v for k, v in PLOTLY_BASE.items() if k != "margin"},
                margin=dict(l=10, r=10, t=40, b=10),
                height=300,
                title=dict(text="Répartition Sentiments", font=dict(color="#ff9800"))
            )
            st.plotly_chart(fig_sent, use_container_width=True)

        with col_dash2:
            # Scores par actif
            tickers_scores = [(a.get("ticker", "?"), a.get("score_perso", 0)) for a in analyses[:10]]
            tickers_scores.sort(key=lambda x: x[1], reverse=True)

            fig_scores = go.Figure(go.Bar(
                x=[t[0] for t in tickers_scores],
                y=[t[1] for t in tickers_scores],
                marker_color=["#00ff88" if s >= 7 else "#ff9800" if s >= 5 else "#ff4b4b"
                              for _, s in tickers_scores],
                text=[f"{s}/10" for _, s in tickers_scores],
                textposition="auto"
            ))
            fig_scores.update_layout(
                **PLOTLY_BASE, height=300,
                title=dict(text="Mes Scores par Actif", font=dict(color="#ff9800")),
                xaxis=_axis(), yaxis=dict(**_axis(), range=[0, 10])
            )
            st.plotly_chart(fig_scores, use_container_width=True)

        # ── Tags les plus utilisés ───────────────────────────
        if tags_flat:
            st.markdown("### 🏷️ MES TAGS LES PLUS UTILISÉS")
            tags_count = {}
            for t in tags_flat:
                tags_count[t] = tags_count.get(t, 0) + 1
            tags_sorted = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)

            cols_tags = st.columns(min(5, len(tags_sorted)))
            for i, (tag, count) in enumerate(tags_sorted[:5]):
                with cols_tags[i]:
                    st.metric(tag, count)

        st.markdown("---")

        # ── Tableau récapitulatif ────────────────────────────
        st.markdown("### 📋 RÉCAPITULATIF")
        df_recap = pd.DataFrame([{
            "Ticker":    a.get("ticker", "?"),
            "Nom":       a.get("nom", "?")[:25],
            "Score":     f"{a.get('score_perso', 0)}/10",
            "Technique": f"{a.get('score_technique', 0)}/10",
            "Sentiment": a.get("sentiment_perso", "N/A"),
            "Entrée":    a.get("prix_entree", "—"),
            "SL":        a.get("stop_loss", "—"),
            "TP":        a.get("take_profit", "—"),
            "Date":      a.get("updated_at", "")[:10],
        } for a in analyses])

        st.dataframe(df_recap, use_container_width=True, hide_index=True)

        # Export tableau complet
        csv = df_recap.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Exporter en CSV",
            data=csv,
            file_name=f"mes_analyses_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="export_csv_dashboard"
        )
