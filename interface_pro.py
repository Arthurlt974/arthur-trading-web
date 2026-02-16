import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime

# ============================================
# 1. FONCTIONS DE RECHERCHE ET DONNÉES
# ============================================

def get_ticker_from_name(query):
    """
    Convertit un nom d'entreprise (ex: Apple) en Ticker (AAPL).
    Si c'est déjà un ticker, il le retourne tel quel.
    """
    query = query.strip()
    # Si c'est déjà un ticker probable (court et sans espace)
    if len(query) <= 5 and query.isalpha():
        return query.upper()
    
    try:
        # Recherche via l'API Yahoo Finance
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        # On utilise un header pour éviter d'être bloqué
        import requests
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        if res['quotes']:
            # On prend le premier résultat
            return res['quotes'][0]['symbol']
    except:
        pass
    return query.upper()

@st.cache_data(ttl=300)
def get_rss_news(source):
    news_items = []
    rss_urls = {
        "Boursorama": "https://www.boursorama.com/rss/actualites/economie/",
        "Investing": "https://fr.investing.com/rss/news.rss"
    }
    url = rss_urls.get(source)
    if not url: return []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            try:
                dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()
                time_str = dt.strftime("%d/%m %H:%M")
            except: time_str = "--:--"
            news_items.append({'title': entry.title, 'link': entry.link, 'time': time_str, 'source': source})
    except: pass
    return news_items

@st.cache_data(ttl=60)
def get_upcoming_events():
    events = []
    symbols = ['AAPL', 'NVDA', 'BTC-USD', 'ETH-USD', 'TSLA']
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol); hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                change = ((price - hist['Open'].iloc[0]) / hist['Open'].iloc[0]) * 100
                events.append({'name': symbol.replace('-USD', ''), 'price': price, 'change': change})
        except: pass
    return events

@st.cache_data(ttl=60)
def get_heatmap_data():
    symbols = ['AAPL', 'NVDA', 'BTC-USD', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META']
    data = []
    for s in symbols:
        try:
            t = yf.Ticker(s); h = t.history(period="1d")
            if not h.empty:
                p = h['Close'].iloc[-1]
                c = ((p - h['Open'].iloc[0]) / h['Open'].iloc[0]) * 100
                data.append({'symbol': s.replace('-USD', ''), 'price': p, 'change': c})
        except: pass
    return data

@st.cache_data(ttl=60)
def get_market_stats():
    symbols = ['AAPL', 'NVDA', 'BTC-USD', 'TSLA']
    stats = []
    for s in symbols:
        try:
            t = yf.Ticker(s); h = t.history(period="5d")
            if len(h) >= 2:
                c5d = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                stats.append({'symbol': s.replace('-USD', ''), 'change': c5d})
        except: pass
    return stats

# ============================================
# 2. INTERFACE PRO
# ============================================

def show_interface_pro():
    st.markdown("""
    <style>
        .stApp { background-color: #000000; }
        .stTextInput input { background-color: #111 !important; color: #FF9500 !important; border: 1px solid #333 !important; }
        .section-header { color: #FF9500; font-size: 14px; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #333; }
        [data-testid="stExpander"] { background-color: #0A0A0A !important; border: 1px solid #333 !important; margin-bottom: 8px; }
        .heatmap-row { display: flex; justify-content: space-between; padding: 8px; border-bottom: 1px solid #1A1A1A; font-size: 13px; color: white;}
        .event-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1A1A1A; color: white;}
        .market-stat-item { display: flex; align-items: center; margin-bottom: 8px; color: #fff; font-size: 12px;}
        .market-stat-bar { flex-grow: 1; height: 8px; background: #222; margin: 0 10px; border-radius: 2px; }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-header">📊 RECHERCHE & ANALYSE</div>', unsafe_allow_html=True)
        
        # Barre de recherche intelligente
        search_query = st.text_input("Tapez un nom (ex: Apple, Nvidia, Bitcoin) ou un symbole", value="Bitcoin", label_visibility="collapsed")
        
        # Conversion Nom -> Ticker
        raw_ticker = get_ticker_from_name(search_query)
        
        # Formatage pour TradingView
        cryptos = ["BTC", "ETH", "SOL", "XRP", "ADA"]
        if any(c in raw_ticker for c in cryptos) or "USD" in raw_ticker:
            # Gestion du format Yahoo (BTC-USD) vers TradingView (BINANCE:BTCUSDT)
            clean_symbol = raw_ticker.split('-')[0]
            tv_symbol = f"BINANCE:{clean_symbol}USDT"
        else:
            tv_symbol = raw_ticker

        html_tv = f"""
        <div style="height:500px; border: 1px solid #1A1A1A; border-radius: 8px; overflow: hidden; margin-top: 10px;">
            <div id="tradingview_main"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
                "width": "100%", "height": "500", "symbol": "{tv_symbol}",
                "interval": "D", "timezone": "Etc/UTC", "theme": "dark",
                "style": "1", "locale": "fr", "toolbar_bg": "#000000",
                "enable_publishing": false, "container_id": "tradingview_main"
            }});
            </script>
        </div>
        """
        components.html(html_tv, height=520)
        
        # Heatmap
        st.markdown('<div class="section-header">🔥 MARKET HEATMAP</div>', unsafe_allow_html=True)
        hm_data = get_heatmap_data()
        for item in hm_data:
            col = "#00C853" if item['change'] >= 0 else "#FF3B30"
            st.markdown(f'<div class="heatmap-row"><b>{item["symbol"]}</b> <span>${item["price"]:,.2f}</span> <span style="color:{col}">{item["change"]:+.2f}%</span></div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">📰 BREAKING NEWS</div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["🇫🇷 Boursorama", "🌐 Investing"])
        
        def draw_news(src):
            with st.container(height=300):
                for n in get_rss_news(src):
                    with st.expander(f"» {n['title']}"):
                        st.caption(f"🕒 {n['time']}")
                        st.link_button("LIRE", n['link'])

        with t1: draw_news("Boursorama")
        with t2: draw_news("Investing")
        
        st.markdown('<div class="section-header">⚡ MOVERS</div>', unsafe_allow_html=True)
        for e in get_upcoming_events():
            c = "#00C853" if e['change'] >= 0 else "#FF3B30"
            st.markdown(f'<div class="event-item"><b>{e["name"]}</b> <div style="text-align:right"><b>${e["price"]:,.2f}</b><br><span style="color:{c}">{e["change"]:+.2f}%</span></div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">📈 MARKET STATS</div>', unsafe_allow_html=True)
        for s in get_market_stats():
            pos = min(max((s['change'] + 10) * 5, 0), 100)
            st.markdown(f'<div class="market-stat-item"><span style="width:50px">{s["symbol"]}</span><div class="market-stat-bar" style="position:relative"><div style="position:absolute;left:{pos}%;width:2px;height:12px;background:#FFF;"></div></div><span>{s["change"]:+.1f}%</span></div>', unsafe_allow_html=True)

if __name__ == "__main__":
    show_interface_pro()

    # --- COLONNE DROITE ---
    with col_right:
        # ----------------------------------------
        # SECTION NEWS (STYLE DAILY BRIEF + SCROLL)
        # ----------------------------------------
        st.markdown('<div class="section-header">📰 BREAKING NEWS</div>', unsafe_allow_html=True)
        
        # Onglets
        tab_bourso, tab_invest = st.tabs(["🇫🇷 Boursorama", "🌐 Investing"])
        
        def display_news_scrollable(source_name):
            news_items = get_rss_news(source_name)
            if not news_items:
                st.info("Aucune actualité récente.")
                return

            # Création d'un conteneur SCROLLABLE de hauteur fixe (300px = environ 3 items)
            # Cela permet d'afficher les 3 premiers et de scroller pour voir les 7 autres
            with st.container(height=300):
                for news in news_items:
                    # Style Expandable
                    with st.expander(f"» {news['title']}"):
                        st.write(f"**SOURCE :** {source_name}")
                        st.caption(f"🕒 DATE : {news['time']}")
                        st.link_button("LIRE L'ARTICLE", news['link'])

        with tab_bourso:
            display_news_scrollable("Boursorama")

        with tab_invest:
            display_news_scrollable("Investing")
        
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
