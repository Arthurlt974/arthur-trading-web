import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
import time
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

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

# --- REFRESH ET LOGIQUE ---
st_autorefresh(interval=30000, key="global_refresh")

# --- FONCTION HORLOGE TEMPS RÉEL ---
def afficher_horloge_temps_reel():
    horloge_html = """
        <div id="clock" style="
            font-size: 28px; font-family: 'Source Code Pro', monospace; 
            color: #26a69a; font-weight: bold; padding: 15px;
            border-radius: 8px; background: #131722; border: 1px solid #242733;
            text-align: center; margin-bottom: 20px;
        ">--:--:--</div>
        <script>
            function updateClock() {
                const now = new Date();
                const offset = 4;
                const localTime = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + (offset * 3600000));
                const h = String(localTime.getHours()).padStart(2, '0');
                const m = String(localTime.getMinutes()).padStart(2, '0');
                const s = String(localTime.getSeconds()).padStart(2, '0');
                document.getElementById('clock').innerText = h + ":" + m + ":" + s;
            }
            setInterval(updateClock, 1000); updateClock();
        </script>
    """
    components.html(horloge_html, height=100)

# --- FONCTION GRAPHIQUE TRADINGVIEW ---
def afficher_graphique_pro(symbol, height=600):
    traduction_symbols = {"^FCHI": "CAC40", "^GSPC": "VANTAGE:SP500", "^IXIC": "NASDAQ", "BTC-USD": "BINANCE:BTCUSDT"}
    tv_symbol = traduction_symbols.get(symbol, symbol.replace(".PA", ""))
    if ".PA" in symbol and symbol not in traduction_symbols: tv_symbol = f"EURONEXT:{tv_symbol}"
    
    tradingview_html = f"""
        <div id="tradingview_chart" style="height:{height}px;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{"autosize": true, "symbol": "{tv_symbol}", "interval": "D", "timezone": "Europe/Paris",
          "theme": "dark", "style": "1", "locale": "fr", "toolbar_bg": "#f1f3f6", "enable_publishing": false,
          "hide_side_toolbar": false, "allow_symbol_change": true, "details": true, "container_id": "tradingview_chart"
        }});
        </script>
    """
    components.html(tradingview_html, height=height + 10)

# --- FONCTIONS DONNÉES ---
@st.cache_data(ttl=5) 
def get_ticker_info(ticker):
    try: return yf.Ticker(ticker).info
    except: return None

@st.cache_data(ttl=5)
def get_ticker_history(ticker, period="2d"):
    try: return yf.Ticker(ticker).history(period=period)
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
# Ajout de l'outil dans la liste radio
outil = st.sidebar.radio("Choisir un outil :", ["📊 Analyseur Pro", "⚔️ Mode Duel", "🌍 Market Monitor", "📰 Daily Brief", "📅 Calendrier Éco"])

# ==========================================
# OUTIL 1 : ANALYSEUR PRO
# ==========================================
if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="NVIDIA")
    ticker = trouver_ticker(nom_entree)
    info = get_ticker_info(ticker)
    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        devise, secteur = info.get('currency', 'EUR'), info.get('sector', 'N/A')
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 0)
        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout, cash_action = (info.get('payoutRatio') or 0) * 100, info.get('totalCashPerShare') or 0
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
        with f1: st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}"); st.write(f"**Ratio P/E :** {per:.2f}")
        with f2: st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %"); st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
        with f3: st.write(f"**Payout Ratio :** {payout:.2f} %"); st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")
        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        score, positifs, negatifs = 0, [], []
        if bpa > 0:
            if per < 12: score += 5; positifs.append("✅ P/E attractif [+5]")
            elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
            else: score += 1; positifs.append("🟡 P/E élevé [+1]")
        else: score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")
        if dette_equity is not None:
            if dette_equity < 50: score += 4; positifs.append("✅ Bilan très solide [+4]")
            elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")
        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende solide [+4]")
        if marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")
        score_f = min(20, max(0, score))
        cs, cd = st.columns([1, 2])
        with cs: st.write(f"## Note : {score_f}/20"); st.progress(score_f / 20)
        with cd: 
            for p in positifs: st.markdown(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.markdown(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)
        st.markdown("---")
        st.subheader(f"📰 Actualités : {nom}")
        tab1, tab2 = st.tabs(["🔥 Direct (24h)", "📚 Archive (7 jours)"])
        search_term = nom.replace(" ", "+")
        url_rss = f"https://news.google.com/rss/search?q={search_term}+(site:investing.com+OR+bourse+OR+stock)&hl=fr&gl=FR&ceid=FR:fr"
        try:
            flux = feedparser.parse(url_rss)
            maintenant = time.time()
            articles = sorted(flux.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)
            with tab1:
                trouve_24h = False
                for entry in articles:
                    pub_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else maintenant
                    if (maintenant - pub_time) < (24 * 3600):
                        trouve_24h = True
                        source = entry.source.get('title', 'Finance')
                        prefix = "📊 Investing |" if "investing" in source.lower() else "🆕"
                        with st.expander(f"{prefix} {entry.title.split(' - ')[0]}"):
                            st.write(f"**Source :** {source}"); st.caption(f"🕒 {entry.published}"); st.link_button("Lire l'article", entry.link)
                if not trouve_24h: st.info("Aucune actualité sur les dernières 24h.")
            with tab2:
                for entry in articles[:12]:
                    source = entry.source.get('title', 'Finance')
                    prefix = "📊 Investing |" if "investing" in source.lower() else "📌"
                    with st.expander(f"{prefix} {entry.title.split(' - ')[0]}"):
                        st.caption(f"📅 {entry.published}"); st.link_button("Voir l'archive", entry.link)
        except: st.error("Erreur flux news.")

# ==========================================
# OUTIL 2 : MODE DUEL
# ==========================================
elif outil == "⚔️ Mode Duel":
    st.title("⚔️ Duel d'Actions")
    c1, c2 = st.columns(2)
    t1, t2 = c1.text_input("Action 1", value="MC.PA"), c2.text_input("Action 2", value="RMS.PA")
    if st.button("Lancer le Duel"):
        def get_d(t):
            tk = trouver_ticker(t); i = get_ticker_info(tk)
            p = i.get('currentPrice') or i.get('regularMarketPrice') or 1
            b = i.get('trailingEps') or 0
            v = (max(0, b) * (8.5 + 2 * 7) * 4.4) / 3.5
            return {"nom": i.get('shortName', t), "prix": p, "valeur": v, "yield": (i.get('dividendYield', 0) or 0)*100}
        try:
            d1, d2 = get_d(t1), get_d(t2)
            df = pd.DataFrame({"Critère": ["Prix", "Valeur Graham", "Rendement Div."],
                d1['nom']: [f"{d1['prix']:.2f}", f"{d1['valeur']:.2f}", f"{d1['yield']:.2f}%"],
                d2['nom']: [f"{d2['prix']:.2f}", f"{d2['valeur']:.2f}", f"{d2['yield']:.2f}%"]})
            st.table(df)
            m1, m2 = (d1['valeur']-d1['prix'])/d1['prix'], (d2['valeur']-d2['prix'])/d2['prix']
            st.success(f"🏆 Meilleur potentiel : {d1['nom'] if m1 > m2 else d2['nom']}")
        except: st.error("Erreur données.")

# ==========================================
# OUTIL 3 : MARKET MONITOR
# ==========================================
elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor"); afficher_horloge_temps_reel()
    h = (datetime.utcnow() + timedelta(hours=4)).hour
    data_horaires = {"Session": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"], "Ouverture (REU)": ["05:30", "12:00", "18:30"],
        "Fermeture (REU)": ["12:00", "20:30", "01:00"],
        "Statut": ["🟢 OUVERT" if 5 <= h < 12 else "🔴 FERMÉ", "🟢 OUVERT" if 12 <= h < 20 else "🔴 FERMÉ", "🟢 OUVERT" if (h >= 18 or h < 1) else "🔴 FERMÉ"]}
    st.table(pd.DataFrame(data_horaires))
    st.markdown("---"); indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    cols = st.columns(len(indices))
    if 'index_selectionne' not in st.session_state: st.session_state.index_selectionne = "^FCHI"
    for i, (tk, nom) in enumerate(indices.items()):
        try:
            hist = get_ticker_history(tk)
            if not hist.empty:
                v_act, v_prec = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                cols[i].metric(nom, f"{v_act:,.2f}", f"{((v_act-v_prec)/v_prec)*100:+.2f}%")
                if cols[i].button(f"Analyser {nom}", key=f"btn_{tk}"): st.session_state.index_selectionne = tk
        except: pass
    st.markdown("---"); afficher_graphique_pro(st.session_state.index_selectionne, height=700)

# ==========================================
# OUTIL 4 : DAILY BRIEF
# ==========================================
elif outil == "📰 Daily Brief":
    st.title("📰 Daily Market Brief")
    tab_eco, tab_tech, tab_quotidien = st.tabs(["🌍 Économie Mondiale", "⚡ Tech & Crypto", "📅 Le Quotidien (Boursorama)"])
    def afficher_flux_daily(url, filtre_24h=False):
        try:
            flux = feedparser.parse(url); maintenant = time.time(); trouve = False
            articles = sorted(flux.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)
            for entry in articles[:15]:
                pub_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else maintenant
                if not filtre_24h or (maintenant - pub_time) < (24 * 3600):
                    trouve = True
                    with st.expander(f"⚡ {entry.title.replace(' - Boursorama', '').split(' - ')[0]}"):
                        st.caption(f"🕒 {entry.published}"); st.link_button("Lire l'article", entry.link)
            if not trouve and filtre_24h: st.warning("En attente d'articles récents...")
        except: st.error("Erreur flux.")
    with tab_eco: afficher_flux_daily("https://news.google.com/rss/search?q=bourse+economie+mondiale&hl=fr&gl=FR&ceid=FR:fr")
    with tab_tech: afficher_flux_daily("https://news.google.com/rss/search?q=crypto+nasdaq+nvidia&hl=fr&gl=FR&ceid=FR:fr")
    with tab_quotidien: afficher_flux_daily("https://news.google.com/rss/search?q=site:boursorama.com&hl=fr&gl=FR&ceid=FR:fr", True)

# ==========================================
# OUTIL 5 : CALENDRIER ÉCONOMIQUE
# ==========================================
elif outil == "📅 Calendrier Éco":
    st.title("📅 Calendrier Économique Temps Réel")
    st.info("Suivez les annonces macroéconomiques mondiales en direct.")
    
    calendrier_html = """
    <iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&category=_main&features=datepicker,timezone&countries=25,32,6,37,7,5&calType=day&timeZone=58&lang=5" 
    width="100%" height="800" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe>
    """
    components.html(calendrier_html, height=850)
