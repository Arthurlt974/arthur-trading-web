import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import numpy as np

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="AM-Trading | Bloomberg Terminal", layout="wide")

# --- INITIALISATION DU WORKSPACE (FÊNETRES MULTIPLES) ---
if "workspace" not in st.session_state:
    st.session_state.workspace = []

# --- STYLE BLOOMBERG TERMINAL (DARK HEADER) ---
st.markdown("""
    <style>
        /* Supprime la ligne blanche/grise en haut et met le header en noir */
        header[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
            color: #ff9800 !important;
        }
        
        /* Supprime la bordure décorative de Streamlit en haut */
        .stApp [data-testid="stDecoration"] {
            display: none;
        }

        /* Fond de l'application et texte de base en orange */
        .stApp { 
            background-color: #0d0d0d; 
            color: #ff9800 !important; 
        }
        
        /* Barre latérale */
        [data-testid="stSidebar"] { 
            background-color: #161616; 
            border-right: 1px solid #333; 
        }
        
        /* Tous les textes en orange */
        h1, h2, h3, p, span, label, div, .stMarkdown { 
            color: #ff9800 !important; 
            text-transform: uppercase; 
        }

        /* Metrics labels */
        [data-testid="stMetricLabel"] {
            color: #ff9800 !important;
        }

        /* Onglets */
        button[data-baseweb="tab"] p {
            color: #ff9800 !important;
        }
        
        /* Boutons */
        .stButton>button {
            background-color: #1a1a1a; 
            color: #ff9800; 
            border: 1px solid #ff9800;
            border-radius: 4px; 
            font-weight: bold; 
            width: 100%;
        }
        .stButton>button:hover { 
            background-color: #ff9800; 
            color: #000; 
        }
    </style>
""", unsafe_allow_html=True)


# --- SYSTÈME DE MOT DE PASSE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.markdown("### [ SECURITY ] TERMINAL ACCESS REQUIRED")
    pwd = st.text_input("ENTER ACCESS CODE :", type="password")
    if st.button("EXECUTE LOGIN"):
        if pwd == "1234":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("!! ACCESS DENIED - INVALID CODE")
    return False

if not check_password():
    st.stop()

st_autorefresh(interval=30000, key="global_refresh")

# --- FONCTION HORLOGE BLOOMBERG (JS) ---
def afficher_horloge_temps_reel():
    horloge_html = """
        <div style="border: 1px solid #ff9800; padding: 10px; background: #000; text-align: center; font-family: monospace;">
            <div style="color: #ff9800; font-size: 12px;">SYSTEM TIME / REUNION UTC+4</div>
            <div id="clock" style="font-size: 32px; color: #00ff00; font-weight: bold;">--:--:--</div>
            <div style="color: #444; font-size: 10px; margin-top:5px;">REAL-TIME FINANCIAL DATA FEED</div>
        </div>
        <script>
            function updateClock() {
                const now = new Date();
                const offset = 4; // UTC+4 Réunion
                const localTime = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + (offset * 3600000));
                const h = String(localTime.getHours()).padStart(2, '0');
                const m = String(localTime.getMinutes()).padStart(2, '0');
                const s = String(localTime.getSeconds()).padStart(2, '0');
                document.getElementById('clock').innerText = h + ":" + m + ":" + s;
            }
            setInterval(updateClock, 1000);
            updateClock();
        </script>
    """
    components.html(horloge_html, height=120)

# --- FONCTION GRAPHIQUE TRADINGVIEW PRO ---
def afficher_graphique_pro(symbol, height=600):
    traduction_symbols = {
        "^FCHI": "CAC40",
        "^GSPC": "VANTAGE:SP500",
        "^IXIC": "NASDAQ",
        "BTC-USD": "BINANCE:BTCUSDT"
    }
    tv_symbol = traduction_symbols.get(symbol, symbol.replace(".PA", ""))
    if ".PA" in symbol and symbol not in traduction_symbols:
        tv_symbol = f"EURONEXT:{tv_symbol}"

    tradingview_html = f"""
        <div id="tradingview_chart" style="height:{height}px;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
          "autosize": true,
          "symbol": "{tv_symbol}",
          "interval": "D",
          "timezone": "Europe/Paris",
          "theme": "dark",
          "style": "1",
          "locale": "fr",
          "toolbar_bg": "#000000",
          "enable_publishing": false,
          "hide_side_toolbar": false,
          "allow_symbol_change": true,
          "details": true,
          "container_id": "tradingview_chart"
        }});
        </script>
    """
    components.html(tradingview_html, height=height + 10)

# --- FONCTIONS DE MISE EN CACHE ---
@st.cache_data(ttl=5) 
def get_ticker_info(ticker):
    try:
        data = yf.Ticker(ticker)
        return data.info
    except: return None

@st.cache_data(ttl=5)
def get_ticker_history(ticker, period="2d"):
    try:
        data = yf.Ticker(ticker)
        return data.history(period=period)
    except: return pd.DataFrame()

def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

# --- FONCTIONS DE CALCUL POUR LE FEAR & GREED ---
def calculer_score_sentiment(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1y")
        if len(data) < 200: return 50, "NEUTRE", "gray"
        prix_actuel = data['Close'].iloc[-1]
        ma200 = data['Close'].rolling(window=200).mean().iloc[-1]
        ratio = (prix_actuel / ma200) - 1
        score = 50 + (ratio * 300) 
        score = max(10, min(90, score))
        if score > 70: return score, "EXTRÊME EUPHORIE 🚀", "#00ffad"
        elif score > 55: return score, "OPTIMISME 📈", "#2ecc71"
        elif score > 45: return score, "NEUTRE ⚖️", "#f1c40f"
        elif score > 30: return score, "PEUR 📉", "#e67e22"
        else: return score, "PANIQUE TOTALE 💀", "#e74c3c"
    except: return 50, "ERREUR", "gray"

def afficher_jauge_pro(score, titre, couleur, sentiment):
    import plotly.graph_objects as go
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        number = {'font': {'size': 30, 'color': "white"}, 'suffix': "%"},
        title = {'text': f"<b>{titre}</b><br><span style='color:{couleur}; font-size:14px;'>{sentiment}</span>", 
                 'font': {'size': 16, 'color': "white"}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': couleur, 'thickness': 0.3},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 30], 'color': "rgba(231, 76, 60, 0.2)"},
                {'range': [30, 45], 'color': "rgba(230, 126, 34, 0.2)"},
                {'range': [45, 55], 'color': "rgba(241, 196, 15, 0.2)"},
                {'range': [55, 70], 'color': "rgba(46, 204, 113, 0.2)"},
                {'range': [70, 100], 'color': "rgba(0, 255, 173, 0.2)"}
            ],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"}, height=300, margin=dict(l=25, r=25, t=100, b=20))
    return fig


# --- NAVIGATION ---
st.sidebar.title("📟 AM-TERMINAL")
outil = st.sidebar.radio("SELECT MODULE :", [
    "ANALYSEUR PRO", 
    "MODE DUEL", 
    "MARKET MONITOR", 
    "DAILY BRIEF", 
    "CALENDRIER ÉCO",
    "Fear and Gread Index",
    "INTERETS COMPOSES",
    "CRYPTO WALLET"
])

# ==========================================
# OUTIL 1 : ANALYSEUR PRO
# ==========================================
if outil == "ANALYSEUR PRO":
    nom_entree = st.sidebar.text_input("TICKER SEARCH", value="NVIDIA")
    ticker = trouver_ticker(nom_entree)
    info = get_ticker_info(ticker)

    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 0)
        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare') or 0
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 else 0

        st.title(f"» {nom} // {ticker}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LAST PRICE", f"{prix:.2f} {devise}")
        c2.metric("GRAHAM VAL", f"{val_theorique:.2f} {devise}")
        c3.metric("POTENTIAL", f"{marge_pourcent:+.2f}%")
        c4.metric("SECTOR", secteur)

        st.markdown("---")
        st.subheader("» ADVANCED TECHNICAL CHART")
        afficher_graphique_pro(ticker, height=650)

        st.markdown("---")
        st.subheader("» FINANCIAL DATA")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.write(f"**EPS (BPA) :** {bpa:.2f} {devise}")
            st.write(f"**P/E RATIO :** {per:.2f}")
        with f2:
            st.write(f"**DEBT/EQUITY :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**DIV. YIELD :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
        with f3:
            st.write(f"**PAYOUT RATIO :** {payout:.2f} %")
            st.write(f"**CASH/SHARE :** {cash_action:.2f} {devise}")

        st.markdown("---")
        st.subheader("» QUALITY SCORE (20 MAX)")
        score = 0
        positifs, negatifs = [], []
        if bpa > 0:
            if per < 12: score += 5; positifs.append("» ATTRACTIVE P/E [+5]")
            elif per < 20: score += 4; positifs.append("» FAIR VALUATION [+4]")
            else: score += 1; positifs.append("• HIGH P/E [+1]")
        else: score -= 5; negatifs.append("!! NEGATIVE EPS [-5]")
        
        if dette_equity is not None:
            if dette_equity < 50: score += 4; positifs.append("» STRONG BALANCE SHEET [+4]")
            elif dette_equity < 100: score += 3; positifs.append("» DEBT UNDER CONTROL [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("!! HIGH LEVERAGE [-4]")
            
        if 10 < payout <= 80: score += 4; positifs.append("» SUSTAINABLE DIVIDEND [+4]")
        elif payout > 95: score -= 4; negatifs.append("!! PAYOUT RISK [-4]")
        if marge_pourcent > 30: score += 5; positifs.append("» GRAHAM DISCOUNT [+5]")

        score_f = min(20, max(0, score))
        cs, cd = st.columns([1, 2])
        with cs:
            st.write(f"## SCORE : {score_f}/20")
            st.progress(score_f / 20)
        with cd:
            for p in positifs: 
                st.markdown(f'<div style="background:#002b00; color:#00ff00; border-left: 4px solid #00ff00; padding:10px; margin-bottom:5px;">{p}</div>', unsafe_allow_html=True)
            for n in negatifs: 
                st.markdown(f'<div style="background:#2b0000; color:#ff0000; border-left: 4px solid #ff0000; padding:10px; margin-bottom:5px;">{n}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(f"» NEWS FEED : {nom}")
        
        tab_action_24h, tab_action_archive = st.tabs(["● LIVE FEED (24H)", "○ HISTORICAL (7D)"])
        search_term = nom.replace(" ", "+")
        url_rss = f"https://news.google.com/rss/search?q={search_term}+(site:investing.com+OR+bourse+OR+stock)&hl=fr&gl=FR&ceid=FR:fr"
        
        try:
            import time
            flux = feedparser.parse(url_rss)
            maintenant = time.time()
            secondes_par_jour = 24 * 3600
            articles = sorted(flux.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)

            with tab_action_24h:
                trouve_24h = False
                for entry in articles:
                    pub_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else maintenant
                    if (maintenant - pub_time) < secondes_par_jour:
                        trouve_24h = True
                        clean_title = entry.title.split(' - ')[0]
                        source = entry.source.get('title', 'Finance')
                        prefix = "■ INV |" if "investing" in source.lower() else "»"
                        with st.expander(f"{prefix} {clean_title}"):
                            st.write(f"**SOURCE :** {source}")
                            st.caption(f"🕒 TIMESTAMP : {entry.published}")
                            st.link_button("OPEN ARTICLE", entry.link)
                if not trouve_24h:
                    st.info("NO RECENT NEWS IN THE LAST 24H.")

            with tab_action_archive:
                for entry in articles[:12]:
                    clean_title = entry.title.split(' - ')[0]
                    source = entry.source.get('title', 'Finance')
                    prefix = "■ INV |" if "investing" in source.lower() else "•"
                    with st.expander(f"{prefix} {clean_title}"):
                        st.write(f"**SOURCE :** {source}")
                        st.caption(f"📅 DATE : {entry.published}")
                        st.link_button("VIEW ARCHIVE", entry.link)
        except Exception:
            st.error("ERROR FETCHING NEWS FEED.")

# ==========================================
# OUTIL 2 : MODE DUEL (VERSION AMÉLIORÉE)
# ==========================================
elif outil == "MODE DUEL":
    st.title("⚔️ EQUITY DUEL : PRO COMPARISON")
    st.write("Comparez deux actifs pour identifier le meilleur point d'entrée.")

    c1, c2 = st.columns(2)
    with c1:
        t1 = st.text_input("TICKER 1", value="MC.PA").upper()
    with c2:
        t2 = st.text_input("TICKER 2", value="RMS.PA").upper()

    if st.button("RUN DEEP ANALYSIS"):
        def get_full_data(t):
            ticker_id = trouver_ticker(t)
            i = get_ticker_info(ticker_id)
            hist = get_ticker_history(ticker_id, period="1y")
            
            p = i.get('currentPrice') or i.get('regularMarketPrice') or 1
            b = i.get('trailingEps') or 0
            v = (max(0, b) * (8.5 + 2 * 7) * 4.4) / 3.5 # Formule Graham
            
            return {
                "nom": i.get('shortName', t),
                "prix": p,
                "valeur": v,
                "yield": (i.get('dividendYield', 0) or 0) * 100,
                "per": i.get('trailingPE', 0),
                "marge": (i.get('profitMargins', 0) or 0) * 100,
                "cap": i.get('marketCap', 0),
                "hist": hist,
                "potential": ((v - p) / p) * 100 if p > 0 else 0
            }

        try:
            with st.spinner('Extracting Market Data...'):
                d1 = get_full_data(t1)
                d2 = get_full_data(t2)

            # --- HEADER DE COMPARAISON ---
            col_a, col_vs, col_b = st.columns([2, 1, 2])
            with col_a:
                st.markdown(f"### {d1['nom']}")
                st.markdown(f"<h1 style='color:#00ff00; margin:0;'>{d1['prix']:.2f}</h1>", unsafe_allow_html=True)
            with col_vs:
                st.markdown("<h1 style='text-align:center; color:#ff9800; padding-top:20px;'>VS</h1>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"### {d2['nom']}")
                st.markdown(f"<h1 style='color:#00ff00; margin:0; text-align:right;'>{d2['prix']:.2f}</h1>", unsafe_allow_html=True)

            st.markdown("---")

            # --- TABLEAU DE COMPARAISON TECHNIQUE ---
            data_comp = {
                "INDICATOR": ["GRAHAM VALUE", "UPSIDE POTENTIAL", "P/E RATIO", "DIV. YIELD", "PROFIT MARGIN"],
                d1['nom']: [f"{d1['valeur']:.2f}", f"{d1['potential']:+.2f}%", f"{d1['per']:.2f}", f"{d1['yield']:.2f}%", f"{d1['marge']:.2f}%"],
                d2['nom']: [f"{d2['valeur']:.2f}", f"{d2['potential']:+.2f}%", f"{d2['per']:.2f}", f"{d2['yield']:.2f}%", f"{d2['marge']:.2f}%"]
            }
            st.table(pd.DataFrame(data_comp))

            # --- ANALYSE GRAPHIQUE ---
            st.subheader("» 1 YEAR PERFORMANCE CORRELATION")
            fig = go.Figure()
            # Normalisation à 100 pour comparer la croissance (%)
            for d in [d1, d2]:
                if not d['hist'].empty:
                    norm_price = (d['hist']['Close'] / d['hist']['Close'].iloc[0]) * 100
                    fig.add_trace(go.Scatter(x=d['hist'].index, y=norm_price, name=d['nom']))

            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ff9800"), xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333", title="Base 100"),
                height=400, margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- VERDICT FINAL ---
            st.markdown("---")
            winner = d1['nom'] if d1['potential'] > d2['potential'] else d2['nom']
            st.markdown(f"""
                <div style="background:#1a1a1a; border: 2px solid #ff9800; padding:20px; border-radius:10px; text-align:center;">
                    <h2 style="color:#ff9800; margin:0;">🏆 ALPHA PICK : {winner}</h2>
                    <p style="color:#00ff00; margin:0;">Basé sur le potentiel de décote Graham et les marges opérationnelles.</p>
                </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"ENGINE ERROR : {str(e)}")
# ==========================================
# OUTIL 3 : MARKET MONITOR
# ==========================================
elif outil == "MARKET MONITOR":
    st.title("» GLOBAL MARKET MONITOR")
    afficher_horloge_temps_reel()

    st.markdown("### » EXCHANGE STATUS")
    h = (datetime.utcnow() + timedelta(hours=4)).hour
    
    data_horaires = {
        "SESSION": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "OPEN (REU)": ["05:30", "12:00", "18:30"],
        "CLOSE (REU)": ["12:00", "20:30", "01:00"],
        "STATUS": [
            "● OPEN" if 5 <= h < 12 else "○ CLOSED", 
            "● OPEN" if 12 <= h < 20 else "○ CLOSED", 
            "● OPEN" if (h >= 18 or h < 1) else "○ CLOSED"
        ]
    }
    st.table(pd.DataFrame(data_horaires))

    st.markdown("---")
    st.subheader("» MARKET DRIVERS")
    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    cols = st.columns(len(indices))
    if 'index_selectionne' not in st.session_state: st.session_state.index_selectionne = "^FCHI"

    for i, (tk, nom) in enumerate(indices.items()):
        try:
            hist_idx = get_ticker_history(tk)
            if not hist_idx.empty:
                val_actuelle, val_prec = hist_idx['Close'].iloc[-1], hist_idx['Close'].iloc[-2]
                variation = ((val_actuelle - val_prec) / val_prec) * 100
                cols[i].metric(nom, f"{val_actuelle:,.2f}", f"{variation:+.2f}%")
                if cols[i].button(f"LOAD {nom}", key=f"btn_{tk}"):
                    st.session_state.index_selectionne = tk
        except: pass

    st.markdown("---")
    nom_sel = indices.get(st.session_state.index_selectionne, "Indice")
    st.subheader(f"» ADVANCED CHART : {nom_sel}")
    afficher_graphique_pro(st.session_state.index_selectionne, height=700)

# ==========================================
# OUTIL 4 : DAILY BRIEF
# ==========================================
elif outil == "DAILY BRIEF":
    st.title("» DAILY BRIEFING")
    st.markdown("---")
    tab_eco, tab_tech, tab_quotidien = st.tabs(["🌍 GLOBAL MACRO", "⚡ TECH & CRYPTO", "📅 DAILY (BOURSORAMA)"])

    def afficher_flux_daily(url, filtre_boursorama_24h=False):
        try:
            import time
            flux = feedparser.parse(url)
            if not flux.entries:
                st.info("NO DATA FOUND.")
                return
            maintenant = time.time()
            secondes_par_jour = 24 * 3600
            articles = sorted(flux.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)
            trouve = False
            for entry in articles[:15]:
                pub_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else maintenant
                if not filtre_boursorama_24h or (maintenant - pub_time) < secondes_par_jour:
                    trouve = True
                    clean_title = entry.title.replace(" - Boursorama", "").split(" - ")[0]
                    with st.expander(f"» {clean_title}"):
                        st.write(f"**SOURCE :** Boursorama / Google News")
                        if 'published' in entry:
                            st.caption(f"🕒 TIMESTAMP : {entry.published}")
                        st.link_button("READ FULL ARTICLE", entry.link)
            if not trouve and filtre_boursorama_24h:
                st.warning("AWAITING FRESH DATA FROM BOURSORAMA...")
        except Exception:
            st.error("FEED ERROR.")

    with tab_eco:
        afficher_flux_daily("https://news.google.com/rss/search?q=bourse+economie+mondiale&hl=fr&gl=FR&ceid=FR:fr")
    with tab_tech:
        afficher_flux_daily("https://news.google.com/rss/search?q=crypto+nasdaq+nvidia&hl=fr&gl=FR&ceid=FR:fr")
    with tab_quotidien:
        st.subheader("» BOURSORAMA DIRECT (24H)")
        afficher_flux_daily("https://news.google.com/rss/search?q=site:boursorama.com&hl=fr&gl=FR&ceid=FR:fr", filtre_boursorama_24h=True)

# ==========================================
# OUTIL 5 : CALENDRIER ÉCONOMIQUE
# ==========================================
elif outil == "CALENDRIER ÉCO":
    st.title("» ECONOMIC CALENDAR")
    st.info("REAL-TIME GLOBAL MACRO EVENTS.")
    calendrier_tv = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {
      "colorTheme": "dark",
      "isMaximized": true,
      "width": "100%",
      "height": "800",
      "locale": "fr",
      "importanceFilter": "-1,0,1",
      "countryFilter": "fr,us,eu,gb,jp"
      }
      </script>
    </div>
    """
    components.html(calendrier_tv, height=800, scrolling=True)

# ==========================================
# OUTIL 6 : FEAR & GREED INDEX
# ==========================================
elif outil == "Fear and Gread Index":
    st.title("🌡️ Market Sentiment Index")
    st.write("Analyse de la force du marché par rapport à sa moyenne long terme (MA200).")
    
    marches = {
        "^GSPC": "🇺🇸 USA (S&P 500)",
        "^FCHI": "🇫🇷 France (CAC 40)",
        "^HSI":  "🇨🇳 Chine (Hang Seng)",
        "BTC-USD": "₿ Bitcoin",
        "GC=F": "🟡 Or (Métal Précieux)"
    }
    
    # Affichage en grille
    c1, c2 = st.columns(2)
    items = list(marches.items())
    
    for i in range(len(items)):
        ticker, nom = items[i]
        score, label, couleur = calculer_score_sentiment(ticker)
        fig = afficher_jauge_pro(score, nom, couleur, label)
        
        if i % 2 == 0:
            c1.plotly_chart(fig, use_container_width=True)
        else:
            c2.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.info("💡 **Conseil** : La 'Panique' (0-30%) indique souvent une opportunité d'achat, tandis que l'Euphorie (70-100%) suggère une bulle potentielle.")

# ==========================================
# NOUVEL OUTIL : SIMULATEUR D'INTÉRÊTS COMPOSÉS
# ==========================================
elif outil == "INTERETS COMPOSES":
    st.title("💰 SIMULATEUR D'INTÉRÊTS COMPOSÉS")
    st.write("Visualisez la puissance de la capitalisation sur le long terme.")

    # Zone de saisie
    col1, col2 = st.columns(2)
    with col1:
        cap_depart = st.number_input("Capital de départ (€)", value=1000.0, step=100.0)
        v_mensuel = st.number_input("Versement mensuel (€)", value=100.0, step=10.0)
    with col2:
        rendement = st.number_input("Taux annuel espéré (%)", value=8.0, step=0.5) / 100
        duree = st.number_input("Durée (années)", value=10, step=1)

    # Calculs
    total = cap_depart
    total_investi = cap_depart
    historique = []

    for i in range(1, int(duree) + 1):
        for mois in range(12):
            total += total * (rendement / 12)
            total += v_mensuel
            total_investi += v_mensuel
        
        historique.append({
            "Année": i,
            "Total": round(total, 2),
            "Investi": round(total_investi, 2),
            "Intérêts": round(total - total_investi, 2)
        })

    # Affichage des résultats
    res1, res2, res3 = st.columns(3)
    res1.metric("VALEUR FINALE", f"{total:,.2f} €")
    res2.metric("TOTAL INVESTI", f"{total_investi:,.2f} €")
    res3.metric("GAIN NET", f"{(total - total_investi):,.2f} €")

    # Graphique de croissance
    df_plot = pd.DataFrame(historique)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot["Année"], y=df_plot["Total"], name="Valeur Totale", line=dict(color='#00ff00')))
    fig.add_trace(go.Scatter(x=df_plot["Année"], y=df_plot["Investi"], name="Capital Investi", line=dict(color='#ff9800')))
    
    fig.update_layout(
        title="Évolution de votre patrimoine",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ff9800"),
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333")
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tableau détaillé
    with st.expander("VOIR LE DÉTAIL ANNÉE PAR ANNÉE"):
        st.table(df_plot)

# ==========================================
# OUTIL 8 : CRYPTO WALLET TRACKER
# ==========================================
elif outil == "CRYPTO WALLET":
    st.title("₿ CRYPTO PROFIT TRACKER")
    
    # Configuration du Portefeuille dans la barre latérale ou en haut
    st.subheader("» CONFIGURATION DES POSITIONS")
    c1, c2 = st.columns(2)
    with c1:
        achat_btc = st.number_input("PRIX D'ACHAT MOYEN BTC ($)", value=40000.0)
        qte_btc = st.number_input("QUANTITÉ BTC DÉTENUE", value=0.01, format="%.4f")
    with c2:
        achat_eth = st.number_input("PRIX D'ACHAT MOYEN ETH ($)", value=2500.0)
        qte_eth = st.number_input("QUANTITÉ ETH DÉTENUE", value=0.1, format="%.4f")

    # Fonction pour récupérer le prix live (API Binance)
    def get_crypto_price(symbol):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
            return float(requests.get(url).json()['price'])
        except: return None

    # Récupération des données
    p_btc = get_crypto_price("BTC")
    p_eth = get_crypto_price("ETH")

    if p_btc and p_eth:
        st.markdown("---")
        st.subheader("» LIVE PERFORMANCE")
        
        # Calculs
        def display_crypto_card(nom, actuel, achat, qte):
            profit_unit = actuel - achat
            profit_total = profit_unit * qte
            perf_pct = (actuel - achat) / achat * 100
            couleur = "#00ff00" if perf_pct >= 0 else "#ff0000"
            signe = "+" if perf_pct >= 0 else ""
            
            st.markdown(f"""
                <div style="border: 1px solid #333; padding: 20px; border-radius: 5px; background: #111;">
                    <h3 style="margin:0; color:#ff9800;">{nom}</h3>
                    <p style="margin:0; font-size:12px; color:#666;">PRIX ACTUEL</p>
                    <h2 style="margin:0; color:#00ff00;">{actuel:,.2f} $</h2>
                    <hr style="border:0.5px solid #222;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <p style="margin:0; font-size:12px; color:#666;">PERFORMANCE</p>
                            <p style="margin:0; color:{couleur}; font-weight:bold;">{signe}{perf_pct:.2f} %</p>
                        </div>
                        <div style="text-align: right;">
                            <p style="margin:0; font-size:12px; color:#666;">PROFIT TOTAL</p>
                            <p style="margin:0; color:{couleur}; font-weight:bold;">{signe}{profit_total:,.2f} $</p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        col_btc, col_eth = st.columns(2)
        with col_btc:
            display_crypto_card("BITCOIN", p_btc, achat_btc, qte_btc)
        with col_eth:
            display_crypto_card("ETHEREUM", p_eth, achat_eth, qte_eth)

        # Résumé du Wallet
        total_val = (p_btc * qte_btc) + (p_eth * qte_eth)
        total_investi = (achat_btc * qte_btc) + (achat_eth * qte_eth)
        profit_global = total_val - total_investi
        perf_globale = (profit_global / total_investi) * 100 if total_investi > 0 else 0

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("VALEUR TOTALE PORTFOLIO", f"{total_val:,.2f} $")
        m2.metric("PROFIT GLOBAL ($)", f"{profit_global:,.2f} $", f"{perf_globale:+.2f}%")
        m3.metric("MARCHÉ", "BTC/USDT", "LIVE")
    else:
        st.error("ERREUR DE CONNEXION À L'API BINANCE")
