import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from streamlit_lightweight_charts import renderLightweightCharts # Nouvel import

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="AM-Trading", layout="wide")
st_autorefresh(interval=15000, key="global_refresh")

# --- FONCTIONS DE MISE EN CACHE (Anti-Blocage & Performance) ---
@st.cache_data(ttl=3600)
def get_ticker_info(ticker):
    try:
        data = yf.Ticker(ticker)
        return data.info
    except:
        return None

@st.cache_data(ttl=30)
def get_ticker_history(ticker, period="5y", interval="1d"):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period=period, interval=interval)
        return hist
    except:
        return pd.DataFrame()

def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: 
        return nom

# --- FONCTION GRAPHIQUE STYLE TRADINGVIEW ---
def afficher_graphique_tradingview(df, type_graph="Candlestick", key="chart"):
    if df.empty:
        return
    
    # Préparation des données pour lightweight-charts
    df_tv = df.reset_index()
    df_tv.columns = [c.lower() for c in df_tv.columns]
    # Conversion du temps pour le format TradingView
    if 'date' in df_tv.columns:
        df_tv['time'] = df_tv['date'].dt.strftime('%Y-%m-%d')
    elif 'datetime' in df_tv.columns:
        df_tv['time'] = df_tv['datetime'].dt.strftime('%Y-%m-%d')
    
    chart_options = {
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#242733"}, "horzLines": {"color": "#242733"}},
        "crosshair": {"mode": 0},
        "priceScale": {"borderColor": "#485c7b"},
        "timeScale": {"borderColor": "#485c7b", "timeVisible": True, "secondsVisible": False}
    }

    if type_graph == "Candlestick":
        series = [{
            "type": "Candlestick",
            "data": df_tv[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records'),
            "options": {"upColor": "#26a69a", "downColor": "#ef5350", "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"}
        }]
    else:
        series = [{
            "type": "Area",
            "data": df_tv[['time', 'close']].rename(columns={'close': 'value'}).to_dict(orient='records'),
            "options": {"topColor": "rgba(33, 150, 243, 0.56)", "bottomColor": "rgba(33, 150, 243, 0.04)", "lineColor": "rgba(33, 150, 243, 1)"}
        }]

    renderLightweightCharts([{"chart": chart_options, "series": series}], key=key)

# --- NAVIGATION ---
st.sidebar.title("🚀 AM-Trading")
outil = st.sidebar.radio("Choisir un outil :", 
    ["📊 Analyseur Pro", "⚔️ Mode Duel", "🌍 Market Monitor"])

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
        mode_graph = st.radio("Style de graphique :", ["Débutant (Ligne)", "Pro (Bougies)"], horizontal=True)

        col_graph, col_data = st.columns([2, 1])
        with col_graph:
            if mode_graph == "Pro (Bougies)":
                choix_int = st.selectbox("Unité de la bougie :", ["1d", "1wk", "1mo"], index=0)
                p_map = {"1d": "5y", "1wk": "max", "1mo": "max"}
                hist = get_ticker_history(ticker, period=p_map[choix_int], interval=choix_int)
                afficher_graphique_tradingview(hist, "Candlestick", key="ana_pro_cand")
            else:
                hist = get_ticker_history(ticker, period="5y")
                afficher_graphique_tradingview(hist, "Area", key="ana_pro_area")

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

        # --- SECTION SCORING ---
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
            if dette_equity < 50: score += 4; positifs.append("✅ Bilan solide [+4]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")
        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende safe [+4]")
        if marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")
        
        score_f = min(20, max(0, score))
        c_s, c_d = st.columns([1, 2])
        with c_s:
            st.write(f"## Note : {score_f}/20")
            st.progress(score_f / 20)
            if score_f >= 15: st.success("🚀 ACHAT FORT")
            elif score_f >= 10: st.info("⚖️ À SURVEILLER")
            else: st.error("⚠️ ÉVITER")
        with c_d:
            for p in positifs: st.markdown(f'<p style="color:#2ecc71;margin:0;font-weight:bold;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.markdown(f'<p style="color:#e74c3c;margin:0;font-weight:bold;">{n}</p>', unsafe_allow_html=True)

        # --- SECTION ACTUALITÉS ---
        st.markdown("---")
        col_n, col_m = st.columns([2, 1])
        with col_n:
            st.subheader(f"📰 Actualités : {nom}")
            search_term = nom.replace(" ", "+")
            url_rss = f"https://news.google.com/rss/search?q={search_term}+stock+bourse&hl=fr&gl=FR&ceid=FR:fr"
            try:
                flux = feedparser.parse(url_rss)
                if flux.entries:
                    for entry in flux.entries[:5]:
                        clean_title = entry.title.split(" - ")[0]
                        with st.expander(f"📌 {clean_title}"):
                            st.write(f"**Source :** {entry.source.get('title', 'Presse Finance')}")
                            st.caption(f"Publié le : {entry.published}")
                            st.link_button("Lire l'article", entry.link)
                else: st.info("Aucune actualité trouvée.")
            except: st.error("Erreur de flux d'actualités.")
        with col_m:
            st.subheader("🌍 Flash Marché")
            url_mkt = "https://news.google.com/rss/search?q=bourse+mondiale+indices&hl=fr&gl=FR&ceid=FR:fr"
            try:
                flux_mkt = feedparser.parse(url_mkt)
                for m_art in flux_mkt.entries[:4]:
                    m_title = m_art.title.split(" - ")[0]
                    st.markdown(f"🔹 **{m_art.source.get('title')}**\n[{m_title}]({m_art.link})")
                    st.write("---")
            except: st.write("Flux indisponible.")

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
            b = i.get('trailingEps') or i.get('forwardEps') or 0
            v = (max(0, b) * (8.5 + 2 * 7) * 4.4) / 3.5
            return {"nom": i.get('shortName', t), "prix": p, "valeur": v, "dette": i.get('debtToEquity', 0), "yield": (i.get('dividendYield', 0) or 0)*100}
        try:
            d1, d2 = get_d(t1), get_d(t2)
            df = pd.DataFrame({
                "Critère": ["Prix", "Valeur Graham", "Dette/Eq", "Rendement"],
                d1['nom']: [f"{d1['prix']:.2f}", f"{d1['valeur']:.2f}", f"{d1['dette']}%", f"{d1['yield']:.2f}%"],
                d2['nom']: [f"{d2['prix']:.2f}", f"{d2['valeur']:.2f}", f"{d2['dette']}%", f"{d2['yield']:.2f}%"]
            })
            st.table(df)
            m1, m2 = (d1['valeur']-d1['prix'])/d1['prix'], (d2['valeur']-d2['prix'])/d2['prix']
            st.success(f"🏆 Gagnant : {d1['nom'] if m1 > m2 else d2['nom']}")
        except: st.error("Données indisponibles.")

# ==========================================
# OUTIL 3 : MARKET MONITOR
# ==========================================
elif outil == "🌍 Market Monitor":
    st_autorefresh(interval=60000, key="datarefresh") # Refresh réduit à 1min pour stabilité
    maintenant = datetime.utcnow() + timedelta(hours=4)
    h = maintenant.hour
    st.title("🌍 Market Monitor (UTC+4)")
    st.subheader(f"🕒 Heure actuelle : {maintenant.strftime('%H:%M:%S')}")

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
            hist_idx = get_ticker_history(tk, period="2d")
            if not hist_idx.empty:
                val_actuelle = hist_idx['Close'].iloc[-1]
                variation = ((val_actuelle - hist_idx['Close'].iloc[-2]) / hist_idx['Close'].iloc[-2]) * 100
                cols[i].metric(nom, f"{val_actuelle:,.2f}", f"{variation:+.2f}%")
                if cols[i].button(f"Analyser {nom}", key=f"btn_{tk}"): st.session_state.index_selectionne = tk
        except: pass

    st.markdown("---")
    nom_sel = indices[st.session_state.index_selectionne]
    st.subheader(f"📈 Graphique TradingView : {nom_sel}")
    mode_graph_mkt = st.radio("Style :", ["Ligne", "Bougies"], horizontal=True, key="mkt_style")
    
    hist_idx_full = get_ticker_history(st.session_state.index_selectionne, period="5y", interval="1d")
    if not hist_idx_full.empty:
        type_tv = "Candlestick" if mode_graph_mkt == "Bougies" else "Area"
        afficher_graphique_tradingview(hist_idx_full, type_tv, key="mkt_chart_tv")
