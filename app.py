import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="Arthur Trading Hub", layout="wide")

# --- CORRECTIF ANTI-BLOCAGE (Session HTTP + Cache) ---
@st.cache_resource
def get_session():
    """Crée une session qui imite un navigateur pour éviter le Rate Limit de Yahoo"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

@st.cache_data(ttl=3600)
def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

def obtenir_action(ticker_symbol):
    """Récupère l'objet Ticker en utilisant la session sécurisée"""
    return yf.Ticker(ticker_symbol, session=get_session())

# --- NAVIGATION ---
st.sidebar.title("🚀 Arthur Trading Hub")
outil = st.sidebar.radio("Choisir un outil :", 
    ["📊 Analyseur Pro", "⚔️ Mode Duel", "🌍 Market Monitor"])

# ==========================================
# OUTIL 1 : ANALYSEUR PRO
# ==========================================
if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="MC.PA")
    ticker = trouver_ticker(nom_entree)
    
    # Utilisation du moteur sécurisé
    action = obtenir_action(ticker)
    
    try:
        info = action.info
        if info and ('currentPrice' in info or 'regularMarketPrice' in info):
            nom = info.get('longName') or info.get('shortName') or ticker
            prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
            devise = info.get('currency', 'EUR')
            secteur = info.get('sector', 'N/A')
            bpa = info.get('trailingEps') or info.get('forwardEps') or 0
            
            per = info.get('trailingPE')
            if not per and bpa > 0: per = prix / bpa
            per = per or 0

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
                    choix_int = st.selectbox("Unité :", ["90m", "1d", "1wk", "1mo"], index=1)
                    p = {"90m": "1mo", "1d": "5y", "1wk": "max", "1mo": "max"}[choix_int]
                    hist = action.history(period=p, interval=choix_int)
                    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#2ecc71', decreasing_line_color='#e74c3c')])
                else:
                    hist = action.history(period="5y")
                    fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], fill='tozeroy', line=dict(color='#00d1ff'))])
                
                fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=10, t=0, b=0), xaxis_rangeslider_visible=False, yaxis_side="right")
                st.plotly_chart(fig, use_container_width=True)

            with col_data:
                st.subheader("📑 Détails Financiers")
                st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
                st.write(f"**Ratio P/E :** {per:.2f}")
                st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
                st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
                st.write(f"**Payout Ratio :** {payout:.2f} %")
                st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

            # --- SYSTEME DE SCORING ---
            st.markdown("---")
            st.subheader("⭐ Scoring Qualité (sur 20)")
            score = 0
            positifs, negatifs = [], []

            if bpa > 0:
                if per < 12: score += 5; positifs.append("✅ P/E attractif [+5]")
                elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
                else: score += 1; positifs.append("🟡 P/
