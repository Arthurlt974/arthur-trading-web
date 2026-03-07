import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime

# ============================================
# 1. FONCTIONS DE DONNÉES
# ============================================

def get_ticker_from_name(query):
    """
    Convertit un nom d'entreprise ou de crypto en Ticker.
    Ex: 'Apple' -> 'AAPL', 'Bitcoin' -> 'BTC-USD'
    """
    query = query.strip()
    # Si c'est déjà un ticker court (ex: AAPL, BTC)
    if len(query) <= 5 and query.isalpha():
        return query.upper()
    
    try:
        # Recherche via l'API Yahoo Finance
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res['quotes']:
            return res['quotes'][0]['symbol']
    except:
        pass
    return query.upper()

@st.cache_data(ttl=300, show_spinner=False)
def get_rss_news(source, _version=2):
    """
    Récupère les news via RSS pour Boursorama ou Investing
    """
    news_items = []
    
    rss_urls = {
        "Boursorama": "https://www.boursorama.com/rss/actualites/economie/",
        "Investing": "https://fr.investing.com/rss/news.rss",
        "WSJ Markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "WSJ Finance": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
    }
    
    url = rss_urls.get(source)
    if not url: return []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]: # On garde les 10 derniers pour avoir de quoi scroller
            try:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime(*entry.published_parsed[:6])
                    time_str = dt.strftime("%d/%m %H:%M")
                else:
                    time_str = "Récemment"
            except:
                time_str = "--:--"

            news_items.append({
                'title': entry.title,
                'link': entry.link,
                'time': time_str,
                'source': source
            })
    except Exception:
        pass

    return news_items

@st.cache_data(ttl=60)
def get_upcoming_events():
    """Données événements (Simulées ou Live)"""
    events = []
    symbols = ['AAPL', 'NVDA', 'BTC-USD', 'ETH-USD', 'TSLA']
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                open_price = hist['Open'].iloc[0]
                change = ((price - open_price) / open_price) * 100
                name = symbol.replace('-USD', '')
                events.append({'name': name, 'time': 'LIVE', 'price': price, 'change': change})
        except: pass
    return events

@st.cache_data(ttl=5)
def get_heatmap_data():
    """Données Heatmap"""
    symbols = ['AAPL', 'NVDA', 'BTC-USD', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META']
    heatmap_data = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                open_price = hist['Open'].iloc[0]
                change = ((price - open_price) / open_price) * 100
                heatmap_data.append({'symbol': symbol.replace('-USD', ''), 'price': price, 'change': change})
        except: pass
    return heatmap_data

@st.cache_data(ttl=60)
def get_market_stats():
    """Données Stats"""
    symbols = ['AAPL', 'NVDA', 'BTC-USD', 'TSLA']
    stats = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                change_5d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                stats.append({'symbol': symbol.replace('-USD', ''), 'change': change_5d})
        except: pass
    return stats

# ============================================
#  FRAGMENT TEMPS RÉEL (REFRESH AUTO)
# ============================================

@st.fragment(run_every=10) # Rafraîchit cette fonction toutes les 10 secondes
def render_realtime_heatmap():
    st.markdown('<div class="section-header">🔥 MARKET HEATMAP (LIVE 10s)</div>', unsafe_allow_html=True)
    hm_data = get_heatmap_data()
    
    # Conteneur pour le style
    st.markdown('<div style="background-color: #0A0A0A; border: 1px solid #1A1A1A; border-radius: 4px; padding: 10px;">', unsafe_allow_html=True)
    for item in hm_data:
        c_class = 'ticker-change-positive' if item['change'] >= 0 else 'ticker-change-negative'
        sign = '+' if item['change'] >= 0 else ''
        bar_col = f"rgba(0,200,83,0.8)" if item['change'] > 0 else f"rgba(255,59,48,0.8)"
        width_pct = min(abs(item['change'])*10, 100)
           
        st.markdown(f'''
        <div class="heatmap-row">
            <span class="heatmap-symbol">{item['symbol']}</span>
            <span class="heatmap-price">${item['price']:,.2f}</span>
            <span class="heatmap-change {c_class}">{sign}{item['change']:.2f}%</span>
            <div class="heatmap-bar" style="background: linear-gradient(90deg, {bar_col} {width_pct}%, transparent {width_pct}%);"></div>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



# ============================================
# 2. FONCTION PRINCIPALE (Module)
# ============================================

def show_interface_pro():
    # --- CSS PERSONNALISÉ ---
    st.markdown("""
    <style>
        .stApp { background-color: #000000; }
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; max-width: 100% !important; }
        
        /* Ticker Style */
        .ticker-compact { background-color: #0A0A0A; border-bottom: 1px solid #2D2D30; padding: 8px 20px; display: flex; gap: 30px; overflow-x: auto; white-space: nowrap; margin-bottom: 15px; }
        .ticker-item { display: inline-flex; align-items: center; gap: 8px; font-family: 'Arial', sans-serif; font-size: 13px; }
        .ticker-symbol { color: #999999; font-weight: 600; }
        .ticker-price { color: #FFFFFF; font-weight: bold; }
        .ticker-change-positive { color: #00C853; }
        .ticker-change-negative { color: #FF3B30; }
        
        /* Section Header */
        .section-header { color: #FF9500; font-size: 14px; font-weight: bold; margin-bottom: 10px; letter-spacing: 0.5px; border-bottom: 1px solid #333; padding-bottom: 5px; }
        
        /* Style spécifique pour les Expanders (Encadrés News) en mode Dark */
        [data-testid="stExpander"] {
            background-color: #0A0A0A !important;
            border: 1px solid #333 !important;
            border-radius: 4px;
            margin-bottom: 8px;
        }
        [data-testid="stExpander"] summary:hover {
            color: #FF9500 !important;
        }
        [data-testid="stExpander"] p, [data-testid="stExpander"] span {
            color: #e0e0e0;
            font-size: 13px;
        }
        
        /* Heatmap & Event Styles */
        .heatmap-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid #1A1A1A; }
        .heatmap-symbol { color: #FFFFFF; font-weight: bold; font-size: 13px; width: 60px; }
        .heatmap-price { color: #FFFFFF; font-size: 13px; width: 80px; }
        .heatmap-change { width: 60px; text-align: right; font-size: 12px; }
        .heatmap-bar { flex: 1; height: 6px; margin: 0 10px; border-radius: 2px; }
        
        .event-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #1A1A1A; }
        .event-name { color: #FFFFFF; font-size: 13px; font-weight: 500; }
        .event-price { color: #FFFFFF; font-size: 14px; font-weight: bold; }
        .event-change-positive { color: #00C853; font-size: 12px; }
        .event-change-negative { color: #FF3B30; font-size: 12px; }
        
        .market-stat-item { display: flex; align-items: center; margin-bottom: 8px; color: #fff; font-size: 12px;}
        .market-stat-symbol { width: 50px; font-weight: bold; }
        .market-stat-bar { flex-grow: 1; height: 8px; background: #222; margin: 0 10px; border-radius: 2px; }

        /* Custom Tabs Style */
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; border-bottom: 1px solid #333; gap: 10px; }
        .stTabs [data-baseweb="tab"] { color: #666; font-size: 12px; padding: 5px 10px; border: none; background-color: transparent; }
        .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #FF9500 !important; border-bottom: 2px solid #FF9500 !important; background-color: transparent; font-weight: bold; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0A0A0A; }
        ::-webkit-scrollbar-thumb { background: #2D2D30; border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)

    # --- LAYOUT PRINCIPAL (2/3 Gauche, 1/3 Droite) ---
    col_left, col_right = st.columns([2, 1])

    # --- COLONNE GAUCHE ---
    with col_left:
        st.markdown('<div class="section-header">📊 TERMINAL DE RECHERCHE</div>', unsafe_allow_html=True)
        
        # BARRE DE RECHERCHE
        search_input = st.text_input("RECHERCHER (NOM OU SYMBOLE)", value="Nvidia", label_visibility="collapsed")
        
        # Traitement du Ticker
        raw_ticker = get_ticker_from_name(search_input)
        
        # Logique de formatage pour TradingView
        cryptos = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOT"]
        if any(c in raw_ticker for c in cryptos) or "USD" in raw_ticker:
            clean_symbol = raw_ticker.split('-')[0].replace("USD", "")
            tv_symbol = f"BINANCE:{clean_symbol}USDT"
        else:
            tv_symbol = raw_ticker # TradingView gère bien les actions US en direct (ex: AAPL)

        # 1. GRAPHIQUE PRINCIPAL
        from chart_module import render_chart
        import time as _t
        _chart_html = render_chart(
            symbol=raw_ticker,
            interval="1d",
            limit=200,
            height=600,
            pair_label=raw_ticker,
            exchange="Yahoo Finance",
            show_ma=True,
        ) + f"<!-- {raw_ticker}:{int(_t.time()*1000)} -->"
        components.html(_chart_html, height=610, scrolling=False)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Heatmap
        st.markdown('<div class="section-header">🔥 MARKET HEATMAP (LIVE TRADINGVIEW)</div>', unsafe_allow_html=True)
        
        html_tv_heatmap = """
        <div style="height: 500px; border: 1px solid #1A1A1A; border-radius: 4px; overflow: hidden;">
            <div class="tradingview-widget-container">
                <div class="tradingview-widget-container__widget"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
                {
                  "exchanges": [],
                  "dataSource": "S&P500",
                  "grouping": "sector",
                  "blockSize": "market_cap",
                  "blockColor": "change",
                  "locale": "fr",
                  "symbolUrl": "",
                  "colorTheme": "dark",
                  "hasTopBar": true,
                  "isDatasetResizable": false,
                  "isBlockSelectionDisabled": false,
                  "width": "100%",
                  "height": "500"
                }
                </script>
            </div>
        </div>
        """
        components.html(html_tv_heatmap, height=520)

    # --- COLONNE DROITE ---
    with col_right:
        # ----------------------------------------
        # SECTION NEWS (STYLE DAILY BRIEF + SCROLL)
        # ----------------------------------------
        st.markdown('<div class="section-header">📰 BREAKING NEWS</div>', unsafe_allow_html=True)
        
        # Onglets
        tab_bourso, tab_invest, tab_wsj = st.tabs(["🇫🇷 Boursorama", "🌐 Investing", "📰 WSJ"])

        def display_news_scrollable(source_name):
            news_items = get_rss_news(source_name)
            if not news_items:
                st.info("Aucune actualité récente.")
                return
            with st.container(height=300):
                for news in news_items:
                    with st.expander(f"» {news['title']}"):
                        st.write(f"**SOURCE :** {source_name}")
                        st.caption(f"🕒 DATE : {news['time']}")
                        st.link_button("LIRE L'ARTICLE", news['link'])

        def display_news_fusionne(sources):
            """Fusionne plusieurs sources RSS triées par date décroissante."""
            all_news = []
            for source_name in sources:
                for item in get_rss_news(source_name):
                    all_news.append(item)
            if not all_news:
                st.info("Aucune actualité récente.")
                return
            all_news.sort(key=lambda x: x['time'], reverse=True)
            with st.container(height=300):
                for news in all_news[:20]:
                    with st.expander(f"» {news['title']}"):
                        st.write(f"**SOURCE :** {news['source']}")
                        st.caption(f"🕒 DATE : {news['time']}")
                        st.link_button("LIRE L'ARTICLE", news['link'])

        with tab_bourso:
            display_news_scrollable("Boursorama")

        with tab_invest:
            display_news_scrollable("Investing")

        with tab_wsj:
            display_news_fusionne(["WSJ Markets", "WSJ Finance"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Events / Stats
        st.markdown('<div class="section-header">⚡ MOVERS (24H)</div>', unsafe_allow_html=True)
        st.markdown('<div style="background-color: #0A0A0A; border: 1px solid #1A1A1A; border-radius: 8px; padding: 15px;">', unsafe_allow_html=True)
        events = get_upcoming_events()
        for evt in events:
            c_class = 'event-change-positive' if evt['change'] >= 0 else 'event-change-negative'
            sign = '+' if evt['change'] >= 0 else ''
            st.markdown(f'''
            <div class="event-item">
                <div class="event-name">{evt['name']}</div>
                <div style="text-align: right;">
                    <div class="event-price">${evt['price']:,.2f}</div>
                    <div class="{c_class}">{sign}{evt['change']:.2f}%</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Market Stats
        st.markdown('<div class="section-header">📈 MARKET STATS</div>', unsafe_allow_html=True)
        st.markdown('<div style="background-color: #0A0A0A; border: 1px solid #1A1A1A; border-radius: 8px; padding: 15px;">', unsafe_allow_html=True)
        market_stats = get_market_stats()
        for stat in market_stats:
            position = min(max((stat['change'] + 10) * 5, 0), 100)
            st.markdown(f'''
            <div class="market-stat-item">
                <span class="market-stat-symbol">{stat['symbol']}</span>
                <div class="market-stat-bar" style="position: relative;">
                    <div style="position: absolute; left: {position}%; top: 50%; transform: translate(-50%, -50%); width: 2px; height: 12px; background: #FFF;"></div>
                </div>
                <span>{stat['change']:+.1f}%</span>
            </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
