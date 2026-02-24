import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import feedparser
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import numpy as np
from fpdf import FPDF
import io
import interface_pro
import interface_crypto_pro
import json
from websocket import create_connection
from firebase_auth import render_auth_page, render_user_sidebar, _save_current_session_config
import interface_economie
import interface_forex
import crypto_tools

# ============================================================
#  FONCTIONS UTILES GLOBALES
# ============================================================

def get_crypto_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        res = requests.get(url, timeout=2).json()
        return float(res['price'])
    except:
        try:
            tkr = symbol + "-USD"
            data = yf.Ticker(tkr).fast_info
            return data['last_price']
        except:
            return None


# ============================================================
#  CLASSE VALORISATION FONDAMENTALE
# ============================================================

class ValuationCalculator:
    """Calculateur de valeur fondamentale pour actions et cryptos"""

    def __init__(self, symbol):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.info = self._get_safe_info()

    def _get_safe_info(self):
        try:
            info = self.ticker.info
            if info.get('currentPrice', 0) == 0 or info.get('currentPrice') is None:
                hist = self.ticker.history(period="1d")
                if not hist.empty:
                    info['currentPrice'] = float(hist['Close'].iloc[-1])
            return info
        except:
            return {}

    def dcf_valuation(self, growth_rate=0.05, discount_rate=0.10, years=5):
        try:
            cash_flow = self.ticker.cashflow
            if cash_flow.empty:
                return {"error": "Données de cash flow non disponibles"}
            fcf = cash_flow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cash_flow.index else None
            if fcf is None or pd.isna(fcf):
                operating_cf = cash_flow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cash_flow.index else 0
                capex = cash_flow.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cash_flow.index else 0
                fcf = operating_cf + capex
            projected_fcf = []
            for year in range(1, years + 1):
                future_fcf = fcf * ((1 + growth_rate) ** year)
                discounted_fcf = future_fcf / ((1 + discount_rate) ** year)
                projected_fcf.append({'year': year, 'fcf': future_fcf, 'discounted_fcf': discounted_fcf})
            terminal_value = (fcf * ((1 + growth_rate) ** years) * (1 + 0.02)) / (discount_rate - 0.02)
            discounted_terminal_value = terminal_value / ((1 + discount_rate) ** years)
            enterprise_value = sum([p['discounted_fcf'] for p in projected_fcf]) + discounted_terminal_value
            shares_outstanding = self.info.get('sharesOutstanding', 0)
            if shares_outstanding == 0:
                return {"error": "Nombre d'actions non disponible"}
            total_debt = self.info.get('totalDebt', 0)
            cash = self.info.get('totalCash', 0)
            net_debt = total_debt - cash
            equity_value = enterprise_value - net_debt
            fair_value_per_share = equity_value / shares_outstanding
            current_price = self.info.get('currentPrice', 0)
            if current_price == 0 or current_price is None:
                try:
                    hist = self.ticker.history(period="1d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except:
                    pass
            upside = ((fair_value_per_share - current_price) / current_price) * 100 if current_price > 0 else 0
            return {
                "method": "DCF",
                "fair_value": round(fair_value_per_share, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(upside, 2),
                "enterprise_value": round(enterprise_value, 2),
                "equity_value": round(equity_value, 2),
                "fcf_current": round(fcf, 2),
                "parameters": {"growth_rate": growth_rate, "discount_rate": discount_rate, "years": years}
            }
        except Exception as e:
            return {"error": f"Erreur DCF: {str(e)}"}

    def pe_valuation(self, target_pe=None):
        try:
            current_price = self.info.get('currentPrice', 0)
            if current_price == 0 or current_price is None:
                try:
                    hist = self.ticker.history(period="1d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except:
                    pass
            trailing_pe = self.info.get('trailingPE', 0)
            forward_pe = self.info.get('forwardPE', 0)
            trailing_eps = self.info.get('trailingEps', 0)
            forward_eps = self.info.get('forwardEps', 0)
            if target_pe is None:
                target_pe = trailing_pe if trailing_pe else 15
            if forward_eps > 0:
                fair_value = forward_eps * target_pe
                eps_used = forward_eps
                eps_type = "Forward EPS"
            elif trailing_eps > 0:
                fair_value = trailing_eps * target_pe
                eps_used = trailing_eps
                eps_type = "Trailing EPS"
            else:
                return {"error": "EPS non disponible"}
            upside = ((fair_value - current_price) / current_price) * 100 if current_price > 0 else 0
            return {
                "method": "P/E Ratio",
                "fair_value": round(fair_value, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(upside, 2),
                "current_pe": round(trailing_pe, 2) if trailing_pe else "N/A",
                "target_pe": round(target_pe, 2) if target_pe else "N/A",
                "eps": round(eps_used, 2),
                "eps_type": eps_type
            }
        except Exception as e:
            return {"error": f"Erreur P/E: {str(e)}"}

    def pb_valuation(self):
        try:
            current_price = self.info.get('currentPrice', 0)
            if current_price == 0 or current_price is None:
                try:
                    hist = self.ticker.history(period="1d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except:
                    pass
            book_value = self.info.get('bookValue', 0)
            pb_ratio = self.info.get('priceToBook', 0)
            if book_value == 0:
                return {"error": "Valeur comptable non disponible"}
            industry_pb = pb_ratio * 0.9
            fair_value = book_value * industry_pb
            upside = ((fair_value - current_price) / current_price) * 100 if current_price > 0 else 0
            return {
                "method": "Price/Book",
                "fair_value": round(fair_value, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(upside, 2),
                "book_value": round(book_value, 2),
                "current_pb": round(pb_ratio, 2),
                "target_pb": round(industry_pb, 2)
            }
        except Exception as e:
            return {"error": f"Erreur P/B: {str(e)}"}

    def nvt_valuation(self, window=90):
        try:
            hist = self.ticker.history(period=f"{window}d")
            if hist.empty:
                return {"error": "Données historiques non disponibles"}
            market_cap = self.info.get('marketCap', 0)
            current_price = self.info.get('currentPrice', 0)
            if current_price == 0 or current_price is None:
                try:
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except:
                    pass
            avg_volume = hist['Volume'].mean()
            avg_price = hist['Close'].mean()
            daily_transaction_value = avg_volume * avg_price
            if daily_transaction_value == 0:
                return {"error": "Volume de transaction trop faible"}
            nvt_ratio = market_cap / daily_transaction_value
            target_nvt = 15
            fair_market_cap = daily_transaction_value * target_nvt
            shares_equiv = market_cap / current_price if current_price > 0 else 1
            fair_value = fair_market_cap / shares_equiv
            upside = ((fair_value - current_price) / current_price) * 100 if current_price > 0 else 0
            if nvt_ratio > 20:
                status = "Surévalué"
            elif nvt_ratio < 10:
                status = "Sous-évalué"
            else:
                status = "Juste valorisé"
            return {
                "method": "NVT Ratio",
                "fair_value": round(fair_value, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(upside, 2),
                "nvt_ratio": round(nvt_ratio, 2),
                "target_nvt": target_nvt,
                "status": status,
                "market_cap": market_cap,
                "daily_tx_value": round(daily_transaction_value, 2)
            }
        except Exception as e:
            return {"error": f"Erreur NVT: {str(e)}"}

    def graham_valuation(self):
        try:
            current_price = self.info.get('currentPrice', 0)
            if current_price == 0 or current_price is None:
                try:
                    hist = self.ticker.history(period="1d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                except:
                    pass
            eps = self.info.get('trailingEps') or self.info.get('forwardEps', 0)
            book_value = self.info.get('bookValue', 0)
            if eps <= 0 or book_value <= 0:
                return {"error": "EPS ou Book Value non disponible"}
            fair_value = (22.5 * eps * book_value) ** 0.5
            upside = ((fair_value - current_price) / current_price) * 100 if current_price > 0 else 0
            return {
                "method": "Graham",
                "fair_value": round(fair_value, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(upside, 2),
                "eps": round(eps, 2),
                "book_value": round(book_value, 2)
            }
        except Exception as e:
            return {"error": f"Erreur Graham: {str(e)}"}

    def get_comprehensive_valuation(self):
        results = {}
        fair_values = []
        is_crypto = "-USD" in self.symbol or self.symbol in ["BTC", "ETH", "BNB"]
        if is_crypto:
            nvt = self.nvt_valuation()
            if "error" not in nvt:
                results["nvt"] = nvt
                fair_values.append(nvt["fair_value"])
        else:
            graham = self.graham_valuation()
            if "error" not in graham:
                results["graham"] = graham
                fair_values.append(graham["fair_value"])
            dcf = self.dcf_valuation()
            if "error" not in dcf:
                results["dcf"] = dcf
                fair_values.append(dcf["fair_value"])
            pe = self.pe_valuation()
            if "error" not in pe:
                results["pe"] = pe
                fair_values.append(pe["fair_value"])
            pb = self.pb_valuation()
            if "error" not in pb:
                results["pb"] = pb
                fair_values.append(pb["fair_value"])
        if fair_values:
            consensus_value = np.median(fair_values)
            current_price = self.info.get('currentPrice', 0)
            consensus_upside = ((consensus_value - current_price) / current_price) * 100 if current_price > 0 else 0
            if consensus_upside > 20:
                recommendation = "ACHAT FORT"
            elif consensus_upside > 10:
                recommendation = "ACHAT"
            elif consensus_upside > -10:
                recommendation = "CONSERVER"
            elif consensus_upside > -20:
                recommendation = "VENTE"
            else:
                recommendation = "VENTE FORTE"
            results["consensus"] = {
                "fair_value": round(consensus_value, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(consensus_upside, 2),
                "methods_used": len(fair_values),
                "recommendation": recommendation
            }
        return results


# ============================================================
#  FONCTIONS UTILITAIRES PARTAGÉES
# ============================================================

@st.cache_data(ttl=5)
def get_ticker_info(ticker):
    try:
        data = yf.Ticker(ticker)
        return data.info
    except:
        return None

@st.cache_data(ttl=5)
def get_ticker_history(ticker, period="2d"):
    try:
        data = yf.Ticker(ticker)
        return data.history(period=period)
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

def calculer_score_sentiment(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1y")
        if len(data) < 200:
            return 50, "NEUTRE", "gray"
        prix_actuel = data['Close'].iloc[-1]
        ma200 = data['Close'].rolling(window=200).mean().iloc[-1]
        ratio = (prix_actuel / ma200) - 1
        score = 50 + (ratio * 300)
        score = max(10, min(90, score))
        if score > 70:   return score, "EXTRÊME EUPHORIE 🚀", "#00ffad"
        elif score > 55: return score, "OPTIMISME 📈", "#2ecc71"
        elif score > 45: return score, "NEUTRE ⚖️", "#f1c40f"
        elif score > 30: return score, "PEUR 📉", "#e67e22"
        else:            return score, "PANIQUE TOTALE 💀", "#e74c3c"
    except:
        return 50, "ERREUR", "gray"

def afficher_jauge_pro(score, titre, couleur, sentiment):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'font': {'size': 30, 'color': "white"}, 'suffix': "%"},
        title={'text': f"<b>{titre}</b><br><span style='color:{couleur}; font-size:14px;'>{sentiment}</span>",
               'font': {'size': 16, 'color': "white"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': couleur, 'thickness': 0.3},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 30],   'color': "rgba(231, 76, 60, 0.2)"},
                {'range': [30, 45],  'color': "rgba(230, 126, 34, 0.2)"},
                {'range': [45, 55],  'color': "rgba(241, 196, 15, 0.2)"},
                {'range': [55, 70],  'color': "rgba(46, 204, 113, 0.2)"},
                {'range': [70, 100], 'color': "rgba(0, 255, 173, 0.2)"}
            ],
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"},
                      height=300, margin=dict(l=25, r=25, t=100, b=20))
    return fig

def afficher_horloge_temps_reel():
    horloge_html = """
        <div style="border: 1px solid #ff9800; padding: 10px; background: #000; text-align: center; font-family: monospace;">
            <div style="color: #ff9800; font-size: 12px;">SYSTEM TIME / REUNION UTC+4</div>
            <div id="clock" style="font-size: 32px; color: #00ff00; font-weight: bold;">--:--:--</div>
            <div style="color: #444; font-size: 10px; margin-top:5px;">REAL-TIME FINANCIAL DATA FEED</div>
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
    components.html(horloge_html, height=120)

def afficher_graphique_pro(symbol, height=600):
    traduction_symbols = {
        "^FCHI": "CAC40",
        "^GSPC": "VANTAGE:SP500",
        "^IXIC": "NASDAQ",
        "BTC-USD": "BINANCE:BTCUSDT"
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
          "details": true,
          "container_id": "tradingview_chart"
        }});
        </script>
    """
    components.html(tradingview_html, height=height + 10)

def afficher_mini_graphique(symbol, chart_id):
    traduction_symbols = {"^FCHI": "CAC40", "^GSPC": "VANTAGE:SP500", "^IXIC": "NASDAQ", "BTC-USD": "BINANCE:BTCUSDT"}
    tv_symbol = traduction_symbols.get(symbol, symbol.replace(".PA", ""))
    if ".PA" in symbol and symbol not in traduction_symbols:
        tv_symbol = f"EURONEXT:{tv_symbol}"
    tradingview_html = f"""
        <div id="tv_chart_{chart_id}" style="height:400px;"></div>
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
          "container_id": "tv_chart_{chart_id}"
        }});
        </script>
    """
    components.html(tradingview_html, height=410)


# ============================================================
#  ORDER BOOK (COINBASE)
# ============================================================

def get_coinbase_order_book(product_id="BTC-USD"):
    try:
        clean_symbol = product_id.replace("USDT", "-USD").upper()
        if "-" not in clean_symbol:
            clean_symbol = f"{clean_symbol}-USD"
        url = f"https://api.exchange.coinbase.com/products/{clean_symbol}/book?level=2"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            bids = pd.DataFrame(data['bids'], columns=['Price', 'Quantity', 'NumOrders']).astype(float)
            asks = pd.DataFrame(data['asks'], columns=['Price', 'Quantity', 'NumOrders']).astype(float)
            return (bids.drop(columns=['NumOrders']), asks.drop(columns=['NumOrders'])), None
        else:
            return None, f"Erreur Coinbase: {response.status_code}"
    except Exception as e:
        return None, str(e)

def show_order_book_ui():
    st.markdown("### 📖 LIVE ORDER BOOK (COINBASE PRO)")
    st.info("Utilisation des serveurs Coinbase pour éviter les restrictions géographiques de Binance.")
    symbol = st.text_input("PAIRE CRYPTO (ex: BTC, ETH, SOL)", value="BTC").upper()
    if st.button("🔄 SYNCHRONISER LE CARNET"):
        with st.spinner("Extraction des ordres en cours..."):
            data_result, error_msg = get_coinbase_order_book(symbol)
            if data_result:
                bids, asks = data_result
                bids = bids.head(15)
                asks = asks.head(15)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("<span style='color:#ff4b4b; font-weight:bold;'>🔴 ORDRES DE VENTE (ASKS)</span>", unsafe_allow_html=True)
                    st.dataframe(asks.sort_values('Price', ascending=False).style.bar(subset=['Quantity'], color='#441111'),
                                 hide_index=True, use_container_width=True)
                with col2:
                    st.markdown("<span style='color:#00ffad; font-weight:bold;'>🟢 ORDRES D'ACHAT (BIDS)</span>", unsafe_allow_html=True)
                    st.dataframe(bids.style.bar(subset=['Quantity'], color='#114411'),
                                 hide_index=True, use_container_width=True)
                best_ask = asks['Price'].min()
                best_bid = bids['Price'].max()
                spread = best_ask - best_bid
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("ASK", f"${best_ask:,.2f}")
                c2.metric("BID", f"${best_bid:,.2f}")
                c3.metric("SPREAD", f"${spread:.2f}", delta=f"{(spread/best_ask)*100:.4f}%", delta_color="inverse")
            else:
                st.error(f"Impossible de récupérer les données : {error_msg}")


# ============================================================
#  INITIALISATION SESSION STATE
# ============================================================

if "multi_charts" not in st.session_state:
    st.session_state.multi_charts = []
if "whale_logs" not in st.session_state:
    st.session_state.whale_logs = []

# ============================================================
#  CONFIGURATION GLOBALE
# ============================================================

st.set_page_config(page_title="AM-Trading | Bloomberg Terminal", layout="wide")

if "workspace" not in st.session_state:
    st.session_state.workspace = []
if "multi_charts" not in st.session_state:
    st.session_state.multi_charts = []

# ============================================================
#  STYLE BLOOMBERG TERMINAL
# ============================================================

st.markdown("""
    <style>
        header[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
            color: #ff9800 !important;
        }
        .stApp [data-testid="stDecoration"] {
            display: none;
        }
        .stApp {
            background-color: #0d0d0d;
            color: #ff9800 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #161616;
            border-right: 1px solid #333;
        }
        h1, h2, h3, p, span, label, div, .stMarkdown {
            color: #ff9800 !important;
            text-transform: uppercase;
        }
        [data-testid="stMetricLabel"] {
            color: #ff9800 !important;
        }
        button[data-baseweb="tab"] p {
            color: #ff9800 !important;
        }
        .stButton>button {
            background-color: #1a1a1a;
            color: #ff9800;
            border: 1px solid #ff9800;
            border-radius: 4px;
            font-weight: bold;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #ff9800;
            color: #000;
        }
    </style>
""", unsafe_allow_html=True)


# ============================================================
#  AUTHENTIFICATION FIREBASE
# ============================================================

if not render_auth_page():
    st.stop()

st_autorefresh(interval=600000, key="global_refresh")


# ============================================================
#  NAVIGATION SIDEBAR
# ============================================================

st.sidebar.markdown("### 🗂️ NAVIGATION")
categorie = st.sidebar.selectbox("CHOISIR UN SECTEUR :", [
    "MARCHÉ CRYPTO", "ACTIONS & BOURSE", "BOITE À OUTILS", "ÉCONOMIE", "FOREX", "INTERFACE PRO", "INTERFACE CRYPTO PRO"
])
st.sidebar.markdown("---")

if categorie == "MARCHÉ CRYPTO":
    outil = st.sidebar.radio("MODULES CRYPTO :", [
        "BITCOIN DOMINANCE",
        "CRYPTO WALLET",
        "HEATMAP LIQUIDATIONS",
        "ORDER BOOK LIVE",
        "WHALE WATCHER",
        "ON-CHAIN ANALYTICS",
        "LIQUIDATIONS & FUNDING",
        "STAKING & YIELD"
    ])
if categorie == "INTERFACE PRO":
    outil = interface_pro.show_interface_pro()
if categorie == "INTERFACE CRYPTO PRO":
    outil = interface_crypto_pro.show_interface_crypto()
if categorie == "ÉCONOMIE":
    interface_economie.show_economie()
    st.stop()
elif categorie == "FOREX":
    interface_forex.show_forex()
    st.stop()
elif outil == "ON-CHAIN ANALYTICS":
    crypto_tools.show_onchain()
elif outil == "LIQUIDATIONS & FUNDING":
    crypto_tools.show_liquidations()
elif outil == "STAKING & YIELD":
    crypto_tools.show_staking()

elif categorie == "ACTIONS & BOURSE":
    outil = st.sidebar.radio("MODULES ACTIONS :", [
        "ANALYSEUR PRO",
        "ANALYSE TECHNIQUE PRO",
        "FIBONACCI CALCULATOR",
        "BACKTESTING ENGINE",
        "VALORISATION FONDAMENTALE",
        "MULTI-CHARTS",
        "EXPERT SYSTEM",
        "THE GRAND COUNCIL️",
        "MODE DUEL",
        "MARKET MONITOR",
        "SCREENER CAC 40",
        "DIVIDEND CALENDAR"
    ])

elif categorie == "BOITE À OUTILS":
    outil = st.sidebar.radio("MES OUTILS :", [
        "DAILY BRIEF",
        "CALENDRIER ÉCO",
        "Fear and Gread Index",
        "CORRÉLATION DASH",
        "INTERETS COMPOSES",
        "HEATMAP MARCHÉ",
        "ALERTS MANAGER"
    ])

st.sidebar.markdown("---")
st.sidebar.info(f"Secteur actif : {categorie.split()[-1]}")

# Barre utilisateur (compte + déconnexion)
render_user_sidebar()


# ============================================================
#  BANDEAU DÉFILANT (MARQUEE)
# ============================================================

# La watchlist est chargée depuis Firebase si user connecté, sinon valeur par défaut
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["BTC-USD", "ETH-USD", "AAPL", "TSLA", "NVDA", "INTC", "AMD",
                                   "GOOGL", "MSFT", "PEP", "KO", "MC.PA", "TTE", "BNP.PA"]

ticker_data_string = ""
for tkr in st.session_state.watchlist:
    try:
        t_info = yf.Ticker(tkr).fast_info
        price = t_info['last_price']
        change = ((price - t_info['previous_close']) / t_info['previous_close']) * 100
        color = "#00ffad" if change >= 0 else "#ff4b4b"
        sign = "+" if change >= 0 else ""
        ticker_data_string += f'<span style="color: white; font-weight: bold; margin-left: 40px; font-family: monospace;">{tkr.replace("-USD", "")}:</span>'
        ticker_data_string += f'<span style="color: {color}; font-weight: bold; margin-left: 5px; font-family: monospace;">{price:,.2f} ({sign}{change:.2f}%)</span>'
    except:
        continue

marquee_html = f"""
<div style="background-color: #000; overflow: hidden; white-space: nowrap; padding: 12px 0; border-top: 2px solid #333; border-bottom: 2px solid #333; margin-bottom: 20px;">
    <div style="display: inline-block; white-space: nowrap; animation: marquee 30s linear infinite;">
        {ticker_data_string} {ticker_data_string} {ticker_data_string}
    </div>
</div>
<style>
@keyframes marquee {{
    0% {{ transform: translateX(0); }}
    100% {{ transform: translateX(-33.33%); }}
}}
</style>
"""
components.html(marquee_html, height=60)


# ════════════════════════════════════════════════════════════
#
#  ██████╗ ██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗
# ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗
# ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║
# ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║
# ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝
#  ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝
#
#  MODULES : MARCHÉ CRYPTO
#  - BITCOIN DOMINANCE
#  - CRYPTO WALLET
#  - HEATMAP LIQUIDATIONS
#  - ORDER BOOK LIVE
#  - WHALE WATCHER
#
# ════════════════════════════════════════════════════════════

# ==========================================
# OUTIL : BITCOIN DOMINANCE (BTC.D)
# ==========================================
if outil == "BITCOIN DOMINANCE":
    st.title("📊 BITCOIN DOMINANCE (BTC.D)")
    st.write("Analyse de la part de marché du Bitcoin par rapport au reste du marché crypto.")

    col1, col2, col3 = st.columns(3)
    p_btc = get_crypto_price("BTC")
    with col1:
        st.metric("BTC PRICE", f"{p_btc:,.0f} $" if p_btc else "N/A")
    with col2:
        st.info("💡 Si BTC.D monte + BTC monte = Altcoins souffrent.")
    with col3:
        st.info("💡 Si BTC.D baisse + BTC stagne = Altseason.")

    st.markdown("---")

    tv_html_dom = """
        <div id="tv_chart_dom" style="height:600px;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({
          "autosize": true,
          "symbol": "CRYPTOCAP:BTC.D",
          "interval": "D",
          "timezone": "Europe/Paris",
          "theme": "dark",
          "style": "1",
          "locale": "fr",
          "toolbar_bg": "#f1f3f6",
          "enable_publishing": false,
          "hide_top_toolbar": false,
          "save_image": false,
          "container_id": "tv_chart_dom"
        });
        </script>
    """
    components.html(tv_html_dom, height=600)

# ==========================================
# OUTIL : CRYPTO WALLET TRACKER
# ==========================================
elif outil == "CRYPTO WALLET":
    st.title("₿ CRYPTO PROFIT TRACKER")

    st.subheader("» CONFIGURATION DES POSITIONS")
    c1, c2 = st.columns(2)
    with c1:
        achat_btc = st.number_input("PRIX D'ACHAT MOYEN BTC ($)", value=40000.0)
        qte_btc = st.number_input("QUANTITÉ BTC DÉTENUE", value=0.01, format="%.4f")
    with c2:
        achat_eth = st.number_input("PRIX D'ACHAT MOYEN ETH ($)", value=2500.0)
        qte_eth = st.number_input("QUANTITÉ ETH DÉTENUE", value=0.1, format="%.4f")

    def get_crypto_price(symbol):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return float(response.json()['price'])
            return yf.Ticker(f"{symbol}-USD").fast_info['last_price']
        except:
            return None

    def display_crypto_card(nom, actuel, achat, qte):
        profit_unit = actuel - achat
        profit_total = profit_unit * qte
        perf_pct = (actuel - achat) / achat * 100
        couleur = "#00ff00" if perf_pct >= 0 else "#ff0000"
        signe = "+" if perf_pct >= 0 else ""
        st.markdown(f"""
            <div style="border: 1px solid #333; padding: 20px; border-radius: 5px; background: #111;">
                <h3 style="margin:0; color:#ff9800;">{nom}</h3>
                <p style="margin:0; font-size:12px; color:#666;">PRIX ACTUEL</p>
                <h2 style="margin:0; color:#00ff00;">{actuel:,.2f} $</h2>
                <hr style="border:0.5px solid #222;">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <p style="margin:0; font-size:12px; color:#666;">PERFORMANCE</p>
                        <p style="margin:0; color:{couleur}; font-weight:bold;">{signe}{perf_pct:.2f} %</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin:0; font-size:12px; color:#666;">PROFIT TOTAL</p>
                        <p style="margin:0; color:{couleur}; font-weight:bold;">{signe}{profit_total:,.2f} $</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    p_btc = get_crypto_price("BTC")
    p_eth = get_crypto_price("ETH")

    if p_btc and p_eth:
        st.markdown("---")
        col_btc, col_eth = st.columns(2)
        with col_btc:
            display_crypto_card("BITCOIN", p_btc, achat_btc, qte_btc)
        with col_eth:
            display_crypto_card("ETHEREUM", p_eth, achat_eth, qte_eth)

        total_val = (p_btc * qte_btc) + (p_eth * qte_eth)
        total_investi = (achat_btc * qte_btc) + (achat_eth * qte_eth)
        profit_global = total_val - total_investi
        perf_globale = (profit_global / total_investi) * 100 if total_investi > 0 else 0

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("VALEUR TOTALE", f"{total_val:,.2f} $")
        m2.metric("PROFIT GLOBAL", f"{profit_global:,.2f} $", f"{perf_globale:+.2f}%")
        m3.metric("STATUS", "LIVE FEED", "OK")
    else:
        st.warning("⚠️ ATTENTE DES DONNÉES MARCHÉ...")

# ==========================================
# OUTIL : HEATMAP LIQUIDATIONS
# ==========================================
elif outil == "HEATMAP LIQUIDATIONS":
    st.markdown("<h1 style='text-align: center; color: #ff9800;'>🔥 MARKET LIQUIDATION HEATMAP</h1>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div style='border:1px solid #333; padding:10px; text-align:center;'><b>ASSET:</b> BTC/USDT</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='border:1px solid #333; padding:10px; text-align:center;'><b>SOURCE:</b> BINANCE FUTURES</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div style='border:1px solid #333; padding:10px; text-align:center;'><b>MODE:</b> PRO FEED LIVE</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    hauteur_pro = 950

    st.markdown(f"""
        <div style="background-color: #000000; padding: 5px; border: 1px solid #ff9800; border-radius: 8px;">
            <iframe
                src="https://www.coinglass.com/fr/pro/futures/LiquidationHeatMap"
                width="100%"
                height="{hauteur_pro}px"
                style="border:none; filter: brightness(0.9) contrast(1.1);"
                scrolling="yes">
            </iframe>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="margin-top:10px; display:flex; justify-content:space-between; color:#666; font-size:12px;">
            <span>GRADIENT: JAUNE (HAUTE DENSITÉ) > VIOLET (BASSE DENSITÉ)</span>
            <span>MISE À JOUR: TEMPS RÉEL (COINGLASS)</span>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# OUTIL : ORDER BOOK LIVE
# ==========================================
elif outil == "ORDER BOOK LIVE":
    show_order_book_ui()

# ==========================================
# OUTIL : WHALE WATCHER
# ==========================================
elif outil == "WHALE WATCHER":
    st.title("🐋 BITCOIN WHALE TRACKER")
    st.write("Surveillance des transactions sur Binance (Flux Temps Réel)")

    if 'whale_logs' not in st.session_state:
        st.session_state.whale_logs = []
    if 'pressure_data' not in st.session_state:
        st.session_state.pressure_data = []

    seuil_baleine = st.slider("SEUIL DE FILTRAGE (BTC)", 0.1, 5.0, 0.5)

    def get_live_trades():
        try:
            url = "https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=50"
            res = requests.get(url, timeout=2).json()
            return res
        except:
            return []

    trades = get_live_trades()

    for t in trades:
        try:
            qty = float(t.get('qty', 0))
            prix = float(t.get('price', 0))
            if qty >= seuil_baleine:
                is_seller = t.get('isBuyerMaker', False)
                color = "🔴" if is_seller else "🟢"
                label = "SELL" if is_seller else "BUY"
                timestamp = t.get('time', 0)
                time_str = datetime.fromtimestamp(timestamp/1000).strftime('%H:%M:%S')
                log = f"{color} | {time_str} | {label} {qty:.2f} BTC @ {prix:,.0f} $"
                if log not in st.session_state.whale_logs:
                    st.session_state.whale_logs.insert(0, log)
                    st.session_state.pressure_data.append(0 if is_seller else 1)
        except:
            continue

    st.session_state.whale_logs = st.session_state.whale_logs[:15]
    if len(st.session_state.pressure_data) > 50:
        st.session_state.pressure_data.pop(0)

    pct_a, pct_v = 50, 50
    if st.session_state.pressure_data:
        total_p = len(st.session_state.pressure_data)
        achats = sum(st.session_state.pressure_data)
        ventes = total_p - achats
        pct_a = (achats / total_p) * 100
        pct_v = (ventes / total_p) * 100

        st.subheader("📊 BUY vs SELL PRESSURE (Whales)")
        c_p1, c_p2 = st.columns([max(1, pct_a), max(1, pct_v)])
        c_p1.markdown(f"<div style='background:#00ff00; height:25px; border-radius:5px 0 0 5px; text-align:center; color:black; font-weight:bold; line-height:25px;'>{pct_a:.0f}% BUY</div>", unsafe_allow_html=True)
        c_p2.markdown(f"<div style='background:#ff0000; height:25px; border-radius:0 5px 5px 0; text-align:center; color:white; font-weight:bold; line-height:25px;'>{pct_v:.0f}% SELL</div>", unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📝 LIVE ACTIVITY LOG")
        if not st.session_state.whale_logs:
            st.info(f"En attente de mouvements > {seuil_baleine} BTC...")
        else:
            for l in st.session_state.whale_logs:
                if "🟢" in l:
                    st.markdown(f"<span style='color:#00ff00; font-family:monospace;'>{l}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:#ff4b4b; font-family:monospace;'>{l}</span>", unsafe_allow_html=True)
    with col2:
        st.subheader("💡 INSIGHT")
        if pct_a > 60:
            st.success("ACCUMULATION : Les baleines achètent agressivement.")
        elif pct_v > 60:
            st.error("DISTRIBUTION : Les baleines vendent leurs positions.")
        else:
            st.warning("INDÉCISION : Flux équilibré entre acheteurs et vendeurs.")


# ════════════════════════════════════════════════════════════
#
#   █████╗  ██████╗████████╗██╗ ██████╗ ███╗   ██╗███████╗
#  ██╔══██╗██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝
#  ███████║██║        ██║   ██║██║   ██║██╔██╗ ██║███████╗
#  ██╔══██║██║        ██║   ██║██║   ██║██║╚██╗██║╚════██║
#  ██║  ██║╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║███████║
#  ╚═╝  ╚═╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝
#
#  MODULES : ACTIONS & BOURSE
#  - ANALYSEUR PRO
#  - ANALYSE TECHNIQUE PRO
#  - FIBONACCI CALCULATOR
#  - BACKTESTING ENGINE
#  - VALORISATION FONDAMENTALE
#  - MULTI-CHARTS
#  - EXPERT SYSTEM
#  - THE GRAND COUNCIL
#  - MODE DUEL
#  - MARKET MONITOR
#  - SCREENER CAC 40
#  - DIVIDEND CALENDAR
#
# ════════════════════════════════════════════════════════════

# ==========================================
# OUTIL : ANALYSEUR PRO
# ==========================================
elif outil == "ANALYSEUR PRO":
    nom_entree = st.sidebar.text_input("TICKER SEARCH", value="NVIDIA")
    ticker = trouver_ticker(nom_entree)
    info = get_ticker_info(ticker)

    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1

        if prix == 0 or prix is None:
            try:
                hist = yf.Ticker(ticker).history(period="1d")
                if not hist.empty:
                    prix = float(hist['Close'].iloc[-1])
            except:
                prix = 1

        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 0)
        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare') or 0

        calculator = ValuationCalculator(ticker)
        valuation_results = calculator.get_comprehensive_valuation()

        if "consensus" in valuation_results:
            val_consensus = valuation_results["consensus"]["fair_value"]
            marge_pourcent = valuation_results["consensus"]["upside_pct"]
            methods_count = valuation_results["consensus"]["methods_used"]
            recommendation = valuation_results["consensus"]["recommendation"]
        else:
            val_consensus = 0
            marge_pourcent = 0
            methods_count = 0
            recommendation = "N/A"

        st.title(f"» {nom} // {ticker}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LAST PRICE", f"{prix:.2f} {devise}")
        c2.metric("CONSENSUS VALUE", f"{val_consensus:.2f} {devise}" if val_consensus > 0 else "N/A")
        c3.metric("POTENTIAL", f"{marge_pourcent:+.2f}%" if val_consensus > 0 else "N/A")
        c4.metric("SECTOR", secteur)

        if recommendation != "N/A":
            if "ACHAT" in recommendation:
                st.success(f"**RECOMMANDATION : {recommendation}** 🚀")
            elif "VENTE" in recommendation:
                st.error(f"**RECOMMANDATION : {recommendation}** ⚠️")
            else:
                st.info(f"**RECOMMANDATION : {recommendation}** ⚖️")

        st.caption(f"Basé sur {methods_count} méthode(s) de valorisation : Graham + DCF + P/E + P/B")
        st.markdown("---")
        st.subheader("» ADVANCED TECHNICAL CHART")
        afficher_graphique_pro(ticker, height=650)

        st.markdown("---")
        st.subheader("» FINANCIAL DATA")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.write(f"**EPS (BPA) :** {bpa:.2f} {devise}")
            st.write(f"**P/E RATIO :** {per:.2f}")
            book_value = info.get('bookValue', 0)
            st.write(f"**BOOK VALUE :** {book_value:.2f} {devise}")
        with f2:
            st.write(f"**DEBT/EQUITY :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**DIV. YIELD :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
        with f3:
            st.write(f"**PAYOUT RATIO :** {payout:.2f} %")
            st.write(f"**CASH/SHARE :** {cash_action:.2f} {devise}")

        st.markdown("---")
        st.subheader("» MÉTHODES DE VALORISATION DÉTAILLÉES")

        methods_available = [method for method in valuation_results.keys() if method not in ["consensus", "dcf"]]

        if methods_available:
            tabs = st.tabs([method.upper() for method in methods_available])
            for idx, method in enumerate(methods_available):
                with tabs[idx]:
                    data = valuation_results[method]
                    if "error" in data:
                        st.warning(f"⚠️ {data['error']}")
                    else:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("VALEUR JUSTE", f"${data['fair_value']:.2f}")
                        with col2:
                            st.metric("PRIX ACTUEL", f"${data['current_price']:.2f}")
                        with col3:
                            upside_val = data['upside_pct']
                            color = "normal" if abs(upside_val) < 10 else ("inverse" if upside_val > 0 else "off")
                            st.metric("POTENTIEL", f"{upside_val:+.1f}%", delta_color=color)
                        st.markdown("---")
                        st.markdown("**PARAMÈTRES DE LA MÉTHODE:**")
                        if method == "graham":
                            col_param = st.columns(3)
                            with col_param[0]: st.info(f"**EPS:** ${data['eps']:.2f}")
                            with col_param[1]: st.info(f"**Book Value:** ${data['book_value']:.2f}")
                            with col_param[2]: st.info(f"**Formule:** √(22.5 × EPS × BV)")
                            st.caption("📚 Formule de Benjamin Graham - Investissement Value")
                        elif method == "pe":
                            col_param = st.columns(3)
                            with col_param[0]: st.info(f"**P/E Actuel:** {data['current_pe']}")
                            with col_param[1]: st.info(f"**P/E Cible:** {data['target_pe']}")
                            with col_param[2]: st.info(f"**EPS:** ${data['eps']:.2f}")
                            st.write(f"- Type EPS: **{data['eps_type']}**")
                        elif method == "pb":
                            col_param = st.columns(3)
                            with col_param[0]: st.info(f"**Valeur Comptable:** ${data['book_value']:.2f}")
                            with col_param[1]: st.info(f"**P/B Actuel:** {data['current_pb']:.2f}")
                            with col_param[2]: st.info(f"**P/B Cible:** {data['target_pb']:.2f}")
                        elif method == "nvt":
                            col_param = st.columns(3)
                            with col_param[0]: st.info(f"**NVT Ratio:** {data['nvt_ratio']:.2f}")
                            with col_param[1]: st.info(f"**Status:** {data['status']}")
                            with col_param[2]: st.info(f"**Market Cap:** ${data['market_cap']:,.0f}")
                            st.write(f"- Volume quotidien moyen: **${data['daily_tx_value']:,.0f}**")
                            st.write(f"- NVT cible: **{data['target_nvt']}**")
                            st.caption("NVT < 10 = Sous-évalué | NVT 10-20 = Juste valorisé | NVT > 20 = Surévalué")

        st.markdown("---")
        st.subheader("» QUALITY SCORE (20 MAX)")
        score = 0
        positifs, negatifs = [], []
        if bpa > 0:
            if per < 12:   score += 5; positifs.append("» ATTRACTIVE P/E [+5]")
            elif per < 20: score += 4; positifs.append("» FAIR VALUATION [+4]")
            else:          score += 1; positifs.append("• HIGH P/E [+1]")
        else:
            score -= 5; negatifs.append("!! NEGATIVE EPS [-5]")

        if dette_equity is not None:
            if dette_equity < 50:    score += 4; positifs.append("» STRONG BALANCE SHEET [+4]")
            elif dette_equity < 100: score += 3; positifs.append("» DEBT UNDER CONTROL [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("!! HIGH LEVERAGE [-4]")

        if 10 < payout <= 80:  score += 4; positifs.append("» SUSTAINABLE DIVIDEND [+4]")
        elif payout > 95:      score -= 4; negatifs.append("!! PAYOUT RISK [-4]")
        if marge_pourcent > 30:  score += 5; positifs.append("» CONSENSUS DISCOUNT [+5]")
        elif marge_pourcent > 15: score += 3; positifs.append("» MODERATE DISCOUNT [+3]")

        score_f = min(20, max(0, score))
        cs, cd = st.columns([1, 2])
        with cs:
            st.write(f"## SCORE : {score_f}/20")
            st.progress(score_f / 20)
        with cd:
            for p in positifs:
                st.markdown(f'<div style="background:#002b00; color:#00ff00; border-left: 4px solid #00ff00; padding:10px; margin-bottom:5px;">{p}</div>', unsafe_allow_html=True)
            for n in negatifs:
                st.markdown(f'<div style="background:#2b0000; color:#ff0000; border-left: 4px solid #ff0000; padding:10px; margin-bottom:5px;">{n}</div>', unsafe_allow_html=True)

        with st.expander("ℹ️ À PROPOS DES 4 MÉTHODES DE VALORISATION"):
            st.markdown(f"""
            **CONSENSUS BASÉ SUR 4 MÉTHODES :**

            Le prix consensus ({val_consensus:.2f} {devise}) est la **médiane** des 4 méthodes suivantes :

            **1️⃣ GRAHAM (Benjamin Graham Formula)**
            - Formule : `√(22.5 × EPS × Book Value)`
            - Meilleure pour : Actions "value" traditionnelles
            - Fiabilité : Haute pour entreprises établies

            **2️⃣ DCF (Discounted Cash Flow)**
            - Principe : Actualisation des flux futurs de trésorerie
            - Meilleure pour : Sociétés matures avec cash flows stables
            - Fiabilité : Haute si les hypothèses sont bonnes

            **3️⃣ P/E RATIO (Price/Earnings)**
            - Principe : Valorisation relative basée sur les bénéfices
            - Meilleure pour : Comparaison sectorielle rapide
            - Fiabilité : Moyenne (dépend du secteur)

            **4️⃣ PRICE/BOOK**
            - Principe : Comparaison prix vs valeur comptable
            - Meilleure pour : Banques, financières, sociétés avec beaucoup d'actifs
            - Fiabilité : Moyenne (moins pertinent pour tech)

            **📊 INTERPRÉTATION DU POTENTIEL :**
            - **> +20%** : Fortement sous-évalué → ACHAT FORT 🚀
            - **+10% à +20%** : Sous-évalué → ACHAT 📈
            - **-10% à +10%** : Juste valorisé → CONSERVER ⚖️
            - **-20% à -10%** : Surévalué → VENTE 📉
            - **< -20%** : Fortement surévalué → VENTE FORTE ⚠️

            ⚠️ **ATTENTION :** Ces valorisations sont des indicateurs, pas des certitudes.
            À combiner avec l'analyse technique et les fondamentaux.
            """)

        st.markdown("---")
        st.subheader(f"» NEWS FEED : {nom}")

        tab_action_24h, tab_action_archive = st.tabs(["● LIVE FEED (24H)", "○ HISTORICAL (7D)"])
        search_term = nom.replace(" ", "+")
        url_rss = f"https://news.google.com/rss/search?q={search_term}+(site:investing.com+OR+bourse+OR+stock)&hl=fr&gl=FR&ceid=FR:fr"

        try:
            import time
            flux = feedparser.parse(url_rss)
            maintenant = time.time()
            secondes_par_jour = 24 * 3600
            articles = sorted(flux.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)

            with tab_action_24h:
                trouve_24h = False
                for entry in articles:
                    pub_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else maintenant
                    if (maintenant - pub_time) < secondes_par_jour:
                        trouve_24h = True
                        clean_title = entry.title.split(' - ')[0]
                        source = entry.source.get('title', 'Finance')
                        prefix = "■ INV |" if "investing" in source.lower() else "»"
                        with st.expander(f"{prefix} {clean_title}"):
                            st.write(f"**SOURCE :** {source}")
                            st.caption(f"🕒 TIMESTAMP : {entry.published}")
                            st.link_button("OPEN ARTICLE", entry.link)
                if not trouve_24h:
                    st.info("NO RECENT NEWS IN THE LAST 24H.")

            with tab_action_archive:
                for entry in articles[:12]:
                    clean_title = entry.title.split(' - ')[0]
                    source = entry.source.get('title', 'Finance')
                    prefix = "■ INV |" if "investing" in source.lower() else "•"
                    with st.expander(f"{prefix} {clean_title}"):
                        st.write(f"**SOURCE :** {source}")
                        st.caption(f"📅 DATE : {entry.published}")
                        st.link_button("VIEW ARCHIVE", entry.link)
        except Exception:
            st.error("ERROR FETCHING NEWS FEED.")
    else:
        st.error(f"⚠️ IMPOSSIBLE DE CHARGER LES DONNÉES POUR {ticker}")

# ==========================================
# OUTIL : ANALYSE TECHNIQUE PRO
# ==========================================
elif outil == "ANALYSE TECHNIQUE PRO":
    st.markdown("## 📈 ANALYSE TECHNIQUE AVANCÉE")
    st.info("Analyse complète avec RSI, MACD, Bollinger Bands et plus")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker_tech = st.text_input("TICKER", value="AAPL", key="tech_ticker").upper()
    with col2:
        period_tech = st.selectbox("PÉRIODE", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=2, key="tech_period")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🚀 ANALYSER", key="tech_analyze")

    if analyze_button:
        try:
            with st.spinner("Chargement et calcul des indicateurs..."):
                df = yf.download(ticker_tech, period=period_tech, progress=False)
                if df.empty:
                    st.error("Aucune donnée disponible pour ce ticker")
                else:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(1)

                    delta = df['Close'].diff()
                    gain = delta.copy(); loss = delta.copy()
                    gain[gain < 0] = 0; loss[loss > 0] = 0; loss = abs(loss)
                    avg_gain = gain.rolling(window=14).mean()
                    avg_loss = loss.rolling(window=14).mean()
                    avg_loss = avg_loss.replace(0, 0.0001)
                    rs = avg_gain / avg_loss
                    df['RSI'] = 100 - (100 / (1 + rs))

                    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
                    df['MACD'] = exp1 - exp2
                    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                    df['MACD_Hist'] = df['MACD'] - df['Signal']

                    df['SMA_20'] = df['Close'].rolling(window=20).mean()
                    df['BB_std'] = df['Close'].rolling(window=20).std()
                    df['BB_Upper'] = df['SMA_20'] + (df['BB_std'] * 2)
                    df['BB_Lower'] = df['SMA_20'] - (df['BB_std'] * 2)
                    df['SMA_50'] = df['Close'].rolling(window=50).mean()
                    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
                    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
                    df = df.dropna()

                    if len(df) == 0:
                        st.error("Pas assez de données pour calculer les indicateurs")
                    else:
                        last_row = df.iloc[-1]
                        rsi_val = float(last_row['RSI'])
                        macd_val = float(last_row['MACD'])
                        signal_val = float(last_row['Signal'])
                        close_val = float(last_row['Close'])
                        bb_upper_val = float(last_row['BB_Upper'])
                        bb_lower_val = float(last_row['BB_Lower'])
                        sma50_val = float(last_row['SMA_50'])
                        volume_val = float(last_row['Volume'])
                        volume_ma_val = float(last_row['Volume_MA'])

                        signals = []
                        score = 0

                        st.write(f"🔍 **Valeurs pour debug:** RSI={rsi_val:.2f}, MACD={macd_val:.4f}, Signal={signal_val:.4f}, Prix={close_val:.2f}, BB_Lower={bb_lower_val:.2f}, BB_Upper={bb_upper_val:.2f}")

                        if rsi_val < 35:
                            signals.append(("RSI", f"🟢 OVERSOLD ({rsi_val:.1f}) - Signal ACHAT", "bullish")); score += 2
                        elif rsi_val > 65:
                            signals.append(("RSI", f"🔴 OVERBOUGHT ({rsi_val:.1f}) - Signal VENTE", "bearish")); score -= 2
                        elif rsi_val < 45:
                            signals.append(("RSI", f"🟢 Légèrement bas ({rsi_val:.1f}) - Opportunité", "bullish")); score += 1
                        elif rsi_val > 55:
                            signals.append(("RSI", f"🟡 Légèrement haut ({rsi_val:.1f}) - Prudence", "neutral")); score -= 1
                        else:
                            signals.append(("RSI", f"🟡 NEUTRE ({rsi_val:.1f})", "neutral"))

                        macd_diff = macd_val - signal_val
                        if macd_diff > 0:
                            if macd_diff > 0.5:
                                signals.append(("MACD", f"🟢 FORTEMENT BULLISH (+{macd_diff:.2f})", "bullish")); score += 2
                            else:
                                signals.append(("MACD", f"🟢 BULLISH (+{macd_diff:.2f})", "bullish")); score += 1
                        else:
                            if macd_diff < -0.5:
                                signals.append(("MACD", f"🔴 FORTEMENT BEARISH ({macd_diff:.2f})", "bearish")); score -= 2
                            else:
                                signals.append(("MACD", f"🔴 BEARISH ({macd_diff:.2f})", "bearish")); score -= 1

                        bb_position = (close_val - bb_lower_val) / (bb_upper_val - bb_lower_val) * 100
                        if bb_position < 10:
                            signals.append(("Bollinger", f"🟢 Prix très proche bande basse ({bb_position:.0f}%) - ACHAT", "bullish")); score += 2
                        elif bb_position < 30:
                            signals.append(("Bollinger", f"🟢 Prix dans zone basse ({bb_position:.0f}%)", "bullish")); score += 1
                        elif bb_position > 90:
                            signals.append(("Bollinger", f"🔴 Prix très proche bande haute ({bb_position:.0f}%) - VENTE", "bearish")); score -= 2
                        elif bb_position > 70:
                            signals.append(("Bollinger", f"🔴 Prix dans zone haute ({bb_position:.0f}%)", "bearish")); score -= 1
                        else:
                            signals.append(("Bollinger", f"🟡 Prix au milieu ({bb_position:.0f}%)", "neutral"))

                        ma_diff_pct = ((close_val - sma50_val) / sma50_val) * 100
                        if ma_diff_pct > 5:
                            signals.append(("MA50", f"🟢 Prix bien au-dessus MA50 (+{ma_diff_pct:.1f}%)", "bullish")); score += 2
                        elif ma_diff_pct > 0:
                            signals.append(("MA50", f"🟢 Prix au-dessus MA50 (+{ma_diff_pct:.1f}%)", "bullish")); score += 1
                        elif ma_diff_pct < -5:
                            signals.append(("MA50", f"🔴 Prix bien en-dessous MA50 ({ma_diff_pct:.1f}%)", "bearish")); score -= 2
                        else:
                            signals.append(("MA50", f"🔴 Prix en-dessous MA50 ({ma_diff_pct:.1f}%)", "bearish")); score -= 1

                        volume_ratio = volume_val / volume_ma_val
                        if volume_ratio > 2:
                            signals.append(("Volume", f"⚠️ Volume TRÈS élevé (x{volume_ratio:.1f})", "important")); score += 2
                        elif volume_ratio > 1.5:
                            signals.append(("Volume", f"⚠️ Volume élevé (x{volume_ratio:.1f})", "important")); score += 1
                        elif volume_ratio < 0.5:
                            signals.append(("Volume", f"📊 Volume faible (x{volume_ratio:.1f})", "neutral"))
                        else:
                            signals.append(("Volume", f"📊 Volume normal (x{volume_ratio:.1f})", "neutral"))

                        if score >= 5:    sentiment = "FORTEMENT HAUSSIER 🚀"; sentiment_color = "#00ff00"
                        elif score >= 2: sentiment = "HAUSSIER 📈"; sentiment_color = "#7fff00"
                        elif score >= 1: sentiment = "LÉGÈREMENT HAUSSIER 📈"; sentiment_color = "#90ee90"
                        elif score <= -5: sentiment = "FORTEMENT BAISSIER 📉"; sentiment_color = "#ff0000"
                        elif score <= -2: sentiment = "BAISSIER 📉"; sentiment_color = "#ff4444"
                        elif score <= -1: sentiment = "LÉGÈREMENT BAISSIER 📉"; sentiment_color = "#ff6347"
                        else:             sentiment = "NEUTRE ➡️"; sentiment_color = "#ff9800"

                        st.markdown(f"""
                            <div style='text-align: center; padding: 20px; background: {sentiment_color}22; border: 3px solid {sentiment_color}; border-radius: 15px; margin: 20px 0;'>
                                <h1 style='color: {sentiment_color}; margin: 0;'>{sentiment}</h1>
                                <p style='color: white; font-size: 20px; margin: 10px 0;'>Score Technique: {score}/10</p>
                                <p style='color: #ccc; font-size: 14px; margin: 5px 0;'>Analyse basée sur 5 indicateurs techniques</p>
                            </div>
                        """, unsafe_allow_html=True)

                        st.markdown("---")
                        st.markdown("### 📊 GRAPHIQUE AVEC INDICATEURS")

                        from plotly.subplots import make_subplots
                        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                                            row_heights=[0.6, 0.2, 0.2],
                                            subplot_titles=('PRIX & BOLLINGER BANDS', 'RSI', 'MACD'))

                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                                      low=df['Low'], close=df['Close'], name='Prix'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='BB Upper',
                                                  line=dict(color='rgba(255,152,0,0.3)', dash='dash')), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name='SMA 20',
                                                  line=dict(color='orange', width=2)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='BB Lower',
                                                  line=dict(color='rgba(255,152,0,0.3)', dash='dash'),
                                                  fill='tonexty', fillcolor='rgba(255,152,0,0.1)'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA 50',
                                                  line=dict(color='cyan', width=2)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI',
                                                  line=dict(color='purple', width=2)), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD',
                                                  line=dict(color='blue', width=2)), row=3, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='Signal',
                                                  line=dict(color='red', width=2)), row=3, col=1)
                        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram',
                                             marker_color='gray'), row=3, col=1)

                        fig.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
                                          height=900, showlegend=True, xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)

                        st.markdown("---")
                        st.markdown("### 🎯 SIGNAUX DÉTECTÉS")
                        cols_signals = st.columns(3)
                        for idx, (indicator, message, signal_type) in enumerate(signals):
                            with cols_signals[idx % 3]:
                                color_map = {"bullish": "#00ff00", "bearish": "#ff0000",
                                             "neutral": "#ff9800", "important": "#00ffff"}
                                st.markdown(f"""
                                    <div style='padding: 15px; background: {color_map.get(signal_type, '#666')}22; border: 2px solid {color_map.get(signal_type, '#666')}; border-radius: 10px; margin: 10px 0; min-height: 100px;'>
                                        <h4 style='color: {color_map.get(signal_type, '#fff')}; margin: 0 0 10px 0;'>{indicator}</h4>
                                        <p style='color: #ccc; font-size: 14px; margin: 0;'>{message}</p>
                                    </div>
                                """, unsafe_allow_html=True)

                        st.markdown("---")
                        st.markdown("### 📊 VALEURS ACTUELLES")
                        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                        with col_stat1:
                            st.metric("RSI", f"{rsi_val:.2f}")
                            st.metric("Prix", f"${close_val:.2f}")
                        with col_stat2:
                            st.metric("MACD", f"{macd_val:.4f}")
                            st.metric("Signal", f"{signal_val:.4f}")
                        with col_stat3:
                            st.metric("BB Upper", f"${bb_upper_val:.2f}")
                            st.metric("BB Lower", f"${bb_lower_val:.2f}")
                        with col_stat4:
                            st.metric("SMA 20", f"${float(last_row['SMA_20']):.2f}")
                            st.metric("SMA 50", f"${sma50_val:.2f}")

        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# OUTIL : FIBONACCI CALCULATOR
# ==========================================
elif outil == "FIBONACCI CALCULATOR":
    st.markdown("## 📐 CALCULATEUR FIBONACCI")
    st.info("Calcul automatique des niveaux de retracement et d'extension de Fibonacci")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker_fib = st.text_input("TICKER", value="AAPL", key="fib_ticker").upper()
    with col2:
        period_fib = st.selectbox("PÉRIODE", ["1mo", "3mo", "6mo", "1y", "2y"], index=1, key="fib_period")
    with col3:
        fib_type = st.selectbox("TYPE", ["Retracement (Baisse)", "Extension (Hausse)"], key="fib_type")

    if st.button("🚀 CALCULER FIBONACCI", key="fib_calc"):
        try:
            with st.spinner("Calcul des niveaux Fibonacci..."):
                df_fib = yf.download(ticker_fib, period=period_fib, progress=False)
                if df_fib.empty:
                    st.error("Aucune donnée disponible")
                else:
                    if isinstance(df_fib.columns, pd.MultiIndex):
                        df_fib.columns = df_fib.columns.get_level_values(0)

                    high_price = float(df_fib['High'].max())
                    low_price = float(df_fib['Low'].min())
                    current_price = float(df_fib['Close'].iloc[-1])
                    high_date = df_fib['High'].idxmax()
                    low_date = df_fib['Low'].idxmin()
                    diff = high_price - low_price

                    if "Baisse" in fib_type:
                        levels = {
                            "0.0% (Haut)": high_price,
                            "23.6%": high_price - (diff * 0.236),
                            "38.2%": high_price - (diff * 0.382),
                            "50.0%": high_price - (diff * 0.500),
                            "61.8%": high_price - (diff * 0.618),
                            "78.6%": high_price - (diff * 0.786),
                            "100.0% (Bas)": low_price
                        }
                        title_chart = "RETRACEMENT FIBONACCI (BAISSE)"
                    else:
                        levels = {
                            "0.0% (Bas)": low_price,
                            "23.6%": low_price + (diff * 0.236),
                            "38.2%": low_price + (diff * 0.382),
                            "50.0%": low_price + (diff * 0.500),
                            "61.8%": low_price + (diff * 0.618),
                            "78.6%": low_price + (diff * 0.786),
                            "100.0% (Haut)": high_price,
                            "127.2%": low_price + (diff * 1.272),
                            "161.8%": low_price + (diff * 1.618)
                        }
                        title_chart = "EXTENSION FIBONACCI (HAUSSE)"

                    st.markdown("### 📊 NIVEAUX CLÉS")
                    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                    with col_info1: st.metric("Prix Actuel", f"${current_price:.2f}")
                    with col_info2: st.metric("Plus Haut", f"${high_price:.2f}", f"{high_date.strftime('%Y-%m-%d')}")
                    with col_info3: st.metric("Plus Bas", f"${low_price:.2f}", f"{low_date.strftime('%Y-%m-%d')}")
                    with col_info4:
                        range_pct = ((high_price - low_price) / low_price) * 100
                        st.metric("Range", f"{range_pct:.1f}%")

                    st.markdown("---")
                    st.markdown("### 📐 NIVEAUX FIBONACCI")
                    fib_data = []
                    for level_name, level_price in levels.items():
                        distance_from_current = ((level_price - current_price) / current_price) * 100
                        if level_price > current_price:
                            sr_type = "🔴 RÉSISTANCE"; color = "#ff4444"
                        elif level_price < current_price:
                            sr_type = "🟢 SUPPORT"; color = "#00ff00"
                        else:
                            sr_type = "🎯 PRIX ACTUEL"; color = "#ff9800"
                        fib_data.append({"Niveau": level_name, "Prix": f"${level_price:.2f}",
                                         "Distance": f"{distance_from_current:+.2f}%", "Type": sr_type,
                                         "Prix_Num": level_price, "Color": color})

                    df_fib_levels = pd.DataFrame(fib_data)
                    for idx, row in df_fib_levels.iterrows():
                        st.markdown(f"""
                            <div style='padding: 12px; background: {row['Color']}22; border-left: 4px solid {row['Color']}; border-radius: 5px; margin: 8px 0;'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <div>
                                        <b style='color: {row['Color']}; font-size: 16px;'>{row['Niveau']}</b>
                                        <span style='color: #ccc; margin-left: 20px;'>{row['Type']}</span>
                                    </div>
                                    <div style='text-align: right;'>
                                        <b style='color: white; font-size: 18px;'>{row['Prix']}</b>
                                        <span style='color: #aaa; margin-left: 15px;'>{row['Distance']}</span>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("### 📈 GRAPHIQUE AVEC NIVEAUX FIBONACCI")
                    fig_fib = go.Figure()
                    fig_fib.add_trace(go.Candlestick(x=df_fib.index, open=df_fib['Open'], high=df_fib['High'],
                                                      low=df_fib['Low'], close=df_fib['Close'], name=ticker_fib))
                    colors_fib = ['#ff0000', '#ff6b6b', '#ffd93d', '#6bcf7f', '#4ecdc4', '#45b7d1', '#96ceb4']
                    for idx, (level_name, level_price) in enumerate(levels.items()):
                        color = colors_fib[idx % len(colors_fib)]
                        fig_fib.add_hline(y=level_price, line_dash="dash", line_color=color, line_width=2,
                                          annotation_text=f"{level_name}: ${level_price:.2f}",
                                          annotation_position="right",
                                          annotation=dict(font=dict(size=11, color=color), bgcolor="rgba(0,0,0,0.7)"))
                    fig_fib.add_hline(y=current_price, line_dash="solid", line_color="#ff9800", line_width=3,
                                      annotation_text=f"Prix Actuel: ${current_price:.2f}", annotation_position="left",
                                      annotation=dict(font=dict(size=12, color="#ff9800", family="Arial Black"),
                                                      bgcolor="rgba(0,0,0,0.9)"))
                    fig_fib.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
                                          title=title_chart, xaxis_rangeslider_visible=False, height=700,
                                          xaxis_title="Date", yaxis_title="Prix ($)")
                    st.plotly_chart(fig_fib, use_container_width=True)

                    st.markdown("---")
                    st.markdown("### 💡 ANALYSE")
                    closest_level = min(levels.items(), key=lambda x: abs(x[1] - current_price))
                    distance_to_closest = abs(closest_level[1] - current_price)
                    distance_pct = (distance_to_closest / current_price) * 100
                    resistances = [price for price in levels.values() if price > current_price]
                    supports = [price for price in levels.values() if price < current_price]
                    next_resistance = min(resistances) if resistances else None
                    next_support = max(supports) if supports else None

                    col_analysis1, col_analysis2 = st.columns(2)
                    with col_analysis1:
                        st.markdown("#### 🎯 NIVEAU LE PLUS PROCHE")
                        st.write(f"**{closest_level[0]}** à **${closest_level[1]:.2f}**")
                        st.write(f"Distance: **{distance_pct:.2f}%**")
                        if distance_pct < 1:   st.success("🎯 Prix très proche d'un niveau clé !")
                        elif distance_pct < 3: st.info("📍 Prix proche d'un niveau Fibonacci")
                        else:                  st.warning("📊 Prix entre deux niveaux")
                    with col_analysis2:
                        st.markdown("#### 🎚️ SUPPORT / RÉSISTANCE")
                        if next_resistance:
                            resistance_dist = ((next_resistance - current_price) / current_price) * 100
                            st.write(f"🔴 **Prochaine résistance:** ${next_resistance:.2f}")
                            st.write(f"   Distance: +{resistance_dist:.2f}%")
                        if next_support:
                            support_dist = ((current_price - next_support) / current_price) * 100
                            st.write(f"🟢 **Prochain support:** ${next_support:.2f}")
                            st.write(f"   Distance: -{support_dist:.2f}%")

                    if next_support and next_resistance:
                        support_dist_pct = ((current_price - next_support) / current_price) * 100
                        resistance_dist_pct = ((next_resistance - current_price) / current_price) * 100
                        st.markdown("---")
                        st.markdown("#### 📋 STRATÉGIE SUGGÉRÉE")
                        st.markdown(f"""
                        <div style='padding: 20px; background: #1a1a1a; border-radius: 10px; border: 2px solid #ff9800;'>
                            <h4 style='color: #ff9800; margin-top: 0;'>📊 Zone de Trading Fibonacci</h4>
                            <ul style='color: #ccc;'>
                                <li><b>Achat potentiel:</b> Près du support à ${next_support:.2f} (-{support_dist_pct:.1f}%)</li>
                                <li><b>Objectif:</b> Résistance à ${next_resistance:.2f} (+{resistance_dist_pct:.1f}%)</li>
                                <li><b>Stop Loss:</b> En-dessous du prochain niveau Fibonacci inférieur</li>
                                <li><b>Ratio Risk/Reward:</b> {(resistance_dist_pct/support_dist_pct):.2f}:1</li>
                            </ul>
                            <p style='color: #999; font-size: 12px; margin-bottom: 0;'>⚠️ Ceci n'est pas un conseil financier. Faites vos propres recherches.</p>
                        </div>
                        """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erreur: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# OUTIL : BACKTESTING ENGINE
# ==========================================
elif outil == "BACKTESTING ENGINE":
    st.markdown("## ⚡ BACKTESTING ENGINE")
    st.info("Testez vos stratégies de trading sur données historiques")

    col_config1, col_config2, col_config3 = st.columns(3)
    with col_config1:
        ticker_bt = st.text_input("TICKER", value="AAPL", key="bt_ticker").upper()
    with col_config2:
        period_bt = st.selectbox("PÉRIODE", ["6mo", "1y", "2y", "5y", "max"], index=1, key="bt_period")
    with col_config3:
        capital_bt = st.number_input("CAPITAL ($)", min_value=1000, value=10000, step=1000, key="bt_capital")

    st.markdown("---")
    st.markdown("### 🎯 STRATÉGIE DE TRADING")

    col_strat1, col_strat2 = st.columns(2)
    with col_strat1:
        strategy = st.selectbox("STRATÉGIE", [
            "RSI Oversold/Overbought",
            "MACD Crossover",
            "Moving Average Cross (Golden Cross)",
            "Bollinger Bounce",
            "Combinée (RSI + MACD)"
        ], key="bt_strategy")
    with col_strat2:
        if "RSI" in strategy:
            col_p1, col_p2 = st.columns(2)
            with col_p1: rsi_buy = st.slider("RSI Achat (<)", 20, 40, 30, key="bt_rsi_buy")
            with col_p2: rsi_sell = st.slider("RSI Vente (>)", 60, 80, 70, key="bt_rsi_sell")
        elif "Bollinger" in strategy:
            bb_period = st.slider("Période Bollinger", 10, 30, 20, key="bt_bb")
        elif "Moving Average" in strategy:
            col_p1, col_p2 = st.columns(2)
            with col_p1: ma_fast = st.slider("MA Rapide", 10, 50, 20, key="bt_ma_fast")
            with col_p2: ma_slow = st.slider("MA Lente", 50, 200, 50, key="bt_ma_slow")

    with st.expander("⚙️ PARAMÈTRES AVANCÉS"):
        col_adv1, col_adv2, col_adv3 = st.columns(3)
        with col_adv1: stop_loss_pct = st.slider("Stop Loss (%)", 0, 20, 5, key="bt_sl")
        with col_adv2: take_profit_pct = st.slider("Take Profit (%)", 0, 50, 0, key="bt_tp", help="0 = désactivé")
        with col_adv3: commission_pct = st.slider("Commission (%)", 0.0, 1.0, 0.1, step=0.1, key="bt_comm")

    if st.button("🚀 LANCER LE BACKTEST", key="bt_launch"):
        try:
            with st.spinner("Backtesting en cours..."):
                df_bt = yf.download(ticker_bt, period=period_bt, progress=False)
                if df_bt.empty:
                    st.error("Aucune donnée disponible")
                else:
                    if isinstance(df_bt.columns, pd.MultiIndex):
                        df_bt.columns = df_bt.columns.get_level_values(0)

                    delta = df_bt['Close'].diff()
                    gain = delta.copy(); loss = delta.copy()
                    gain[gain < 0] = 0; loss[loss > 0] = 0; loss = abs(loss)
                    avg_gain = gain.rolling(window=14).mean()
                    avg_loss = loss.rolling(window=14).mean()
                    avg_loss = avg_loss.replace(0, 0.0001)
                    rs = avg_gain / avg_loss
                    df_bt['RSI'] = 100 - (100 / (1 + rs))

                    exp1 = df_bt['Close'].ewm(span=12, adjust=False).mean()
                    exp2 = df_bt['Close'].ewm(span=26, adjust=False).mean()
                    df_bt['MACD'] = exp1 - exp2
                    df_bt['Signal'] = df_bt['MACD'].ewm(span=9, adjust=False).mean()

                    bb_p = bb_period if "Bollinger" in strategy else 20
                    df_bt['BB_SMA'] = df_bt['Close'].rolling(window=bb_p).mean()
                    df_bt['BB_std'] = df_bt['Close'].rolling(window=bb_p).std()
                    df_bt['BB_Upper'] = df_bt['BB_SMA'] + (df_bt['BB_std'] * 2)
                    df_bt['BB_Lower'] = df_bt['BB_SMA'] - (df_bt['BB_std'] * 2)

                    if "Moving Average" in strategy:
                        df_bt['MA_Fast'] = df_bt['Close'].rolling(window=ma_fast).mean()
                        df_bt['MA_Slow'] = df_bt['Close'].rolling(window=ma_slow).mean()
                    else:
                        df_bt['MA_Fast'] = df_bt['Close'].rolling(window=20).mean()
                        df_bt['MA_Slow'] = df_bt['Close'].rolling(window=50).mean()

                    df_bt = df_bt.dropna()

                    capital = float(capital_bt)
                    position = 0; shares = 0; entry_price = 0
                    trades = []; equity_curve = []

                    for i in range(1, len(df_bt)):
                        row = df_bt.iloc[i]
                        prev_row = df_bt.iloc[i-1]
                        current_price = float(row['Close'])
                        current_equity = capital if position == 0 else (shares * current_price)
                        equity_curve.append({'Date': row.name, 'Equity': current_equity})

                        if position == 1 and entry_price > 0:
                            if stop_loss_pct > 0 and current_price <= entry_price * (1 - stop_loss_pct/100):
                                capital = shares * current_price * (1 - commission_pct/100)
                                profit = capital - (shares * entry_price)
                                trades.append({'Date': row.name, 'Type': 'STOP LOSS', 'Prix': current_price,
                                               'Shares': shares, 'P/L': profit,
                                               'P/L %': (profit / (shares * entry_price)) * 100, 'Capital': capital})
                                position = 0; shares = 0; entry_price = 0; continue
                            if take_profit_pct > 0 and current_price >= entry_price * (1 + take_profit_pct/100):
                                capital = shares * current_price * (1 - commission_pct/100)
                                profit = capital - (shares * entry_price)
                                trades.append({'Date': row.name, 'Type': 'TAKE PROFIT', 'Prix': current_price,
                                               'Shares': shares, 'P/L': profit,
                                               'P/L %': (profit / (shares * entry_price)) * 100, 'Capital': capital})
                                position = 0; shares = 0; entry_price = 0; continue

                        buy_signal = False; sell_signal = False

                        if strategy == "RSI Oversold/Overbought":
                            if float(row['RSI']) < rsi_buy and position == 0: buy_signal = True
                            elif float(row['RSI']) > rsi_sell and position == 1: sell_signal = True
                        elif strategy == "MACD Crossover":
                            if float(row['MACD']) > float(row['Signal']) and float(prev_row['MACD']) <= float(prev_row['Signal']) and position == 0: buy_signal = True
                            elif float(row['MACD']) < float(row['Signal']) and float(prev_row['MACD']) >= float(prev_row['Signal']) and position == 1: sell_signal = True
                        elif strategy == "Moving Average Cross (Golden Cross)":
                            if float(row['MA_Fast']) > float(row['MA_Slow']) and float(prev_row['MA_Fast']) <= float(prev_row['MA_Slow']) and position == 0: buy_signal = True
                            elif float(row['MA_Fast']) < float(row['MA_Slow']) and float(prev_row['MA_Fast']) >= float(prev_row['MA_Slow']) and position == 1: sell_signal = True
                        elif strategy == "Bollinger Bounce":
                            if current_price <= float(row['BB_Lower']) and position == 0: buy_signal = True
                            elif current_price >= float(row['BB_Upper']) and position == 1: sell_signal = True
                        elif strategy == "Combinée (RSI + MACD)":
                            if float(row['RSI']) < 35 and float(row['MACD']) > float(row['Signal']) and position == 0: buy_signal = True
                            elif (float(row['RSI']) > 65 or float(row['MACD']) < float(row['Signal'])) and position == 1: sell_signal = True

                        if buy_signal and position == 0:
                            shares = (capital * (1 - commission_pct/100)) / current_price
                            entry_price = current_price
                            trades.append({'Date': row.name, 'Type': 'BUY', 'Prix': current_price,
                                           'Shares': shares, 'P/L': 0, 'P/L %': 0, 'Capital': 0})
                            capital = 0; position = 1
                        elif sell_signal and position == 1:
                            capital = shares * current_price * (1 - commission_pct/100)
                            profit = capital - (shares * entry_price)
                            trades.append({'Date': row.name, 'Type': 'SELL', 'Prix': current_price,
                                           'Shares': shares, 'P/L': profit,
                                           'P/L %': (profit / (shares * entry_price)) * 100, 'Capital': capital})
                            position = 0; shares = 0; entry_price = 0

                    final_price = float(df_bt['Close'].iloc[-1])
                    final_value = shares * final_price if position == 1 else capital
                    total_return = final_value - capital_bt
                    total_return_pct = (total_return / capital_bt) * 100

                    buy_hold_shares = capital_bt / float(df_bt['Close'].iloc[0])
                    buy_hold_value = buy_hold_shares * final_price
                    buy_hold_return = buy_hold_value - capital_bt
                    buy_hold_return_pct = (buy_hold_return / capital_bt) * 100

                    df_trades = pd.DataFrame(trades)
                    if len(df_trades) > 0:
                        completed_trades = df_trades[df_trades['Type'].isin(['SELL', 'STOP LOSS', 'TAKE PROFIT'])]
                        if len(completed_trades) > 0:
                            winning_trades = completed_trades[completed_trades['P/L'] > 0]
                            losing_trades = completed_trades[completed_trades['P/L'] <= 0]
                            num_trades = len(completed_trades)
                            num_wins = len(winning_trades); num_losses = len(losing_trades)
                            win_rate = (num_wins / num_trades * 100) if num_trades > 0 else 0
                            avg_win = winning_trades['P/L'].mean() if len(winning_trades) > 0 else 0
                            avg_loss = losing_trades['P/L'].mean() if len(losing_trades) > 0 else 0
                            equity_series = pd.Series([e['Equity'] for e in equity_curve])
                            running_max = equity_series.cummax()
                            drawdown = ((equity_series - running_max) / running_max) * 100
                            max_drawdown = drawdown.min()
                            returns = equity_series.pct_change().dropna()
                            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 0 and returns.std() > 0 else 0
                        else:
                            num_trades = win_rate = avg_win = avg_loss = max_drawdown = sharpe = 0
                            num_wins = num_losses = 0
                    else:
                        num_trades = win_rate = avg_win = avg_loss = max_drawdown = sharpe = 0
                        num_wins = num_losses = 0

                    st.markdown("---")
                    st.markdown("## 📊 RÉSULTATS DU BACKTEST")
                    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                    with col_res1: st.metric("Capital Initial", f"${capital_bt:,.0f}")
                    with col_res2: st.metric("Capital Final", f"${final_value:,.0f}", f"{total_return_pct:+.2f}%")
                    with col_res3: st.metric("Profit/Loss", f"${total_return:+,.0f}")
                    with col_res4: st.metric("Nombre de Trades", num_trades)

                    st.markdown("---")
                    st.markdown("### 📈 COMPARAISON : STRATÉGIE VS BUY & HOLD")
                    col_comp1, col_comp2 = st.columns(2)
                    with col_comp1:
                        st.markdown(f"<div style='padding: 20px; background: {'#00ff0022' if total_return_pct >= 0 else '#ff000022'}; border: 2px solid {'#00ff00' if total_return_pct >= 0 else '#ff0000'}; border-radius: 10px;'><h3 style='color: {'#00ff00' if total_return_pct >= 0 else '#ff0000'}; margin: 0 0 10px 0;'>🤖 STRATÉGIE: {strategy}</h3><p style='color: white; font-size: 28px; margin: 10px 0;'>{total_return_pct:+.2f}%</p><p style='color: #ccc; font-size: 16px; margin: 0;'>${final_value:,.0f}</p></div>", unsafe_allow_html=True)
                    with col_comp2:
                        st.markdown(f"<div style='padding: 20px; background: {'#00ff0022' if buy_hold_return_pct >= 0 else '#ff000022'}; border: 2px solid {'#00ff00' if buy_hold_return_pct >= 0 else '#ff0000'}; border-radius: 10px;'><h3 style='color: {'#00ff00' if buy_hold_return_pct >= 0 else '#ff0000'}; margin: 0 0 10px 0;'>💎 BUY & HOLD</h3><p style='color: white; font-size: 28px; margin: 10px 0;'>{buy_hold_return_pct:+.2f}%</p><p style='color: #ccc; font-size: 16px; margin: 0;'>${buy_hold_value:,.0f}</p></div>", unsafe_allow_html=True)

                    performance_diff = total_return_pct - buy_hold_return_pct
                    if performance_diff > 0:   st.success(f"🎉 La stratégie a surperformé le Buy & Hold de **{performance_diff:.2f}%** !")
                    elif performance_diff < 0: st.warning(f"⚠️ La stratégie a sous-performé le Buy & Hold de **{abs(performance_diff):.2f}%**")
                    else:                      st.info("➡️ Performance égale au Buy & Hold")

                    st.markdown("---")
                    st.markdown("### 📉 MÉTRIQUES DE PERFORMANCE")
                    col_metrics = st.columns(5)
                    with col_metrics[0]: st.metric("Win Rate", f"{win_rate:.1f}%")
                    with col_metrics[1]: st.metric("Trades Gagnants", num_wins)
                    with col_metrics[2]: st.metric("Trades Perdants", num_losses)
                    with col_metrics[3]: st.metric("Max Drawdown", f"{max_drawdown:.2f}%")
                    with col_metrics[4]: st.metric("Sharpe Ratio", f"{sharpe:.2f}")

                    st.markdown("---")
                    col_avg = st.columns(3)
                    with col_avg[0]: st.metric("Gain Moyen", f"${avg_win:+,.0f}")
                    with col_avg[1]: st.metric("Perte Moyenne", f"${avg_loss:+,.0f}")
                    with col_avg[2]:
                        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                        st.metric("Profit Factor", f"{profit_factor:.2f}")

                    st.markdown("---")
                    st.markdown("### 📈 EQUITY CURVE")
                    df_equity = pd.DataFrame(equity_curve)
                    fig_equity = go.Figure()
                    fig_equity.add_trace(go.Scatter(x=df_equity['Date'], y=df_equity['Equity'],
                                                     fill='tozeroy', name='Portfolio Value',
                                                     line=dict(color='cyan', width=3),
                                                     fillcolor='rgba(0, 255, 255, 0.1)'))
                    fig_equity.add_hline(y=capital_bt, line_dash="dash", line_color="orange",
                                         annotation_text="Capital Initial",
                                         annotation=dict(font=dict(size=10)))
                    buy_hold_equity = [buy_hold_shares * float(df_bt.loc[date, 'Close']) for date in df_equity['Date']]
                    fig_equity.add_trace(go.Scatter(x=df_equity['Date'], y=buy_hold_equity,
                                                     name='Buy & Hold', line=dict(color='yellow', width=2, dash='dash')))
                    fig_equity.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
                                              title="Évolution du Capital vs Buy & Hold",
                                              xaxis_title="Date", yaxis_title="Valeur ($)", height=500, hovermode='x unified')
                    st.plotly_chart(fig_equity, use_container_width=True)

                    if len(trades) > 0:
                        st.markdown("---")
                        st.markdown("### 📍 POINTS D'ENTRÉE ET SORTIE")
                        fig_trades = go.Figure()
                        fig_trades.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Close'], name='Prix',
                                                         line=dict(color='white', width=2)))
                        if "Moving Average" in strategy:
                            fig_trades.add_trace(go.Scatter(x=df_bt.index, y=df_bt['MA_Fast'], name=f'MA{ma_fast}',
                                                             line=dict(color='cyan', width=1.5)))
                            fig_trades.add_trace(go.Scatter(x=df_bt.index, y=df_bt['MA_Slow'], name=f'MA{ma_slow}',
                                                             line=dict(color='magenta', width=1.5)))
                        if "Bollinger" in strategy:
                            fig_trades.add_trace(go.Scatter(x=df_bt.index, y=df_bt['BB_Upper'], name='BB Upper',
                                                             line=dict(color='orange', width=1, dash='dash')))
                            fig_trades.add_trace(go.Scatter(x=df_bt.index, y=df_bt['BB_Lower'], name='BB Lower',
                                                             line=dict(color='orange', width=1, dash='dash')))
                        buys = df_trades[df_trades['Type'] == 'BUY']
                        if len(buys) > 0:
                            fig_trades.add_trace(go.Scatter(x=buys['Date'], y=buys['Prix'], mode='markers',
                                                             name='ACHAT', marker=dict(color='green', size=12, symbol='triangle-up')))
                        sells = df_trades[df_trades['Type'].isin(['SELL', 'STOP LOSS', 'TAKE PROFIT'])]
                        if len(sells) > 0:
                            fig_trades.add_trace(go.Scatter(x=sells['Date'], y=sells['Prix'], mode='markers',
                                                             name='VENTE', marker=dict(color='red', size=12, symbol='triangle-down')))
                        fig_trades.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
                                                  title=f"Stratégie: {strategy}", xaxis_title="Date", yaxis_title="Prix ($)",
                                                  height=600, hovermode='x unified')
                        st.plotly_chart(fig_trades, use_container_width=True)

                        st.markdown("---")
                        st.markdown("### 📋 HISTORIQUE DES TRADES")
                        df_display = df_trades.copy()
                        df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d')
                        df_display['Prix'] = df_display['Prix'].apply(lambda x: f"${x:.2f}")
                        df_display['Shares'] = df_display['Shares'].apply(lambda x: f"{x:.4f}")
                        df_display['P/L'] = df_display['P/L'].apply(lambda x: f"${x:+,.2f}" if x != 0 else "-")
                        df_display['P/L %'] = df_display['P/L %'].apply(lambda x: f"{x:+.2f}%" if x != 0 else "-")
                        st.dataframe(df_display[['Date', 'Type', 'Prix', 'Shares', 'P/L', 'P/L %']],
                                     use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ Aucun trade n'a été exécuté avec cette stratégie sur la période sélectionnée.")

        except Exception as e:
            st.error(f"Erreur lors du backtesting: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# OUTIL : VALORISATION FONDAMENTALE
# ==========================================
elif outil == "VALORISATION FONDAMENTALE":
    st.markdown("## 💰 VALORISATION FONDAMENTALE")
    st.markdown("**Calculez la valeur théorique d'un actif avec plusieurs méthodes d'évaluation**")

    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("TICKER DE L'ACTIF", value="AAPL",
                                help="Ex: AAPL, MSFT, GOOGL, BTC-USD, ETH-USD, MC.PA")
    with col2:
        st.write("")
        st.write("")
        if st.button("🔍 ANALYSER LA VALORISATION", use_container_width=True):
            st.session_state['valuation_symbol'] = symbol

    if 'valuation_symbol' in st.session_state:
        symbol = st.session_state['valuation_symbol']
        with st.spinner(f"Analyse fondamentale de {symbol} en cours..."):
            calculator = ValuationCalculator(symbol)
            results = calculator.get_comprehensive_valuation()

            if not results:
                st.error("❌ Impossible de valoriser cet actif (données insuffisantes)")
            else:
                if "consensus" in results:
                    st.markdown("---")
                    st.markdown("### 📊 CONSENSUS DE VALORISATION")
                    cons = results["consensus"]
                    col1, col2, col3, col4 = st.columns(4)
                    with col1: st.metric("PRIX ACTUEL", f"${cons['current_price']:.2f}")
                    with col2: st.metric("VALEUR JUSTE", f"${cons['fair_value']:.2f}")
                    with col3:
                        delta_color = "normal" if abs(cons['upside_pct']) < 10 else ("inverse" if cons['upside_pct'] > 0 else "off")
                        st.metric("POTENTIEL", f"{cons['upside_pct']:+.1f}%", delta_color=delta_color)
                    with col4:
                        rec = cons['recommendation']
                        if "ACHAT" in rec:   st.success(f"**{rec}** 🚀")
                        elif "VENTE" in rec: st.error(f"**{rec}** ⚠️")
                        else:                st.info(f"**{rec}** ⚖️")
                    st.caption(f"Basé sur {cons['methods_used']} méthode(s) de valorisation")

                    upside = cons['upside_pct']
                    if upside > 0:
                        gauge_color = "#00ff00" if upside > 20 else "#00ffad"
                        sentiment = f"SOUS-ÉVALUÉ de {upside:.1f}%"
                    else:
                        gauge_color = "#ff4b4b" if upside < -20 else "#ff9800"
                        sentiment = f"SURÉVALUÉ de {abs(upside):.1f}%"
                    gauge_score = max(0, min(100, 50 + (upside / 2)))

                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number", value=gauge_score,
                        number={'font': {'size': 30, 'color': "white"}},
                        title={'text': f"<b>INDICE DE VALORISATION</b><br><span style='color:{gauge_color}; font-size:14px;'>{sentiment}</span>",
                               'font': {'size': 16, 'color': "white"}},
                        gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                               'bar': {'color': gauge_color, 'thickness': 0.3},
                               'bgcolor': "rgba(0,0,0,0)",
                               'steps': [
                                   {'range': [0, 25],   'color': "rgba(255, 75, 75, 0.2)"},
                                   {'range': [25, 45],  'color': "rgba(255, 152, 0, 0.2)"},
                                   {'range': [45, 55],  'color': "rgba(241, 196, 15, 0.2)"},
                                   {'range': [55, 75],  'color': "rgba(0, 255, 173, 0.2)"},
                                   {'range': [75, 100], 'color': "rgba(0, 255, 0, 0.2)"}
                               ]}
                    ))
                    fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"},
                                            height=300, margin=dict(l=25, r=25, t=100, b=20))
                    st.plotly_chart(fig_gauge, use_container_width=True)

                st.markdown("---")
                st.markdown("### 📈 DÉTAILS PAR MÉTHODE DE VALORISATION")
                methods_available = [method for method in results.keys() if method not in ["consensus", "dcf"]]
                if methods_available:
                    tabs = st.tabs([method.upper() for method in methods_available])
                    for idx, method in enumerate(methods_available):
                        with tabs[idx]:
                            data = results[method]
                            if "error" in data:
                                st.warning(f"⚠️ {data['error']}")
                            else:
                                col1, col2, col3 = st.columns(3)
                                with col1: st.metric("VALEUR JUSTE", f"${data['fair_value']:.2f}")
                                with col2: st.metric("PRIX ACTUEL", f"${data['current_price']:.2f}")
                                with col3:
                                    upside_val = data['upside_pct']
                                    color = "normal" if abs(upside_val) < 10 else ("inverse" if upside_val > 0 else "off")
                                    st.metric("POTENTIEL", f"{upside_val:+.1f}%", delta_color=color)
                                st.markdown("---")
                                st.markdown("**PARAMÈTRES DE LA MÉTHODE:**")
                                if method == "dcf":
                                    col_param = st.columns(3)
                                    with col_param[0]: st.info(f"**Valeur d'Entreprise:** ${data['enterprise_value']:,.0f}")
                                    with col_param[1]: st.info(f"**Valeur des Actions:** ${data['equity_value']:,.0f}")
                                    with col_param[2]: st.info(f"**FCF Actuel:** ${data['fcf_current']:,.0f}")
                                    params = data['parameters']
                                    st.write(f"- Taux de croissance: **{params['growth_rate']*100:.1f}%**")
                                    st.write(f"- Taux d'actualisation: **{params['discount_rate']*100:.1f}%**")
                                    st.write(f"- Projection: **{params['years']} ans**")
                                elif method == "pe":
                                    col_param = st.columns(3)
                                    with col_param[0]: st.info(f"**P/E Actuel:** {data['current_pe']}")
                                    with col_param[1]: st.info(f"**P/E Cible:** {data['target_pe']}")
                                    with col_param[2]: st.info(f"**EPS:** ${data['eps']:.2f}")
                                    st.write(f"- Type EPS: **{data['eps_type']}**")
                                elif method == "pb":
                                    col_param = st.columns(3)
                                    with col_param[0]: st.info(f"**Valeur Comptable:** ${data['book_value']:.2f}")
                                    with col_param[1]: st.info(f"**P/B Actuel:** {data['current_pb']:.2f}")
                                    with col_param[2]: st.info(f"**P/B Cible:** {data['target_pb']:.2f}")
                                elif method == "graham":
                                    col_param = st.columns(3)
                                    with col_param[0]: st.info(f"**EPS:** ${data['eps']:.2f}")
                                    with col_param[1]: st.info(f"**Book Value:** ${data['book_value']:.2f}")
                                    with col_param[2]: st.info(f"**Formule:** √(22.5 × EPS × BV)")
                                    st.caption("📚 Formule de Benjamin Graham - Investissement Value")
                                elif method == "nvt":
                                    col_param = st.columns(3)
                                    with col_param[0]: st.info(f"**NVT Ratio:** {data['nvt_ratio']:.2f}")
                                    with col_param[1]: st.info(f"**Status:** {data['status']}")
                                    with col_param[2]: st.info(f"**Market Cap:** ${data['market_cap']:,.0f}")
                                    st.write(f"- Volume quotidien moyen: **${data['daily_tx_value']:,.0f}**")
                                    st.write(f"- NVT cible: **{data['target_nvt']}**")
                                    st.caption("NVT < 10 = Sous-évalué | NVT 10-20 = Juste valorisé | NVT > 20 = Surévalué")

                st.markdown("---")
                st.markdown("### ℹ️ INFORMATIONS COMPLÉMENTAIRES")
                info = calculator.info
                if info:
                    col_info = st.columns(4)
                    with col_info[0]: st.write(f"**Secteur:** {info.get('sector', 'N/A')}")
                    with col_info[1]: st.write(f"**Industrie:** {info.get('industry', 'N/A')}")
                    with col_info[2]:
                        market_cap = info.get('marketCap', 0)
                        st.write(f"**Cap. Boursière:** ${market_cap/1e9:.2f}B" if market_cap > 0 else "**Cap. Boursière:** N/A")
                    with col_info[3]:
                        employees = info.get('fullTimeEmployees', 'N/A')
                        st.write(f"**Employés:** {employees:,}" if isinstance(employees, int) else f"**Employés:** {employees}")

                with st.expander("📖 GUIDE D'INTERPRÉTATION"):
                    st.markdown("""
                    **COMMENT INTERPRÉTER LES RÉSULTATS:**

                    **Potentiel (Upside %):**
                    - **> +20%** : Fortement sous-évalué → ACHAT FORT 🚀
                    - **+10% à +20%** : Sous-évalué → ACHAT 📈
                    - **-10% à +10%** : Juste valorisé → CONSERVER ⚖️
                    - **-20% à -10%** : Surévalué → VENTE 📉
                    - **< -20%** : Fortement surévalué → VENTE FORTE ⚠️

                    ⚠️ À combiner avec l'analyse technique. Ne constitue pas un conseil en investissement.
                    """)

# ==========================================
# OUTIL : MULTI-CHARTS
# ==========================================
elif outil == "MULTI-CHARTS":
    st.title("🖥️ MULTI-WINDOW WORKSPACE")

    col_input, col_add, col_clear = st.columns([3, 1, 1])
    with col_input:
        new_ticker = st.text_input("SYMBOLE (ex: BTC-USD, AAPL)", key="add_chart_input").upper()
    with col_add:
        if st.button("OUVRIR FENÊTRE +"):
            if new_ticker and new_ticker not in st.session_state.multi_charts:
                st.session_state.multi_charts.append(new_ticker)
                st.rerun()
    with col_clear:
        if st.button("TOUT FERMER"):
            st.session_state.multi_charts = []
            st.rerun()

    if st.session_state.multi_charts:
        all_windows_html = ""
        for i, ticker_chart in enumerate(st.session_state.multi_charts):
            traduction_symbols = {"^FCHI": "CAC40", "^GSPC": "VANTAGE:SP500", "^IXIC": "NASDAQ", "BTC-USD": "BINANCE:BTCUSDT"}
            tv_symbol = traduction_symbols.get(ticker_chart, ticker_chart.replace(".PA", ""))
            if ".PA" in ticker_chart and ticker_chart not in traduction_symbols:
                tv_symbol = f"EURONEXT:{tv_symbol}"
            all_windows_html += f"""
            <div id="win_{i}" class="floating-window" style="
                width: 450px; height: 350px;
                position: absolute; top: {50 + (i*40)}px; left: {50 + (i*40)}px;
                background: #0d0d0d; border: 2px solid #ff9800; z-index: {100 + i};
                display: flex; flex-direction: column; box-shadow: 0 10px 30px rgba(0,0,0,0.8);
            ">
                <div class="window-header" style="
                    background: #1a1a1a; color: #ff9800; padding: 10px;
                    cursor: move; font-family: monospace; border-bottom: 1px solid #ff9800;
                    display: flex; justify-content: space-between; align-items: center;
                ">
                    <span>📟 {ticker_chart}</span>
                    <span style="font-size: 9px; color: #555;">[DRAG HEADER]</span>
                </div>
                <div id="tv_chart_{i}" style="flex-grow: 1; width: 100%;"></div>
            </div>
            <script>
            new TradingView.widget({{
              "autosize": true, "symbol": "{tv_symbol}", "interval": "D",
              "timezone": "Europe/Paris", "theme": "dark", "style": "1",
              "locale": "fr", "container_id": "tv_chart_{i}"
            }});
            </script>
            """
        full_component_code = f"""
        <script src="https://code.jquery.com/jquery-3.6.0.js"></script>
        <script src="https://code.jquery.com/ui/1.13.2/jquery-ui.js"></script>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <style>
            body {{ background-color: transparent; overflow: hidden; margin: 0; }}
            .floating-window {{ border-radius: 4px; overflow: hidden; }}
            .ui-resizable-se {{ background: #ff9800; width: 12px; height: 12px; bottom: 0; right: 0; }}
        </style>
        <div id="desktop" style="width: 100%; height: 100vh; position: relative;">
            {all_windows_html}
        </div>
        <script>
            $(function() {{
                $(".floating-window").draggable({{
                    handle: ".window-header",
                    containment: "#desktop",
                    stack: ".floating-window"
                }});
                $(".floating-window").resizable({{
                    minHeight: 250,
                    minWidth: 350,
                    handles: "se"
                }});
            }});
        </script>
        """
        components.html(full_component_code, height=900, scrolling=False)

# ==========================================
# OUTIL : EXPERT SYSTEM
# ==========================================
elif outil == "EXPERT SYSTEM":
    st.markdown("<h1 style='text-align: center; color: #ff9800;'>🏛️ THE WALL STREET COUNCIL</h1>", unsafe_allow_html=True)
    st.write("CONSULTATION DES GRANDS MAÎTRES DE L'INVESTISSEMENT SUR VOTRE ACTIF.")

    nom_entree = st.text_input("📝 NOM DE L'ACTION À EXPERTISER :", value="LVMH")

    if nom_entree:
        with st.spinner("Consultation des Maîtres en cours..."):
            ticker = trouver_ticker(nom_entree)
            action = yf.Ticker(ticker)
            info = action.info

            if info and ('currentPrice' in info or 'regularMarketPrice' in info):
                nom = info.get('longName', ticker)
                prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
                if prix == 0 or prix is None:
                    try:
                        hist = yf.Ticker(ticker).history(period="1d")
                        if not hist.empty: prix = float(hist['Close'].iloc[-1])
                    except: prix = 1

                bpa = info.get('trailingEps') or info.get('forwardEps') or 0
                per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 50)
                roe = (info.get('returnOnEquity', 0)) * 100
                marge_op = (info.get('operatingMargins', 0)) * 100
                croissance = (info.get('earningsGrowth', 0.08)) * 100
                devise = info.get('currency', '€')

                calc = ValuationCalculator(ticker)
                valuation = calc.get_comprehensive_valuation()
                if "consensus" in valuation:
                    val_graham = valuation["consensus"]["fair_value"]
                else:
                    book_value = info.get('bookValue', 0)
                    val_graham = (22.5 * bpa * book_value) ** 0.5 if bpa > 0 and book_value > 0 else 0

                score_graham = int(min(5, max(0, (val_graham / prix) * 2.5))) if prix > 0 and val_graham > 0 else 0
                score_buffett = int(min(5, (roe / 4)))
                if marge_op > 20: score_buffett = min(5, score_buffett + 1)
                peg = per / croissance if croissance > 0 else 5
                score_lynch = int(max(0, 5 - (peg * 1.2)))
                score_joel = int(min(5, (roe / 5) + (25 / per)))
                total = min(20, score_graham + score_buffett + score_lynch + score_joel)

                st.markdown(f"### 📊 ANALYSE STRATÉGIQUE : {nom}")
                c1, c2, c3 = st.columns(3)
                c1.metric("COURS", f"{prix:.2f} {devise}")
                c2.metric("ROE", f"{roe:.1f} %")
                c3.metric("P/E RATIO", f"{per:.1f}")
                st.markdown("---")

                def afficher_expert(nom_m, score, avis, detail):
                    col_m1, col_m2 = st.columns([1, 3])
                    with col_m1:
                        st.markdown(f"**{nom_m}**")
                        stars = "★" * score + "☆" * (5 - score)
                        color = "#00ff00" if score >= 4 else "#ff9800" if score >= 2 else "#ff0000"
                        st.markdown(f"<span style='color:{color}; font-size:20px;'>{stars}</span>", unsafe_allow_html=True)
                    with col_m2:
                        st.markdown(f"*'{avis}'*")
                        st.caption(detail)

                afficher_expert("BENJAMIN GRAHAM", score_graham, "Décote / Valeur Intrinsèque", f"Valeur théorique Graham : {val_graham:.2f} {devise}")
                afficher_expert("WARREN BUFFETT", score_buffett, "Moat / Rentabilité des Capitaux", f"La marge opérationnelle de {marge_op:.1f}% indique un avantage compétitif.")
                afficher_expert("PETER LYNCH", score_lynch, "Prix payé pour la Croissance", "Analyse basée sur le PEG (P/E divisé par la croissance).")
                afficher_expert("JOEL GREENBLATT", score_joel, "Efficience Magique (ROE/PER)", "Recherche des meilleures entreprises au prix le moins cher.")

                st.markdown("---")
                c_score1, c_score2 = st.columns([1, 2])
                with c_score1:
                    st.subheader("🏆 SCORE FINAL")
                    c_final = "#00ff00" if total >= 15 else "#ff9800" if total >= 10 else "#ff0000"
                    st.markdown(f"<h1 style='color:{c_final}; font-size:60px;'>{total}/20</h1>", unsafe_allow_html=True)
                with c_score2:
                    st.subheader("💡 VERDICT DU CONSEIL")
                    if total >= 16:   st.success("💎 PÉPITE : Les Maîtres sont unanimes. L'actif présente une qualité exceptionnelle et un prix attractif.")
                    elif total >= 12: st.info("✅ SOLIDE : Un investissement de qualité qui respecte la majorité des critères fondamentaux.")
                    elif total >= 8:  st.warning("⚖️ MOYEN : Des points de friction subsistent. Attendre un meilleur point d'entrée.")
                    else:             st.error("🛑 RISQUÉ : Trop de points faibles. L'actif est soit surévalué, soit ses fondamentaux sont en déclin.")
            else:
                st.error("❌ TICKER NON TROUVÉ OU DONNÉES INCOMPLÈTES.")

# ==========================================
# OUTIL : THE GRAND COUNCIL (15 EXPERTS)
# ==========================================
elif outil == "THE GRAND COUNCIL️":
    st.markdown("""
        <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); border: 3px solid #ff9800; border-radius: 15px; margin-bottom: 20px;'>
            <h1 style='color: #ff9800; margin: 0; font-size: 42px; text-shadow: 0 0 20px #ff9800;'>🏛️ THE GRAND COUNCIL OF WALL STREET</h1>
            <p style='color: #ffb84d; margin: 10px 0 0 0; font-size: 16px;'>15 Légendes de l'Investissement Analysent Votre Actif</p>
        </div>
    """, unsafe_allow_html=True)

    col_input1, col_input2 = st.columns([3, 1])
    with col_input1:
        nom_entree = st.text_input("📝 TICKER OU NOM DE L'ACTIF", value="AAPL", key="council_ticker")
    with col_input2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🚀 CONVOQUER LE CONSEIL", key="council_btn", use_container_width=True)

    if analyze_btn and nom_entree:
        with st.spinner("⏳ Le Conseil délibère... Veuillez patienter."):
            try:
                ticker = trouver_ticker(nom_entree)
                action = yf.Ticker(ticker)
                info = action.info

                if info and ('currentPrice' in info or 'regularMarketPrice' in info):
                    p = info.get('currentPrice') or info.get('regularMarketPrice') or 1
                    if p == 0 or p is None or p < 0.01:
                        try:
                            hist = yf.Ticker(ticker).history(period="5d")
                            if not hist.empty: p = float(hist['Close'].iloc[-1])
                        except: p = 1

                    nom_complet = info.get('longName', info.get('shortName', ticker))
                    secteur = info.get('sector', 'N/A')

                    calc = ValuationCalculator(ticker)
                    valuation = calc.get_comprehensive_valuation()
                    if "consensus" in valuation:
                        graham_fair_value = valuation["consensus"]["fair_value"]
                    else:
                        eps_temp = info.get('trailingEps') or info.get('forwardEps', 0)
                        bv_temp = info.get('bookValue', 0)
                        graham_fair_value = (22.5 * eps_temp * bv_temp) ** 0.5 if eps_temp > 0 and bv_temp > 0 else p * 1.2

                    eps = info.get('trailingEps', info.get('forwardEps', 1))
                    per = info.get('trailingPE', info.get('forwardPE', 20))
                    roe = (info.get('returnOnEquity', 0) or 0) * 100
                    marge = (info.get('operatingMargins', 0) or 0) * 100
                    yield_div = (info.get('dividendYield', 0) or 0) * 100
                    croissance = (info.get('earningsGrowth', 0.05) or 0.05) * 100
                    dette_equity = info.get('debtToEquity', 100) or 100
                    pb_ratio = info.get('priceToBook', 2) or 2
                    fcf = info.get('freeCashflow', 0) or 0
                    revenue_growth = (info.get('revenueGrowth', 0) or 0) * 100
                    current_ratio = info.get('currentRatio', 1) or 1
                    quick_ratio = info.get('quickRatio', 1) or 1
                    ps_ratio = info.get('priceToSalesTrailing12Months', 5) or 5
                    total_cash = info.get('totalCash', 0) or 0
                    total_debt = info.get('totalDebt', 0) or 0
                    ma50 = info.get('fiftyDayAverage', p)
                    ma200 = info.get('twoHundredDayAverage', p)

                    st.markdown("### 📊 INFORMATIONS DE L'ACTIF")
                    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                    with col_info1:
                        st.metric("Société", nom_complet[:20] + "..." if len(nom_complet) > 20 else nom_complet)
                        st.metric("Secteur", secteur)
                    with col_info2:
                        st.metric("Prix Actuel", f"${p:.2f}")
                        marge_securite = ((graham_fair_value - p) / p) * 100
                        st.metric("Marge Sécurité", f"{marge_securite:+.1f}%")
                    with col_info3:
                        st.metric("P/E Ratio", f"{per:.1f}" if per else "N/A")
                        st.metric("ROE", f"{roe:.1f}%" if roe else "N/A")
                    with col_info4:
                        st.metric("Dette/Equity", f"{dette_equity:.0f}" if dette_equity else "N/A")
                        st.metric("FCF", f"${fcf/1e9:.2f}B" if fcf > 0 else "N/A")
                    st.markdown("---")

                    def get_expert_details(pts_list):
                        score_base = sum([1 for pt in pts_list if pt])
                        score = min(5, max(1, score_base + 1))
                        avis_dict = {
                            5: "Exceptionnel. L'actif coche toutes mes cases stratégiques. Je recommande fortement.",
                            4: "Très solide. Quelques détails manquent pour la perfection, mais c'est prometteur.",
                            3: "Acceptable. Je reste prudent sur certains ratios, analyse approfondie nécessaire.",
                            2: "Médiocre. Le profil risque/rendement ne m'enchante pas du tout.",
                            1: "À éviter absolument. Cela va à l'encontre de ma philosophie d'investissement."
                        }
                        return score, avis_dict[score]

                    experts_config = [
                        {"nom": "Benjamin Graham",    "style": "Value Investing",   "emoji": "📚",
                         "pts": [p < graham_fair_value, p < (graham_fair_value * 0.67), pb_ratio < 1.5, dette_equity < 50]},
                        {"nom": "Warren Buffett",     "style": "Moat/Qualité",      "emoji": "🎩",
                         "pts": [roe > 15, roe > 25, marge > 10, marge > 20]},
                        {"nom": "Peter Lynch",        "style": "PEG Growth",        "emoji": "📈",
                         "pts": [per < 30, (per / croissance < 1.5 if croissance > 0 else False), croissance > 10, croissance > 20]},
                        {"nom": "Joel Greenblatt",    "style": "Magic Formula",     "emoji": "✨",
                         "pts": [roe > 20, per < 20, roe > 30, per < 12]},
                        {"nom": "John Templeton",     "style": "Contrarian",        "emoji": "🌍",
                         "pts": [per < 15, per < 10, p < ma50, p < ma200]},
                        {"nom": "Philip Fisher",      "style": "Growth Maximum",    "emoji": "🚀",
                         "pts": [croissance > 15, croissance > 30, marge > 15, revenue_growth > 10]},
                        {"nom": "Charles Munger",     "style": "Lollapalooza",      "emoji": "🧠",
                         "pts": [roe > 18, dette_equity < 40, marge > 15, fcf > 0]},
                        {"nom": "David Dreman",       "style": "Contrarian Value",  "emoji": "⚖️",
                         "pts": [per < 15, yield_div > 2, yield_div > 4, p < ma200]},
                        {"nom": "William O'Neil",     "style": "CANSLIM",           "emoji": "📊",
                         "pts": [croissance > 20, p > ma50, p > ma200, croissance > 40]},
                        {"nom": "Bill Ackman",        "style": "Activist",          "emoji": "💼",
                         "pts": [fcf > 0, marge > 20, yield_div > 0, roe > 15]},
                        {"nom": "Ray Dalio",          "style": "Macro/Balance",     "emoji": "🌐",
                         "pts": [dette_equity < 70, dette_equity < 30, yield_div > 1, current_ratio > 1.5]},
                        {"nom": "Cathie Wood",        "style": "Innovation",        "emoji": "🔮",
                         "pts": [croissance > 20, croissance > 50, revenue_growth > 30, marge < 0]},
                        {"nom": "James O'Shaughnessy","style": "Quantitative",      "emoji": "🔢",
                         "pts": [pb_ratio < 2, ps_ratio < 1.5, yield_div > 1, per < 25]},
                        {"nom": "Nassim Taleb",       "style": "Anti-Fragile",      "emoji": "🛡️",
                         "pts": [total_cash > total_debt, current_ratio > 2, quick_ratio > 1.5, dette_equity < 50]},
                        {"nom": "Gerald Loeb",        "style": "Momentum",          "emoji": "⚡",
                         "pts": [p > ma50, p > ma200, croissance > 15, revenue_growth > 10]},
                    ]

                    final_results = []
                    total_pts = 0
                    consensus_bullish = 0
                    consensus_bearish = 0

                    for exp in experts_config:
                        sc, av = get_expert_details(exp["pts"])
                        final_results.append({"Expert": exp["nom"], "Style": exp["style"],
                                               "Emoji": exp["emoji"], "Note": sc, "Avis": av})
                        total_pts += sc
                        if sc >= 4: consensus_bullish += 1
                        elif sc <= 2: consensus_bearish += 1

                    final_score_20 = round((total_pts / 75) * 20, 1)
                    df_scores = pd.DataFrame(final_results)

                    st.markdown("### 📊 NOTATION DES 15 EXPERTS")
                    fig = go.Figure(data=[go.Bar(
                        x=df_scores['Expert'], y=df_scores['Note'],
                        text=df_scores['Note'], textposition='auto',
                        marker=dict(color=df_scores['Note'],
                                    colorscale=[[0,'#ff0000'],[0.3,'#ff6b6b'],[0.5,'#ff9800'],[0.7,'#7fff00'],[1,'#00ff00']],
                                    line=dict(color='black', width=2)),
                        hovertemplate='<b>%{x}</b><br>Note: %{y}/5<br><extra></extra>'
                    )])
                    fig.update_layout(paper_bgcolor='black', plot_bgcolor='black',
                                      font=dict(color="white", size=11), height=400,
                                      margin=dict(t=30, b=120, l=40, r=40),
                                      yaxis=dict(range=[0, 5], dtick=1, gridcolor='#333', title="Note /5"),
                                      xaxis=dict(tickangle=-45), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("---")
                    color_f = "#00ff00" if final_score_20 >= 14 else "#ff9800" if final_score_20 >= 10 else "#ff0000"
                    if final_score_20 >= 16:   verdict = "ACHAT FORT 🚀"; verdict_desc = "Consensus exceptionnel du conseil"
                    elif final_score_20 >= 14: verdict = "ACHAT 📈"; verdict_desc = "Opportunité solide validée"
                    elif final_score_20 >= 12: verdict = "CONSERVER 📊"; verdict_desc = "Position neutre à surveiller"
                    elif final_score_20 >= 10: verdict = "PRUDENCE ⚠️"; verdict_desc = "Risques identifiés"
                    else:                      verdict = "ÉVITER ❌"; verdict_desc = "Consensus négatif"

                    col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
                    with col_res1:
                        st.markdown(f"<div style='text-align:center; padding:25px; border:3px solid {color_f}; border-radius:15px; background: linear-gradient(135deg, #0a0a0a 0%, #000000 100%);'><h1 style='color:{color_f}; margin:0; font-size: 48px;'>{final_score_20} / 20</h1><h3 style='color:white; margin: 10px 0;'>{verdict}</h3><small style='color:#999;'>{verdict_desc}</small></div>", unsafe_allow_html=True)
                    with col_res2:
                        st.markdown(f"<div style='text-align:center; padding:20px; border:2px solid #00ff00; border-radius:10px; background:#0a0a0a;'><h2 style='color:#00ff00; margin:0; font-size: 32px;'>{consensus_bullish}</h2><small style='color:#ccc;'>EXPERTS POSITIFS</small></div>", unsafe_allow_html=True)
                    with col_res3:
                        st.markdown(f"<div style='text-align:center; padding:20px; border:2px solid #ff0000; border-radius:10px; background:#0a0a0a;'><h2 style='color:#ff0000; margin:0; font-size: 32px;'>{consensus_bearish}</h2><small style='color:#ccc;'>EXPERTS NÉGATIFS</small></div>", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    def generate_pdf(ticker_name, score, verdict_text, df):
                        verdict_clean = verdict_text.replace("🚀","").replace("📈","").replace("📊","").replace("⚠️","").replace("❌","").strip()
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_text_color(255, 152, 0)
                        pdf.set_font("Arial", 'B', 20)
                        pdf.cell(190, 15, "THE GRAND COUNCIL OF WALL STREET", ln=True, align='C')
                        pdf.set_font("Arial", 'B', 16)
                        pdf.cell(190, 10, f"ANALYSE : {ticker_name}", ln=True, align='C')
                        pdf.ln(5)
                        pdf.set_font("Arial", 'B', 28)
                        pdf.cell(190, 15, f"SCORE : {score}/20", ln=True, align='C')
                        pdf.set_font("Arial", 'B', 14)
                        pdf.cell(190, 10, f"VERDICT : {verdict_clean}", ln=True, align='C')
                        pdf.ln(10)
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", '', 10)
                        pdf.cell(190, 7, f"Date du rapport : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
                        pdf.ln(5)
                        for _, row in df.iterrows():
                            pdf.set_font("Arial", 'B', 11)
                            pdf.cell(190, 7, f"{row['Expert']} ({row['Style']}) - {row['Note']}/5", ln=True)
                            pdf.set_font("Arial", '', 9)
                            avis_clean = row['Avis'].encode('latin-1', 'replace').decode('latin-1')
                            pdf.multi_cell(190, 5, f"Avis : {avis_clean}")
                            pdf.ln(3)
                        pdf.ln(5)
                        pdf.set_font("Arial", 'I', 8)
                        pdf.multi_cell(190, 4, "AVERTISSEMENT : Ce rapport est genere automatiquement a des fins educatives. Il ne constitue pas un conseil financier.")
                        return bytes(pdf.output(dest='S'))

                    pdf_bytes = generate_pdf(nom_complet, final_score_20, verdict, df_scores)
                    st.download_button(label="📥 TÉLÉCHARGER LE RAPPORT COMPLET (PDF)", data=pdf_bytes,
                                       file_name=f"Grand_Council_Report_{ticker}_{datetime.now().strftime('%Y%m%d')}.pdf",
                                       mime="application/pdf", use_container_width=True)

                    st.markdown("---")
                    st.markdown("### 🏛️ AVIS DÉTAILLÉS DES EXPERTS")
                    cols = st.columns(3)
                    for i, row in df_scores.iterrows():
                        with cols[i % 3]:
                            stars = "★" * row['Note'] + "☆" * (5 - row['Note'])
                            color = "#00ff00" if row['Note'] >= 4 else "#ff9800" if row['Note'] >= 2 else "#ff0000"
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #0a0a0a 0%, #000000 100%); padding:18px; border-radius:12px; margin-bottom:15px; border:2px solid {color}; min-height:190px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <span style="font-size: 28px;">{row['Emoji']}</span>
                                    <span style="color:{color}; font-size:20px;">{stars}</span>
                                </div>
                                <b style="color:{color}; font-size: 16px;">{row['Expert']}</b><br>
                                <small style="color:#888; font-size: 11px;">{row['Style']}</small><br>
                                <div style="margin-top: 12px; padding: 10px; background: #050505; border-radius: 6px; border-left: 3px solid {color};">
                                    <p style="color:#bbb; font-size:12px; margin:0;"><i>"{row['Avis']}"</i></p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("### 📊 ANALYSE STATISTIQUE")
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1: st.metric("Note Moyenne", f"{df_scores['Note'].mean():.2f}/5")
                    with col_stat2:
                        max_score = df_scores['Note'].max()
                        st.metric("Plus Optimiste", df_scores[df_scores['Note'] == max_score]['Expert'].iloc[0], f"{max_score}/5")
                    with col_stat3:
                        min_score = df_scores['Note'].min()
                        st.metric("Plus Pessimiste", df_scores[df_scores['Note'] == min_score]['Expert'].iloc[0], f"{min_score}/5")
                    with col_stat4:
                        std_dev = df_scores['Note'].std()
                        st.metric("Écart-type", f"{std_dev:.2f}", "Consensus" if std_dev < 1 else "Divergent")

                else:
                    st.error("❌ Données boursières introuvables pour ce ticker.")
            except Exception as e:
                st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# ==========================================
# OUTIL : MODE DUEL
# ==========================================
elif outil == "MODE DUEL":
    st.markdown("""
        <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); border: 3px solid #ff9800; border-radius: 15px; margin-bottom: 20px;'>
            <h1 style='color: #ff9800; margin: 0; font-size: 48px; text-shadow: 0 0 20px #ff9800;'>⚔️ EQUITY DUEL</h1>
            <p style='color: #ffb84d; margin: 10px 0 0 0; font-size: 18px;'>Comparaison Professionnelle d'Actions</p>
        </div>
    """, unsafe_allow_html=True)

    if 'duel_result' not in st.session_state: st.session_state.duel_result = None
    if 'duel_history' not in st.session_state: st.session_state.duel_history = []

    col_input1, col_input2, col_input3 = st.columns([2, 2, 1])
    with col_input1: t1 = st.text_input("🔵 TICKER 1", value="MC.PA", key="duel_t1").upper()
    with col_input2: t2 = st.text_input("🔴 TICKER 2", value="RMS.PA", key="duel_t2").upper()
    with col_input3:
        st.markdown("<br>", unsafe_allow_html=True)
        run_duel = st.button("⚔️ DUEL !", key="run_duel", use_container_width=True)

    def get_full_data(t):
        ticker_id = trouver_ticker(t)
        ticker_obj = yf.Ticker(ticker_id)
        i = ticker_obj.info
        hist = ticker_obj.history(period="1y")

        p = i.get('currentPrice') or i.get('regularMarketPrice') or 1
        if p == 0 or p is None or p < 0.01:
            try:
                h = ticker_obj.history(period="5d")
                p = float(h['Close'].iloc[-1]) if not h.empty else 1
            except: p = 1

        try:
            calc = ValuationCalculator(ticker_id)
            valuation_results = calc.get_comprehensive_valuation()
            v = valuation_results["consensus"]["fair_value"] if "consensus" in valuation_results else p * 1.2
        except:
            v = p * 1.2

        div_yield_raw = i.get('dividendYield', 0) or 0
        if div_yield_raw > 10:   div_yield = div_yield_raw
        elif div_yield_raw > 1:  div_yield = div_yield_raw
        else:                    div_yield = div_yield_raw * 100
        if div_yield > 20:       div_yield = div_yield / 100

        per = i.get('trailingPE') or i.get('forwardPE', 0)
        marge = (i.get('profitMargins', 0) or 0) * 100
        roe = (i.get('returnOnEquity', 0) or 0) * 100
        debt_equity = i.get('debtToEquity', 0) or 0
        pb_ratio = i.get('priceToBook', 0) or 0
        market_cap = i.get('marketCap', 0) or 0
        beta = i.get('beta', 0) or 0
        revenue_growth = (i.get('revenueGrowth', 0) or 0) * 100
        potential = ((v - p) / p) * 100 if p > 0 and v > 0 else 0

        if not hist.empty:
            perf_1m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0
            perf_3m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-63]) - 1) * 100 if len(hist) >= 63 else 0
            perf_1y = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
            volatility = hist['Close'].pct_change().std() * 100 * (252 ** 0.5)
        else:
            perf_1m = perf_3m = perf_1y = volatility = 0

        return {"ticker": ticker_id, "nom": i.get('shortName', t), "nom_complet": i.get('longName', i.get('shortName', t)),
                "secteur": i.get('sector', 'N/A'), "industrie": i.get('industry', 'N/A'),
                "prix": p, "valeur": v, "potential": potential, "yield": div_yield,
                "per": per, "marge": marge, "roe": roe, "debt_equity": debt_equity,
                "pb_ratio": pb_ratio, "market_cap": market_cap, "beta": beta,
                "revenue_growth": revenue_growth, "perf_1m": perf_1m, "perf_3m": perf_3m,
                "perf_1y": perf_1y, "volatility": volatility, "hist": hist}

    if run_duel:
        try:
            with st.spinner('⏳ Analyse des deux actifs en cours...'):
                res_d1 = get_full_data(t1)
                res_d2 = get_full_data(t2)
                st.session_state.duel_result = (res_d1, res_d2)
                st.session_state.duel_history.append({'date': datetime.now(), 'ticker1': t1, 'ticker2': t2})
                st.success("✅ Analyse terminée !")
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    if st.session_state.duel_result:
        d1, d2 = st.session_state.duel_result
        st.markdown("---")

        col_a, col_vs, col_b = st.columns([2, 1, 2])
        with col_a:
            st.markdown(f"<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%); border-radius: 10px; border: 3px solid #2196f3;'><h2 style='color: #fff; margin: 0;'>🔵 {d1['nom']}</h2><p style='color: #ccc; font-size: 12px; margin: 5px 0;'>{d1['secteur']}</p><h1 style='color: #00ff00; margin: 10px 0; font-size: 42px;'>${d1['prix']:.2f}</h1></div>", unsafe_allow_html=True)
        with col_vs:
            st.markdown("<div style='text-align: center; padding-top: 30px;'><h1 style='color: #ff9800; font-size: 48px; margin: 0;'>⚔️</h1><p style='color: #ff9800; font-size: 16px;'>VS</p></div>", unsafe_allow_html=True)
        with col_b:
            st.markdown(f"<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #c62828 0%, #f44336 100%); border-radius: 10px; border: 3px solid #ef5350;'><h2 style='color: #fff; margin: 0;'>🔴 {d2['nom']}</h2><p style='color: #ccc; font-size: 12px; margin: 5px 0;'>{d2['secteur']}</p><h1 style='color: #00ff00; margin: 10px 0; font-size: 42px;'>${d2['prix']:.2f}</h1></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📊 COMPARAISON DÉTAILLÉE")
        comparison_data = {
            "INDICATEUR": ["💰 Market Cap","📈 Valeur Intrinsèque","🎯 Potentiel (%)","📊 P/E Ratio","💎 P/B Ratio",
                           "💵 Dividende (%)","📈 Marge Profit (%)","💪 ROE (%)","🏦 Dette/Equity","⚡ Beta",
                           "📈 Croissance CA (%)","📊 Perf 1M (%)","📊 Perf 3M (%)","📊 Perf 1Y (%)","📉 Volatilité (%)"],
            f"🔵 {d1['nom']}": [
                f"${d1['market_cap']/1e9:.2f}B" if d1['market_cap'] > 0 else "N/A", f"${d1['valeur']:.2f}",
                f"{d1['potential']:+.2f}%", f"{d1['per']:.2f}" if d1['per'] else "N/A",
                f"{d1['pb_ratio']:.2f}" if d1['pb_ratio'] else "N/A", f"{d1['yield']:.2f}%",
                f"{d1['marge']:.2f}%", f"{d1['roe']:.2f}%", f"{d1['debt_equity']:.0f}" if d1['debt_equity'] else "N/A",
                f"{d1['beta']:.2f}" if d1['beta'] else "N/A", f"{d1['revenue_growth']:.2f}%",
                f"{d1['perf_1m']:+.2f}%", f"{d1['perf_3m']:+.2f}%", f"{d1['perf_1y']:+.2f}%", f"{d1['volatility']:.2f}%"
            ],
            f"🔴 {d2['nom']}": [
                f"${d2['market_cap']/1e9:.2f}B" if d2['market_cap'] > 0 else "N/A", f"${d2['valeur']:.2f}",
                f"{d2['potential']:+.2f}%", f"{d2['per']:.2f}" if d2['per'] else "N/A",
                f"{d2['pb_ratio']:.2f}" if d2['pb_ratio'] else "N/A", f"{d2['yield']:.2f}%",
                f"{d2['marge']:.2f}%", f"{d2['roe']:.2f}%", f"{d2['debt_equity']:.0f}" if d2['debt_equity'] else "N/A",
                f"{d2['beta']:.2f}" if d2['beta'] else "N/A", f"{d2['revenue_growth']:.2f}%",
                f"{d2['perf_1m']:+.2f}%", f"{d2['perf_3m']:+.2f}%", f"{d2['perf_1y']:+.2f}%", f"{d2['volatility']:.2f}%"
            ]
        }
        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 📈 PERFORMANCE RELATIVE (1 AN)")
        if not d1['hist'].empty and not d2['hist'].empty:
            fig = go.Figure()
            norm_d1 = (d1['hist']['Close'] / d1['hist']['Close'].iloc[0]) * 100
            norm_d2 = (d2['hist']['Close'] / d2['hist']['Close'].iloc[0]) * 100
            fig.add_trace(go.Scatter(x=d1['hist'].index, y=norm_d1, name=f"🔵 {d1['nom']}",
                                      line=dict(color='#2196f3', width=3), fill='tozeroy', fillcolor='rgba(33, 150, 243, 0.1)'))
            fig.add_trace(go.Scatter(x=d2['hist'].index, y=norm_d2, name=f"🔴 {d2['nom']}",
                                      line=dict(color='#f44336', width=3), fill='tozeroy', fillcolor='rgba(244, 67, 54, 0.1)'))
            fig.add_hline(y=100, line_dash="dash", line_color="#ff9800",
                          annotation_text="Base 100", annotation_position="right")
            fig.update_layout(paper_bgcolor='#0d0d0d', plot_bgcolor='#0d0d0d', font=dict(color='#ff9800'),
                               height=500, hovermode='x unified',
                               xaxis=dict(title="Date", gridcolor='#333', showgrid=True),
                               yaxis=dict(title="Performance (%)", gridcolor='#333', showgrid=True),
                               legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor='rgba(0,0,0,0.5)'))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🏆 VERDICT")

        def calculate_score(d):
            score = 0
            if d['potential'] > 30: score += 3
            elif d['potential'] > 15: score += 2
            elif d['potential'] > 0: score += 1
            if d['per'] and d['per'] < 15: score += 2
            elif d['per'] and d['per'] < 25: score += 1
            if d['yield'] > 3: score += 2
            elif d['yield'] > 1: score += 1
            if d['roe'] > 20: score += 2
            elif d['roe'] > 15: score += 1
            if d['debt_equity'] < 50: score += 2
            elif d['debt_equity'] < 100: score += 1
            if d['perf_1y'] > 20: score += 2
            elif d['perf_1y'] > 0: score += 1
            return score

        score1 = calculate_score(d1)
        score2 = calculate_score(d2)

        col_verdict1, col_verdict2 = st.columns(2)
        with col_verdict1:
            color1 = "#00ff00" if score1 > score2 else "#ff9800" if score1 == score2 else "#ff4444"
            st.markdown(f"<div style='text-align: center; padding: 20px; background: {color1}22; border: 3px solid {color1}; border-radius: 10px;'><h3 style='color: {color1};'>🔵 {d1['nom']}</h3><h1 style='color: {color1}; font-size: 48px; margin: 10px 0;'>{score1}/14</h1><p style='color: white;'>{'🏆 GAGNANT' if score1 > score2 else '🤝 ÉGALITÉ' if score1 == score2 else '👎 PERDANT'}</p></div>", unsafe_allow_html=True)
        with col_verdict2:
            color2 = "#00ff00" if score2 > score1 else "#ff9800" if score2 == score1 else "#ff4444"
            st.markdown(f"<div style='text-align: center; padding: 20px; background: {color2}22; border: 3px solid {color2}; border-radius: 10px;'><h3 style='color: {color2};'>🔴 {d2['nom']}</h3><h1 style='color: {color2}; font-size: 48px; margin: 10px 0;'>{score2}/14</h1><p style='color: white;'>{'🏆 GAGNANT' if score2 > score1 else '🤝 ÉGALITÉ' if score2 == score1 else '👎 PERDANT'}</p></div>", unsafe_allow_html=True)

        st.markdown("---")
        if score1 > score2:   st.success(f"✅ **RECOMMANDATION:** {d1['nom']} présente de meilleurs fondamentaux")
        elif score2 > score1: st.success(f"✅ **RECOMMANDATION:** {d2['nom']} présente de meilleurs fondamentaux")
        else:                 st.info("⚖️ **RECOMMANDATION:** Les deux actions sont équivalentes selon nos critères")
        st.caption("⚠️ Cette analyse est automatique et ne constitue pas un conseil d'investissement. DYOR.")

# ==========================================
# OUTIL : MARKET MONITOR
# ==========================================
elif outil == "MARKET MONITOR":
    st.title("» GLOBAL MARKET MONITOR")
    afficher_horloge_temps_reel()

    st.markdown("### » EXCHANGE STATUS")
    h = (datetime.utcnow() + timedelta(hours=4)).hour
    data_horaires = {
        "SESSION": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "OPEN (REU)": ["05:30", "12:00", "18:30"],
        "CLOSE (REU)": ["12:00", "20:30", "01:00"],
        "STATUS": [
            "● OPEN" if 5 <= h < 12 else "○ CLOSED",
            "● OPEN" if 12 <= h < 20 else "○ CLOSED",
            "● OPEN" if (h >= 18 or h < 1) else "○ CLOSED"
        ]
    }
    st.table(pd.DataFrame(data_horaires))

    st.markdown("---")
    st.subheader("» MARKET DRIVERS")
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
                if cols[i].button(f"LOAD {nom}", key=f"btn_{tk}"):
                    st.session_state.index_selectionne = tk
        except: pass

    st.markdown("---")
    nom_sel = indices.get(st.session_state.index_selectionne, "Indice")
    st.subheader(f"» ADVANCED CHART : {nom_sel}")
    afficher_graphique_pro(st.session_state.index_selectionne, height=700)

# ==========================================
# OUTIL : SCREENER CAC 40
# ==========================================
elif outil == "SCREENER CAC 40":
    st.markdown("<h1 style='text-align: center; color: #ff9800;'>🇫🇷 SCREENER CAC 40 STRATÉGIQUE</h1>", unsafe_allow_html=True)
    st.info("Ce screener scanne l'intégralité du CAC 40 en appliquant ta méthode 'Analyseur Pro' ( Graham + Score de Qualité ).")

    if st.button("🚀 LANCER LE SCAN COMPLET"):
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
            status_text.text(f"Analyse de {t} ({i+1}/40)...")
            progress_bar.progress((i + 1) / len(cac40_tickers))
            try:
                action = yf.Ticker(t)
                info = action.info
                if not info or 'currentPrice' not in info: continue
                nom = info.get('shortName') or t
                prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
                if prix == 0 or prix is None:
                    try:
                        hist = yf.Ticker(t).history(period="1d")
                        if not hist.empty: prix = float(hist['Close'].iloc[-1])
                    except: prix = 1
                bpa = info.get('trailingEps') or info.get('forwardEps') or 0
                per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 0)
                dette_equity = info.get('debtToEquity')
                payout = (info.get('payoutRatio') or 0) * 100
                try:
                    calc = ValuationCalculator(t)
                    valuation_results = calc.get_comprehensive_valuation()
                    if "consensus" in valuation_results:
                        val_theorique = valuation_results["consensus"]["fair_value"]
                        marge_pourcent = valuation_results["consensus"]["upside_pct"]
                        methods_count = valuation_results["consensus"]["methods_used"]
                    else:
                        book_value = info.get('bookValue', 0)
                        val_theorique = (22.5 * bpa * book_value) ** 0.5 if bpa > 0 and book_value > 0 else 0
                        marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 and val_theorique > 0 else 0
                        methods_count = 1
                except:
                    book_value = info.get('bookValue', 0)
                    val_theorique = (22.5 * bpa * book_value) ** 0.5 if bpa > 0 and book_value > 0 else 0
                    marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 and val_theorique > 0 else 0
                    methods_count = 1

                score = 0
                if bpa > 0:
                    if per < 12: score += 5
                    elif per < 20: score += 4
                    else: score += 1
                else: score -= 5
                if dette_equity is not None:
                    if dette_equity < 50: score += 4
                    elif dette_equity < 100: score += 3
                    elif dette_equity > 200: score -= 4
                if 10 < payout <= 80: score += 4
                elif payout > 95: score -= 4
                if marge_pourcent > 30: score += 5
                score_f = min(20, max(0, score))
                resultats.append({"Ticker": t, "Nom": nom, "Score": score_f,
                                   "Potentiel %": round(marge_pourcent, 1), "Méthodes": methods_count,
                                   "P/E": round(per, 1), "Dette/Eq %": round(dette_equity, 1) if dette_equity else "N/A",
                                   "Prix": f"{prix:.2f} €"})
            except Exception: continue

        status_text.success("✅ Analyse du CAC 40 terminée.")
        df_res = pd.DataFrame(resultats).sort_values(by="Score", ascending=False)

        st.markdown("---")
        st.subheader("🏆 TOP OPPORTUNITÉS DÉTECTÉES")
        c1, c2, c3 = st.columns(3)
        top_3 = df_res.head(3).to_dict('records')
        if len(top_3) >= 1: c1.metric(top_3[0]['Nom'], f"{top_3[0]['Score']}/20", f"{top_3[0]['Potentiel %']}% Pot.")
        if len(top_3) >= 2: c2.metric(top_3[1]['Nom'], f"{top_3[1]['Score']}/20", f"{top_3[1]['Potentiel %']}% Pot.")
        if len(top_3) >= 3: c3.metric(top_3[2]['Nom'], f"{top_3[2]['Score']}/20", f"{top_3[2]['Potentiel %']}% Pot.")

        st.markdown("---")
        st.subheader("📋 CLASSEMENT COMPLET DES ACTIONS")

        def style_noir_complet(df):
            return df.style.set_table_styles([
                {'selector': 'th', 'props': [('background-color','#111111'),('color','#ff9800'),('border','1px solid #333333'),('font-weight','bold')]},
                {'selector': 'td', 'props': [('background-color','#000000'),('color','#ffffff'),('border','1px solid #222222')]},
                {'selector': '', 'props': [('background-color','#000000')]}
            ]).applymap(lambda v: f'color: {"#00ff00" if v >= 15 else "#ff9800" if v >= 10 else "#ff4b4b"}; font-weight: bold;', subset=['Score'])

        st.dataframe(style_noir_complet(df_res), use_container_width=True, height=600)

        fig_screener = go.Figure(data=[go.Bar(x=df_res['Nom'], y=df_res['Score'],
            marker_color=['#00ff00' if s >= 15 else '#ff9800' if s >= 10 else '#ff4b4b' for s in df_res['Score']])])
        fig_screener.update_layout(title="Comparaison des Scores (Logic: Analyseur Pro)", template="plotly_dark",
                                   paper_bgcolor='black', plot_bgcolor='black')
        st.plotly_chart(fig_screener, use_container_width=True)

# ==========================================
# OUTIL : DIVIDEND CALENDAR
# ==========================================
elif outil == "DIVIDEND CALENDAR":
    st.title("💰 DIVIDEND CALENDAR")
    st.info("Calendrier des Dividendes")

    index_choice = st.selectbox("📊 INDICE",
        ["S&P 500 Dividend Aristocrats", "CAC 40", "NASDAQ Dividend", "Custom Watchlist"], key="div_index")

    def generate_dividend_data():
        today = datetime.now()
        dividends = []
        if index_choice == "S&P 500 Dividend Aristocrats":
            companies = [
                {"ticker":"JNJ","name":"Johnson & Johnson","yield":3.1,"amount":1.19,"freq":"Trimestriel"},
                {"ticker":"PG","name":"Procter & Gamble","yield":2.5,"amount":0.94,"freq":"Trimestriel"},
                {"ticker":"KO","name":"Coca-Cola","yield":3.0,"amount":0.48,"freq":"Trimestriel"},
                {"ticker":"PEP","name":"PepsiCo","yield":2.8,"amount":1.27,"freq":"Trimestriel"},
                {"ticker":"MCD","name":"McDonald's","yield":2.2,"amount":1.67,"freq":"Trimestriel"},
                {"ticker":"WMT","name":"Walmart","yield":1.5,"amount":0.57,"freq":"Trimestriel"},
                {"ticker":"MMM","name":"3M Company","yield":6.2,"amount":1.51,"freq":"Trimestriel"},
                {"ticker":"KMB","name":"Kimberly-Clark","yield":3.7,"amount":1.21,"freq":"Trimestriel"},
            ]
        elif index_choice == "CAC 40":
            companies = [
                {"ticker":"TTE.PA","name":"TotalEnergies","yield":5.2,"amount":0.79,"freq":"Trimestriel"},
                {"ticker":"SAN.PA","name":"Sanofi","yield":4.1,"amount":3.70,"freq":"Annuel"},
                {"ticker":"OR.PA","name":"L'Oréal","yield":1.8,"amount":5.50,"freq":"Annuel"},
                {"ticker":"BNP.PA","name":"BNP Paribas","yield":5.8,"amount":4.40,"freq":"Annuel"},
                {"ticker":"EN.PA","name":"Bouygues","yield":4.5,"amount":1.90,"freq":"Annuel"},
            ]
        else:
            companies = [
                {"ticker":"AAPL","name":"Apple","yield":0.5,"amount":0.24,"freq":"Trimestriel"},
                {"ticker":"MSFT","name":"Microsoft","yield":0.8,"amount":0.75,"freq":"Trimestriel"},
            ]
        for i, company in enumerate(companies):
            ex_date = today + timedelta(days=3 + i*7)
            payment_date = ex_date + timedelta(days=14)
            dividends.append({**company, "ex_date": ex_date, "payment_date": payment_date,
                               "status": "À venir" if ex_date > today else "Détaché"})
        return sorted(dividends, key=lambda x: x['ex_date'])

    dividends = generate_dividend_data()

    st.markdown("### 📊 STATISTIQUES")
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1: st.metric("Rendement Moyen", f"{sum([d['yield'] for d in dividends]) / len(dividends):.2f}%")
    with col_stat2: st.metric("Dividendes à venir", len([d for d in dividends if d['status'] == "À venir"]))
    with col_stat3: st.metric("Montant Total", f"${sum([d['amount'] for d in dividends]):.2f}")
    with col_stat4: st.metric("Rendement Max", f"{max([d['yield'] for d in dividends]):.1f}%")

    st.markdown("---")
    st.markdown("### 📅 CALENDRIER DES DÉTACHEMENTS")
    for div in dividends:
        status_emoji = "🟢" if div['status'] == "À venir" else "⚪"
        yield_emoji = "🔥" if div['yield'] >= 4 else "⭐" if div['yield'] >= 2 else "📊"
        with st.expander(f"{status_emoji} {div['name']} - {div['yield']:.2f}% {yield_emoji}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Ticker:** {div['ticker']}")
                st.write(f"**Fréquence:** {div['freq']}")
                st.write(f"**Statut:** {div['status']}")
            with col2:
                st.write(f"**Montant:** ${div['amount']:.2f}")
                st.write(f"**Ex-Date:** {div['ex_date'].strftime('%d/%m/%Y')}")
                st.write(f"**Paiement:** {div['payment_date'].strftime('%d/%m/%Y')}")

    st.markdown("---")
    st.markdown("### 🏆 TOP 5 RENDEMENTS")
    top_yields = sorted(dividends, key=lambda x: x['yield'], reverse=True)[:5]
    df_top = pd.DataFrame([{'Rang': idx+1, 'Société': div['name'], 'Ticker': div['ticker'],
                             'Rendement': f"{div['yield']:.2f}%", 'Montant': f"${div['amount']:.2f}",
                             'Ex-Date': div['ex_date'].strftime('%d/%m/%Y')} for idx, div in enumerate(top_yields)])
    st.dataframe(df_top, use_container_width=True, hide_index=True)
    st.caption("⚠️ Données simulées. Pour des données réelles, consultez Dividend.com ou les sites des sociétés.")


# ════════════════════════════════════════════════════════════
#
#  ██████╗  ██████╗ ██╗████████╗███████╗    █████╗
# ██╔═══██╗██╔═══██╗██║╚══██╔══╝██╔════╝   ██╔══██╗
# ██║   ██║██║   ██║██║   ██║   ███████╗   ███████║
# ██║   ██║██║   ██║██║   ██║   ╚════██║   ██╔══██║
# ╚██████╔╝╚██████╔╝██║   ██║   ███████║   ██║  ██║
#  ╚═════╝  ╚═════╝ ╚═╝   ╚═╝   ╚══════╝   ╚═╝  ╚═╝
#
#  MODULES : BOITE À OUTILS
#  - DAILY BRIEF
#  - CALENDRIER ÉCO
#  - FEAR & GREED INDEX
#  - CORRÉLATION DASH
#  - INTERETS COMPOSES
#  - HEATMAP MARCHÉ
#  - ALERTS MANAGER
#  - INSIDER TRADING TRACKER
#
# ════════════════════════════════════════════════════════════

# ==========================================
# OUTIL : DAILY BRIEF
# ==========================================
elif outil == "DAILY BRIEF":
    st.title("» DAILY BRIEFING")
    st.markdown("---")
    tab_eco, tab_tech, tab_quotidien = st.tabs(["🌍 GLOBAL MACRO", "⚡ TECH & CRYPTO", "📅 DAILY (BOURSORAMA)"])

    def afficher_flux_daily(url, filtre_boursorama_24h=False):
        try:
            import time
            flux = feedparser.parse(url)
            if not flux.entries: st.info("NO DATA FOUND."); return
            maintenant = time.time()
            secondes_par_jour = 24 * 3600
            articles = sorted(flux.entries, key=lambda x: x.get('published_parsed', 0), reverse=True)
            trouve = False
            for entry in articles[:15]:
                pub_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else maintenant
                if not filtre_boursorama_24h or (maintenant - pub_time) < secondes_par_jour:
                    trouve = True
                    clean_title = entry.title.replace(" - Boursorama", "").split(" - ")[0]
                    with st.expander(f"» {clean_title}"):
                        st.write(f"**SOURCE :** Boursorama / Google News")
                        if 'published' in entry: st.caption(f"🕒 TIMESTAMP : {entry.published}")
                        st.link_button("READ FULL ARTICLE", entry.link)
            if not trouve and filtre_boursorama_24h:
                st.warning("AWAITING FRESH DATA FROM BOURSORAMA...")
        except Exception: st.error("FEED ERROR.")

    with tab_eco:
        afficher_flux_daily("https://news.google.com/rss/search?q=bourse+economie+mondiale&hl=fr&gl=FR&ceid=FR:fr")
    with tab_tech:
        afficher_flux_daily("https://news.google.com/rss/search?q=crypto+nasdaq+nvidia&hl=fr&gl=FR&ceid=FR:fr")
    with tab_quotidien:
        st.subheader("» BOURSORAMA DIRECT (24H)")
        afficher_flux_daily("https://news.google.com/rss/search?q=site:boursorama.com&hl=fr&gl=FR&ceid=FR:fr", filtre_boursorama_24h=True)

# ==========================================
# OUTIL : CALENDRIER ÉCONOMIQUE
# ==========================================
elif outil == "CALENDRIER ÉCO":
    st.markdown("<h1 style='color:#ff9800;'>» ECONOMIC CALENDAR</h1>", unsafe_allow_html=True)

    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        pays = st.multiselect("🌍 PAYS", 
            ["US", "EU", "FR", "GB", "JP", "CN", "DE"],
            default=["US", "EU", "FR"])
    with col2:
        importance = st.selectbox("⚡ IMPORTANCE", 
            ["Tous", "High only", "Medium + High"],
            index=2)
    with col3:
        periode = st.selectbox("📅 PÉRIODE",
            ["Cette semaine", "Aujourd'hui", "Demain", "Ce mois"],
            index=0)

    # Mapping
    pays_map = {"US": "us", "EU": "eu", "FR": "fr", "GB": "gb", "JP": "jp", "CN": "cn", "DE": "de"}
    periode_map = {
        "Cette semaine": "thisWeek",
        "Aujourd'hui":   "today",
        "Demain":        "tomorrow",
        "Ce mois":       "thisMonth"
    }
    importance_map = {
        "Tous":            "-1,0,1",
        "High only":       "1",
        "Medium + High":   "0,1"
    }

    pays_str       = ",".join([pays_map[p] for p in pays]) if pays else "us,eu,fr"
    importance_str = importance_map[importance]
    periode_str    = periode_map[periode]

    calendrier_html = f"""
    <div style="background:#000; border:1px solid #ff9800; border-radius:8px; padding:5px;">
        <div class="tradingview-widget-container" style="height:750px;">
            <div class="tradingview-widget-container__widget"></div>
            <script type="text/javascript" 
                src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
            {{
                "colorTheme": "dark",
                "isMaximized": true,
                "width": "100%",
                "height": "750",
                "locale": "fr",
                "importanceFilter": "{importance_str}",
                "countryFilter": "{pays_str}",
                "dateRange": "{periode_str}"
            }}
            </script>
        </div>
    </div>
    """

    components.html(calendrier_html, height=780, scrolling=True)

    st.markdown("""
        <div style='display:flex; justify-content:space-between; color:#555; font-size:11px; margin-top:8px; font-family:monospace;'>
            <span>⚡ ROUGE = Impact Fort | 🟡 ORANGE = Impact Moyen | ⚪ GRIS = Faible</span>
            <span>SOURCE: TRADINGVIEW LIVE</span>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# OUTIL : FEAR & GREED INDEX
# ==========================================
elif outil == "Fear and Gread Index":
    st.title("🌡️ Market Sentiment Index")
    st.write("Analyse de la force du marché par rapport à sa moyenne long terme (MA200).")

    marches = {
        "^GSPC": "🇺🇸 USA (S&P 500)",
        "^FCHI": "🇫🇷 France (CAC 40)",
        "^HSI":  "🇨🇳 Chine (Hang Seng)",
        "BTC-USD": "₿ Bitcoin",
        "GC=F": "🟡 Or (Métal Précieux)"
    }
    c1, c2 = st.columns(2)
    items = list(marches.items())
    for i in range(len(items)):
        ticker, nom = items[i]
        score, label, couleur = calculer_score_sentiment(ticker)
        fig = afficher_jauge_pro(score, nom, couleur, label)
        if i % 2 == 0: c1.plotly_chart(fig, use_container_width=True)
        else:           c2.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.info("💡 **Conseil** : La 'Panique' (0-30%) indique souvent une opportunité d'achat, tandis que l'Euphorie (70-100%) suggère une bulle potentielle.")

# ==========================================
# OUTIL : CORRÉLATION DASH
# ==========================================
elif outil == "CORRÉLATION DASH":
    st.title("📊 ASSET CORRELATION MATRIX")
    st.write("Analyse de la corrélation sur les 30 derniers jours (Données Daily)")

    assets = {
        "BTC-USD": "Bitcoin", "^GSPC": "S&P 500", "GC=F": "Or (Gold)",
        "DX-Y.NYB": "Dollar Index", "^IXIC": "Nasdaq", "ETH-USD": "Ethereum"
    }
    with st.spinner('Calculating correlations...'):
        try:
            data = yf.download(list(assets.keys()), period="60d", interval="1d")['Close']
            returns = data.pct_change().dropna()
            corr_matrix = returns.corr()
            corr_matrix.columns = [assets[c] for c in corr_matrix.columns]
            corr_matrix.index = [assets[i] for i in corr_matrix.index]

            fig = go.Figure(data=go.Heatmap(z=corr_matrix.values, x=corr_matrix.columns,
                                             y=corr_matrix.index, colorscale='RdYlGn', zmin=-1, zmax=1))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="#ff9800"), height=500)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔍 KEY INSIGHTS")
                btc_sp = corr_matrix.loc["Bitcoin", "S&P 500"]
                if btc_sp > 0.7:   st.warning(f"⚠️ BTC / S&P 500 : Forte Corrélation ({btc_sp:.2f}). Le marché crypto suit les actions US.")
                elif btc_sp < 0.3: st.success(f"✅ BTC / S&P 500 : Découplage ({btc_sp:.2f}). Le BTC suit sa propre route.")
                else:              st.info(f"⚖️ BTC / S&P 500 : Corrélation Modérée ({btc_sp:.2f}).")
            with col2:
                st.subheader("📖 INTERPRÉTATION")
                st.write("**+1.0** : Les actifs bougent identiquement.")
                st.write("**0.0** : Aucun lien entre les deux.")
                st.write("**-1.0** : Les actifs bougent en sens opposé.")
        except Exception as e:
            st.error(f"Erreur de calcul : {e}")

# ==========================================
# OUTIL : INTÉRÊTS COMPOSÉS
# ==========================================
elif outil == "INTERETS COMPOSES":
    st.title("💰 SIMULATEUR D'INTÉRÊTS COMPOSÉS")
    st.write("Visualisez la puissance de la capitalisation sur le long terme.")

    col1, col2 = st.columns(2)
    with col1:
        cap_depart = st.number_input("Capital de départ (€)", value=1000.0, step=100.0)
        v_mensuel = st.number_input("Versement mensuel (€)", value=100.0, step=10.0)
    with col2:
        rendement = st.number_input("Taux annuel espéré (%)", value=8.0, step=0.5) / 100
        duree = st.number_input("Durée (années)", value=10, step=1)

    total = cap_depart
    total_investi = cap_depart
    historique = []
    for i in range(1, int(duree) + 1):
        for mois in range(12):
            total += total * (rendement / 12)
            total += v_mensuel
            total_investi += v_mensuel
        historique.append({"Année": i, "Total": round(total, 2),
                            "Investi": round(total_investi, 2), "Intérêts": round(total - total_investi, 2)})

    res1, res2, res3 = st.columns(3)
    res1.metric("VALEUR FINALE", f"{total:,.2f} €")
    res2.metric("TOTAL INVESTI", f"{total_investi:,.2f} €")
    res3.metric("GAIN NET", f"{(total - total_investi):,.2f} €")

    df_plot = pd.DataFrame(historique)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot["Année"], y=df_plot["Total"], name="Valeur Totale", line=dict(color='#00ff00')))
    fig.add_trace(go.Scatter(x=df_plot["Année"], y=df_plot["Investi"], name="Capital Investi", line=dict(color='#ff9800')))
    fig.update_layout(title="Évolution de votre patrimoine", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#ff9800"),
                      xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("VOIR LE DÉTAIL ANNÉE PAR ANNÉE"):
        st.table(df_plot)

# ==========================================
# OUTIL : HEATMAP MARCHÉ
# ==========================================
elif outil == "HEATMAP MARCHÉ":
    st.markdown("## 🌊 HEATMAP DE MARCHÉ")
    st.info("Visualisation TreeMap interactive des performances du marché")

    col_market1, col_market2 = st.columns(2)
    with col_market1:
        market_choice = st.selectbox("MARCHÉ", ["S&P 500 Top 30","CAC 40","NASDAQ Top 20","Crypto Top 15","Secteurs S&P 500"], key="heatmap_market")
    with col_market2:
        time_period = st.selectbox("PÉRIODE", ["1 Jour","5 Jours","1 Mois","3 Mois","1 An"], key="heatmap_period")

    if st.button("🎨 GÉNÉRER LA HEATMAP", key="gen_heatmap"):
        try:
            with st.spinner(f"Génération de la heatmap {market_choice}..."):
                period_map = {"1 Jour":"1d","5 Jours":"5d","1 Mois":"1mo","3 Mois":"3mo","1 An":"1y"}
                period = period_map[time_period]
                heatmap_data = []

                if market_choice == "S&P 500 Top 30":
                    tickers_list = [("AAPL","Tech"),("MSFT","Tech"),("GOOGL","Tech"),("AMZN","Consumer"),("NVDA","Tech"),("META","Tech"),("TSLA","Auto"),("BRK-B","Finance"),("UNH","Healthcare"),("JNJ","Healthcare"),("V","Finance"),("XOM","Energy"),("WMT","Consumer"),("JPM","Finance"),("PG","Consumer"),("MA","Finance"),("CVX","Energy"),("HD","Consumer"),("ABBV","Healthcare"),("MRK","Healthcare"),("KO","Consumer"),("PEP","Consumer"),("COST","Consumer"),("AVGO","Tech"),("MCD","Consumer"),("CSCO","Tech"),("TMO","Healthcare"),("ACN","Tech"),("ADBE","Tech"),("NKE","Consumer")]
                elif market_choice == "CAC 40":
                    tickers_list = [("AIR.PA","Industrie"),("BNP.PA","Finance"),("CA.PA","Finance"),("ACA.PA","Finance"),("DSY.PA","Tech"),("ENGI.PA","Energie"),("RMS.PA","Luxe"),("MC.PA","Luxe"),("OR.PA","Luxe"),("SAN.PA","Pharma"),("CS.PA","Finance"),("BN.PA","Alimentaire"),("KER.PA","Luxe"),("RI.PA","Luxe"),("PUB.PA","Média"),("RNO.PA","Auto"),("SAF.PA","Luxe"),("SGO.PA","Luxe"),("SU.PA","Energie"),("GLE.PA","Finance"),("TEP.PA","Telecom"),("TTE.PA","Energie"),("URW.PA","Immobilier"),("VIV.PA","Telecom")]
                elif market_choice == "NASDAQ Top 20":
                    tickers_list = [("AAPL","Tech"),("MSFT","Tech"),("GOOGL","Tech"),("AMZN","E-commerce"),("NVDA","Tech"),("META","Social"),("TSLA","Auto"),("AVGO","Semi"),("ASML","Semi"),("COST","Retail"),("ADBE","Software"),("CSCO","Network"),("PEP","Beverage"),("NFLX","Streaming"),("CMCSA","Media"),("INTC","Semi"),("AMD","Semi"),("QCOM","Semi"),("TXN","Semi"),("AMAT","Semi")]
                elif market_choice == "Crypto Top 15":
                    tickers_list = [(f"{c}-USD", "Crypto") for c in ["BTC","ETH","BNB","SOL","XRP","ADA","DOGE","MATIC","DOT","AVAX","LINK","UNI","ATOM","LTC","BCH"]]
                else:
                    tickers_list = [("XLK","Technology"),("XLF","Finance"),("XLV","Healthcare"),("XLE","Energy"),("XLY","Consumer Discretionary"),("XLP","Consumer Staples"),("XLI","Industrials"),("XLU","Utilities"),("XLRE","Real Estate"),("XLC","Communication"),("XLB","Materials")]

                for ticker_item, sector in tickers_list:
                    try:
                        df = yf.download(ticker_item, period=period, progress=False)
                        if not df.empty:
                            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                            start_price = float(df['Close'].iloc[0])
                            end_price = float(df['Close'].iloc[-1])
                            change_pct = ((end_price - start_price) / start_price) * 100
                            display_name = ticker_item.replace('.PA','').replace('-USD','') if market_choice in ["CAC 40","Crypto Top 15"] else ticker_item
                            heatmap_data.append({'Ticker': display_name, 'Sector': sector, 'Change': change_pct, 'Price': end_price})
                    except: continue

                if heatmap_data:
                    df_heatmap = pd.DataFrame(heatmap_data)
                    st.success(f"✅ {len(df_heatmap)} actifs chargés")

                    st.markdown("### 📊 STATISTIQUES DU MARCHÉ")
                    avg_change = df_heatmap['Change'].mean()
                    positive_count = len(df_heatmap[df_heatmap['Change'] > 0])
                    top_gainer = df_heatmap.loc[df_heatmap['Change'].idxmax()]
                    top_loser = df_heatmap.loc[df_heatmap['Change'].idxmin()]
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                    with col_stat1: st.metric("Variation Moyenne", f"{avg_change:+.2f}%")
                    with col_stat2: st.metric("Actions en hausse", f"{positive_count}/{len(df_heatmap)}", f"{(positive_count/len(df_heatmap))*100:.0f}%")
                    with col_stat3: st.metric("Top Gainer 🚀", top_gainer['Ticker'], f"{top_gainer['Change']:+.2f}%")
                    with col_stat4: st.metric("Top Loser 📉", top_loser['Ticker'], f"{top_loser['Change']:+.2f}%")

                    st.markdown("---")
                    st.markdown("### 🏆 TOP 5 GAINERS & LOSERS")
                    col_gain, col_loss = st.columns(2)
                    with col_gain:
                        st.markdown("#### 🚀 TOP GAINERS")
                        for idx, row in df_heatmap.nlargest(5, 'Change').iterrows():
                            st.markdown(f"<div style='padding: 12px; background: #00ff0022; border-left: 4px solid #00ff00; border-radius: 5px; margin: 8px 0;'><div style='display: flex; justify-content: space-between;'><b style='color: #00ff00; font-size: 16px;'>{row['Ticker']}</b><b style='color: white; font-size: 16px;'>{row['Change']:+.2f}%</b></div><small style='color: #ccc;'>${row['Price']:.2f}</small></div>", unsafe_allow_html=True)
                    with col_loss:
                        st.markdown("#### 📉 TOP LOSERS")
                        for idx, row in df_heatmap.nsmallest(5, 'Change').iterrows():
                            st.markdown(f"<div style='padding: 12px; background: #ff000022; border-left: 4px solid #ff0000; border-radius: 5px; margin: 8px 0;'><div style='display: flex; justify-content: space-between;'><b style='color: #ff0000; font-size: 16px;'>{row['Ticker']}</b><b style='color: white; font-size: 16px;'>{row['Change']:+.2f}%</b></div><small style='color: #ccc;'>${row['Price']:.2f}</small></div>", unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("### 📊 DISTRIBUTION DES PERFORMANCES")
                    fig_dist = go.Figure()
                    fig_dist.add_trace(go.Histogram(x=df_heatmap['Change'], nbinsx=30, marker_color='cyan',
                                                     marker_line_color='black', marker_line_width=1.5, name='Distribution'))
                    fig_dist.add_vline(x=avg_change, line_dash="dash", line_color="orange", line_width=3,
                                       annotation_text=f"Moyenne: {avg_change:+.2f}%", annotation_position="top")
                    fig_dist.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
                                           title="Distribution des variations", xaxis_title="Variation (%)",
                                           yaxis_title="Nombre d'actifs", height=400, showlegend=False)
                    st.plotly_chart(fig_dist, use_container_width=True)

                    if market_choice not in ["Crypto Top 15", "Secteurs S&P 500"]:
                        st.markdown("---")
                        st.markdown("### 🎯 PERFORMANCE PAR SECTEUR")
                        sector_perf = df_heatmap.groupby('Sector')['Change'].agg(['mean', 'count']).reset_index()
                        sector_perf.columns = ['Secteur', 'Variation Moyenne (%)', 'Nombre']
                        sector_perf = sector_perf.sort_values('Variation Moyenne (%)', ascending=False)
                        fig_sector = go.Figure(go.Bar(x=sector_perf['Secteur'], y=sector_perf['Variation Moyenne (%)'],
                            marker_color=['green' if x >= 0 else 'red' for x in sector_perf['Variation Moyenne (%)']],
                            text=sector_perf['Variation Moyenne (%)'].apply(lambda x: f"{x:+.2f}%"), textposition='auto'))
                        fig_sector.update_layout(template="plotly_dark", paper_bgcolor='black', plot_bgcolor='black',
                                                  title="Performance Moyenne par Secteur", xaxis_title="Secteur",
                                                  yaxis_title="Variation Moyenne (%)", height=400)
                        st.plotly_chart(fig_sector, use_container_width=True)

                    st.markdown("---")
                    st.markdown("### 📋 TABLEAU COMPLET")
                    df_display = df_heatmap.copy().sort_values('Change', ascending=False)
                    df_display['Change'] = df_display['Change'].apply(lambda x: f"{x:+.2f}%")
                    df_display['Price'] = df_display['Price'].apply(lambda x: f"${x:.2f}")
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else:
                    st.error("❌ Impossible de charger les données du marché")
        except Exception as e:
            st.error(f"Erreur lors de la génération: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# ==========================================
# OUTIL : ALERTS MANAGER
# ==========================================
elif outil == "ALERTS MANAGER":
    st.markdown("""
        <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); border: 3px solid #ff9800; border-radius: 15px; margin-bottom: 20px;'>
            <h1 style='color: #ff9800; margin: 0; font-size: 48px; text-shadow: 0 0 20px #ff9800;'>🔔 ALERTS MANAGER</h1>
            <p style='color: #ffb84d; margin: 10px 0 0 0; font-size: 18px;'>Système d'Alertes Prix & Volume</p>
        </div>
    """, unsafe_allow_html=True)

    if 'alerts' not in st.session_state: st.session_state.alerts = []
    if 'triggered_alerts' not in st.session_state: st.session_state.triggered_alerts = []

    tab1, tab2, tab3 = st.tabs(["➕ CRÉER ALERTE", "📋 MES ALERTES", "✅ ALERTES DÉCLENCHÉES"])

    with tab1:
        st.markdown("### ➕ NOUVELLE ALERTE")
        col_create1, col_create2 = st.columns(2)
        with col_create1:
            alert_ticker = st.text_input("TICKER", value="AAPL", key="alert_ticker").upper()
            alert_type = st.selectbox("TYPE D'ALERTE",
                ["Prix au-dessus","Prix en-dessous","Volume supérieur","Variation % positive","Variation % négative"], key="alert_type")
        with col_create2:
            if "Prix" in alert_type:
                alert_value = st.number_input("PRIX CIBLE ($)", min_value=0.01, value=150.0, step=1.0, key="alert_value")
            elif "Volume" in alert_type:
                alert_value = st.number_input("VOLUME MINIMUM", min_value=1000000, value=100000000, step=1000000, key="alert_value_vol")
            else:
                alert_value = st.number_input("VARIATION (%)", min_value=0.1, value=5.0, step=0.5, key="alert_value_pct")
            alert_name = st.text_input("NOM DE L'ALERTE (optionnel)", key="alert_name", placeholder="Ex: AAPL breakout 150")
        if st.button("🚀 CRÉER L'ALERTE", key="create_alert_btn", use_container_width=True):
            new_alert = {'id': len(st.session_state.alerts) + 1, 'ticker': alert_ticker, 'type': alert_type,
                         'value': alert_value, 'name': alert_name if alert_name else f"{alert_ticker} {alert_type}",
                         'created_at': datetime.now(), 'active': True}
            st.session_state.alerts.append(new_alert)
            st.success(f"✅ Alerte créée : {new_alert['name']}")
            st.rerun()

    with tab2:
        st.markdown("### 📋 ALERTES ACTIVES")
        if st.session_state.alerts:
            if st.button("🔍 VÉRIFIER TOUTES LES ALERTES", key="check_all"):
                with st.spinner("Vérification des alertes en cours..."):
                    for alert in st.session_state.alerts:
                        if not alert['active']: continue
                        try:
                            df = yf.download(alert['ticker'], period="2d", progress=False)
                            if df.empty: continue
                            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                            current_price = float(df['Close'].iloc[-1])
                            current_volume = float(df['Volume'].iloc[-1])
                            change_pct = ((current_price - float(df['Close'].iloc[-2])) / float(df['Close'].iloc[-2])) * 100 if len(df) >= 2 else 0
                            triggered = False
                            if alert['type'] == "Prix au-dessus" and current_price >= alert['value']: triggered = True
                            elif alert['type'] == "Prix en-dessous" and current_price <= alert['value']: triggered = True
                            elif alert['type'] == "Volume supérieur" and current_volume >= alert['value']: triggered = True
                            elif alert['type'] == "Variation % positive" and change_pct >= alert['value']: triggered = True
                            elif alert['type'] == "Variation % négative" and change_pct <= -alert['value']: triggered = True
                            if triggered:
                                st.session_state.triggered_alerts.append({'alert': alert, 'triggered_at': datetime.now(),
                                                                           'current_price': current_price,
                                                                           'current_volume': current_volume, 'change_pct': change_pct})
                                alert['active'] = False
                        except: continue
                    st.success("✅ Vérification terminée !")
                    st.rerun()
            st.markdown("---")
            active_alerts = [a for a in st.session_state.alerts if a['active']]
            if active_alerts:
                for alert in active_alerts:
                    col_alert1, col_alert2 = st.columns([4, 1])
                    emoji_map = {"Prix au-dessus":"📈","Prix en-dessous":"📉","Volume supérieur":"📊","Variation % positive":"🚀","Variation % négative":"⚠️"}
                    with col_alert1:
                        st.markdown(f"<div style='padding: 15px; background: linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%); border-radius: 10px; margin: 10px 0; border: 2px solid #ff9800;'><h4 style='color: #ff9800; margin: 0 0 5px 0;'>{emoji_map.get(alert['type'],'🔔')} {alert['name']}</h4><p style='color: #ccc; margin: 0; font-size: 14px;'>{alert['ticker']} • {alert['type']} • Valeur: {alert['value']:,.2f}</p><small style='color: #666;'>Créée le {alert['created_at'].strftime('%d/%m/%Y %H:%M')}</small></div>", unsafe_allow_html=True)
                    with col_alert2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_alert_{alert['id']}", help="Supprimer l'alerte"):
                            st.session_state.alerts.remove(alert)
                            st.rerun()
            else:
                st.info("Aucune alerte active.")
        else:
            st.info("Aucune alerte créée. Créez votre première alerte !")

    with tab3:
        st.markdown("### ✅ ALERTES DÉCLENCHÉES")
        if st.session_state.triggered_alerts:
            if st.button("🗑️ Effacer l'historique", key="clear_triggered"):
                st.session_state.triggered_alerts = []
                st.rerun()
            st.markdown("---")
            for triggered in sorted(st.session_state.triggered_alerts, key=lambda x: x['triggered_at'], reverse=True):
                alert = triggered['alert']
                st.markdown(f"""
                    <div style='padding: 20px; background: #00ff0022; border-radius: 10px; margin: 15px 0; border: 3px solid #00ff00;'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                            <h3 style='color: #00ff00; margin: 0;'>✅ {alert['name']}</h3>
                            <span style='color: #00ff00; font-size: 18px; font-weight: bold;'>DÉCLENCHÉE</span>
                        </div>
                        <p style='color: #ccc; margin: 5px 0;'><b>Ticker:</b> {alert['ticker']} | <b>Type:</b> {alert['type']} | <b>Seuil:</b> {alert['value']:,.2f}</p>
                        <div style='background: #0a0a0a; padding: 15px; border-radius: 8px; margin-top: 10px;'>
                            <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;'>
                                <div><p style='color: #999; font-size: 11px; margin: 0;'>PRIX ACTUEL</p><h4 style='color: white; margin: 5px 0 0 0;'>${triggered['current_price']:,.2f}</h4></div>
                                <div><p style='color: #999; font-size: 11px; margin: 0;'>VOLUME</p><h4 style='color: white; margin: 5px 0 0 0;'>{triggered['current_volume']:,.0f}</h4></div>
                                <div><p style='color: #999; font-size: 11px; margin: 0;'>VARIATION</p><h4 style='color: {"#00ff00" if triggered["change_pct"] >= 0 else "#ff0000"}; margin: 5px 0 0 0;'>{triggered['change_pct']:+.2f}%</h4></div>
                            </div>
                        </div>
                        <p style='color: #666; font-size: 12px; margin: 10px 0 0 0;'>🕐 Déclenchée le {triggered['triggered_at'].strftime('%d/%m/%Y à %H:%M:%S')}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune alerte déclenchée pour le moment")

    st.markdown("---")
    st.markdown("### 📊 STATISTIQUES")
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1: st.metric("Total Alertes", len(st.session_state.alerts))
    with col_stats2: st.metric("Alertes Actives", len([a for a in st.session_state.alerts if a['active']]))
    with col_stats3: st.metric("Alertes Déclenchées", len(st.session_state.triggered_alerts))
