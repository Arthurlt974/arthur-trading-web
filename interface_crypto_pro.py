import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import feedparser
import requests
from datetime import datetime

# ============================================
# 1. FONCTIONS UTILITAIRES CRYPTO
# ============================================

def get_crypto_pair(query):
    """
    Convertit une recherche (nom ou symbole) en paire de trading Binance.
    Ex: 'Bitcoin' -> 'BINANCE:BTCUSDT', 'ETH' -> 'BINANCE:ETHUSDT'
    """
    query = query.strip().upper()
    
    # Dictionnaire de mapping manuel pour les plus connus
    mapping = {
        "BITCOIN": "BTC", "ETHER": "ETH", "ETHEREUM": "ETH", "RIPPLE": "XRP",
        "CARDANO": "ADA", "SOLANA": "SOL", "DOGECOIN": "DOGE", "POLKADOT": "DOT",
        "AVALANCHE": "AVAX", "SHIBA": "SHIB", "MATIC": "MATIC", "POLYGON": "MATIC"
    }
    
    # Si c'est un nom complet, on le convertit en ticker
    if query in mapping:
        ticker = mapping[query]
    else:
        ticker = query
    
    # Si l'utilisateur a déjà mis le format complet (ex: COINBASE:BTCUSD), on laisse
    if ":" in ticker:
        return ticker
    
    # Nettoyage
    ticker = ticker.replace("-USD", "").replace("USDT", "").replace("USD", "")
    
    # Par défaut on renvoie la paire USDT sur Binance
    return f"BINANCE:{ticker}USDT"

@st.cache_data(ttl=300)
def get_crypto_news(source):
    """Récupère les flux RSS Spécial Crypto"""
    news_items = []
    
    # Flux RSS Crypto
    rss_urls = {
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "CoinTelegraph": "https://cointelegraph.com/rss",
        "Decrypt": "https://decrypt.co/feed",
        "Cryptoast": "https://cryptoast.fr/feed/" 
    }
    
    url = rss_urls.get(source)
    if not url: return []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            try:
                dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()
                time_str = dt.strftime("%H:%M")
            except:
                time_str = "--:--"
            
            news_items.append({
                'title': entry.title,
                'link': entry.link,
                'time': time_str,
                'source': source
            })
    except:
        pass
    return news_items

@st.cache_data(ttl=60)
def get_crypto_movers():
    """Récupère les Top Movers Crypto via yfinance"""
    top_cryptos = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "DOGE-USD", "DOT-USD", "LINK-USD", "MATIC-USD"]
    movers = []
    
    for symbol in top_cryptos:
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            price = info['last_price']
            prev_close = info['previous_close']
            change = ((price - prev_close) / prev_close) * 100
            name = symbol.replace("-USD", "")
            movers.append({"name": name, "price": price, "change": change})
        except:
            pass
            
    # Tri par variation absolue (les plus gros mouvements en premier)
    return sorted(movers, key=lambda x: abs(x['change']), reverse=True)

# ============================================
# 2. INTERFACE PRINCIPALE CRYPTO PRO
# ============================================

def show_interface_crypto():
    # --- CSS STYLE TERMINAL (Même que l'original) ---
    st.markdown("""
    <style>
        .stApp { background-color: #000000; }
        .block-container { padding-top: 1rem !important; max-width: 98% !important; }
        
        /* Barre de recherche style Bloomberg */
        .stTextInput input {
            background-color: #111 !important;
            color: #00ffad !important; /* Vert crypto */
            border: 1px solid #333 !important;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }

        .section-header { 
            color: #00ffad; /* Vert Crypto */
            font-size: 14px; 
            font-weight: bold; 
            margin-bottom: 10px; 
            border-bottom: 1px solid #333; 
            padding-bottom: 5px; 
            margin-top: 20px;
            letter-spacing: 1px;
        }
        
        /* News Brief Style */
        .news-time-brief { color: #666; font-size: 11px; font-weight: bold; margin-right: 10px; }
        
        /* Badges Sources */
        .source-badge { font-size: 10px; font-weight: 900; padding: 2px 6px; border-radius: 3px; margin-right: 10px; display: inline-block; text-transform: uppercase;}
        .badge-coindesk { background-color: #F7931A; color: black; } /* Orange Bitcoin */
        .badge-cointele { background-color: #FABE2C; color: black; } /* Jaune */
        .badge-cryptoast { background-color: #0056b3; color: white; } /* Bleu */

        [data-testid="stExpander"] { 
            background-color: #0A0A0A !important; 
            border: none !important; 
            border-bottom: 1px solid #1A1A1A !important; 
            border-radius: 0px !important; 
        }
        
        /* Event Item pour Movers */
        .event-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1A1A1A; color: white; font-size: 13px;}
    </style>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([2.2, 1], gap="medium")

    # --- COLONNE GAUCHE (Graphiques & Heatmap Crypto) ---
    with col_left:
        st.markdown('<div class="section-header">📊 CRYPTO TERMINAL</div>', unsafe_allow_html=True)
        
        # BARRE DE RECHERCHE INTELLIGENTE
        c_search, c_info = st.columns([2, 1])
        with c_search:
            search_input = st.text_input("RECHERCHER UNE CRYPTO (ex: BTC, Solana, PEPE)", value="BTC", label_visibility="collapsed")
        
        # Traitement du Ticker
        tv_symbol = get_crypto_pair(search_input)
        
        # Affichage du symbole actif
        with c_info:
            st.markdown(f"<div style='text-align:right; color:#666; padding-top:10px;'>ACTIVE: <b style='color:#fff'>{tv_symbol}</b></div>", unsafe_allow_html=True)

        # 1. GRAPHIQUE PRINCIPAL (TradingView Crypto)
        html_chart = f"""
        <div style="height:550px; border: 1px solid #1A1A1A; border-radius: 4px; overflow: hidden; margin-top: 5px;">
            <div id="tv_chart_crypto"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
                "width": "100%", "height": "550", "symbol": "{tv_symbol}",
                "interval": "60", "timezone": "Europe/Paris", "theme": "dark", 
                "style": "1", "locale": "fr", "toolbar_bg": "#000000", 
                "enable_publishing": false, "container_id": "tv_chart_crypto",
                "overrides": {{
                    "paneProperties.background": "#000000",
                    "paneProperties.vertGridProperties.color": "#111",
                    "paneProperties.horzGridProperties.color": "#111"
                }}
            }});
            </script>
        </div>
        """
        components.html(html_chart, height=560)

        # 2. HEATMAP CRYPTO (TradingView Widget Spécifique)
        st.markdown('<div class="section-header">🔥 CRYPTO HEATMAP (LIVE)</div>', unsafe_allow_html=True)
        
        html_heatmap = """
        <div style="height: 500px; border: 1px solid #1A1A1A; border-radius: 4px; overflow: hidden;">
            <div class="tradingview-widget-container">
                <div class="tradingview-widget-container__widget"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-crypto-coins-heatmap.js" async>
                {
                "dataSource": "Crypto",
                "blockSize": "market_cap_calc",
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
        components.html(html_heatmap, height=510)

    # --- COLONNE DROITE (News Crypto & Movers) ---
    with col_right:
        st.markdown('<div class="section-header">📰 CRYPTO WIRE</div>', unsafe_allow_html=True)
        
        # Onglets stylisés
        tab_cd, tab_ct, tab_fr = st.tabs(["🇺🇸 CoinDesk", "🇺🇸 CoinTelegraph", "🇫🇷 Cryptoast"])
        
        # Fonction d'affichage optimisée style "Daily Brief"
        def render_crypto_news(source):
            news_data = get_crypto_news(source)
            # Hauteur augmentée à 300px pour un scroll confortable à côté de la heatmap
            with st.container(height=300): 
                if not news_data:
                    st.info("Chargement des news...")
                for n in news_data:
                    # En-tête ultra-propre et aligné
                    header = f"{n['time']} | {source} » {n['title'][:60]}..."
                    with st.expander(header):
                        st.markdown(f"**{n['title']}**")
                        st.caption(f"Source: {source} • Heure: {n['time']}")
                        st.link_button("LIRE L'ARTICLE", n['link'])

        with tab_cd: render_crypto_news("CoinDesk")
        with tab_ct: render_crypto_news("CoinTelegraph")
        with tab_fr: render_crypto_news("Cryptoast")

        # --- LIVE MARKET MOVERS ---
        st.markdown('<br><div class="section-header">🚀 24H MOVERS</div>', unsafe_allow_html=True)
        
        movers = get_crypto_movers()
        with st.container(height=300):
            for m in movers:
                color = "#00ffad" if m['change'] >= 0 else "#ff4b4b"
                sign = "+" if m['change'] >= 0 else ""
                st.markdown(f'''
                <div class="event-item">
                    <b>{m['name']}</b> 
                    <div style="text-align:right">
                        <b>${m['price']:,.2f}</b> 
                        <span style="color:{color}; margin-left:8px;">{sign}{m['change']:.2f}%</span>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

if __name__ == "__main__":
    show_interface_crypto()
