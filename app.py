import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from fpdf import FPDF
import io
import json
from scipy import stats
import ta
from sklearn.preprocessing import MinMaxScaler

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="AM-Trading | Bloomberg Terminal Pro", layout="wide", initial_sidebar_state="expanded")

# --- INITIALISATION DES VARIABLES DE SESSION ---
if "multi_charts" not in st.session_state:
    st.session_state.multi_charts = []
if "whale_logs" not in st.session_state:
    st.session_state.whale_logs = []
if "workspace" not in st.session_state:
    st.session_state.workspace = []
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {"positions": [], "cash": 100000}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = []
if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = {}

# --- STYLE BLOOMBERG TERMINAL AMÉLIORÉ ---
st.markdown("""
    <style>
        /* Suppression des éléments Streamlit par défaut */
        header[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
            color: #ff9800 !important;
        }
        
        .stApp [data-testid="stDecoration"] {
            display: none;
        }

        /* Fond noir profond */
        .stApp { 
            background-color: #0d0d0d; 
            color: #ff9800 !important; 
        }
        
        /* Sidebar améliorée */
        [data-testid="stSidebar"] { 
            background: linear-gradient(180deg, #161616 0%, #0a0a0a 100%);
            border-right: 2px solid #ff9800; 
        }
        
        /* Tous les textes en orange Bloomberg */
        h1, h2, h3, h4, h5, h6, p, span, label, div, .stMarkdown { 
            color: #ff9800 !important; 
            text-transform: uppercase; 
            font-family: 'Courier New', monospace;
        }

        /* Metrics */
        [data-testid="stMetricLabel"] {
            color: #ff9800 !important;
            font-weight: bold;
        }
        
        [data-testid="stMetricValue"] {
            color: #00ff00 !important;
            font-size: 28px !important;
        }

        /* Onglets stylisés */
        button[data-baseweb="tab"] {
            background-color: #1a1a1a;
            border: 1px solid #333;
            color: #ff9800 !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #ff9800;
            color: #000 !important;
            border: 2px solid #ffb84d;
        }
        
        /* Boutons */
        .stButton>button {
            background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
            color: #ff9800; 
            border: 2px solid #ff9800;
            border-radius: 6px; 
            font-weight: bold; 
            width: 100%;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stButton>button:hover { 
            background: linear-gradient(135deg, #ff9800 0%, #ffb84d 100%);
            color: #000; 
            box-shadow: 0 0 20px rgba(255, 152, 0, 0.6);
            transform: translateY(-2px);
        }
        
        /* Input fields */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stSelectbox>div>div>select {
            background-color: #1a1a1a;
            color: #ff9800;
            border: 1px solid #ff9800;
            border-radius: 4px;
        }
        
        /* DataFrames */
        .dataframe {
            background-color: #000 !important;
            color: #ff9800 !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #1a1a1a;
            border: 1px solid #ff9800;
            color: #ff9800 !important;
        }
        
        /* Cards style */
        .card {
            background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%);
            border: 2px solid #ff9800;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }
        ::-webkit-scrollbar-track {
            background: #0d0d0d;
        }
        ::-webkit-scrollbar-thumb {
            background: #ff9800;
            border-radius: 6px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #ffb84d;
        }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES AMÉLIORÉES ---
def get_crypto_price(symbol):
    """Récupère le prix d'une crypto via Binance ou Yahoo Finance"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3).json()
        return float(res['price'])
    except:
        try:
            tkr = symbol + "-USD"
            data = yf.Ticker(tkr).fast_info
            return data.get('last_price', 0)
        except:
            return None

def get_crypto_24h_change(symbol):
    """Récupère le changement 24h d'une crypto"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3).json()
        return float(res['priceChangePercent'])
    except:
        return 0

def calculate_technical_indicators(df):
    """Calcule les indicateurs techniques sur un DataFrame"""
    try:
        # Copie pour éviter les problèmes
        df = df.copy()
        
        # Flatten les colonnes si nécessaire (problème yfinance multi-ticker)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Convertir en Series si nécessaire
        close = df['Close'].squeeze() if hasattr(df['Close'], 'squeeze') else df['Close']
        high = df['High'].squeeze() if hasattr(df['High'], 'squeeze') else df['High']
        low = df['Low'].squeeze() if hasattr(df['Low'], 'squeeze') else df['Low']
        volume = df['Volume'].squeeze() if hasattr(df['Volume'], 'squeeze') else df['Volume']
        
        # RSI
        df['RSI'] = ta.momentum.RSIIndicator(close, window=14).rsi()
        
        # MACD
        macd = ta.trend.MACD(close)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(close)
        df['BB_High'] = bollinger.bollinger_hband()
        df['BB_Mid'] = bollinger.bollinger_mavg()
        df['BB_Low'] = bollinger.bollinger_lband()
        
        # Moving Averages
        df['SMA_20'] = ta.trend.SMAIndicator(close, window=20).sma_indicator()
        df['SMA_50'] = ta.trend.SMAIndicator(close, window=50).sma_indicator()
        df['EMA_12'] = ta.trend.EMAIndicator(close, window=12).ema_indicator()
        df['EMA_26'] = ta.trend.EMAIndicator(close, window=26).ema_indicator()
        
        # ATR (Average True Range)
        df['ATR'] = ta.volatility.AverageTrueRange(high, low, close).average_true_range()
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(high, low, close)
        df['Stoch_K'] = stoch.stoch()
        df['Stoch_D'] = stoch.stoch_signal()
        
        # ADX (Average Directional Index)
        df['ADX'] = ta.trend.ADXIndicator(high, low, close).adx()
        
        # Volume indicators
        df['OBV'] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        df['Volume_SMA'] = volume.rolling(window=20).mean()
        
        return df
    except Exception as e:
        st.error(f"Erreur calcul indicateurs: {str(e)}")
        return df

def analyze_market_sentiment(df):
    """Analyse le sentiment du marché basé sur les indicateurs"""
    try:
        latest = df.iloc[-1]
        signals = []
        score = 0
        
        # RSI
        if latest['RSI'] < 30:
            signals.append(("RSI", "OVERSOLD - SIGNAL ACHAT", "bullish"))
            score += 2
        elif latest['RSI'] > 70:
            signals.append(("RSI", "OVERBOUGHT - SIGNAL VENTE", "bearish"))
            score -= 2
        else:
            signals.append(("RSI", "NEUTRE", "neutral"))
        
        # MACD
        if latest['MACD'] > latest['MACD_Signal']:
            signals.append(("MACD", "BULLISH CROSSOVER", "bullish"))
            score += 1
        else:
            signals.append(("MACD", "BEARISH SIGNAL", "bearish"))
            score -= 1
        
        # Bollinger Bands
        if latest['Close'] < latest['BB_Low']:
            signals.append(("Bollinger", "BELOW LOWER BAND - ACHAT", "bullish"))
            score += 2
        elif latest['Close'] > latest['BB_High']:
            signals.append(("Bollinger", "ABOVE UPPER BAND - VENTE", "bearish"))
            score -= 2
        else:
            signals.append(("Bollinger", "DANS LA BANDE", "neutral"))
        
        # Moving Averages
        if latest['Close'] > latest['SMA_50']:
            signals.append(("MA", "PRIX > SMA50 - TREND HAUSSIER", "bullish"))
            score += 1
        else:
            signals.append(("MA", "PRIX < SMA50 - TREND BAISSIER", "bearish"))
            score -= 1
        
        # Volume
        if latest['Volume'] > latest['Volume_SMA'] * 1.5:
            signals.append(("Volume", "VOLUME ANORMAL ÉLEVÉ", "important"))
            score += 1
        
        # ADX
        if latest['ADX'] > 25:
            signals.append(("ADX", "FORTE TENDANCE", "important"))
        else:
            signals.append(("ADX", "TENDANCE FAIBLE", "neutral"))
        
        # Déterminer le sentiment global
        if score >= 3:
            sentiment = "FORTEMENT HAUSSIER"
            color = "#00ff00"
        elif score >= 1:
            sentiment = "LÉGÈREMENT HAUSSIER"
            color = "#7fff00"
        elif score <= -3:
            sentiment = "FORTEMENT BAISSIER"
            color = "#ff0000"
        elif score <= -1:
            sentiment = "LÉGÈREMENT BAISSIER"
            color = "#ff6347"
        else:
            sentiment = "NEUTRE"
            color = "#ff9800"
        
        return sentiment, color, score, signals
    except Exception as e:
        return "ERREUR", "#ff0000", 0, []

# --- SYSTÈME DE MOT DE PASSE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    
    st.markdown("""
        <div style='text-align: center; padding: 50px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); border: 3px solid #ff9800; border-radius: 15px;'>
            <h1 style='color: #ff9800; text-shadow: 0 0 10px #ff9800;'>🔐 BLOOMBERG TERMINAL PRO</h1>
            <p style='color: #ffb84d;'>SECURE ACCESS REQUIRED</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("ENTER ACCESS CODE:", type="password", key="pwd_input")
        if st.button("🚀 EXECUTE LOGIN", use_container_width=True):
            if pwd == "1234":
                st.session_state["password_correct"] = True
                st.success("✅ ACCESS GRANTED")
                st.rerun()
            else:
                st.error("❌ ACCESS DENIED - INVALID CODE")
    return False

if not check_password():
    st.stop()

# Auto-refresh toutes les 10 minutes
st_autorefresh(interval=600000, key="global_refresh")

# --- HORLOGE TEMPS RÉEL ---
def afficher_horloge_temps_reel():
    horloge_html = """
        <div style="border: 2px solid #ff9800; padding: 15px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); text-align: center; font-family: 'Courier New', monospace; border-radius: 10px; box-shadow: 0 0 20px rgba(255, 152, 0, 0.3);">
            <div style="color: #ff9800; font-size: 14px; font-weight: bold;">⏰ SYSTEM TIME / REUNION UTC+4</div>
            <div id="clock" style="font-size: 42px; color: #00ff00; font-weight: bold; text-shadow: 0 0 10px #00ff00; margin: 10px 0;">--:--:--</div>
            <div style="color: #666; font-size: 11px; margin-top:5px;">REAL-TIME FINANCIAL DATA FEED ACTIVE</div>
        </div>
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
            setInterval(updateClock, 1000);
            updateClock();
        </script>
    """
    components.html(horloge_html, height=140)

# --- GRAPHIQUE TRADINGVIEW PRO ---
def afficher_graphique_pro(symbol, height=600):
    traduction_symbols = {
        "^FCHI": "CAC40",
        "^GSPC": "VANTAGE:SP500",
        "^IXIC": "NASDAQ",
        "BTC-USD": "BINANCE:BTCUSDT",
        "ETH-USD": "BINANCE:ETHUSDT"
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
          "studies": [
            "RSI@tv-basicstudies",
            "MASimple@tv-basicstudies",
            "MACD@tv-basicstudies",
            "BB@tv-basicstudies"
          ],
          "container_id": "tradingview_chart"
        }});
        </script>
    """
    components.html(tradingview_html, height=height)

# --- HEADER PRINCIPAL ---
st.markdown("""
    <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); border: 3px solid #ff9800; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 0 30px rgba(255, 152, 0, 0.4);'>
        <h1 style='color: #ff9800; margin: 0; font-size: 48px; text-shadow: 0 0 20px #ff9800;'>📊 BLOOMBERG TERMINAL PRO</h1>
        <p style='color: #ffb84d; margin: 10px 0 0 0; font-size: 16px;'>ADVANCED MARKET INTELLIGENCE & TRADING PLATFORM</p>
    </div>
""", unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    afficher_horloge_temps_reel()
    st.markdown("---")
    st.markdown("### 🎯 NAVIGATION PRINCIPALE")
    
    outil = st.selectbox(
        "SÉLECTIONNER UN MODULE:",
        [
            "🏠 DASHBOARD PRINCIPAL",
            "📈 ANALYSE TECHNIQUE PRO",
            "💰 CRYPTO TRACKER LIVE",
            "🎯 ANALYSEUR D'ACTION",
            "🔍 SCREENER CAC 40",
            "🤖 TRADING BOT SIMULATOR",
            "📊 PORTFOLIO MANAGER",
            "⚡ BACKTESTING ENGINE",
            "📰 NEWS SENTIMENT ANALYZER",
            "🌊 HEATMAP DE MARCHÉ",
            "📉 CORRELATION MATRIX",
            "🎲 MONTE CARLO SIMULATOR",
            "💎 FIBONACCI CALCULATOR",
            "📊 VOLUME PROFILE ANALYZER",
            "🔔 ALERT MANAGER",
            "📚 WATCHLIST MANAGER",
            "🌐 MARKET OVERVIEW",
            "💹 FOREX DASHBOARD",
            "🏦 FUNDAMENTAL SCREENER",
            "📈 PATTERN RECOGNITION"
        ]
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ PARAMÈTRES")
    refresh_rate = st.slider("Taux de rafraîchissement (sec)", 5, 300, 60)
    show_alerts = st.checkbox("Afficher les alertes", value=True)
    
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; font-size: 10px;'>
            <p>AM-TRADING TERMINAL v2.0</p>
            <p>© 2024 All Rights Reserved</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# MODULE: DASHBOARD PRINCIPAL
# ==========================================
if outil == "🏠 DASHBOARD PRINCIPAL":
    st.markdown("<h1 style='text-align: center;'>🏠 DASHBOARD PRINCIPAL</h1>", unsafe_allow_html=True)
    
    # Indices majeurs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            btc_price = get_crypto_price("BTC")
            btc_change = get_crypto_24h_change("BTC")
            st.metric("₿ BITCOIN", f"${btc_price:,.2f}" if btc_price else "N/A", f"{btc_change:+.2f}%" if btc_change else "N/A")
        except:
            st.metric("₿ BITCOIN", "N/A", "N/A")
    
    with col2:
        try:
            eth_price = get_crypto_price("ETH")
            eth_change = get_crypto_24h_change("ETH")
            st.metric("Ξ ETHEREUM", f"${eth_price:,.2f}" if eth_price else "N/A", f"{eth_change:+.2f}%" if eth_change else "N/A")
        except:
            st.metric("Ξ ETHEREUM", "N/A", "N/A")
    
    with col3:
        try:
            sp500 = yf.Ticker("^GSPC").fast_info
            st.metric("📈 S&P 500", f"{sp500['last_price']:,.2f}", f"{sp500.get('change_percent', 0):+.2f}%")
        except:
            st.metric("📈 S&P 500", "N/A", "N/A")
    
    with col4:
        try:
            cac40 = yf.Ticker("^FCHI").fast_info
            st.metric("🇫🇷 CAC 40", f"{cac40['last_price']:,.2f}", f"{cac40.get('change_percent', 0):+.2f}%")
        except:
            st.metric("🇫🇷 CAC 40", "N/A", "N/A")
    
    st.markdown("---")
    
    # Graphiques multi-colonnes
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📊 PERFORMANCE S&P 500")
        try:
            sp_data = yf.download("^GSPC", period="1mo", progress=False)
            fig_sp = go.Figure()
            fig_sp.add_trace(go.Candlestick(
                x=sp_data.index,
                open=sp_data['Open'],
                high=sp_data['High'],
                low=sp_data['Low'],
                close=sp_data['Close'],
                name='S&P 500'
            ))
            fig_sp.update_layout(
                template="plotly_dark",
                paper_bgcolor='black',
                plot_bgcolor='black',
                xaxis_rangeslider_visible=False,
                height=400
            )
            st.plotly_chart(fig_sp, use_container_width=True)
        except:
            st.error("Erreur chargement S&P 500")
    
    with col_right:
        st.markdown("### 💰 PERFORMANCE BITCOIN")
        try:
            btc_data = yf.download("BTC-USD", period="1mo", progress=False)
            fig_btc = go.Figure()
            fig_btc.add_trace(go.Candlestick(
                x=btc_data.index,
                open=btc_data['Open'],
                high=btc_data['High'],
                low=btc_data['Low'],
                close=btc_data['Close'],
                name='Bitcoin'
            ))
            fig_btc.update_layout(
                template="plotly_dark",
                paper_bgcolor='black',
                plot_bgcolor='black',
                xaxis_rangeslider_visible=False,
                height=400
            )
            st.plotly_chart(fig_btc, use_container_width=True)
        except:
            st.error("Erreur chargement Bitcoin")
    
    st.markdown("---")
    
    # Watchlist rapide
    st.markdown("### 👀 WATCHLIST RAPIDE")
    if len(st.session_state.watchlist) > 0:
        watch_cols = st.columns(5)
        for idx, ticker in enumerate(st.session_state.watchlist[:5]):
            try:
                data = yf.Ticker(ticker).fast_info
                with watch_cols[idx]:
                    st.metric(
                        ticker,
                        f"${data['last_price']:.2f}",
                        f"{data.get('change_percent', 0):+.2f}%"
                    )
            except:
                with watch_cols[idx]:
                    st.metric(ticker, "N/A", "N/A")
    else:
        st.info("Aucun ticker dans la watchlist. Utilisez le module WATCHLIST MANAGER.")
    
    st.markdown("---")
    
    # Market News
    st.markdown("### 📰 MARKET NEWS (RSS)")
    try:
        feed = feedparser.parse("https://www.investing.com/rss/news.rss")
        for entry in feed.entries[:5]:
            with st.expander(f"📌 {entry.title}"):
                st.write(entry.summary)
                st.caption(f"Source: {entry.link}")
    except:
        st.warning("Impossible de charger les news")

# ==========================================
# MODULE: ANALYSE TECHNIQUE PRO
# ==========================================
elif outil == "📈 ANALYSE TECHNIQUE PRO":
    st.markdown("<h1 style='text-align: center;'>📈 ANALYSE TECHNIQUE PROFESSIONNELLE</h1>", unsafe_allow_html=True)
    
    col_input1, col_input2, col_input3 = st.columns(3)
    with col_input1:
        ticker_tech = st.text_input("TICKER", value="AAPL", key="tech_ticker").upper()
    with col_input2:
        period_tech = st.selectbox("PÉRIODE", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], key="tech_period")
    with col_input3:
        interval_tech = st.selectbox("INTERVALLE", ["1d", "1wk", "1mo"], key="tech_interval")
    
    if st.button("🚀 LANCER L'ANALYSE", key="launch_tech_analysis"):
        try:
            with st.spinner("Chargement des données et calcul des indicateurs..."):
                # Téléchargement données
                df = yf.download(ticker_tech, period=period_tech, interval=interval_tech, progress=False)
                
                if df.empty:
                    st.error("Aucune donnée disponible pour ce ticker")
                else:
                    # Calcul indicateurs
                    df = calculate_technical_indicators(df)
                    
                    # Analyse sentiment
                    sentiment, sentiment_color, score, signals = analyze_market_sentiment(df)
                    
                    # Affichage sentiment
                    st.markdown(f"""
                        <div style='text-align: center; padding: 20px; background: {sentiment_color}22; border: 3px solid {sentiment_color}; border-radius: 15px; margin: 20px 0;'>
                            <h2 style='color: {sentiment_color}; margin: 0;'>{sentiment}</h2>
                            <p style='color: #fff; font-size: 24px; margin: 10px 0;'>SCORE: {score}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Graphique principal avec indicateurs
                    st.markdown("### 📊 GRAPHIQUE AVEC INDICATEURS")
                    
                    fig = make_subplots(
                        rows=4, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.03,
                        row_heights=[0.5, 0.2, 0.15, 0.15],
                        subplot_titles=('PRIX & MOYENNES MOBILES', 'VOLUME', 'RSI', 'MACD')
                    )
                    
                    # Candlestick
                    fig.add_trace(go.Candlestick(
                        x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'],
                        name='Prix'
                    ), row=1, col=1)
                    
                    # Bollinger Bands
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], name='BB High', line=dict(color='rgba(255,152,0,0.3)', dash='dash')), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Mid'], name='BB Mid', line=dict(color='rgba(255,152,0,0.5)')), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], name='BB Low', line=dict(color='rgba(255,152,0,0.3)', dash='dash')), row=1, col=1)
                    
                    # Moving Averages
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name='SMA 20', line=dict(color='cyan', width=1.5)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA 50', line=dict(color='magenta', width=1.5)), row=1, col=1)
                    
                    # Volume
                    colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' for i in range(len(df))]
                    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=colors), row=2, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['Volume_SMA'], name='Volume MA', line=dict(color='orange', width=2)), row=2, col=1)
                    
                    # RSI
                    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple', width=2)), row=3, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
                    
                    # MACD
                    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue', width=2)), row=4, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name='Signal', line=dict(color='red', width=2)), row=4, col=1)
                    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color='gray'), row=4, col=1)
                    
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='black',
                        plot_bgcolor='black',
                        height=1000,
                        showlegend=True,
                        xaxis_rangeslider_visible=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tableau des signaux
                    st.markdown("### 📋 SIGNAUX DÉTECTÉS")
                    signal_data = []
                    for indicator, message, signal_type in signals:
                        color_map = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡", "important": "🟠"}
                        signal_data.append({
                            "Indicateur": indicator,
                            "Signal": f"{color_map.get(signal_type, '⚪')} {message}",
                            "Type": signal_type.upper()
                        })
                    
                    df_signals = pd.DataFrame(signal_data)
                    st.dataframe(df_signals, use_container_width=True, hide_index=True)
                    
                    # Statistiques avancées
                    st.markdown("### 📊 STATISTIQUES AVANCÉES")
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    
                    latest = df.iloc[-1]
                    with col_stat1:
                        st.metric("RSI Actuel", f"{latest['RSI']:.2f}")
                        st.metric("ATR", f"{latest['ATR']:.2f}")
                    
                    with col_stat2:
                        st.metric("Stochastic K", f"{latest['Stoch_K']:.2f}")
                        st.metric("Stochastic D", f"{latest['Stoch_D']:.2f}")
                    
                    with col_stat3:
                        st.metric("ADX", f"{latest['ADX']:.2f}")
                        volatility = df['Close'].pct_change().std() * 100
                        st.metric("Volatilité", f"{volatility:.2f}%")
                    
                    with col_stat4:
                        returns_1m = ((df['Close'].iloc[-1] / df['Close'].iloc[-21]) - 1) * 100 if len(df) >= 21 else 0
                        st.metric("Return 1M", f"{returns_1m:+.2f}%")
                        max_dd = ((df['Close'].cummax() - df['Close']) / df['Close'].cummax()).max() * 100
                        st.metric("Max Drawdown", f"-{max_dd:.2f}%")
                    
        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")

# ==========================================
# MODULE: CRYPTO TRACKER LIVE
# ==========================================
elif outil == "💰 CRYPTO TRACKER LIVE":
    st.markdown("<h1 style='text-align: center;'>💰 CRYPTO TRACKER EN TEMPS RÉEL</h1>", unsafe_allow_html=True)
    
    # Top cryptos à suivre
    crypto_list = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "MATIC", "DOT", "AVAX"]
    
    st.markdown("### 🔥 TOP CRYPTOMONNAIES")
    
    crypto_data = []
    for crypto in crypto_list:
        try:
            price = get_crypto_price(crypto)
            change_24h = get_crypto_24h_change(crypto)
            
            if price and change_24h is not None:
                crypto_data.append({
                    "Crypto": crypto,
                    "Prix": f"${price:,.2f}",
                    "Change 24h": f"{change_24h:+.2f}%",
                    "Prix Num": price,
                    "Change Num": change_24h
                })
        except:
            continue
    
    if crypto_data:
        df_crypto = pd.DataFrame(crypto_data)
        
        # Grille de metrics
        cols = st.columns(5)
        for idx, row in enumerate(df_crypto.head(10).itertuples()):
            col_idx = idx % 5
            with cols[col_idx]:
                delta_color = "normal" if row._5 >= 0 else "inverse"
                st.metric(
                    row.Crypto,
                    row.Prix,
                    row._3,
                    delta_color=delta_color
                )
        
        st.markdown("---")
        
        # Graphique comparatif
        st.markdown("### 📊 PERFORMANCE 24H COMPARÉE")
        fig_crypto_comp = go.Figure(data=[
            go.Bar(
                x=df_crypto['Crypto'],
                y=df_crypto['Change Num'],
                marker_color=['green' if x >= 0 else 'red' for x in df_crypto['Change Num']],
                text=df_crypto['Change 24h'],
                textposition='auto'
            )
        ])
        fig_crypto_comp.update_layout(
            template="plotly_dark",
            paper_bgcolor='black',
            plot_bgcolor='black',
            title="Variation 24h (%)",
            xaxis_title="Crypto",
            yaxis_title="Variation (%)",
            height=500
        )
        st.plotly_chart(fig_crypto_comp, use_container_width=True)
        
        # Tableau détaillé
        st.markdown("### 📋 TABLEAU DÉTAILLÉ")
        st.dataframe(df_crypto[['Crypto', 'Prix', 'Change 24h']], use_container_width=True, hide_index=True)
    
    else:
        st.warning("Impossible de charger les données crypto")
    
    st.markdown("---")
    
    # Analyse détaillée d'une crypto
    st.markdown("### 🔍 ANALYSE DÉTAILLÉE")
    crypto_select = st.selectbox("Sélectionner une crypto", crypto_list)
    
    if st.button(f"Analyser {crypto_select}", key="analyze_crypto"):
        try:
            ticker_crypto = f"{crypto_select}-USD"
            df_crypto_detail = yf.download(ticker_crypto, period="3mo", progress=False)
            
            if not df_crypto_detail.empty:
                df_crypto_detail = calculate_technical_indicators(df_crypto_detail)
                
                # Graphique
                fig_crypto_detail = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.7, 0.3],
                    subplot_titles=(f'{crypto_select} PRIX', 'RSI')
                )
                
                fig_crypto_detail.add_trace(go.Candlestick(
                    x=df_crypto_detail.index,
                    open=df_crypto_detail['Open'],
                    high=df_crypto_detail['High'],
                    low=df_crypto_detail['Low'],
                    close=df_crypto_detail['Close'],
                    name=crypto_select
                ), row=1, col=1)
                
                fig_crypto_detail.add_trace(go.Scatter(
                    x=df_crypto_detail.index,
                    y=df_crypto_detail['SMA_20'],
                    name='SMA 20',
                    line=dict(color='cyan', width=2)
                ), row=1, col=1)
                
                fig_crypto_detail.add_trace(go.Scatter(
                    x=df_crypto_detail.index,
                    y=df_crypto_detail['RSI'],
                    name='RSI',
                    line=dict(color='purple', width=2)
                ), row=2, col=1)
                
                fig_crypto_detail.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig_crypto_detail.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                
                fig_crypto_detail.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='black',
                    plot_bgcolor='black',
                    height=700,
                    xaxis_rangeslider_visible=False
                )
                
                st.plotly_chart(fig_crypto_detail, use_container_width=True)
                
                # Stats
                sentiment, sentiment_color, score, signals = analyze_market_sentiment(df_crypto_detail)
                st.markdown(f"""
                    <div style='text-align: center; padding: 15px; background: {sentiment_color}22; border: 2px solid {sentiment_color}; border-radius: 10px;'>
                        <h3 style='color: {sentiment_color};'>{sentiment}</h3>
                        <p style='color: white;'>Score: {score}</p>
                    </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

# ==========================================
# MODULE: ANALYSEUR D'ACTION
# ==========================================
elif outil == "🎯 ANALYSEUR D'ACTION":
    st.markdown("<h1 style='text-align: center;'>🎯 ANALYSEUR D'ACTION PROFESSIONNEL</h1>", unsafe_allow_html=True)
    
    ticker = st.text_input("ENTRER LE TICKER", value="AAPL").upper()
    
    if st.button("🚀 ANALYSER", key="analyze_stock"):
        try:
            action = yf.Ticker(ticker)
            info = action.info
            hist = action.history(period="1y")
            
            if info and 'currentPrice' in info:
                # Infos générales
                st.markdown("### 📊 INFORMATIONS GÉNÉRALES")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Société", info.get('longName', ticker))
                    st.metric("Secteur", info.get('sector', 'N/A'))
                
                with col2:
                    current_price = info.get('currentPrice', 0)
                    st.metric("Prix Actuel", f"${current_price:.2f}")
                    target_price = info.get('targetMeanPrice', 0)
                    if target_price:
                        potential = ((target_price - current_price) / current_price) * 100
                        st.metric("Potentiel", f"{potential:+.2f}%")
                
                with col3:
                    market_cap = info.get('marketCap', 0)
                    st.metric("Market Cap", f"${market_cap/1e9:.2f}B" if market_cap else "N/A")
                    pe_ratio = info.get('trailingPE', 0)
                    st.metric("P/E Ratio", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
                
                with col4:
                    div_yield = info.get('dividendYield', 0)
                    st.metric("Div. Yield", f"{div_yield*100:.2f}%" if div_yield else "0%")
                    beta = info.get('beta', 0)
                    st.metric("Beta", f"{beta:.2f}" if beta else "N/A")
                
                st.markdown("---")
                
                # Graphique TradingView
                st.markdown("### 📈 GRAPHIQUE INTERACTIF")
                afficher_graphique_pro(ticker, height=500)
                
                st.markdown("---")
                
                # Analyse technique
                st.markdown("### 🔧 ANALYSE TECHNIQUE")
                if not hist.empty:
                    hist = calculate_technical_indicators(hist)
                    sentiment, sentiment_color, score, signals = analyze_market_sentiment(hist)
                    
                    st.markdown(f"""
                        <div style='text-align: center; padding: 20px; background: {sentiment_color}22; border: 3px solid {sentiment_color}; border-radius: 15px;'>
                            <h2 style='color: {sentiment_color};'>{sentiment}</h2>
                            <p style='color: white; font-size: 20px;'>Score Technique: {score}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Signaux
                    signal_cols = st.columns(3)
                    for idx, (indicator, message, signal_type) in enumerate(signals):
                        with signal_cols[idx % 3]:
                            color_map = {
                                "bullish": "#00ff00",
                                "bearish": "#ff0000",
                                "neutral": "#ff9800",
                                "important": "#00ffff"
                            }
                            emoji_map = {
                                "bullish": "🟢",
                                "bearish": "🔴",
                                "neutral": "🟡",
                                "important": "🔵"
                            }
                            st.markdown(f"""
                                <div style='padding: 10px; background: {color_map.get(signal_type, '#666')}22; border: 2px solid {color_map.get(signal_type, '#666')}; border-radius: 8px; margin: 5px 0;'>
                                    <b style='color: {color_map.get(signal_type, '#fff')};'>{emoji_map.get(signal_type, '⚪')} {indicator}</b><br>
                                    <small style='color: #ccc;'>{message}</small>
                                </div>
                            """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Analyse fondamentale (style expert)
                st.markdown("### 💎 ANALYSE FONDAMENTALE")
                
                bpa = info.get('trailingEps', 0)
                per = info.get('trailingPE', 0)
                dette_equity = info.get('debtToEquity', 0)
                roe = info.get('returnOnEquity', 0)
                profit_margin = info.get('profitMargins', 0)
                
                # Calcul Graham
                val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5 if bpa > 0 else 0
                marge_securite = ((val_theorique - current_price) / current_price) * 100 if current_price > 0 else 0
                
                col_fund1, col_fund2, col_fund3 = st.columns(3)
                
                with col_fund1:
                    st.metric("BPA (EPS)", f"${bpa:.2f}" if bpa else "N/A")
                    st.metric("P/E Ratio", f"{per:.2f}" if per else "N/A")
                
                with col_fund2:
                    st.metric("Dette/Equity", f"{dette_equity:.2f}" if dette_equity else "N/A")
                    st.metric("ROE", f"{roe*100:.2f}%" if roe else "N/A")
                
                with col_fund3:
                    st.metric("Marge Profit", f"{profit_margin*100:.2f}%" if profit_margin else "N/A")
                    st.metric("Valeur Graham", f"${val_theorique:.2f}")
                
                # Score qualité
                quality_score = 0
                if bpa > 0 and per < 20: quality_score += 5
                if dette_equity < 50: quality_score += 4
                if roe and roe > 0.15: quality_score += 4
                if profit_margin and profit_margin > 0.1: quality_score += 4
                if marge_securite > 30: quality_score += 3
                
                quality_score = min(20, quality_score)
                
                score_color = "#00ff00" if quality_score >= 15 else "#ff9800" if quality_score >= 10 else "#ff0000"
                
                st.markdown(f"""
                    <div style='text-align: center; padding: 20px; background: {score_color}22; border: 3px solid {score_color}; border-radius: 15px; margin-top: 20px;'>
                        <h1 style='color: {score_color};'>{quality_score} / 20</h1>
                        <p style='color: white;'>SCORE DE QUALITÉ FONDAMENTALE</p>
                        <p style='color: white; font-size: 18px;'>Marge de sécurité: {marge_securite:+.2f}%</p>
                    </div>
                """, unsafe_allow_html=True)
                
            else:
                st.error("Données non disponibles pour ce ticker")
                
        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")

# ==========================================
# MODULE: SCREENER CAC 40
# ==========================================
elif outil == "🔍 SCREENER CAC 40":
    st.markdown("<h1 style='text-align: center;'>🔍 SCREENER CAC 40 STRATÉGIQUE</h1>", unsafe_allow_html=True)
    st.info("Scanner complet du CAC 40 avec notation Graham + Technique")
    
    if st.button("🚀 LANCER LE SCAN COMPLET", key="scan_cac40"):
        cac40_tickers = [
            "AIR.PA", "AIRP.PA", "ALO.PA", "MT.PA", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA",
            "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA", "RMS.PA",
            "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORP.PA", "RI.PA", "PUB.PA",
            "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "SW.PA", "STMPA.PA",
            "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
        ]
        
        resultats = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, t in enumerate(cac40_tickers):
            status_text.text(f"⏳ Analyse de {t} ({i+1}/40)...")
            progress_bar.progress((i + 1) / len(cac40_tickers))
            
            try:
                action = yf.Ticker(t)
                info = action.info
                if not info or 'currentPrice' not in info:
                    continue
                
                nom = info.get('shortName', t)
                prix = info.get('currentPrice', info.get('regularMarketPrice', 1))
                bpa = info.get('trailingEps', info.get('forwardEps', 0))
                per = info.get('trailingPE', (prix/bpa if bpa > 0 else 0))
                dette_equity = info.get('debtToEquity', 0)
                payout = (info.get('payoutRatio', 0)) * 100
                roe = info.get('returnOnEquity', 0)
                profit_margin = info.get('profitMargins', 0)
                
                # Graham
                val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
                marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 else 0
                
                # Score qualité
                score = 0
                if bpa > 0:
                    if per < 12:
                        score += 5
                    elif per < 20:
                        score += 4
                    else:
                        score += 1
                else:
                    score -= 5
                
                if dette_equity < 50:
                    score += 4
                elif dette_equity < 100:
                    score += 3
                elif dette_equity > 200:
                    score -= 4
                
                if 10 < payout <= 80:
                    score += 4
                elif payout > 95:
                    score -= 4
                
                if marge_pourcent > 30:
                    score += 5
                
                if roe and roe > 0.15:
                    score += 3
                
                if profit_margin and profit_margin > 0.1:
                    score += 2
                
                score_f = min(20, max(0, score))
                
                resultats.append({
                    "Ticker": t,
                    "Nom": nom,
                    "Score": score_f,
                    "Potentiel %": round(marge_pourcent, 1),
                    "P/E": round(per, 1) if per else 0,
                    "Dette/Eq": round(dette_equity, 1) if dette_equity else 0,
                    "ROE %": round(roe*100, 1) if roe else 0,
                    "Prix €": round(prix, 2)
                })
            except:
                continue
        
        status_text.success("✅ Analyse du CAC 40 terminée!")
        df_res = pd.DataFrame(resultats).sort_values(by="Score", ascending=False)
        
        # Top 3
        st.markdown("---")
        st.markdown("### 🏆 TOP 3 OPPORTUNITÉS")
        c1, c2, c3 = st.columns(3)
        top_3 = df_res.head(3).to_dict('records')
        
        if len(top_3) >= 1:
            with c1:
                st.markdown(f"""
                    <div style='text-align: center; padding: 20px; background: #00ff0022; border: 3px solid #00ff00; border-radius: 15px;'>
                        <h2 style='color: #00ff00;'>🥇 {top_3[0]['Nom']}</h2>
                        <p style='color: white; font-size: 24px;'>{top_3[0]['Score']}/20</p>
                        <p style='color: #00ff00;'>Potentiel: {top_3[0]['Potentiel %']}%</p>
                    </div>
                """, unsafe_allow_html=True)
        
        if len(top_3) >= 2:
            with c2:
                st.markdown(f"""
                    <div style='text-align: center; padding: 20px; background: #ff980022; border: 3px solid #ff9800; border-radius: 15px;'>
                        <h2 style='color: #ff9800;'>🥈 {top_3[1]['Nom']}</h2>
                        <p style='color: white; font-size: 24px;'>{top_3[1]['Score']}/20</p>
                        <p style='color: #ff9800;'>Potentiel: {top_3[1]['Potentiel %']}%</p>
                    </div>
                """, unsafe_allow_html=True)
        
        if len(top_3) >= 3:
            with c3:
                st.markdown(f"""
                    <div style='text-align: center; padding: 20px; background: #cd7f3222; border: 3px solid #cd7f32; border-radius: 15px;'>
                        <h2 style='color: #cd7f32;'>🥉 {top_3[2]['Nom']}</h2>
                        <p style='color: white; font-size: 24px;'>{top_3[2]['Score']}/20</p>
                        <p style='color: #cd7f32;'>Potentiel: {top_3[2]['Potentiel %']}%</p>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 CLASSEMENT COMPLET")
        
        # Style du tableau
        def style_table(df):
            def color_score(val):
                if val >= 15:
                    return 'color: #00ff00; font-weight: bold;'
                elif val >= 10:
                    return 'color: #ff9800; font-weight: bold;'
                else:
                    return 'color: #ff0000; font-weight: bold;'
            
            return df.style.applymap(color_score, subset=['Score'])
        
        st.dataframe(style_table(df_res), use_container_width=True, height=600)
        
        # Graphique
        fig_screener = go.Figure(data=[go.Bar(
            x=df_res['Nom'],
            y=df_res['Score'],
            marker_color=['#00ff00' if s >= 15 else '#ff9800' if s >= 10 else '#ff0000' for s in df_res['Score']],
            text=df_res['Score'],
            textposition='auto'
        )])
        fig_screener.update_layout(
            title="COMPARAISON DES SCORES CAC 40",
            template="plotly_dark",
            paper_bgcolor='black',
            plot_bgcolor='black',
            xaxis_title="Actions",
            yaxis_title="Score /20",
            height=500
        )
        st.plotly_chart(fig_screener, use_container_width=True)

# ==========================================
# MODULE: TRADING BOT SIMULATOR
# ==========================================
elif outil == "🤖 TRADING BOT SIMULATOR":
    st.markdown("<h1 style='text-align: center;'>🤖 TRADING BOT SIMULATOR</h1>", unsafe_allow_html=True)
    st.info("Simule des stratégies de trading automatiques")
    
    col_bot1, col_bot2, col_bot3 = st.columns(3)
    
    with col_bot1:
        ticker_bot = st.text_input("TICKER", value="AAPL").upper()
    with col_bot2:
        strategy = st.selectbox("STRATÉGIE", [
            "RSI Oversold/Overbought",
            "MACD Crossover",
            "Moving Average Cross",
            "Bollinger Bounce"
        ])
    with col_bot3:
        capital_initial = st.number_input("CAPITAL INITIAL ($)", value=10000, step=1000)
    
    if st.button("🚀 LANCER LA SIMULATION", key="run_bot"):
        try:
            with st.spinner("Simulation en cours..."):
                # Téléchargement données
                df_bot = yf.download(ticker_bot, period="1y", progress=False)
                df_bot = calculate_technical_indicators(df_bot)
                
                # Variables de simulation
                capital = capital_initial
                position = 0
                trades = []
                
                # STRATÉGIE RSI
                if strategy == "RSI Oversold/Overbought":
                    for i in range(50, len(df_bot)):
                        row = df_bot.iloc[i]
                        
                        # Achat si RSI < 30
                        if row['RSI'] < 30 and position == 0:
                            shares = capital / row['Close']
                            position = shares
                            capital = 0
                            trades.append({
                                'Date': row.name,
                                'Type': 'BUY',
                                'Prix': row['Close'],
                                'Shares': shares,
                                'Capital': capital
                            })
                        
                        # Vente si RSI > 70
                        elif row['RSI'] > 70 and position > 0:
                            capital = position * row['Close']
                            trades.append({
                                'Date': row.name,
                                'Type': 'SELL',
                                'Prix': row['Close'],
                                'Shares': position,
                                'Capital': capital
                            })
                            position = 0
                
                # STRATÉGIE MACD
                elif strategy == "MACD Crossover":
                    for i in range(50, len(df_bot)):
                        row = df_bot.iloc[i]
                        prev_row = df_bot.iloc[i-1]
                        
                        # Achat si MACD croise au-dessus du signal
                        if row['MACD'] > row['MACD_Signal'] and prev_row['MACD'] <= prev_row['MACD_Signal'] and position == 0:
                            shares = capital / row['Close']
                            position = shares
                            capital = 0
                            trades.append({
                                'Date': row.name,
                                'Type': 'BUY',
                                'Prix': row['Close'],
                                'Shares': shares,
                                'Capital': capital
                            })
                        
                        # Vente si MACD croise en-dessous du signal
                        elif row['MACD'] < row['MACD_Signal'] and prev_row['MACD'] >= prev_row['MACD_Signal'] and position > 0:
                            capital = position * row['Close']
                            trades.append({
                                'Date': row.name,
                                'Type': 'SELL',
                                'Prix': row['Close'],
                                'Shares': position,
                                'Capital': capital
                            })
                            position = 0
                
                # STRATÉGIE MA CROSS
                elif strategy == "Moving Average Cross":
                    for i in range(50, len(df_bot)):
                        row = df_bot.iloc[i]
                        prev_row = df_bot.iloc[i-1]
                        
                        # Achat si SMA20 croise au-dessus SMA50
                        if row['SMA_20'] > row['SMA_50'] and prev_row['SMA_20'] <= prev_row['SMA_50'] and position == 0:
                            shares = capital / row['Close']
                            position = shares
                            capital = 0
                            trades.append({
                                'Date': row.name,
                                'Type': 'BUY',
                                'Prix': row['Close'],
                                'Shares': shares,
                                'Capital': capital
                            })
                        
                        # Vente si SMA20 croise en-dessous SMA50
                        elif row['SMA_20'] < row['SMA_50'] and prev_row['SMA_20'] >= prev_row['SMA_50'] and position > 0:
                            capital = position * row['Close']
                            trades.append({
                                'Date': row.name,
                                'Type': 'SELL',
                                'Prix': row['Close'],
                                'Shares': position,
                                'Capital': capital
                            })
                            position = 0
                
                # STRATÉGIE BOLLINGER
                elif strategy == "Bollinger Bounce":
                    for i in range(50, len(df_bot)):
                        row = df_bot.iloc[i]
                        
                        # Achat si prix touche bande basse
                        if row['Close'] <= row['BB_Low'] and position == 0:
                            shares = capital / row['Close']
                            position = shares
                            capital = 0
                            trades.append({
                                'Date': row.name,
                                'Type': 'BUY',
                                'Prix': row['Close'],
                                'Shares': shares,
                                'Capital': capital
                            })
                        
                        # Vente si prix touche bande haute
                        elif row['Close'] >= row['BB_High'] and position > 0:
                            capital = position * row['Close']
                            trades.append({
                                'Date': row.name,
                                'Type': 'SELL',
                                'Prix': row['Close'],
                                'Shares': position,
                                'Capital': capital
                            })
                            position = 0
                
                # Calcul final
                final_value = capital if capital > 0 else position * df_bot['Close'].iloc[-1]
                profit = final_value - capital_initial
                profit_pct = (profit / capital_initial) * 100
                
                # Affichage résultats
                st.markdown("### 📊 RÉSULTATS DE LA SIMULATION")
                
                col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                with col_res1:
                    st.metric("Capital Initial", f"${capital_initial:,.2f}")
                with col_res2:
                    st.metric("Capital Final", f"${final_value:,.2f}")
                with col_res3:
                    st.metric("Profit/Loss", f"${profit:+,.2f}", f"{profit_pct:+.2f}%")
                with col_res4:
                    st.metric("Nombre de Trades", len(trades))
                
                # Performance vs Buy & Hold
                buy_hold_value = capital_initial * (df_bot['Close'].iloc[-1] / df_bot['Close'].iloc[0])
                buy_hold_profit = buy_hold_value - capital_initial
                buy_hold_pct = (buy_hold_profit / capital_initial) * 100
                
                st.markdown("---")
                st.markdown("### 📈 COMPARAISON BUY & HOLD")
                col_comp1, col_comp2 = st.columns(2)
                with col_comp1:
                    st.metric("Stratégie Bot", f"${final_value:,.2f}", f"{profit_pct:+.2f}%")
                with col_comp2:
                    st.metric("Buy & Hold", f"${buy_hold_value:,.2f}", f"{buy_hold_pct:+.2f}%")
                
                # Graphique des trades
                if trades:
                    st.markdown("---")
                    st.markdown("### 📍 POINTS D'ENTRÉE/SORTIE")
                    
                    fig_trades = go.Figure()
                    
                    # Prix
                    fig_trades.add_trace(go.Scatter(
                        x=df_bot.index,
                        y=df_bot['Close'],
                        name='Prix',
                        line=dict(color='white', width=2)
                    ))
                    
                    # Points d'achat
                    buys = [t for t in trades if t['Type'] == 'BUY']
                    if buys:
                        fig_trades.add_trace(go.Scatter(
                            x=[t['Date'] for t in buys],
                            y=[t['Prix'] for t in buys],
                            mode='markers',
                            name='ACHAT',
                            marker=dict(color='green', size=15, symbol='triangle-up')
                        ))
                    
                    # Points de vente
                    sells = [t for t in trades if t['Type'] == 'SELL']
                    if sells:
                        fig_trades.add_trace(go.Scatter(
                            x=[t['Date'] for t in sells],
                            y=[t['Prix'] for t in sells],
                            mode='markers',
                            name='VENTE',
                            marker=dict(color='red', size=15, symbol='triangle-down')
                        ))
                    
                    fig_trades.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='black',
                        plot_bgcolor='black',
                        title=f"Simulation {strategy} sur {ticker_bot}",
                        height=600,
                        xaxis_title="Date",
                        yaxis_title="Prix"
                    )
                    
                    st.plotly_chart(fig_trades, use_container_width=True)
                    
                    # Tableau des trades
                    st.markdown("### 📋 HISTORIQUE DES TRADES")
                    df_trades = pd.DataFrame(trades)
                    st.dataframe(df_trades, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Erreur simulation: {str(e)}")

# ==========================================
# MODULE: PORTFOLIO MANAGER
# ==========================================
elif outil == "📊 PORTFOLIO MANAGER":
    st.markdown("<h1 style='text-align: center;'>📊 PORTFOLIO MANAGER</h1>", unsafe_allow_html=True)
    
    st.markdown("### 💼 VOTRE PORTEFEUILLE")
    
    # Résumé du portfolio
    total_value = st.session_state.portfolio["cash"]
    for pos in st.session_state.portfolio["positions"]:
        try:
            current_price = yf.Ticker(pos['ticker']).fast_info['last_price']
            total_value += pos['shares'] * current_price
        except:
            pass
    
    col_port1, col_port2, col_port3 = st.columns(3)
    with col_port1:
        st.metric("Valeur Totale", f"${total_value:,.2f}")
    with col_port2:
        st.metric("Cash Disponible", f"${st.session_state.portfolio['cash']:,.2f}")
    with col_port3:
        invested = total_value - st.session_state.portfolio['cash']
        st.metric("Investi", f"${invested:,.2f}")
    
    st.markdown("---")
    
    # Ajouter une position
    st.markdown("### ➕ AJOUTER UNE POSITION")
    col_add1, col_add2, col_add3, col_add4 = st.columns(4)
    
    with col_add1:
        new_ticker = st.text_input("Ticker", key="new_ticker").upper()
    with col_add2:
        new_shares = st.number_input("Nombre d'actions", min_value=0.0, value=1.0, step=0.1, key="new_shares")
    with col_add3:
        new_price = st.number_input("Prix d'achat", min_value=0.0, value=100.0, step=0.1, key="new_price")
    with col_add4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Ajouter", key="add_position"):
            cost = new_shares * new_price
            if cost <= st.session_state.portfolio['cash']:
                st.session_state.portfolio['positions'].append({
                    'ticker': new_ticker,
                    'shares': new_shares,
                    'buy_price': new_price,
                    'date': datetime.now().strftime("%Y-%m-%d")
                })
                st.session_state.portfolio['cash'] -= cost
                st.success(f"✅ Position ajoutée: {new_shares} {new_ticker} @ ${new_price}")
                st.rerun()
            else:
                st.error("❌ Cash insuffisant")
    
    st.markdown("---")
    
    # Affichage des positions
    if st.session_state.portfolio["positions"]:
        st.markdown("### 📊 POSITIONS ACTUELLES")
        
        positions_data = []
        for pos in st.session_state.portfolio["positions"]:
            try:
                ticker_info = yf.Ticker(pos['ticker']).fast_info
                current_price = ticker_info['last_price']
                current_value = pos['shares'] * current_price
                cost_basis = pos['shares'] * pos['buy_price']
                profit_loss = current_value - cost_basis
                profit_loss_pct = (profit_loss / cost_basis) * 100
                
                positions_data.append({
                    'Ticker': pos['ticker'],
                    'Shares': pos['shares'],
                    'Prix Achat': f"${pos['buy_price']:.2f}",
                    'Prix Actuel': f"${current_price:.2f}",
                    'Valeur': f"${current_value:,.2f}",
                    'P/L': f"${profit_loss:+,.2f}",
                    'P/L %': f"{profit_loss_pct:+.2f}%",
                    'Date': pos['date']
                })
            except:
                positions_data.append({
                    'Ticker': pos['ticker'],
                    'Shares': pos['shares'],
                    'Prix Achat': f"${pos['buy_price']:.2f}",
                    'Prix Actuel': 'N/A',
                    'Valeur': 'N/A',
                    'P/L': 'N/A',
                    'P/L %': 'N/A',
                    'Date': pos['date']
                })
        
        df_positions = pd.DataFrame(positions_data)
        st.dataframe(df_positions, use_container_width=True, hide_index=True)
        
        # Graphique de répartition
        st.markdown("### 🥧 RÉPARTITION DU PORTFOLIO")
        fig_pie = go.Figure(data=[go.Pie(
            labels=[p['Ticker'] for p in positions_data],
            values=[float(p['Valeur'].replace('$', '').replace(',', '')) for p in positions_data if p['Valeur'] != 'N/A']
        )])
        fig_pie.update_layout(
            template="plotly_dark",
            paper_bgcolor='black',
            plot_bgcolor='black'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aucune position dans le portefeuille")

# ==========================================
# MODULE: BACKTESTING ENGINE
# ==========================================
elif outil == "⚡ BACKTESTING ENGINE":
    st.markdown("<h1 style='text-align: center;'>⚡ BACKTESTING ENGINE</h1>", unsafe_allow_html=True)
    st.info("Testez vos stratégies de trading sur données historiques")
    
    col_bt1, col_bt2, col_bt3 = st.columns(3)
    
    with col_bt1:
        ticker_bt = st.text_input("TICKER", value="AAPL", key="bt_ticker").upper()
    with col_bt2:
        period_bt = st.selectbox("PÉRIODE", ["1y", "2y", "5y", "10y"], key="bt_period")
    with col_bt3:
        capital_bt = st.number_input("CAPITAL ($)", value=10000, step=1000, key="bt_capital")
    
    # Paramètres de stratégie
    st.markdown("### ⚙️ PARAMÈTRES DE STRATÉGIE")
    col_strat1, col_strat2, col_strat3 = st.columns(3)
    
    with col_strat1:
        rsi_low = st.slider("RSI Achat (<)", 10, 40, 30)
    with col_strat2:
        rsi_high = st.slider("RSI Vente (>)", 60, 90, 70)
    with col_strat3:
        stop_loss_pct = st.slider("Stop Loss (%)", 1, 20, 5)
    
    if st.button("🚀 LANCER LE BACKTEST", key="launch_backtest"):
        try:
            with st.spinner("Backtesting en cours..."):
                # Télécharger données
                df_bt = yf.download(ticker_bt, period=period_bt, progress=False)
                df_bt = calculate_technical_indicators(df_bt)
                
                # Variables
                capital = capital_bt
                position = 0
                entry_price = 0
                trades_bt = []
                equity_curve = []
                
                for i in range(50, len(df_bt)):
                    row = df_bt.iloc[i]
                    
                    # Stop Loss
                    if position > 0 and entry_price > 0:
                        if row['Close'] <= entry_price * (1 - stop_loss_pct/100):
                            # Vente stop loss
                            capital = position * row['Close']
                            trades_bt.append({
                                'Date': row.name,
                                'Type': 'STOP LOSS',
                                'Prix': row['Close'],
                                'P/L': capital - (position * entry_price)
                            })
                            position = 0
                            entry_price = 0
                    
                    # Signal achat RSI
                    if row['RSI'] < rsi_low and position == 0:
                        shares = capital / row['Close']
                        position = shares
                        entry_price = row['Close']
                        capital = 0
                        trades_bt.append({
                            'Date': row.name,
                            'Type': 'BUY',
                            'Prix': row['Close'],
                            'P/L': 0
                        })
                    
                    # Signal vente RSI
                    elif row['RSI'] > rsi_high and position > 0:
                        capital = position * row['Close']
                        profit = capital - (position * entry_price)
                        trades_bt.append({
                            'Date': row.name,
                            'Type': 'SELL',
                            'Prix': row['Close'],
                            'P/L': profit
                        })
                        position = 0
                        entry_price = 0
                    
                    # Equity curve
                    current_equity = capital if capital > 0 else position * row['Close']
                    equity_curve.append({
                        'Date': row.name,
                        'Equity': current_equity
                    })
                
                # Valeur finale
                final_value = capital if capital > 0 else position * df_bt['Close'].iloc[-1]
                total_return = ((final_value - capital_bt) / capital_bt) * 100
                
                # Calcul métriques
                winning_trades = [t for t in trades_bt if t['P/L'] > 0]
                losing_trades = [t for t in trades_bt if t['P/L'] < 0]
                win_rate = (len(winning_trades) / len([t for t in trades_bt if t['Type'] in ['SELL', 'STOP LOSS']]) * 100) if len([t for t in trades_bt if t['Type'] in ['SELL', 'STOP LOSS']]) > 0 else 0
                
                avg_win = np.mean([t['P/L'] for t in winning_trades]) if winning_trades else 0
                avg_loss = np.mean([t['P/L'] for t in losing_trades]) if losing_trades else 0
                
                # Max drawdown
                equity_series = pd.Series([e['Equity'] for e in equity_curve])
                running_max = equity_series.cummax()
                drawdown = ((equity_series - running_max) / running_max * 100)
                max_drawdown = drawdown.min()
                
                # Sharpe Ratio (simplifié)
                returns = equity_series.pct_change().dropna()
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
                
                # Affichage résultats
                st.markdown("### 📊 RÉSULTATS DU BACKTEST")
                
                col_metrics = st.columns(5)
                with col_metrics[0]:
                    st.metric("Return Total", f"{total_return:+.2f}%")
                with col_metrics[1]:
                    st.metric("Nombre Trades", len(trades_bt))
                with col_metrics[2]:
                    st.metric("Win Rate", f"{win_rate:.1f}%")
                with col_metrics[3]:
                    st.metric("Max Drawdown", f"{max_drawdown:.2f}%")
                with col_metrics[4]:
                    st.metric("Sharpe Ratio", f"{sharpe:.2f}")
                
                st.markdown("---")
                
                col_perf = st.columns(4)
                with col_perf[0]:
                    st.metric("Capital Initial", f"${capital_bt:,.2f}")
                with col_perf[1]:
                    st.metric("Capital Final", f"${final_value:,.2f}")
                with col_perf[2]:
                    st.metric("Avg Win", f"${avg_win:+,.2f}")
                with col_perf[3]:
                    st.metric("Avg Loss", f"${avg_loss:+,.2f}")
                
                st.markdown("---")
                
                # Graphique Equity Curve
                st.markdown("### 📈 EQUITY CURVE")
                df_equity = pd.DataFrame(equity_curve)
                
                fig_equity = go.Figure()
                fig_equity.add_trace(go.Scatter(
                    x=df_equity['Date'],
                    y=df_equity['Equity'],
                    fill='tozeroy',
                    name='Portfolio Value',
                    line=dict(color='cyan', width=3)
                ))
                
                # Ligne du capital initial
                fig_equity.add_hline(
                    y=capital_bt,
                    line_dash="dash",
                    line_color="orange",
                    annotation_text="Capital Initial"
                )
                
                fig_equity.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='black',
                    plot_bgcolor='black',
                    title="Évolution du Capital",
                    height=500,
                    xaxis_title="Date",
                    yaxis_title="Valeur ($)"
                )
                
                st.plotly_chart(fig_equity, use_container_width=True)
                
                # Tableau des trades
                st.markdown("### 📋 HISTORIQUE DES TRADES")
                df_trades_bt = pd.DataFrame(trades_bt)
                st.dataframe(df_trades_bt, use_container_width=True, hide_index=True)
                
                # Statistiques détaillées
                st.markdown("### 📊 STATISTIQUES DÉTAILLÉES")
                col_stats1, col_stats2 = st.columns(2)
                
                with col_stats1:
                    st.markdown("**Trades Gagnants**")
                    st.write(f"- Nombre: {len(winning_trades)}")
                    st.write(f"- Profit Total: ${sum([t['P/L'] for t in winning_trades]):,.2f}")
                    st.write(f"- Profit Moyen: ${avg_win:,.2f}")
                
                with col_stats2:
                    st.markdown("**Trades Perdants**")
                    st.write(f"- Nombre: {len(losing_trades)}")
                    st.write(f"- Perte Totale: ${sum([t['P/L'] for t in losing_trades]):,.2f}")
                    st.write(f"- Perte Moyenne: ${avg_loss:,.2f}")
                
        except Exception as e:
            st.error(f"Erreur backtest: {str(e)}")

# ==========================================
# MODULE: NEWS SENTIMENT ANALYZER
# ==========================================
elif outil == "📰 NEWS SENTIMENT ANALYZER":
    st.markdown("<h1 style='text-align: center;'>📰 NEWS SENTIMENT ANALYZER</h1>", unsafe_allow_html=True)
    
    # Flux RSS multiples
    news_sources = {
        "Investing.com": "https://www.investing.com/rss/news.rss",
        "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
        "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss"
    }
    
    source_selected = st.selectbox("Choisir la source", list(news_sources.keys()))
    
    if st.button("📡 CHARGER LES NEWS", key="load_news"):
        try:
            with st.spinner(f"Chargement depuis {source_selected}..."):
                feed = feedparser.parse(news_sources[source_selected])
                
                if feed.entries:
                    st.success(f"✅ {len(feed.entries)} articles chargés")
                    
                    for idx, entry in enumerate(feed.entries[:15]):
                        # Analyse sentiment basique (keywords)
                        title_lower = entry.title.lower()
                        sentiment = "NEUTRE"
                        sentiment_color = "#ff9800"
                        
                        positive_keywords = ['gain', 'hausse', 'record', 'profit', 'surge', 'rally', 'bull']
                        negative_keywords = ['chute', 'baisse', 'crash', 'perte', 'fall', 'drop', 'bear', 'decline']
                        
                        if any(kw in title_lower for kw in positive_keywords):
                            sentiment = "POSITIF 🟢"
                            sentiment_color = "#00ff00"
                        elif any(kw in title_lower for kw in negative_keywords):
                            sentiment = "NÉGATIF 🔴"
                            sentiment_color = "#ff0000"
                        
                        with st.expander(f"📌 {entry.title}"):
                            st.markdown(f"""
                                <div style='padding: 10px; background: {sentiment_color}22; border-left: 4px solid {sentiment_color}; border-radius: 5px; margin-bottom: 10px;'>
                                    <b>Sentiment:</b> {sentiment}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.write(entry.summary if hasattr(entry, 'summary') else "Pas de résumé disponible")
                            st.caption(f"🔗 [Lire l'article complet]({entry.link})")
                            st.caption(f"📅 {entry.published if hasattr(entry, 'published') else 'Date inconnue'}")
                else:
                    st.warning("Aucun article trouvé")
        except Exception as e:
            st.error(f"Erreur chargement news: {str(e)}")

# ==========================================
# MODULE: HEATMAP DE MARCHÉ
# ==========================================
elif outil == "🌊 HEATMAP DE MARCHÉ":
    st.markdown("<h1 style='text-align: center;'>🌊 HEATMAP DE MARCHÉ</h1>", unsafe_allow_html=True)
    
    market_choice = st.selectbox("SÉLECTIONNER UN MARCHÉ", [
        "S&P 500 Secteurs",
        "CAC 40",
        "Crypto Top 20",
        "NASDAQ 100"
    ])
    
    if st.button("🎨 GÉNÉRER LA HEATMAP", key="gen_heatmap"):
        try:
            with st.spinner("Génération de la heatmap..."):
                heatmap_data = []
                
                if market_choice == "S&P 500 Secteurs":
                    sectors = {
                        "Tech": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"],
                        "Finance": ["JPM", "BAC", "WFC", "GS", "MS"],
                        "Healthcare": ["UNH", "JNJ", "PFE", "ABBV", "MRK"],
                        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
                        "Consumer": ["AMZN", "TSLA", "HD", "NKE", "MCD"]
                    }
                    
                    for sector, tickers in sectors.items():
                        for ticker in tickers:
                            try:
                                data = yf.Ticker(ticker).fast_info
                                change = data.get('change_percent', 0)
                                heatmap_data.append({
                                    'Sector': sector,
                                    'Ticker': ticker,
                                    'Change': change
                                })
                            except:
                                pass
                
                elif market_choice == "CAC 40":
                    cac_tickers = [
                        "AIR.PA", "AIRP.PA", "ALO.PA", "BNP.PA", "EN.PA", "CAP.PA",
                        "CA.PA", "ACA.PA", "DSY.PA", "ENGI.PA", "RMS.PA", "MC.PA"
                    ]
                    for ticker in cac_tickers:
                        try:
                            data = yf.Ticker(ticker).fast_info
                            change = data.get('change_percent', 0)
                            heatmap_data.append({
                                'Ticker': ticker.replace('.PA', ''),
                                'Change': change
                            })
                        except:
                            pass
                
                elif market_choice == "Crypto Top 20":
                    cryptos = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "MATIC", "DOT", "AVAX"]
                    for crypto in cryptos:
                        try:
                            change = get_crypto_24h_change(crypto)
                            heatmap_data.append({
                                'Crypto': crypto,
                                'Change': change
                            })
                        except:
                            pass
                
                if heatmap_data:
                    df_heatmap = pd.DataFrame(heatmap_data)
                    
                    # Créer la heatmap
                    if 'Sector' in df_heatmap.columns:
                        # Heatmap par secteur
                        fig_heatmap = go.Figure(data=go.Treemap(
                            labels=df_heatmap['Ticker'],
                            parents=df_heatmap['Sector'],
                            values=abs(df_heatmap['Change']),
                            marker=dict(
                                colors=df_heatmap['Change'],
                                colorscale='RdYlGn',
                                cmid=0,
                                colorbar=dict(title="Change %")
                            ),
                            text=df_heatmap.apply(lambda x: f"{x['Ticker']}<br>{x['Change']:+.2f}%", axis=1),
                            textposition='middle center'
                        ))
                    else:
                        # Heatmap simple
                        fig_heatmap = go.Figure(data=go.Treemap(
                            labels=df_heatmap[df_heatmap.columns[0]],
                            values=abs(df_heatmap['Change']),
                            marker=dict(
                                colors=df_heatmap['Change'],
                                colorscale='RdYlGn',
                                cmid=0,
                                colorbar=dict(title="Change %")
                            ),
                            text=df_heatmap.apply(lambda x: f"{x[df_heatmap.columns[0]]}<br>{x['Change']:+.2f}%", axis=1),
                            textposition='middle center'
                        ))
                    
                    fig_heatmap.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='black',
                        height=700,
                        title=f"Heatmap: {market_choice}"
                    )
                    
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                    
                    # Stats
                    st.markdown("### 📊 STATISTIQUES")
                    col_heat1, col_heat2, col_heat3 = st.columns(3)
                    
                    with col_heat1:
                        avg_change = df_heatmap['Change'].mean()
                        st.metric("Variation Moyenne", f"{avg_change:+.2f}%")
                    
                    with col_heat2:
                        top_gainer = df_heatmap.loc[df_heatmap['Change'].idxmax()]
                        st.metric("Top Gainer", f"{top_gainer[0]}", f"{top_gainer['Change']:+.2f}%")
                    
                    with col_heat3:
                        top_loser = df_heatmap.loc[df_heatmap['Change'].idxmin()]
                        st.metric("Top Loser", f"{top_loser[0]}", f"{top_loser['Change']:+.2f}%")
                
        except Exception as e:
            st.error(f"Erreur génération heatmap: {str(e)}")

# ==========================================
# MODULE: CORRELATION MATRIX
# ==========================================
elif outil == "📉 CORRELATION MATRIX":
    st.markdown("<h1 style='text-align: center;'>📉 MATRICE DE CORRÉLATION</h1>", unsafe_allow_html=True)
    st.info("Analysez les corrélations entre différents actifs")
    
    # Sélection des tickers
    default_tickers = "AAPL, MSFT, GOOGL, AMZN, TSLA"
    tickers_input = st.text_input("TICKERS (séparés par des virgules)", value=default_tickers)
    period_corr = st.selectbox("PÉRIODE", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
    
    if st.button("📊 CALCULER LA CORRÉLATION", key="calc_corr"):
        try:
            tickers_list = [t.strip().upper() for t in tickers_input.split(',')]
            
            with st.spinner("Téléchargement des données..."):
                # Télécharger toutes les données
                df_corr = pd.DataFrame()
                for ticker in tickers_list:
                    try:
                        data = yf.download(ticker, period=period_corr, progress=False)['Close']
                        df_corr[ticker] = data
                    except:
                        st.warning(f"Impossible de charger {ticker}")
                
                if not df_corr.empty:
                    # Calculer les returns
                    returns = df_corr.pct_change().dropna()
                    
                    # Matrice de corrélation
                    corr_matrix = returns.corr()
                    
                    # Heatmap
                    st.markdown("### 🔥 MATRICE DE CORRÉLATION")
                    fig_corr = go.Figure(data=go.Heatmap(
                        z=corr_matrix.values,
                        x=corr_matrix.columns,
                        y=corr_matrix.columns,
                        colorscale='RdBu',
                        zmid=0,
                        text=corr_matrix.values,
                        texttemplate='%{text:.2f}',
                        textfont={"size": 12},
                        colorbar=dict(title="Corrélation")
                    ))
                    
                    fig_corr.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='black',
                        height=600,
                        title="Corrélation des Returns"
                    )
                    
                    st.plotly_chart(fig_corr, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Scatter plots des paires les plus corrélées
                    st.markdown("### 📈 PAIRES FORTEMENT CORRÉLÉES")
                    
                    # Trouver les paires avec corrélation > 0.7
                    strong_corr = []
                    for i in range(len(corr_matrix.columns)):
                        for j in range(i+1, len(corr_matrix.columns)):
                            corr_val = corr_matrix.iloc[i, j]
                            if abs(corr_val) > 0.7:
                                strong_corr.append((
                                    corr_matrix.columns[i],
                                    corr_matrix.columns[j],
                                    corr_val
                                ))
                    
                    if strong_corr:
                        for ticker1, ticker2, corr_val in strong_corr[:3]:  # Top 3
                            fig_scatter = go.Figure()
                            fig_scatter.add_trace(go.Scatter(
                                x=returns[ticker1],
                                y=returns[ticker2],
                                mode='markers',
                                name=f'{ticker1} vs {ticker2}',
                                marker=dict(
                                    size=8,
                                    color=returns[ticker1],
                                    colorscale='Viridis',
                                    showscale=True
                                )
                            ))
                            
                            fig_scatter.update_layout(
                                template="plotly_dark",
                                paper_bgcolor='black',
                                plot_bgcolor='black',
                                title=f"{ticker1} vs {ticker2} (Corr: {corr_val:.2f})",
                                xaxis_title=f"{ticker1} Returns",
                                yaxis_title=f"{ticker2} Returns",
                                height=400
                            )
                            
                            st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Tableau de corrélation
                    st.markdown("### 📋 TABLEAU DE CORRÉLATION")
                    st.dataframe(corr_matrix.style.background_gradient(cmap='RdYlGn', vmin=-1, vmax=1), use_container_width=True)
                    
        except Exception as e:
            st.error(f"Erreur calcul corrélation: {str(e)}")

# ==========================================
# MODULE: MONTE CARLO SIMULATOR
# ==========================================
elif outil == "🎲 MONTE CARLO SIMULATOR":
    st.markdown("<h1 style='text-align: center;'>🎲 MONTE CARLO SIMULATOR</h1>", unsafe_allow_html=True)
    st.info("Simulez des milliers de scénarios futurs basés sur les données historiques")
    
    col_mc1, col_mc2, col_mc3 = st.columns(3)
    
    with col_mc1:
        ticker_mc = st.text_input("TICKER", value="AAPL", key="mc_ticker").upper()
    with col_mc2:
        days_forecast = st.number_input("JOURS À SIMULER", min_value=30, max_value=365, value=90, step=30)
    with col_mc3:
        num_simulations = st.number_input("NOMBRE DE SIMULATIONS", min_value=100, max_value=10000, value=1000, step=100)
    
    if st.button("🎲 LANCER LA SIMULATION", key="run_monte_carlo"):
        try:
            with st.spinner("Simulation Monte Carlo en cours..."):
                # Télécharger données historiques
                df_mc = yf.download(ticker_mc, period="1y", progress=False)
                
                if not df_mc.empty:
                    # Calculer returns et volatilité
                    returns = df_mc['Close'].pct_change().dropna()
                    mean_return = returns.mean()
                    std_return = returns.std()
                    
                    last_price = df_mc['Close'].iloc[-1]
                    
                    # Simulations
                    simulations = np.zeros((days_forecast, num_simulations))
                    
                    for sim in range(num_simulations):
                        prices = [last_price]
                        for day in range(days_forecast):
                            price = prices[-1] * (1 + np.random.normal(mean_return, std_return))
                            prices.append(price)
                        simulations[:, sim] = prices[1:]
                    
                    # Graphique des simulations
                    st.markdown("### 📊 SIMULATIONS MONTE CARLO")
                    
                    fig_mc = go.Figure()
                    
                    # Afficher un échantillon de simulations
                    sample_size = min(100, num_simulations)
                    for i in range(0, num_simulations, num_simulations // sample_size):
                        fig_mc.add_trace(go.Scatter(
                            y=simulations[:, i],
                            mode='lines',
                            line=dict(width=0.5, color='rgba(0, 255, 255, 0.1)'),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                    
                    # Moyenne et percentiles
                    mean_path = simulations.mean(axis=1)
                    percentile_5 = np.percentile(simulations, 5, axis=1)
                    percentile_95 = np.percentile(simulations, 95, axis=1)
                    
                    fig_mc.add_trace(go.Scatter(
                        y=mean_path,
                        mode='lines',
                        name='Moyenne',
                        line=dict(color='yellow', width=3)
                    ))
                    
                    fig_mc.add_trace(go.Scatter(
                        y=percentile_95,
                        mode='lines',
                        name='95e Percentile',
                        line=dict(color='green', width=2, dash='dash')
                    ))
                    
                    fig_mc.add_trace(go.Scatter(
                        y=percentile_5,
                        mode='lines',
                        name='5e Percentile',
                        line=dict(color='red', width=2, dash='dash'),
                        fill='tonexty',
                        fillcolor='rgba(255, 255, 0, 0.1)'
                    ))
                    
                    # Ligne du prix actuel
                    fig_mc.add_hline(
                        y=last_price,
                        line_dash="dash",
                        line_color="white",
                        annotation_text="Prix Actuel"
                    )
                    
                    fig_mc.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='black',
                        plot_bgcolor='black',
                        title=f"Simulations Monte Carlo - {ticker_mc}",
                        xaxis_title="Jours",
                        yaxis_title="Prix ($)",
                        height=600
                    )
                    
                    st.plotly_chart(fig_mc, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Statistiques
                    st.markdown("### 📊 STATISTIQUES DES SIMULATIONS")
                    
                    final_prices = simulations[-1, :]
                    
                    col_stat_mc1, col_stat_mc2, col_stat_mc3, col_stat_mc4 = st.columns(4)
                    
                    with col_stat_mc1:
                        st.metric("Prix Actuel", f"${last_price:.2f}")
                        st.metric("Prix Moyen (J+{})".format(days_forecast), f"${mean_path[-1]:.2f}")
                    
                    with col_stat_mc2:
                        median_price = np.median(final_prices)
                        st.metric("Prix Médian", f"${median_price:.2f}")
                        prob_increase = (final_prices > last_price).sum() / num_simulations * 100
                        st.metric("Prob. Hausse", f"{prob_increase:.1f}%")
                    
                    with col_stat_mc3:
                        st.metric("95e Percentile", f"${percentile_95[-1]:.2f}")
                        st.metric("5e Percentile", f"${percentile_5[-1]:.2f}")
                    
                    with col_stat_mc4:
                        max_price = final_prices.max()
                        min_price = final_prices.min()
                        st.metric("Prix Maximum", f"${max_price:.2f}")
                        st.metric("Prix Minimum", f"${min_price:.2f}")
                    
                    st.markdown("---")
                    
                    # Distribution des prix finaux
                    st.markdown("### 📈 DISTRIBUTION DES PRIX FINAUX")
                    
                    fig_dist = go.Figure()
                    fig_dist.add_trace(go.Histogram(
                        x=final_prices,
                        nbinsx=50,
                        name='Distribution',
                        marker_color='cyan'
                    ))
                    
                    fig_dist.add_vline(
                        x=last_price,
                        line_dash="dash",
                        line_color="white",
                        annotation_text="Prix Actuel"
                    )
                    
                    fig_dist.update_layout(
                        template="plotly_dark",
                        paper_bgcolor='black',
                        plot_bgcolor='black',
                        title="Distribution des Prix Finaux",
                        xaxis_title="Prix ($)",
                        yaxis_title="Fréquence",
                        height=400
                    )
                    
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                    # Tableau des scénarios
                    st.markdown("### 📋 SCÉNARIOS CLÉS")
                    scenarios = pd.DataFrame({
                        'Scénario': ['Pessimiste (5%)', 'Conservateur (25%)', 'Médian (50%)', 'Optimiste (75%)', 'Très Optimiste (95%)'],
                        'Prix Final': [
                            np.percentile(final_prices, 5),
                            np.percentile(final_prices, 25),
                            np.percentile(final_prices, 50),
                            np.percentile(final_prices, 75),
                            np.percentile(final_prices, 95)
                        ]
                    })
                    scenarios['Variation %'] = ((scenarios['Prix Final'] - last_price) / last_price * 100).round(2)
                    scenarios['Prix Final'] = scenarios['Prix Final'].round(2)
                    
                    st.dataframe(scenarios, use_container_width=True, hide_index=True)
                    
        except Exception as e:
            st.error(f"Erreur simulation Monte Carlo: {str(e)}")

# ==========================================
# MODULES ADDITIONNELS (suite en commentaire car limite atteinte)
# ==========================================

# Les modules suivants peuvent être ajoutés :
# - Fibonacci Calculator
# - Volume Profile Analyzer
# - Alert Manager
# - Watchlist Manager
# - Market Overview
# - Forex Dashboard
# - Fundamental Screener
# - Pattern Recognition

# Ils suivraient la même structure avec des fonctionnalités spécifiques

st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px; padding: 20px;'>
        <p>🚀 BLOOMBERG TERMINAL PRO - v2.0</p>
        <p>© 2024 AM-TRADING | All Rights Reserved</p>
        <p style='color: #ff9800;'>⚡ POWERED BY ADVANCED ANALYTICS</p>
    </div>
""", unsafe_allow_html=True)
