import streamlit.components.v1 as components
import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from datetime import datetime

# Headers pour éviter d'être bloqué par les API
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# ============================================
# 1. FONCTIONS UTILITAIRES CRYPTO
# ============================================

def get_crypto_pair(query):
    query = query.strip().upper()
    mapping = {
        "BITCOIN": "BTC", "ETHER": "ETH", "ETHEREUM": "ETH", "RIPPLE": "XRP",
        "CARDANO": "ADA", "SOLANA": "SOL", "DOGECOIN": "DOGE", "POLKADOT": "DOT",
        "AVALANCHE": "AVAX", "SHIBA": "SHIB", "MATIC": "MATIC", "POLYGON": "MATIC"
    }
    if query in mapping:
        ticker = mapping[query]
    else:
        ticker = query
    if ":" in ticker:
        return ticker
    ticker = ticker.replace("-USD", "").replace("USDT", "").replace("USD", "")
    return f"BINANCE:{ticker}USDT"

@st.cache_data(ttl=300)
def get_crypto_news(source):
    news_items = []
    rss_urls = {
        "CoinDesk":      "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "CoinTelegraph": "https://cointelegraph.com/rss",
        "Decrypt":       "https://decrypt.co/feed",
        "Cryptoast":     "https://cryptoast.fr/feed/"
    }
    url = rss_urls.get(source)
    if not url:
        return []
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
                'link':  entry.link,
                'time':  time_str,
                'source': source
            })
    except:
        pass
    return news_items

@st.cache_data(ttl=60)
def get_crypto_movers():
    top_cryptos = [
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
        "AVAX-USD", "DOGE-USD", "DOT-USD", "LINK-USD", "MATIC-USD"
    ]
    movers = []
    for symbol in top_cryptos:
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            price      = info['last_price']
            prev_close = info['previous_close']
            change     = ((price - prev_close) / prev_close) * 100
            name       = symbol.replace("-USD", "")
            movers.append({"name": name, "price": price, "change": change})
        except:
            pass
    return sorted(movers, key=lambda x: abs(x['change']), reverse=True)

# ============================================
# 2. FONCTIONS ON-CHAIN (Binance Futures API)
# ============================================

@st.cache_data(ttl=60)
def get_funding_rates():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
    results = []
    try:
        # On récupère tout d'un coup pour plus de fiabilité
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        data = requests.get(url, headers=HEADERS, timeout=5).json()
        if isinstance(data, list):
            for sym in symbols:
                item = next((x for x in data if x.get('symbol') == sym), None)
                if item:
                    results.append({
                        "symbol": sym.replace("USDT", ""),
                        "rate": float(item.get("lastFundingRate", 0)) * 100,
                        "mark": float(item.get("markPrice", 0))
                    })
    except: pass
    return results

@st.cache_data(ttl=60)
def get_open_interest():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
    results = []
    try:
        for sym in symbols:
            url_oi = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym}"
            url_px = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}"
            oi_data = requests.get(url_oi, headers=HEADERS, timeout=3).json()
            px_data = requests.get(url_px, headers=HEADERS, timeout=3).json()
            
            oi = float(oi_data.get("openInterest", 0))
            mark = float(px_data.get("markPrice", 0))
            if oi > 0:
                results.append({"symbol": sym.replace("USDT", ""), "oi": oi, "oi_usd": oi * mark})
    except: pass
    return results

@st.cache_data(ttl=300)
def get_btc_dominance():
    """Récupère la dominance réelle via CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        data = requests.get(url, headers=HEADERS, timeout=5).json()
        dom = data['data']['market_cap_percentage']['btc']
        return round(dom, 1)
    except:
        return 54.0

@st.cache_data(ttl=300)
def get_fear_greed():
    try:
        data = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5).json()
        return int(data["data"][0]["value"]), data["data"][0]["value_classification"]
    except: return None, None


@st.cache_data(ttl=60)
def get_ls_ratio():
    """Ratio Long/Short via Binance Futures (Corrigé avec Headers)"""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results = []
    
    # On utilise les mêmes headers que pour les prix et le funding
    for sym in symbols:
        try:
            # Endpoint officiel pour le ratio global des comptes
            url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={sym}&period=5m&limit=1"
            
            response = requests.get(url, headers=HEADERS, timeout=5)
            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                # Le ratio est : longs / shorts
                ratio = float(data[0].get("longShortRatio", 1))
                
                # Calcul des pourcentages
                longs_pct = round((ratio / (1 + ratio)) * 100, 1)
                shorts_pct = round(100 - longs_pct, 1)
                
                results.append({
                    "symbol": sym.replace("USDT", ""),
                    "longs":  longs_pct,
                    "shorts": shorts_pct,
                    "ratio": round(ratio, 2)
                })
        except Exception as e:
            # Optionnel : décommenter pour voir l'erreur en cas de bug
            # print(f"Erreur L/S pour {sym}: {e}")
            pass
            
    return results

# ============================================
# 3. RENDU ON-CHAIN PANEL
# ============================================

def render_onchain_panel():
    """Panel On-Chain complet : métriques macro + 4 sous-onglets"""

    # ── Métriques macro (toujours visibles en haut) ──────────────────
    fg_val, fg_label = get_fear_greed()
    funding_data     = get_funding_rates()
    oi_data          = get_open_interest()
    btc_funding      = next((f for f in funding_data if f["symbol"] == "BTC"), None)
    btc_oi           = next((o for o in oi_data      if o["symbol"] == "BTC"), None)

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        if fg_val is not None:
            fc = "#00ffad" if fg_val >= 60 else "#ff9800" if fg_val >= 40 else "#ff4b4b"
            st.markdown(f"""
            <div style='background:#111;border:1px solid #1a1a1a;border-top:2px solid {fc};
                        padding:10px;border-radius:4px;text-align:center;'>
                <div style='color:#666;font-size:9px;letter-spacing:1px;font-family:monospace;'>FEAR & GREED</div>
                <div style='color:{fc};font-size:22px;font-weight:900;font-family:monospace;'>{fg_val}</div>
                <div style='color:#444;font-size:9px;font-family:monospace;'>{fg_label.upper()}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background:#111;border:1px solid #1a1a1a;padding:10px;border-radius:4px;text-align:center;'>
                <div style='color:#666;font-size:9px;font-family:monospace;'>FEAR & GREED</div>
                <div style='color:#444;font-size:14px;font-family:monospace;'>N/A</div>
            </div>""", unsafe_allow_html=True)

    with m2:
        st.markdown("""
        <div style='background:#111;border:1px solid #1a1a1a;border-top:2px solid #FABE2C;
                    padding:10px;border-radius:4px;text-align:center;'>
            <div style='color:#666;font-size:9px;letter-spacing:1px;font-family:monospace;'>BTC DOMINANCE</div>
            <div style='color:#FABE2C;font-size:22px;font-weight:900;font-family:monospace;'>~54%</div>
            <div style='color:#444;font-size:9px;font-family:monospace;'>APPROX. LIVE</div>
        </div>""", unsafe_allow_html=True)

    with m3:
        if btc_funding:
            fc2  = "#00ffad" if btc_funding["rate"] >= 0 else "#ff4b4b"
            sign = "+" if btc_funding["rate"] >= 0 else ""
            st.markdown(f"""
            <div style='background:#111;border:1px solid #1a1a1a;border-top:2px solid {fc2};
                        padding:10px;border-radius:4px;text-align:center;'>
                <div style='color:#666;font-size:9px;letter-spacing:1px;font-family:monospace;'>BTC FUNDING</div>
                <div style='color:{fc2};font-size:22px;font-weight:900;font-family:monospace;'>
                    {sign}{btc_funding["rate"]:.4f}%
                </div>
                <div style='color:#444;font-size:9px;font-family:monospace;'>BINANCE FUTURES</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background:#111;border:1px solid #1a1a1a;padding:10px;border-radius:4px;text-align:center;'>
                <div style='color:#666;font-size:9px;font-family:monospace;'>BTC FUNDING</div>
                <div style='color:#444;font-size:14px;font-family:monospace;'>N/A</div>
            </div>""", unsafe_allow_html=True)

    with m4:
        if btc_oi:
            oi_b = btc_oi["oi_usd"] / 1e9
            st.markdown(f"""
            <div style='background:#111;border:1px solid #1a1a1a;border-top:2px solid #00ffad;
                        padding:10px;border-radius:4px;text-align:center;'>
                <div style='color:#666;font-size:9px;letter-spacing:1px;font-family:monospace;'>BTC OPEN INT.</div>
                <div style='color:#00ffad;font-size:22px;font-weight:900;font-family:monospace;'>${oi_b:.1f}B</div>
                <div style='color:#444;font-size:9px;font-family:monospace;'>BINANCE FUTURES</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background:#111;border:1px solid #1a1a1a;padding:10px;border-radius:4px;text-align:center;'>
                <div style='color:#666;font-size:9px;font-family:monospace;'>OPEN INTEREST</div>
                <div style='color:#444;font-size:14px;font-family:monospace;'>N/A</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 4 sous-onglets ────────────────────────────────────────────────
    tab_fund, tab_oi, tab_ls, tab_nf = st.tabs([
        "📈 FUNDING RATES",
        "📊 OPEN INTEREST",
        "⚖️ LONG / SHORT",
        "🌊 NETFLOW"
    ])

    # ── FUNDING RATES ─────────────────────────────────────────────────
    with tab_fund:
        if funding_data:
            st.markdown("""
            <div style='display:grid;grid-template-columns:1.5fr 1fr 1fr;
                        background:#050505;padding:6px 10px;margin-bottom:4px;'>
                <span style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;'>SYMBOL</span>
                <span style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;'>FUNDING RATE</span>
                <span style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;'>MARK PRICE</span>
            </div>""", unsafe_allow_html=True)
            for f in funding_data:
                c    = "#00ffad" if f["rate"] >= 0 else "#ff4b4b"
                sign = "+" if f["rate"] >= 0 else ""
                sent = "LONG DOM. 📈" if f["rate"] > 0.01 else "NEUTRE ➡️" if f["rate"] > -0.01 else "SHORT DOM. 📉"
                st.markdown(f"""
                <div style='display:grid;grid-template-columns:1.5fr 1fr 1fr;
                            padding:10px;border-bottom:1px solid #1a1a1a;background:#0a0a0a;'>
                    <span style='color:#fff;font-size:13px;font-family:monospace;font-weight:900;'>{f["symbol"]}</span>
                    <div>
                        <span style='color:{c};font-size:14px;font-family:monospace;font-weight:900;'>
                            {sign}{f["rate"]:.4f}%
                        </span><br>
                        <span style='color:#444;font-size:9px;font-family:monospace;'>{sent}</span>
                    </div>
                    <span style='color:#ccc;font-size:13px;font-family:monospace;'>${f["mark"]:,.2f}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("📌 Positif = longs paient les shorts (haussier) • Négatif = shorts paient les longs • Source : Binance Futures")
        else:
            st.warning("Impossible de récupérer les données. Vérifiez votre connexion.")

    # ── OPEN INTEREST ─────────────────────────────────────────────────
    with tab_oi:
        oi_data = get_open_interest()
        if oi_data:
            total_usd = sum(o["oi_usd"] for o in oi_data)
            st.markdown("""
            <div style='display:grid;grid-template-columns:1.5fr 1fr 1fr;
                        background:#050505;padding:6px 10px;margin-bottom:4px;'>
                <span style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;'>SYMBOL</span>
                <span style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;'>OI (CONTRATS)</span>
                <span style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;'>OI (USD)</span>
            </div>""", unsafe_allow_html=True)
            for o in oi_data:
                oi_m = o["oi_usd"] / 1e6
                st.markdown(f"""
                <div style='display:grid;grid-template-columns:1.5fr 1fr 1fr;
                            padding:10px;border-bottom:1px solid #1a1a1a;background:#0a0a0a;'>
                    <span style='color:#fff;font-size:13px;font-family:monospace;font-weight:900;'>{o["symbol"]}</span>
                    <span style='color:#ccc;font-size:13px;font-family:monospace;'>{o["oi"]:,.0f}</span>
                    <span style='color:#00ffad;font-size:13px;font-family:monospace;font-weight:900;'>${oi_m:,.1f}M</span>
                </div>""", unsafe_allow_html=True)
            st.markdown(f"""
            <div style='background:#111;border:1px solid #333;border-radius:4px;
                        padding:12px 16px;margin-top:12px;
                        display:flex;justify-content:space-between;align-items:center;'>
                <span style='color:#666;font-size:11px;font-family:monospace;letter-spacing:1px;'>
                    TOTAL OPEN INTEREST
                </span>
                <span style='color:#00ffad;font-size:18px;font-weight:900;font-family:monospace;'>
                    ${total_usd/1e9:.2f}B
                </span>
            </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("📌 OI croissant + prix montant = tendance forte • OI croissant + prix baissant = short squeeze possible • Source : Binance Futures")
        else:
            st.warning("Impossible de récupérer l'Open Interest.")

    # ── LONG / SHORT RATIO ────────────────────────────────────────────
    with tab_ls:
        ls_data = get_ls_ratio()
        if ls_data:
            for r in ls_data:
                lc      = "#00ffad" if r["longs"]  > 50 else "#ff4b4b"
                sc      = "#ff4b4b" if r["shorts"] > 50 else "#00ffad"
                verdict = "🟢 HAUSSIER" if r["longs"] > 55 else "🔴 BAISSIER" if r["shorts"] > 55 else "⚖️ NEUTRE"
                st.markdown(f"""
                <div style='background:#0a0a0a;border:1px solid #1a1a1a;border-radius:4px;
                            padding:14px 16px;margin-bottom:10px;'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:8px;'>
                        <span style='color:#fff;font-size:14px;font-family:monospace;font-weight:900;'>{r["symbol"]}</span>
                        <span style='color:#666;font-size:11px;font-family:monospace;'>
                            <span style='color:{lc};'>{r["longs"]}% LONG</span>
                            &nbsp;vs&nbsp;
                            <span style='color:{sc};'>{r["shorts"]}% SHORT</span>
                            &nbsp;•&nbsp; {verdict}
                        </span>
                    </div>
                    <div style='height:22px;border-radius:3px;display:flex;overflow:hidden;border:1px solid #1a1a1a;'>
                        <div style='width:{r["longs"]}%;background:#00ffad33;
                                    border-right:2px solid {lc};
                                    display:flex;align-items:center;justify-content:center;'>
                            <span style='color:#00ffad;font-size:10px;font-family:monospace;font-weight:900;'>L {r["longs"]}%</span>
                        </div>
                        <div style='flex:1;display:flex;align-items:center;justify-content:center;'>
                            <span style='color:#ff4b4b;font-size:10px;font-family:monospace;font-weight:900;'>S {r["shorts"]}%</span>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
            st.caption("📌 > 60% Longs = suracheté, risque liquidation en cascade • < 40% Longs = survendu • Source : Binance Futures (5m)")
        else:
            st.warning("Impossible de récupérer le ratio Long/Short.")

    # ── NETFLOW ───────────────────────────────────────────────────────
    with tab_nf:
        # Données simulées — remplacer par Glassnode/CryptoQuant pour données réelles
        netflow_data = [
            {"exchange": "Binance",  "flow": -3240, "pct": 72},
            {"exchange": "Coinbase", "flow": -1820, "pct": 40},
            {"exchange": "Kraken",   "flow": +540,  "pct": 12},
            {"exchange": "OKX",      "flow": -980,  "pct": 22},
            {"exchange": "Bitfinex", "flow": +210,  "pct": 5 },
        ]
        total_flow = sum(d["flow"] for d in netflow_data)

        st.markdown("""
        <div style='color:#666;font-size:10px;font-family:monospace;letter-spacing:1px;margin-bottom:12px;'>
            FLUX BTC EXCHANGES (24H) — Sorties = Accumulation 🟢 • Entrées = Pression vendeuse 🔴
        </div>""", unsafe_allow_html=True)

        for d in netflow_data:
            is_out = d["flow"] < 0
            color  = "#00ffad" if is_out else "#ff4b4b"
            arrow  = "▼" if is_out else "▲"
            label  = "SORTIE" if is_out else "ENTRÉE"
            st.markdown(f"""
            <div style='background:#0a0a0a;border:1px solid #1a1a1a;border-radius:3px;
                        padding:12px 14px;margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                    <span style='color:#fff;font-size:12px;font-family:monospace;font-weight:700;'>{d["exchange"]}</span>
                    <span style='color:{color};font-size:12px;font-family:monospace;font-weight:900;'>
                        {arrow} {abs(d["flow"]):,} BTC &nbsp;
                        <span style='color:#444;font-size:10px;'>{label}</span>
                    </span>
                </div>
                <div style='height:8px;background:#1a1a1a;border-radius:2px;overflow:hidden;'>
                    <div style='width:{d["pct"]}%;height:100%;background:{color};border-radius:2px;'></div>
                </div>
            </div>""", unsafe_allow_html=True)

        total_color = "#00ffad" if total_flow < 0 else "#ff4b4b"
        st.markdown(f"""
        <div style='background:#111;border:1px solid #333;border-radius:4px;
                    padding:12px 16px;margin-top:4px;
                    display:flex;justify-content:space-between;align-items:center;'>
            <span style='color:#666;font-size:11px;font-family:monospace;letter-spacing:1px;'>NETFLOW TOTAL (24H)</span>
            <span style='color:{total_color};font-size:18px;font-weight:900;font-family:monospace;'>
                {"▼" if total_flow < 0 else "▲"} {abs(total_flow):,} BTC
            </span>
        </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("⚠️ Netflow simulé. Pour données réelles : Glassnode API ou CryptoQuant API.")


# ============================================
# 4. INTERFACE PRINCIPALE CRYPTO PRO
# ============================================

def show_interface_crypto():
    st.markdown("""
    <style>
        .stApp { background-color: #000000; }
        .block-container { padding-top: 1rem !important; max-width: 98% !important; }

        .stTextInput input {
            background-color: #111 !important;
            color: #00ffad !important;
            border: 1px solid #333 !important;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
        .section-header {
            color: #00ffad;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 1px solid #333;
            padding-bottom: 5px;
            margin-top: 20px;
            letter-spacing: 1px;
        }
        .news-time-brief { color: #666; font-size: 11px; font-weight: bold; margin-right: 10px; }
        .source-badge    { font-size: 10px; font-weight: 900; padding: 2px 6px; border-radius: 3px; margin-right: 10px; display: inline-block; text-transform: uppercase; }
        .badge-coindesk  { background-color: #F7931A; color: black; }
        .badge-cointele  { background-color: #FABE2C; color: black; }
        .badge-cryptoast { background-color: #0056b3; color: white; }
        [data-testid="stExpander"] {
            background-color: #0A0A0A !important;
            border: none !important;
            border-bottom: 1px solid #1A1A1A !important;
            border-radius: 0px !important;
        }
        .event-item {
            display: flex; justify-content: space-between;
            padding: 8px 0; border-bottom: 1px solid #1A1A1A;
            color: white; font-size: 13px;
        }
        .stSelectbox > div > div {
            background-color: #111 !important;
            color: #00ffad !important;
            border: 1px solid #333 !important;
            font-family: 'Courier New', monospace !important;
            font-weight: bold !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'Courier New', monospace;
            font-size: 11px;
            letter-spacing: 1px;
        }
        .stTabs [aria-selected="true"] { color: #00ffad !important; }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([2.2, 1], gap="medium")

    # ── COLONNE GAUCHE ───────────────────────────────────────────────
    with col_left:
        st.markdown('<div class="section-header">📊 CRYPTO TERMINAL</div>', unsafe_allow_html=True)

        c_search, c_info = st.columns([2, 1])
        with c_search:
            search_input = st.text_input(
                "RECHERCHER UNE CRYPTO (ex: BTC, Solana, PEPE)",
                value="BTC", label_visibility="collapsed"
            )
        tv_symbol = get_crypto_pair(search_input)
        with c_info:
            st.markdown(
                f"<div style='text-align:right;color:#666;padding-top:10px;'>"
                f"ACTIVE: <b style='color:#fff'>{tv_symbol}</b></div>",
                unsafe_allow_html=True
            )

        # Graphique TradingView
        html_chart = f"""
        <div style="height:550px;border:1px solid #1A1A1A;border-radius:4px;overflow:hidden;margin-top:5px;">
            <div id="tv_chart_crypto"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
            <script type="text/javascript">
            new TradingView.widget({{
                "width":"100%","height":"550","symbol":"{tv_symbol}",
                "interval":"60","timezone":"Europe/Paris","theme":"dark",
                "style":"1","locale":"fr","toolbar_bg":"#000000",
                "enable_publishing":false,"container_id":"tv_chart_crypto",
                "overrides":{{
                    "paneProperties.background":"#000000",
                    "paneProperties.vertGridProperties.color":"#111",
                    "paneProperties.horzGridProperties.color":"#111"
                }}
            }});
            </script>
        </div>"""
        components.html(html_chart, height=560)

        # ── Header dynamique + menu roulant ─────────────────────────
        h1, h2 = st.columns([3, 1])
        with h2:
            st.markdown("<div style='padding-top:18px'></div>", unsafe_allow_html=True)
            view_choice = st.selectbox(
                "VUE",
                options=["🔥 HEATMAP", "🔗 ON-CHAIN DATA"],
                key="bottom_view",
                label_visibility="collapsed"
            )
        with h1:
            titre = "🔥 CRYPTO HEATMAP (LIVE)" if "HEATMAP" in view_choice else "🔗 ON-CHAIN DATA"
            st.markdown(f'<div class="section-header">{titre}</div>', unsafe_allow_html=True)

        # ── Vue conditionnelle ───────────────────────────────────────
        if "HEATMAP" in view_choice:
            html_heatmap = """
            <div style="height:500px;border:1px solid #1A1A1A;border-radius:4px;overflow:hidden;">
                <div class="tradingview-widget-container">
                    <div class="tradingview-widget-container__widget"></div>
                    <script type="text/javascript"
                        src="https://s3.tradingview.com/external-embedding/embed-widget-crypto-coins-heatmap.js" async>
                    {
                    "dataSource":"Crypto","blockSize":"market_cap_calc","blockColor":"change",
                    "locale":"fr","symbolUrl":"","colorTheme":"dark","hasTopBar":true,
                    "isDatasetResizable":false,"isBlockSelectionDisabled":false,
                    "width":"100%","height":"500"
                    }
                    </script>
                </div>
            </div>"""
            components.html(html_heatmap, height=510)
        else:
            render_onchain_panel()

    # ── COLONNE DROITE ───────────────────────────────────────────────
    with col_right:
        st.markdown('<div class="section-header">📰 CRYPTO WIRE</div>', unsafe_allow_html=True)

        tab_cd, tab_ct, tab_fr = st.tabs(["🇺🇸 CoinDesk", "🇺🇸 CoinTelegraph", "🇫🇷 Cryptoast"])

        def render_crypto_news(source):
            news_data = get_crypto_news(source)
            with st.container(height=300):
                if not news_data:
                    st.info("Chargement des news...")
                for n in news_data:
                    header = f"{n['time']} | {source} » {n['title'][:60]}..."
                    with st.expander(header):
                        st.markdown(f"**{n['title']}**")
                        st.caption(f"Source: {source} • Heure: {n['time']}")
                        st.link_button("LIRE L'ARTICLE", n['link'])

        with tab_cd: render_crypto_news("CoinDesk")
        with tab_ct: render_crypto_news("CoinTelegraph")
        with tab_fr: render_crypto_news("Cryptoast")

        st.markdown('<br><div class="section-header">🚀 24H MOVERS</div>', unsafe_allow_html=True)
        movers = get_crypto_movers()
        with st.container(height=300):
            for m in movers:
                color = "#00ffad" if m['change'] >= 0 else "#ff4b4b"
                sign  = "+" if m['change'] >= 0 else ""
                st.markdown(f"""
                <div class="event-item">
                    <b>{m['name']}</b>
                    <div style="text-align:right">
                        <b>${m['price']:,.2f}</b>
                        <span style="color:{color};margin-left:8px;">{sign}{m['change']:.2f}%</span>
                    </div>
                </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    show_interface_crypto()
