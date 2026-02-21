import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import feedparser
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ============================================
# FONCTIONS DE DONNÉES AMÉLIORÉES
# ============================================

def get_ticker_from_name(query):
    """Convertit un nom en Ticker avec fallback"""
    query = query.strip()
    if len(query) <= 5 and query.isalpha():
        return query.upper()
    
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        if res.get('quotes'):
            return res['quotes'][0]['symbol']
    except:
        pass
    return query.upper()

@st.cache_data(ttl=300)
def get_rss_news(source):
    """News RSS avec gestion des erreurs"""
    news_items = []
    rss_urls = {
        "Boursorama": "https://www.boursorama.com/rss/actualites/economie/",
        "Investing": "https://fr.investing.com/rss/news.rss",
        "Reuters": "https://news.google.com/rss/search?q=finance+Reuters&hl=fr&gl=FR&ceid=FR:fr",
        "Bloomberg": "https://news.google.com/rss/search?q=finance+Bloomberg&hl=fr&gl=FR&ceid=FR:fr"
    }
    
    url = rss_urls.get(source)
    if not url:
        return []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            try:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime(*entry.published_parsed[:6])
                    time_str = dt.strftime("%H:%M")
                    date_str = dt.strftime("%d/%m")
                else:
                    time_str = "LIVE"
                    date_str = datetime.now().strftime("%d/%m")
            except:
                time_str = "LIVE"
                date_str = datetime.now().strftime("%d/%m")

            news_items.append({
                'title': entry.title,
                'link': entry.link,
                'time': time_str,
                'date': date_str,
                'source': source
            })
    except:
        pass

    return news_items

@st.cache_data(ttl=30)
def get_market_overview():
    """Vue d'ensemble des marchés principaux"""
    indices = {
        '^GSPC': 'S&P 500',
        '^DJI': 'DOW JONES',
        '^IXIC': 'NASDAQ',
        '^FTSE': 'FTSE 100',
        '^FCHI': 'CAC 40',
        '^N225': 'NIKKEI',
        'BTC-USD': 'BITCOIN',
        'ETH-USD': 'ETHEREUM',
        'GC=F': 'GOLD',
        'CL=F': 'OIL'
    }
    
    overview = []
    for symbol, name in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                price = float(hist['Close'].iloc[-1])
                prev_price = float(hist['Close'].iloc[-2])
                change = ((price - prev_price) / prev_price) * 100
                volume = int(hist['Volume'].iloc[-1]) if hist['Volume'].iloc[-1] > 0 else 0
                
                overview.append({
                    'symbol': symbol,
                    'name': name,
                    'price': price,
                    'change': change,
                    'volume': volume
                })
        except:
            continue
    
    return overview

@st.cache_data(ttl=30)
def get_detailed_ticker_data(ticker_symbol):
    """Données détaillées d'un ticker avec tous les ratios"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        hist = ticker.history(period="1y")
        
        if hist.empty:
            return None
        
        # Prix actuel
        current_price = info.get('currentPrice', 0)
        if current_price == 0 or current_price is None:
            current_price = float(hist['Close'].iloc[-1])
        
        # Calcul des variations
        if len(hist) >= 2:
            prev_close = float(hist['Close'].iloc[-2])
            change_1d = ((current_price - prev_close) / prev_close) * 100
        else:
            change_1d = 0
        
        if len(hist) >= 5:
            price_5d_ago = float(hist['Close'].iloc[-5])
            change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
        else:
            change_5d = 0
        
        if len(hist) >= 20:
            price_1m_ago = float(hist['Close'].iloc[-20])
            change_1m = ((current_price - price_1m_ago) / price_1m_ago) * 100
        else:
            change_1m = 0
        
        # Calcul des moyennes mobiles
        if len(hist) >= 50:
            sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            distance_sma50 = ((current_price - sma_50) / sma_50) * 100
        else:
            sma_50 = None
            distance_sma50 = 0
        
        if len(hist) >= 200:
            sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            distance_sma200 = ((current_price - sma_200) / sma_200) * 100
        else:
            sma_200 = None
            distance_sma200 = 0
        
        # Calcul du RSI
        if len(hist) >= 14:
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            loss = loss.replace(0, 0.0001)
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1])
        else:
            current_rsi = 50
        
        # Volume
        avg_volume = hist['Volume'].mean()
        current_volume = hist['Volume'].iloc[-1]
        volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 1
        
        # Ratios financiers
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('trailingPE', 0)
        forward_pe = info.get('forwardPE', 0)
        peg_ratio = info.get('pegRatio', 0)
        price_to_book = info.get('priceToBook', 0)
        dividend_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        beta = info.get('beta', 0)
        eps = info.get('trailingEps', 0)
        revenue = info.get('totalRevenue', 0)
        profit_margin = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
        debt_to_equity = info.get('debtToEquity', 0)
        
        # 52 week range
        week_52_high = info.get('fiftyTwoWeekHigh', 0)
        week_52_low = info.get('fiftyTwoWeekLow', 0)
        if week_52_high > 0 and week_52_low > 0:
            range_position = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100
        else:
            range_position = 50
        
        return {
            'symbol': ticker_symbol,
            'name': info.get('longName', ticker_symbol),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'currency': info.get('currency', 'USD'),
            'current_price': current_price,
            'change_1d': change_1d,
            'change_5d': change_5d,
            'change_1m': change_1m,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'distance_sma50': distance_sma50,
            'distance_sma200': distance_sma200,
            'rsi': current_rsi,
            'volume': current_volume,
            'avg_volume': avg_volume,
            'volume_ratio': volume_ratio,
            'market_cap': market_cap,
            'pe_ratio': pe_ratio,
            'forward_pe': forward_pe,
            'peg_ratio': peg_ratio,
            'price_to_book': price_to_book,
            'dividend_yield': dividend_yield,
            'beta': beta,
            'eps': eps,
            'revenue': revenue,
            'profit_margin': profit_margin,
            'roe': roe,
            'debt_to_equity': debt_to_equity,
            'week_52_high': week_52_high,
            'week_52_low': week_52_low,
            'range_position': range_position,
            'hist': hist
        }
    except Exception as e:
        return None

def create_advanced_candlestick_chart(df, ticker_name, height=600):
    """Graphique chandelier avancé avec indicateurs"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=('', '', '', '')
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price',
        increasing_line_color='#00C853',
        decreasing_line_color='#FF3B30',
        increasing_fillcolor='#00C853',
        decreasing_fillcolor='#FF3B30'
    ), row=1, col=1)
    
    # Moving Averages
    if len(df) >= 20:
        sma_20 = df['Close'].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_20,
            name='SMA 20',
            line=dict(color='#FF9500', width=1.5),
            opacity=0.7
        ), row=1, col=1)
    
    if len(df) >= 50:
        sma_50 = df['Close'].rolling(window=50).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_50,
            name='SMA 50',
            line=dict(color='#00BFFF', width=1.5),
            opacity=0.7
        ), row=1, col=1)
    
    # RSI
    if len(df) >= 14:
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        loss = loss.replace(0, 0.0001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi,
            name='RSI',
            line=dict(color='#9370DB', width=2)
        ), row=2, col=1)
        
        fig.add_hline(y=70, line_dash="dash", line_color="#FF3B30", line_width=1, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00C853", line_width=1, row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="#666666", line_width=1, row=2, col=1)
    
    # MACD
    if len(df) >= 26:
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        fig.add_trace(go.Scatter(
            x=df.index, y=macd,
            name='MACD',
            line=dict(color='#00BFFF', width=2)
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=df.index, y=signal,
            name='Signal',
            line=dict(color='#FF9500', width=2)
        ), row=3, col=1)
        
        colors = ['#00C853' if val >= 0 else '#FF3B30' for val in histogram]
        fig.add_trace(go.Bar(
            x=df.index, y=histogram,
            name='Histogram',
            marker_color=colors,
            opacity=0.5
        ), row=3, col=1)
    
    # Volume
    colors = ['#00C853' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#FF3B30' for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.4
    ), row=4, col=1)
    
    # Layout
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#000000',
        plot_bgcolor='#0A0A0A',
        font=dict(color='#CCCCCC', family='Arial, sans-serif', size=11),
        title=dict(
            text=f"<b>{ticker_name}</b> | ADVANCED TECHNICAL ANALYSIS",
            font=dict(color='#FF9500', size=16),
            x=0.5,
            xanchor='center'
        ),
        height=height,
        showlegend=True,
        legend=dict(
            bgcolor='#1A1A1A',
            bordercolor='#333333',
            borderwidth=1,
            font=dict(size=10)
        ),
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Grilles
    for i in range(1, 5):
        fig.update_xaxes(gridcolor='#1A1A1A', showgrid=True, row=i, col=1)
        fig.update_yaxes(gridcolor='#1A1A1A', showgrid=True, row=i, col=1)
    
    # Labels
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="Volume", row=4, col=1)
    
    return fig

# ============================================
# INTERFACE BLOOMBERG ULTRA-PROFESSIONNELLE
# ============================================

def show_interface_pro():
    # CSS BLOOMBERG TERMINAL
    st.markdown("""
    <style>
        /* === BASE === */
        .stApp { background-color: #000000; }
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; max-width: 100% !important; }
        
        /* === BLOOMBERG HEADER === */
        .bloomberg-main-header {
            background: linear-gradient(90deg, #FF9500 0%, #FFB84D 100%);
            padding: 15px 30px;
            margin: -0.5rem -1rem 20px -1rem;
            border-bottom: 3px solid #000000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .bloomberg-title {
            color: #000000;
            font-size: 24px;
            font-weight: 900;
            letter-spacing: 2px;
            margin: 0;
        }
        .bloomberg-subtitle {
            color: #000000;
            font-size: 11px;
            opacity: 0.8;
            letter-spacing: 1px;
        }
        
        /* === TICKER TAPE === */
        .ticker-tape-container {
            background: linear-gradient(90deg, #0A0A0A 0%, #1A1A1A 50%, #0A0A0A 100%);
            border-top: 2px solid #FF9500;
            border-bottom: 2px solid #FF9500;
            padding: 12px 0;
            margin: 20px -1rem;
            overflow: hidden;
            white-space: nowrap;
        }
        .ticker-tape {
            display: inline-block;
            animation: scroll-left 60s linear infinite;
            padding-left: 100%;
        }
        @keyframes scroll-left {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        .ticker-item {
            display: inline-block;
            margin: 0 40px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .ticker-symbol { color: #FF9500; font-weight: bold; margin-right: 10px; }
        .ticker-price { color: #FFFFFF; margin-right: 10px; }
        .ticker-up { color: #00C853; font-weight: bold; }
        .ticker-down { color: #FF3B30; font-weight: bold; }
        
        /* === SECTION HEADERS === */
        .section-header {
            color: #FF9500;
            font-size: 14px;
            font-weight: bold;
            margin: 25px 0 12px 0;
            letter-spacing: 1.5px;
            border-bottom: 2px solid #333;
            padding-bottom: 8px;
            text-transform: uppercase;
        }
        
        /* === METRIC CARDS BLOOMBERG === */
        .metric-card-pro {
            background: linear-gradient(145deg, #0A0A0A, #1A1A1A);
            border: 1px solid #333333;
            border-left: 3px solid #FF9500;
            border-radius: 3px;
            padding: 18px;
            margin: 10px 0;
        }
        .metric-label-pro {
            color: #888888;
            font-size: 10px;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .metric-value-pro {
            color: #00C853;
            font-size: 28px;
            font-weight: 900;
            font-family: 'Courier New', monospace;
            line-height: 1.2;
        }
        .metric-delta-pro {
            color: #00C853;
            font-size: 14px;
            font-weight: bold;
            margin-top: 8px;
        }
        .metric-delta-negative {
            color: #FF3B30 !important;
        }
        
        /* === LIVE PRICE DISPLAY === */
        .live-price-container {
            background: linear-gradient(145deg, #0A0A0A, #151515);
            border: 2px solid #FF9500;
            border-radius: 5px;
            padding: 25px;
            text-align: center;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(255, 149, 0, 0.3);
        }
        .live-price-symbol {
            color: #FF9500;
            font-size: 16px;
            letter-spacing: 3px;
            font-weight: bold;
            margin-bottom: 12px;
        }
        .live-price-value {
            color: #00C853;
            font-size: 56px;
            font-weight: 900;
            font-family: 'Courier New', monospace;
            text-shadow: 0 0 10px rgba(0, 200, 83, 0.4);
            line-height: 1;
        }
        .live-price-change {
            font-size: 22px;
            font-weight: bold;
            margin-top: 12px;
        }
        .live-price-volume {
            color: #888888;
            font-size: 12px;
            margin-top: 10px;
            letter-spacing: 1px;
        }
        
        /* === STATUS INDICATORS === */
        .status-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1.5px;
            margin: 5px;
        }
        .status-open {
            background: #00C853;
            color: #000000;
        }
        .status-closed {
            background: #FF3B30;
            color: #FFFFFF;
        }
        
        /* === DATA TABLE BLOOMBERG === */
        .data-row {
            display: flex;
            justify-content: space-between;
            padding: 12px 15px;
            border-bottom: 1px solid #1A1A1A;
            background: #0A0A0A;
        }
        .data-row:hover {
            background: #151515;
        }
        .data-label {
            color: #888888;
            font-size: 12px;
            letter-spacing: 0.5px;
        }
        .data-value {
            color: #FFFFFF;
            font-weight: bold;
            font-size: 13px;
        }
        
        /* === NEWS FEED === */
        .news-item {
            background: #0A0A0A;
            border-left: 3px solid #FF9500;
            padding: 12px 15px;
            margin: 8px 0;
            border-radius: 2px;
        }
        .news-item:hover {
            background: #151515;
        }
        .news-time {
            color: #888888;
            font-size: 10px;
            margin-bottom: 5px;
        }
        .news-title {
            color: #FFFFFF;
            font-size: 13px;
            font-weight: 500;
            line-height: 1.4;
        }
        
        /* === TABS BLOOMBERG === */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #0A0A0A;
            border-bottom: 2px solid #333;
            gap: 5px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #666;
            font-size: 12px;
            padding: 8px 16px;
            border: none;
            background-color: transparent;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: #FF9500 !important;
            border-bottom: 3px solid #FF9500 !important;
            background-color: transparent;
        }
        
        /* === EXPANDERS === */
        [data-testid="stExpander"] {
            background-color: #0A0A0A !important;
            border: 1px solid #333 !important;
            border-radius: 3px;
            margin-bottom: 8px;
        }
        [data-testid="stExpander"] summary:hover {
            color: #FF9500 !important;
            background-color: #151515 !important;
        }
        
        /* === PROGRESS BAR === */
        .progress-container {
            background: #1A1A1A;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-bar {
            height: 100%;
            transition: width 0.3s ease;
        }
        
        /* === SCROLLBAR === */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #0A0A0A; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #FF9500; }
        
        /* === INPUT BLOOMBERG === */
        input, textarea {
            background-color: #1A1A1A !important;
            color: #FFFFFF !important;
            border: 2px solid #333 !important;
            border-radius: 3px !important;
            font-family: 'Courier New', monospace !important;
        }
        input:focus, textarea:focus {
            border-color: #FF9500 !important;
            box-shadow: 0 0 10px rgba(255, 149, 0, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # === BLOOMBERG HEADER ===
    st.markdown("""
    <div class='bloomberg-main-header'>
        <div>
            <div class='bloomberg-title'>⚡ BLOOMBERG TERMINAL PRO</div>
            <div class='bloomberg-subtitle'>REAL-TIME MARKET INTELLIGENCE PLATFORM</div>
        </div>
        <div class='bloomberg-subtitle' id='clock-header'>LOADING...</div>
    </div>
    <script>
        function updateHeaderClock() {
            const now = new Date();
            const h = String(now.getHours()).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('clock-header').innerText = 
                'MARKET TIME: ' + h + ':' + m + ':' + s + ' | LIVE FEED ACTIVE';
        }
        setInterval(updateHeaderClock, 1000);
        updateHeaderClock();
    </script>
    """, unsafe_allow_html=True)
    
    # === TICKER TAPE ===
    market_overview = get_market_overview()
    if market_overview:
        ticker_html = ""
        for ticker in market_overview * 2:  # Doubler pour scroll infini
            color_class = "ticker-up" if ticker['change'] >= 0 else "ticker-down"
            arrow = "▲" if ticker['change'] >= 0 else "▼"
            sign = "+" if ticker['change'] >= 0 else ""
            
            ticker_html += f"""
            <span class='ticker-item'>
                <span class='ticker-symbol'>{ticker['name']}</span>
                <span class='ticker-price'>{ticker['price']:,.2f}</span>
                <span class='{color_class}'>{arrow} {sign}{ticker['change']:.2f}%</span>
            </span>
            """
        
        st.markdown(f"""
        <div class='ticker-tape-container'>
            <div class='ticker-tape'>{ticker_html}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # === MARKET STATUS ===
    now = datetime.utcnow() + timedelta(hours=4)
    is_market_hours = (9 <= now.hour < 16) and (now.weekday() < 5)
    
    col_status1, col_status2, col_status3, col_status4 = st.columns(4)
    with col_status1:
        status_class = "status-open" if is_market_hours else "status-closed"
        status_text = "OPEN" if is_market_hours else "CLOSED"
        st.markdown(f"<div class='status-badge {status_class}'>🇺🇸 NYSE: {status_text}</div>", unsafe_allow_html=True)
    with col_status2:
        st.markdown(f"<div class='status-badge {status_class}'>📊 NASDAQ: {status_text}</div>", unsafe_allow_html=True)
    with col_status3:
        st.markdown(f"<div class='status-badge status-closed'>🇪🇺 EURONEXT: CLOSED</div>", unsafe_allow_html=True)
    with col_status4:
        st.markdown(f"<div class='status-badge status-open'>₿ CRYPTO: 24/7</div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # === LAYOUT PRINCIPAL (70/30) ===
    col_main, col_sidebar = st.columns([7, 3])
    
    # === COLONNE PRINCIPALE ===
    with col_main:
        st.markdown('<div class="section-header">🔍 ADVANCED EQUITY ANALYZER</div>', unsafe_allow_html=True)
        
        # Recherche améliorée
        search_col1, search_col2 = st.columns([4, 1])
        with search_col1:
            search_input = st.text_input(
                "SEARCH TICKER OR COMPANY NAME",
                value="AAPL",
                label_visibility="collapsed",
                key="search_pro"
            )
        with search_col2:
            analyze_btn = st.button("🚀 ANALYZE", use_container_width=True)
        
        if search_input:
            ticker_symbol = get_ticker_from_name(search_input)
            ticker_data = get_detailed_ticker_data(ticker_symbol)
            
            if ticker_data:
                # === PRIX EN TEMPS RÉEL ===
                price_color = "#00C853" if ticker_data['change_1d'] >= 0 else "#FF3B30"
                arrow = "▲" if ticker_data['change_1d'] >= 0 else "▼"
                sign = "+" if ticker_data['change_1d'] >= 0 else ""
                
                st.markdown(f"""
                <div class='live-price-container'>
                    <div class='live-price-symbol'>{ticker_symbol} | {ticker_data['name']}</div>
                    <div class='live-price-value' style='color: {price_color};'>{ticker_data['currency']} {ticker_data['current_price']:,.2f}</div>
                    <div class='live-price-change' style='color: {price_color};'>{arrow} {sign}{ticker_data['change_1d']:.2f}% TODAY</div>
                    <div class='live-price-volume'>VOL: {ticker_data['volume']:,} | AVG: {ticker_data['avg_volume']:,.0f} ({ticker_data['volume_ratio']:.2f}x)</div>
                </div>
                """, unsafe_allow_html=True)
                
                # === MÉTRIQUES RAPIDES ===
                st.markdown('<div class="section-header">📊 KEY PERFORMANCE INDICATORS</div>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class='metric-card-pro'>
                        <div class='metric-label-pro'>1 DAY CHANGE</div>
                        <div class='metric-value-pro' style='color: {"#00C853" if ticker_data["change_1d"] >= 0 else "#FF3B30"};'>
                            {sign}{ticker_data['change_1d']:.2f}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class='metric-card-pro'>
                        <div class='metric-label-pro'>5 DAY CHANGE</div>
                        <div class='metric-value-pro' style='color: {"#00C853" if ticker_data["change_5d"] >= 0 else "#FF3B30"};'>
                            {"+"+str(round(ticker_data['change_5d'], 2)) if ticker_data['change_5d'] >= 0 else round(ticker_data['change_5d'], 2)}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class='metric-card-pro'>
                        <div class='metric-label-pro'>1 MONTH CHANGE</div>
                        <div class='metric-value-pro' style='color: {"#00C853" if ticker_data["change_1m"] >= 0 else "#FF3B30"};'>
                            {"+"+str(round(ticker_data['change_1m'], 2)) if ticker_data['change_1m'] >= 0 else round(ticker_data['change_1m'], 2)}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    rsi_color = "#FF3B30" if ticker_data['rsi'] > 70 else "#00C853" if ticker_data['rsi'] < 30 else "#FFB84D"
                    st.markdown(f"""
                    <div class='metric-card-pro'>
                        <div class='metric-label-pro'>RSI (14)</div>
                        <div class='metric-value-pro' style='color: {rsi_color};'>
                            {ticker_data['rsi']:.1f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === GRAPHIQUE AVANCÉ ===
                st.markdown('<div class="section-header">📈 TECHNICAL ANALYSIS CHART</div>', unsafe_allow_html=True)
                
                fig = create_advanced_candlestick_chart(ticker_data['hist'], ticker_data['name'], height=700)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === DONNÉES FINANCIÈRES COMPLÈTES ===
                st.markdown('<div class="section-header">💰 FUNDAMENTAL DATA</div>', unsafe_allow_html=True)
                
                tab1, tab2, tab3, tab4 = st.tabs(["📊 OVERVIEW", "💹 VALUATION", "📈 PERFORMANCE", "⚖️ POSITION"])
                
                with tab1:
                    # Overview
                    st.markdown(f"""
                    <div class='data-row'><span class='data-label'>SECTOR</span><span class='data-value'>{ticker_data['sector']}</span></div>
                    <div class='data-row'><span class='data-label'>INDUSTRY</span><span class='data-value'>{ticker_data['industry']}</span></div>
                    <div class='data-row'><span class='data-label'>MARKET CAP</span><span class='data-value'>${ticker_data['market_cap']/1e9:.2f}B</span></div>
                    <div class='data-row'><span class='data-label'>BETA</span><span class='data-value'>{ticker_data['beta']:.2f}</span></div>
                    <div class='data-row'><span class='data-label'>52W HIGH</span><span class='data-value'>${ticker_data['week_52_high']:.2f}</span></div>
                    <div class='data-row'><span class='data-label'>52W LOW</span><span class='data-value'>${ticker_data['week_52_low']:.2f}</span></div>
                    """, unsafe_allow_html=True)
                    
                    # 52W Range Position
                    st.markdown("<div style='margin: 15px 0;'><span class='data-label'>52 WEEK RANGE POSITION</span></div>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class='progress-container'>
                        <div class='progress-bar' style='width: {ticker_data['range_position']:.1f}%; background: linear-gradient(90deg, #FF3B30, #FFB84D, #00C853);'></div>
                    </div>
                    <div style='text-align: center; color: #888; font-size: 11px;'>{ticker_data['range_position']:.1f}% of range</div>
                    """, unsafe_allow_html=True)
                
                with tab2:
                    # Valuation
                    st.markdown(f"""
                    <div class='data-row'><span class='data-label'>P/E RATIO (TTM)</span><span class='data-value'>{ticker_data['pe_ratio']:.2f if ticker_data['pe_ratio'] > 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>FORWARD P/E</span><span class='data-value'>{ticker_data['forward_pe']:.2f if ticker_data['forward_pe'] > 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>PEG RATIO</span><span class='data-value'>{ticker_data['peg_ratio']:.2f if ticker_data['peg_ratio'] > 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>PRICE / BOOK</span><span class='data-value'>{ticker_data['price_to_book']:.2f if ticker_data['price_to_book'] > 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>EPS (TTM)</span><span class='data-value'>${ticker_data['eps']:.2f if ticker_data['eps'] != 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>DIVIDEND YIELD</span><span class='data-value'>{ticker_data['dividend_yield']:.2f}% if ticker_data['dividend_yield'] > 0 else "N/A"}</span></div>
                    """, unsafe_allow_html=True)
                
                with tab3:
                    # Performance
                    st.markdown(f"""
                    <div class='data-row'><span class='data-label'>REVENUE (TTM)</span><span class='data-value'>${ticker_data['revenue']/1e9:.2f}B if ticker_data['revenue'] > 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>PROFIT MARGIN</span><span class='data-value'>{ticker_data['profit_margin']:.2f}% if ticker_data['profit_margin'] != 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>ROE</span><span class='data-value'>{ticker_data['roe']:.2f}% if ticker_data['roe'] != 0 else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>DEBT / EQUITY</span><span class='data-value'>{ticker_data['debt_to_equity']:.2f if ticker_data['debt_to_equity'] > 0 else "N/A"}</span></div>
                    """, unsafe_allow_html=True)
                
                with tab4:
                    # Technical Position
                    st.markdown(f"""
                    <div class='data-row'><span class='data-label'>SMA 50</span><span class='data-value'>${ticker_data['sma_50']:.2f if ticker_data['sma_50'] else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>DISTANCE FROM SMA 50</span><span class='data-value' style='color: {"#00C853" if ticker_data["distance_sma50"] >= 0 else "#FF3B30"};'>{ticker_data['distance_sma50']:+.2f}%</span></div>
                    <div class='data-row'><span class='data-label'>SMA 200</span><span class='data-value'>${ticker_data['sma_200']:.2f if ticker_data['sma_200'] else "N/A"}</span></div>
                    <div class='data-row'><span class='data-label'>DISTANCE FROM SMA 200</span><span class='data-value' style='color: {"#00C853" if ticker_data["distance_sma200"] >= 0 else "#FF3B30"};'>{ticker_data['distance_sma200']:+.2f}%</span></div>
                    <div class='data-row'><span class='data-label'>RSI (14)</span><span class='data-value' style='color: {"#FF3B30" if ticker_data["rsi"] > 70 else "#00C853" if ticker_data["rsi"] < 30 else "#FFB84D"};'>{ticker_data['rsi']:.2f}</span></div>
                    """, unsafe_allow_html=True)
                    
                    # RSI Gauge
                    st.markdown("<div style='margin: 20px 0;'><span class='data-label'>RSI INDICATOR</span></div>", unsafe_allow_html=True)
                    rsi_position = ticker_data['rsi']
                    if rsi_position > 70:
                        rsi_status = "OVERBOUGHT - SELL SIGNAL"
                        rsi_color = "#FF3B30"
                    elif rsi_position < 30:
                        rsi_status = "OVERSOLD - BUY SIGNAL"
                        rsi_color = "#00C853"
                    else:
                        rsi_status = "NEUTRAL"
                        rsi_color = "#FFB84D"
                    
                    st.markdown(f"""
                    <div class='progress-container' style='background: linear-gradient(90deg, #00C853 0%, #00C853 30%, #FFB84D 30%, #FFB84D 70%, #FF3B30 70%, #FF3B30 100%);'>
                        <div style='position: absolute; left: {rsi_position}%; top: 50%; transform: translate(-50%, -50%); width: 3px; height: 12px; background: #FFF; box-shadow: 0 0 5px #FFF;'></div>
                    </div>
                    <div style='text-align: center; color: {rsi_color}; font-size: 12px; font-weight: bold; margin-top: 5px;'>{rsi_status}</div>
                    """, unsafe_allow_html=True)
            else:
                st.error("❌ Unable to load data for this ticker. Please check the symbol and try again.")
    
    # === COLONNE SIDEBAR (NEWS & ALERTS) ===
    with col_sidebar:
        st.markdown('<div class="section-header">📰 LIVE NEWS FEED</div>', unsafe_allow_html=True)
        
        news_tabs = st.tabs(["📊 Bloomberg", "💼 Reuters", "🇫🇷 Boursorama", "🌐 Investing"])
        
        for idx, (tab, source) in enumerate(zip(news_tabs, ["Bloomberg", "Reuters", "Boursorama", "Investing"])):
            with tab:
                news_items = get_rss_news(source)
                if news_items:
                    with st.container(height=400):
                        for news in news_items[:10]:
                            st.markdown(f"""
                            <div class='news-item'>
                                <div class='news-time'>{news['date']} {news['time']} | {news['source']}</div>
                                <div class='news-title'>{news['title']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("📖 READ", key=f"news_{source}_{news_items.index(news)}", use_container_width=True):
                                st.write(f"[Open Article]({news['link']})")
                else:
                    st.info("No recent news available")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Market Movers
        st.markdown('<div class="section-header">🔥 TOP MOVERS (24H)</div>', unsafe_allow_html=True)
        
        market_data = get_market_overview()
        if market_data:
            # Trier par variation absolue
            sorted_movers = sorted(market_data, key=lambda x: abs(x['change']), reverse=True)[:8]
            
            with st.container(height=350):
                for mover in sorted_movers:
                    color = "#00C853" if mover['change'] >= 0 else "#FF3B30"
                    arrow = "▲" if mover['change'] >= 0 else "▼"
                    sign = "+" if mover['change'] >= 0 else ""
                    
                    st.markdown(f"""
                    <div class='data-row'>
                        <div>
                            <div style='color: #FFF; font-weight: bold; font-size: 13px;'>{mover['name']}</div>
                            <div style='color: #888; font-size: 11px;'>${mover['price']:,.2f}</div>
                        </div>
                        <div style='text-align: right; color: {color}; font-weight: bold;'>
                            {arrow} {sign}{mover['change']:.2f}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# Fonction d'export
__all__ = ['show_interface_pro']
