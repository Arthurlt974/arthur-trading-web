import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from streamlit_lightweight_charts import renderLightweightCharts

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="AM-Trading", layout="wide")
st_autorefresh(interval=15000, key="global_refresh")

# --- FONCTIONS DE MISE EN CACHE ---
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
        return data.history(period=period, interval=interval)
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

# --- FONCTION GRAPHIQUE TRADINGVIEW ---
def afficher_tv_chart(df, type_graph="Candlestick", key="chart"):
    if df.empty:
        st.error("Aucune donnée disponible pour le graphique.")
        return
    
    df_tv = df.reset_index()
    df_tv.columns = [c.lower() for c in df_tv.columns]
    # Formatage de la date pour TradingView
    df_tv['time'] = df_tv['date'].dt.strftime('%Y-%m-%d')
    
    chart_options = {
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#242733"}, "horzLines": {"color": "#242733"}},
        "priceScale": {"borderColor": "#485c7b"},
        "timeScale": {"borderColor": "#485c7b"}
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
        prix = info.get('currentPrice', 1)
        devise = info.get('currency', 'EUR')
        bpa = info.get('trailingEps', 0)
        per = info.get('trailingPE', 0)
        
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 else 0

        st.title(f"📊 {nom} ({ticker})")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")

        st.markdown("---")
        mode_graph = st.radio("Style :", ["Ligne", "Bougies"], horizontal=True)

        # Graphique TradingView
        hist = get_ticker_history(ticker)
        type_tv = "Candlestick" if mode_graph == "Bougies" else "Area"
        afficher_tv_chart(hist, type_tv, key="ana_chart")

        # ... (Garder le reste de ton code pour le Scoring et les News)
        st.markdown("---")
        st.subheader("📰 Actualités")
        # (Ton code feedparser ici...)

# ==========================================
# OUTIL 3 : MARKET MONITOR
# ==========================================
elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor")
    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    
    if 'index_sel' not in st.session_state:
        st.session_state.index_sel = "^FCHI"

    cols = st.columns(len(indices))
    for i, (tk, nom) in enumerate(indices.items()):
        if cols[i].button(nom):
            st.session_state.index_sel = tk

    st.subheader(f"📈 Graphique : {indices[st.session_state.index_sel]}")
    hist_mkt = get_ticker_history(st.session_state.index_sel)
    afficher_tv_chart(hist_mkt, "Candlestick", key="mkt_chart")
