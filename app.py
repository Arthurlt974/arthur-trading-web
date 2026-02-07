import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="AM-Trading", layout="wide")
# L'autorefresh est à 30s pour les données, l'horloge JS gère les secondes
st_autorefresh(interval=30000, key="global_refresh")

# --- FONCTION HORLOGE TEMPS RÉEL (JS) ---
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

# --- FONCTION GRAPHIQUE TRADINGVIEW PRO ---
def afficher_graphique_pro(symbol, height=600):
    traduction_symbols = {
        "^FCHI": "CAC40",            # Indice CAC40 par TVC
        "^GSPC": "VANTAGE:SP500",      # S&P index cash CFD par VANTAGE
        "^IXIC": "NASDAQ",         # Indice Nasdaq 100 par NASDAQ
        "BTC-USD": "BINANCE:BTCUSDT"   # Bitcoin
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
          "hotlist": true,
          "calendar": true,
          "show_popup_button": true,
          "container_id": "tradingview_chart"
        }});
        </script>
    """
    components.html(tradingview_html, height=height + 10)

# --- FONCTIONS DE MISE EN CACHE ---
@st.cache_data(ttl=3600)
def get_ticker_info(ticker):
    try:
        data = yf.Ticker(ticker)
        return data.info
    except: return None

@st.cache_data(ttl=60)
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
outil = st.sidebar.radio("Choisir un outil :", ["📊 Analyseur Pro", "⚔️ Mode Duel", "🌍 Market Monitor"])

# ==========================================
# OUTIL 1 : ANALYSEUR PRO
# ==========================================
if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="MC.PA")
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
        col_graph, col_data = st.columns([2, 1])
        with col_graph:
            afficher_graphique_pro(ticker)
        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

        # --- SCORING ---
        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        score = 0
        positifs, negatifs = [], []
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
        elif payout > 95: score -= 4; negatifs.append("🚨 Payout Ratio risqué [-4]")
        if marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")

        score_f = min(20, max(0, score))
        cs, cd = st.columns([1, 2])
        with cs:
            st.write(f"## Note : {score_f}/20")
            st.progress(score_f / 20)
        with cd:
            for p in positifs: st.markdown(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.markdown(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)

        # --- ACTUALITÉS ---
        st.markdown("---")
        st.subheader(f"📰 Actualités : {nom}")
        search_term = nom.replace(" ", "+")
        url_rss = f"https://news.google.com/rss/search?q={search_term}+stock+bourse&hl=fr&gl=FR&ceid=FR:fr"
        try:
            flux = feedparser.parse(url_rss)
            for entry in flux.entries[:5]:
                with st.expander(f"📌 {entry.title.split(' - ')[0]}"):
                    st.write(f"**Source :** {entry.source.get('title')}")
                    st.link_button("Lire l'article", entry.link)
        except: st.error("Erreur de flux d'actualités.")

# ==========================================
# OUTIL 2 : MODE DUEL
# ==========================================
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

# ==========================================
# OUTIL 3 : MARKET MONITOR
# ==========================================
elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor")
    afficher_horloge_temps_reel()

    st.markdown("### 🕒 Statut des Bourses")
    h = (datetime.utcnow() + timedelta(hours=4)).hour
    data_horaires = {
        "Session": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "Ouverture (REU)": ["05:30", "12:00", "18:30"],
        "Statut": ["🟢 OUVERT" if 5 <= h < 12 else "🔴 FERMÉ", "🟢 OUVERT" if 12 <= h < 20 else "🔴 FERMÉ", "🟢 OUVERT" if (h >= 18 or h < 1) else "🔴 FERMÉ"]
    }
    st.table(pd.DataFrame(data_horaires))

    st.markdown("---")
    st.subheader("⚡ Moteurs du Marché")
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
    nom_sel = indices.get(st.session_state.index_selectionne, "Indice")
    st.subheader(f"📈 Graphique Avancé : {nom_sel}")
    afficher_graphique_pro(st.session_state.index_selectionne, height=700)
