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

# ============================================
# CONFIGURATION GLOBALE
# ============================================
st.set_page_config(page_title="AM-Trading | Bloomberg Terminal", layout="wide")

# ============================================
# INITIALISATION SESSION STATE (CORRIGÉ)
# ============================================
# Initialiser une seule fois tous les états
if "multi_charts" not in st.session_state:
    st.session_state.multi_charts = []

if "whale_logs" not in st.session_state:
    st.session_state.whale_logs = []

if "workspace" not in st.session_state:
    st.session_state.workspace = []

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

# ============================================
# FONCTIONS UTILITAIRES (CORRIGÉES)
# ============================================

def get_crypto_price(symbol):
    """Récupère le prix d'une crypto via Binance ou Yahoo Finance"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return float(response.json()['price'])
        else:
            return None
    except:
        try:
            # Fallback sur Yahoo Finance
            tkr = symbol + "-USD"
            data = yf.Ticker(tkr).fast_info
            return data.get('last_price')
        except:
            return None

# ============================================
# STYLE BLOOMBERG TERMINAL
# ============================================
st.markdown("""
    <style>
        /* Supprime la ligne blanche/grise en haut */
        header[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
            color: #ff9800 !important;
        }
        
        .stApp [data-testid="stDecoration"] {
            display: none;
        }

        /* Fond noir */
        .stApp { 
            background-color: #0d0d0d; 
            color: #ff9800 !important; 
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] { 
            background-color: #161616; 
            border-right: 1px solid #333; 
        }
        
        /* Textes en orange */
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
        
        /* Boutons */
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

# ============================================
# SYSTÈME DE MOT DE PASSE
# ============================================
def check_password():
    if st.session_state.password_correct:
        return True
    
    st.markdown("### [ SECURITY ] TERMINAL ACCESS REQUIRED")
    pwd = st.text_input("ENTER ACCESS CODE :", type="password", key="pwd_input")
    
    if st.button("EXECUTE LOGIN"):
        if pwd == "1234":
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("!! ACCESS DENIED - INVALID CODE")
    return False

if not check_password():
    st.stop()

# Auto-refresh toutes les 10 minutes
st_autorefresh(interval=600000, key="global_refresh")

# ============================================
# FONCTION HORLOGE
# ============================================
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

# ============================================
# FONCTION GRAPHIQUE TRADINGVIEW
# ============================================
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

# ============================================
# HEADER PRINCIPAL
# ============================================
st.markdown("<h1 style='text-align: center; color: #ff9800;'>📊 BLOOMBERG TERMINAL PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>ADVANCED MARKET INTELLIGENCE PLATFORM</p>", unsafe_allow_html=True)
st.markdown("---")

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    afficher_horloge_temps_reel()
    st.markdown("---")
    st.markdown("### 🎯 NAVIGATION")
    
    outil = st.selectbox(
        "MODULE:",
        [
            "DASHBOARD PRINCIPAL",
            "CRYPTO LIVE TRACKER",
            "ANALYSEUR PRO",
            "SCREENER CAC 40",
            "NEWS FEED",
            "MULTI-CHARTS"
        ]
    )

# ============================================
# MODULE: DASHBOARD PRINCIPAL
# ============================================
if outil == "DASHBOARD PRINCIPAL":
    st.markdown("## 📊 DASHBOARD PRINCIPAL")
    
    # Indices majeurs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            btc_price = get_crypto_price("BTC")
            if btc_price:
                st.metric("₿ BITCOIN", f"${btc_price:,.2f}")
            else:
                st.metric("₿ BITCOIN", "N/A")
        except:
            st.metric("₿ BITCOIN", "N/A")
    
    with col2:
        try:
            eth_price = get_crypto_price("ETH")
            if eth_price:
                st.metric("Ξ ETHEREUM", f"${eth_price:,.2f}")
            else:
                st.metric("Ξ ETHEREUM", "N/A")
        except:
            st.metric("Ξ ETHEREUM", "N/A")
    
    with col3:
        try:
            sp500 = yf.Ticker("^GSPC")
            info = sp500.fast_info
            st.metric("📈 S&P 500", f"{info['last_price']:,.2f}")
        except:
            st.metric("📈 S&P 500", "N/A")
    
    with col4:
        try:
            cac40 = yf.Ticker("^FCHI")
            info = cac40.fast_info
            st.metric("🇫🇷 CAC 40", f"{info['last_price']:,.2f}")
        except:
            st.metric("🇫🇷 CAC 40", "N/A")
    
    st.markdown("---")
    
    # Graphique S&P 500
    st.markdown("### 📈 S&P 500 - 30 JOURS")
    try:
        df_sp = yf.download("^GSPC", period="1mo", progress=False)
        if not df_sp.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_sp.index,
                open=df_sp['Open'],
                high=df_sp['High'],
                low=df_sp['Low'],
                close=df_sp['Close'],
                name='S&P 500'
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='black',
                plot_bgcolor='black',
                xaxis_rangeslider_visible=False,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur chargement graphique: {str(e)}")

# ============================================
# MODULE: CRYPTO LIVE TRACKER
# ============================================
elif outil == "CRYPTO LIVE TRACKER":
    st.markdown("## 💰 CRYPTO LIVE TRACKER")
    
    crypto_list = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "MATIC"]
    
    cols = st.columns(4)
    for idx, crypto in enumerate(crypto_list):
        with cols[idx % 4]:
            try:
                price = get_crypto_price(crypto)
                if price:
                    st.metric(f"{crypto}", f"${price:,.2f}")
                else:
                    st.metric(f"{crypto}", "N/A")
            except:
                st.metric(f"{crypto}", "N/A")
    
    st.markdown("---")
    
    # Graphique détaillé
    crypto_select = st.selectbox("SÉLECTIONNER UNE CRYPTO", crypto_list)
    
    try:
        ticker_crypto = f"{crypto_select}-USD"
        df_crypto = yf.download(ticker_crypto, period="1mo", progress=False)
        
        if not df_crypto.empty:
            fig_crypto = go.Figure()
            fig_crypto.add_trace(go.Candlestick(
                x=df_crypto.index,
                open=df_crypto['Open'],
                high=df_crypto['High'],
                low=df_crypto['Low'],
                close=df_crypto['Close'],
                name=crypto_select
            ))
            fig_crypto.update_layout(
                template="plotly_dark",
                paper_bgcolor='black',
                plot_bgcolor='black',
                title=f"{crypto_select} - 30 JOURS",
                xaxis_rangeslider_visible=False,
                height=500
            )
            st.plotly_chart(fig_crypto, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur: {str(e)}")

# ============================================
# MODULE: ANALYSEUR PRO
# ============================================
elif outil == "ANALYSEUR PRO":
    st.markdown("## 🎯 ANALYSEUR D'ACTION PROFESSIONNEL")
    
    ticker = st.text_input("TICKER (ex: AAPL, TSLA, MC.PA)", value="AAPL").upper()
    
    if st.button("🚀 ANALYSER"):
        try:
            action = yf.Ticker(ticker)
            info = action.info
            
            if info and 'currentPrice' in info:
                # Infos de base
                st.markdown("### 📊 INFORMATIONS")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Société", info.get('longName', ticker))
                    st.metric("Secteur", info.get('sector', 'N/A'))
                
                with col2:
                    current_price = info.get('currentPrice', 0)
                    st.metric("Prix Actuel", f"${current_price:.2f}")
                    pe = info.get('trailingPE', 0)
                    st.metric("P/E Ratio", f"{pe:.2f}" if pe else "N/A")
                
                with col3:
                    market_cap = info.get('marketCap', 0)
                    st.metric("Market Cap", f"${market_cap/1e9:.2f}B" if market_cap else "N/A")
                    div_yield = info.get('dividendYield', 0)
                    st.metric("Dividend", f"{div_yield*100:.2f}%" if div_yield else "0%")
                
                st.markdown("---")
                
                # Graphique TradingView
                st.markdown("### 📈 GRAPHIQUE INTERACTIF")
                afficher_graphique_pro(ticker, height=500)
                
                st.markdown("---")
                
                # Analyse Graham simplifiée
                st.markdown("### 💎 ANALYSE FONDAMENTALE")
                
                bpa = info.get('trailingEps', 0)
                per = info.get('trailingPE', 0)
                dette_equity = info.get('debtToEquity', 0)
                
                # Valeur théorique Graham
                val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5 if bpa > 0 else 0
                marge_securite = ((val_theorique - current_price) / current_price) * 100 if current_price > 0 else 0
                
                col_fund1, col_fund2, col_fund3 = st.columns(3)
                
                with col_fund1:
                    st.metric("BPA (EPS)", f"${bpa:.2f}" if bpa else "N/A")
                
                with col_fund2:
                    st.metric("Valeur Graham", f"${val_theorique:.2f}")
                
                with col_fund3:
                    st.metric("Marge Sécurité", f"{marge_securite:+.2f}%")
                
                # Score qualité
                score = 0
                if bpa > 0 and per < 20:
                    score += 5
                if dette_equity and dette_equity < 50:
                    score += 5
                if marge_securite > 30:
                    score += 5
                
                score = min(15, score)
                score_color = "#00ff00" if score >= 10 else "#ff9800" if score >= 5 else "#ff0000"
                
                st.markdown(f"""
                    <div style='text-align: center; padding: 20px; background: {score_color}22; border: 2px solid {score_color}; border-radius: 10px; margin-top: 20px;'>
                        <h1 style='color: {score_color};'>{score} / 15</h1>
                        <p style='color: white;'>SCORE DE QUALITÉ</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Impossible de récupérer les données pour ce ticker")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

# ============================================
# MODULE: SCREENER CAC 40
# ============================================
elif outil == "SCREENER CAC 40":
    st.markdown("## 🔍 SCREENER CAC 40")
    st.info("Scanner le CAC 40 avec notation Graham")
    
    if st.button("🚀 LANCER LE SCAN"):
        cac40_tickers = [
            "AIR.PA", "AIRP.PA", "ALO.PA", "MT.PA", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA",
            "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA", "RMS.PA",
            "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORP.PA", "RI.PA", "PUB.PA",
            "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "SW.PA", "STMPA.PA",
            "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
        ]
        
        resultats = []
        progress = st.progress(0)
        status = st.empty()
        
        for i, t in enumerate(cac40_tickers):
            status.text(f"Analyse {t} ({i+1}/40)")
            progress.progress((i + 1) / len(cac40_tickers))
            
            try:
                action = yf.Ticker(t)
                info = action.info
                
                if not info or 'currentPrice' not in info:
                    continue
                
                nom = info.get('shortName', t)
                prix = info.get('currentPrice', 1)
                bpa = info.get('trailingEps', 0)
                per = info.get('trailingPE', 0)
                dette = info.get('debtToEquity', 0)
                
                val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5 if bpa > 0 else 0
                marge = ((val_theorique - prix) / prix) * 100 if prix > 0 else 0
                
                score = 0
                if bpa > 0 and per < 20:
                    score += 5
                if dette and dette < 50:
                    score += 5
                if marge > 30:
                    score += 5
                
                resultats.append({
                    "Ticker": t,
                    "Nom": nom,
                    "Score": score,
                    "Potentiel %": round(marge, 1),
                    "P/E": round(per, 1) if per else 0,
                    "Prix €": round(prix, 2)
                })
            except:
                continue
        
        status.success("✅ Analyse terminée!")
        
        if resultats:
            df_res = pd.DataFrame(resultats).sort_values(by="Score", ascending=False)
            
            # Top 3
            st.markdown("### 🏆 TOP 3")
            c1, c2, c3 = st.columns(3)
            top = df_res.head(3).to_dict('records')
            
            if len(top) >= 1:
                with c1:
                    st.metric(top[0]['Nom'], f"{top[0]['Score']}/15", f"{top[0]['Potentiel %']}%")
            if len(top) >= 2:
                with c2:
                    st.metric(top[1]['Nom'], f"{top[1]['Score']}/15", f"{top[1]['Potentiel %']}%")
            if len(top) >= 3:
                with c3:
                    st.metric(top[2]['Nom'], f"{top[2]['Score']}/15", f"{top[2]['Potentiel %']}%")
            
            st.markdown("---")
            st.dataframe(df_res, use_container_width=True, hide_index=True)
            
            # Graphique
            fig = go.Figure(data=[go.Bar(
                x=df_res['Nom'],
                y=df_res['Score'],
                marker_color=['#00ff00' if s >= 10 else '#ff9800' if s >= 5 else '#ff0000' for s in df_res['Score']]
            )])
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='black',
                plot_bgcolor='black',
                title="Scores CAC 40",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================
# MODULE: NEWS FEED
# ============================================
elif outil == "NEWS FEED":
    st.markdown("## 📰 NEWS FEED")
    
    try:
        feed = feedparser.parse("https://www.investing.com/rss/news.rss")
        
        if feed.entries:
            for entry in feed.entries[:10]:
                with st.expander(f"📌 {entry.title}"):
                    st.write(entry.summary if hasattr(entry, 'summary') else "Pas de résumé")
                    st.caption(f"🔗 [Lire l'article]({entry.link})")
        else:
            st.warning("Aucune news disponible")
    except Exception as e:
        st.error(f"Erreur chargement news: {str(e)}")

# ============================================
# MODULE: MULTI-CHARTS
# ============================================
elif outil == "MULTI-CHARTS":
    st.markdown("## 📊 MULTI-CHARTS")
    
    # Ajouter un graphique
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        new_ticker = st.text_input("TICKER À AJOUTER", key="multi_ticker").upper()
    with col_add2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ AJOUTER"):
            if new_ticker and new_ticker not in st.session_state.multi_charts:
                st.session_state.multi_charts.append(new_ticker)
                st.success(f"✅ {new_ticker} ajouté")
                st.rerun()
    
    # Afficher les graphiques
    if st.session_state.multi_charts:
        for ticker in st.session_state.multi_charts:
            col_chart, col_btn = st.columns([10, 1])
            
            with col_chart:
                st.markdown(f"### {ticker}")
                try:
                    df = yf.download(ticker, period="1mo", progress=False)
                    if not df.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Candlestick(
                            x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close']
                        ))
                        fig.update_layout(
                            template="plotly_dark",
                            paper_bgcolor='black',
                            plot_bgcolor='black',
                            xaxis_rangeslider_visible=False,
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                except:
                    st.error(f"Erreur chargement {ticker}")
            
            with col_btn:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{ticker}"):
                    st.session_state.multi_charts.remove(ticker)
                    st.rerun()
    else:
        st.info("Aucun graphique. Ajoutez un ticker ci-dessus.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #666;'>© 2024 AM-TRADING | Bloomberg Terminal Pro</p>", unsafe_allow_html=True)
