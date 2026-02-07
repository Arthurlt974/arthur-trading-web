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

# --- FONCTIONS DE CALCUL ET SENTIMENT ---

def calculer_score_sentiment(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1y")
        if len(data) < 200: return 50, "NEUTRE", "gray"
        
        prix_actuel = data['Close'].iloc[-1]
        ma200 = data['Close'].rolling(window=200).mean().iloc[-1]
        
        # Calcul de l'écart relatif (Ratio)
        ratio = (prix_actuel / ma200) - 1
        
        # Formule lissée pour le score
        score = 50 + (ratio * 300) 
        score = max(10, min(90, score)) # Bridage visuel pour éviter les bords
        
        if score > 70: return score, "EXTRÊME EUPHORIE 🚀", "#00ffad"
        elif score > 55: return score, "OPTIMISME 📈", "#2ecc71"
        elif score > 45: return score, "NEUTRE ⚖️", "#f1c40f"
        elif score > 30: return score, "PEUR 📉", "#e67e22"
        else: return score, "PANIQUE TOTALE 💀", "#e74c3c"
    except:
        return 50, "ERREUR", "gray"

def afficher_jauge_pro(score, titre, couleur, sentiment):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        number = {'font': {'size': 45, 'color': "white"}, 'suffix': "%"},
        title = {
            'text': f"{titre}<br><span style='color:{couleur}; font-size:18px;'>{sentiment}</span>", 
            'font': {'size': 22, 'color': "white"}
        },
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': couleur, 'thickness': 0.3},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "#242733",
            'steps': [
                {'range': [0, 30], 'color': "rgba(231, 76, 60, 0.2)"},
                {'range': [30, 45], 'color': "rgba(230, 126, 34, 0.2)"},
                {'range': [45, 55], 'color': "rgba(241, 196, 15, 0.2)"},
                {'range': [55, 70], 'color': "rgba(46, 204, 113, 0.2)"},
                {'range': [70, 100], 'color': "rgba(0, 255, 173, 0.2)"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={'color': "white", 'family': "Arial"},
        height=380, 
        margin=dict(l=50, r=50, t=100, b=20)
    )
    return fig

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="AM-Trading", layout="wide")

# --- SYSTÈME DE MOT DE PASSE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("### 🔒 Accès Restreint")
    pwd = st.text_input("Mot de passe :", type="password")
    
    if st.button("Se connecter"):
        if pwd == "1234":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Mot de passe incorrect")
    return False

if not check_password():
    st.stop()

# --- REFRESH ---
st_autorefresh(interval=30000, key="global_refresh")

# --- HORLOGE ---
def afficher_horloge_temps_reel():
    horloge_html = """
        <div id="clock" style="
            font-size: 28px; 
            font-family: 'Source Code Pro', monospace; 
            color: #26a69a; 
            font-weight: bold;
            padding: 15px;
            border-radius: 8px;
            background: #131722;
            border: 1px solid #242733;
            text-align: center;
            margin-bottom: 20px;
        ">--:--:--</div>
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
    components.html(horloge_html, height=100)

# --- GRAPHIQUES ---
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
          "toolbar_bg": "#f1f3f6",
          "enable_publishing": false,
          "hide_side_toolbar": false,
          "allow_symbol_change": true,
          "details": true,
          "container_id": "tradingview_chart"
        }});
        </script>
    """
    components.html(tradingview_html, height=height + 10)

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

# --- NAVIGATION ---
st.sidebar.title("🚀 AM-Trading")
outil = st.sidebar.radio("Choisir un outil :", ["📊 Analyseur Pro", "🌡️ Sentiment Index", "⚔️ Mode Duel", "🌍 Market Monitor", "📰 Daily Brief", "📅 Calendrier Éco"])

if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="NVIDIA")
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

        st.title(f"📊 {nom} ({ticker})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)
        st.markdown("---")
        st.subheader("📈 Analyse Technique Pro")
        afficher_graphique_pro(ticker, height=650)
        st.markdown("---")
        st.subheader("📑 Détails Financiers")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
        with f2:
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
        with f3:
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

elif outil == "⚔️ Mode Duel":
    st.title("⚔️ Duel d'Actions")
    c1, c2 = st.columns(2)
    t1 = c1.text_input("Action 1", value="MC.PA")
    t2 = c2.text_input("Action 2", value="RMS.PA")
    if st.button("Lancer le Duel"):
        def get_d(t):
            ticker_id = trouver_ticker(t)
            i = get_ticker_info(ticker_id)
            p = i.get('currentPrice') or i.get('regularMarketPrice') or 1
            b = i.get('trailingEps') or 0
            v = (max(0, b) * (8.5 + 2 * 7) * 4.4) / 3.5
            return {"nom": i.get('shortName', t), "prix": p, "valeur": v, "yield": (i.get('dividendYield', 0) or 0)*100}
        try:
            d1, d2 = get_d(t1), get_d(t2)
            df = pd.DataFrame({
                "Critère": ["Prix", "Valeur Graham", "Rendement Div."],
                d1['nom']: [f"{d1['prix']:.2f}", f"{d1['valeur']:.2f}", f"{d1['yield']:.2f}%"],
                d2['nom']: [f"{d2['prix']:.2f}", f"{d2['valeur']:.2f}", f"{d2['yield']:.2f}%"]
            })
            st.table(df)
            m1, m2 = (d1['valeur']-d1['prix'])/d1['prix'], (d2['valeur']-d2['prix'])/d2['prix']
            st.success(f"🏆 Meilleur potentiel : {d1['nom'] if m1 > m2 else d2['nom']}")
        except: st.error("Erreur de données.")

elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor")
    afficher_horloge_temps_reel()
    st.markdown("### 🕒 Statut des Bourses")
    h = (datetime.utcnow() + timedelta(hours=4)).hour
    data_horaires = {
        "Session": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "Ouverture (REU)": ["05:30", "12:00", "18:30"],
        "Fermeture (REU)": ["12:00", "20:30", "01:00"],
        "Statut": [
            "🟢 OUVERT" if 5 <= h < 12 else "🔴 FERMÉ", 
            "🟢 OUVERT" if 12 <= h < 20 else "🔴 FERMÉ", 
            "🟢 OUVERT" if (h >= 18 or h < 1) else "🔴 FERMÉ"
        ]
    }
    st.table(pd.DataFrame(data_horaires))
    st.markdown("---")
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
                if cols[i].button(f"Analyser {nom}", key=f"btn_{tk}"):
                    st.session_state.index_selectionne = tk
        except: pass
    st.markdown("---")
    afficher_graphique_pro(st.session_state.index_selectionne, height=700)

elif outil == "📰 Daily Brief":
    st.title("📰 Daily Market Brief")
    st.markdown("---")
    tab_eco, tab_tech, tab_quotidien = st.tabs(["🌍 Économie Mondiale", "⚡ Tech & Crypto", "📅 Le Quotidien (Boursorama)"])
    def afficher_flux_daily(url, filtre_boursorama_24h=False):
        try:
            import time
            flux = feedparser.parse(url)
            if not flux.entries:
                st.info("Aucune actualité trouvée.")
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
                    with st.expander(f"⚡ {clean_title}"):
                        st.write(f"**Source :** Boursorama Actualités")
                        if 'published' in entry:
                            st.caption(f"🕒 Publié le : {entry.published}")
                        st.link_button("Lire l'article complet", entry.link)
            if not trouve and filtre_boursorama_24h:
                st.warning("En attente de nouveaux articles Boursorama pour aujourd'hui...")
        except: st.error("Erreur flux.")
    with tab_eco:
        url_eco = "https://news.google.com/rss/search?q=bourse+economie+mondiale&hl=fr&gl=FR&ceid=FR:fr"
        afficher_flux_daily(url_eco)
    with tab_tech:
        url_tech = "https://news.google.com/rss/search?q=crypto+nasdaq+nvidia&hl=fr&gl=FR&ceid=FR:fr"
        afficher_flux_daily(url_tech)
    with tab_quotidien:
        url_boursorama = "https://news.google.com/rss/search?q=site:boursorama.com&hl=fr&gl=FR&ceid=FR:fr"
        afficher_flux_daily(url_boursorama, filtre_boursorama_24h=True)

elif outil == "📅 Calendrier Éco":
    st.title("📅 Calendrier Économique")
    st.info("Annonces macroéconomiques mondiales en direct.")
    calendrier_tv = """
    <meta charset="UTF-8">
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      { "colorTheme": "dark", "isMaximized": true, "width": "100%", "height": "800", "locale": "fr", "importanceFilter": "-1,0,1", "countryFilter": "fr,us,eu,gb,jp" }
      </script>
    </div>
    """
    components.html(calendrier_tv, height=800, scrolling=True)

# ==========================================
# OUTIL 6 : FEAR & GREED INDEX PRO
# ==========================================
elif outil == "🌡️ Sentiment Index":
    st.title("🌡️ Market Sentiment Index")
    st.write("Analyse de l'écart à la Moyenne Mobile 200 jours (MA200).")
    
    marches = {
        "^GSPC": "🇺🇸 USA - S&P 500",
        "^FCHI": "🇫🇷 France - CAC 40",
        "^HSI":  "🇭🇰 Asie - Hang Seng",
        "BTC-USD": "₿ Crypto - Bitcoin",
        "GC=F": "🟡 Or - Métal Précieux",
        "NVDA": "🤖 Tech - NVIDIA"
    }
    
    c1, c2 = st.columns(2)
    for i, (ticker, nom) in enumerate(marches.items()):
        score, label, couleur = calculer_score_sentiment(ticker)
        fig = afficher_jauge_pro(score, nom, couleur, label)
        if i % 2 == 0:
            c1.plotly_chart(fig, use_container_width=True)
        else:
            c2.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.info("💡 **Stratégie** : Un score proche de 0 (Panique) est souvent une zone d'achat. Un score proche de 100 (Euphorie) invite à la prudence.")
