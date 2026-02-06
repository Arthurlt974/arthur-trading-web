import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="Arthur Trading Hub", layout="wide")

# --- FONCTION DE RECHERCHE DE TICKER ---
def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

# --- NAVIGATION ---
st.sidebar.title("🚀 Arthur Trading Hub")
outil = st.sidebar.radio("Choisir un outil :", 
    ["📊 Analyseur Pro", "⚔️ Mode Duel", "🌍 Market Monitor"])

# ==========================================
# OUTIL 1 : ANALYSEUR PRO (Version perfectionnée)
# ==========================================
if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="MC.PA")
    ticker = trouver_ticker(nom_entree)
    action = yf.Ticker(ticker)
    info = action.info

    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 0)
        devise = info.get('currency', 'EUR')
        
        # Graham & Stats
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge = ((val_theorique - prix) / prix) * 100
        
        st.title(f"📊 {nom} ({ticker})")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Prix", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge:+.2f}%")

        st.markdown("---")
        mode_g = st.radio("Style :", ["Ligne", "Bougies"], horizontal=True)
        
        col_g, col_d = st.columns([2, 1])
        with col_g:
            if mode_g == "Bougies":
                int_v = st.selectbox("Intervalle :", ["1d", "1wk", "1mo"], index=0)
                hist = action.history(period="5y", interval=int_v)
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
            else:
                hist = action.history(period="5y")
                fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], fill='tozeroy')])
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_d:
            st.subheader("📑 Détails")
            st.write(f"**P/E Ratio :** {per:.2f}")
            st.write(f"**Dette/Equity :** {info.get('debtToEquity', 'N/A')} %")
            st.write(f"**Payout :** {info.get('payoutRatio', 0)*100:.1f} %")
            st.write(f"**Secteur :** {info.get('sector', 'N/A')}")
            
            # Score rapide
            score = 10
            if per < 15: score += 5
            if marge > 20: score += 5
            st.write(f"### Note : {score}/20")
            st.progress(score/20)

# ==========================================
# OUTIL 2 : MODE DUEL (Inspiré de Duel V2.py)
# ==========================================
elif outil == "⚔️ Mode Duel":
    st.title("⚔️ Duel d'Actions")
    st.write("Comparez deux actifs pour voir lequel est le plus solide fondamentalement.")
    
    col_a, col_b = st.columns(2)
    with col_a: t1 = st.text_input("Action 1", value="AAPL")
    with col_b: t2 = st.text_input("Action 2", value="MSFT")
    
    if st.button("Lancer le Duel"):
        d1, d2 = yf.Ticker(trouver_ticker(t1)).info, yf.Ticker(trouver_ticker(t2)).info
        
        if d1 and d2:
            def get_stats(d):
                p = d.get('currentPrice', 1)
                b = d.get('trailingEps', 0)
                v = (max(0, b) * (8.5 + 2 * 7) * 4.4) / 3.5
                return {"nom": d.get('shortName'), "prix": p, "valeur": v, "dette": d.get('debtToEquity', 999), "div": (d.get('dividendYield', 0) or 0)*100}

            s1, s2 = get_stats(d1), get_stats(d2)
            
            # Tableau de duel
            df_duel = pd.DataFrame({
                "Critère": ["Prix", "Valeur Graham", "Dette/Equity", "Rendement Div."],
                s1['nom']: [f"{s1['prix']:.2f}", f"{s1['valeur']:.2f}", f"{s1['dette']}%", f"{s1['div']:.2f}%"],
                s2['nom']: [f"{s2['prix']:.2f}", f"{s2['valeur']:.2f}", f"{s2['dette']}%", f"{s2['div']:.2f}%"]
            })
            st.table(df_duel)
            
            # Verdict
            pts1 = (1 if s1['valeur']>s1['prix'] else 0) + (1 if s1['dette']<s2['dette'] else 0)
            pts2 = (1 if s2['valeur']>s2['prix'] else 0) + (1 if s2['dette']<s1['dette'] else 0)
            v_nom = s1['nom'] if pts1 > pts2 else s2['nom']
            st.success(f"🏆 Verdict : {v_nom} remporte le duel !")

# ==========================================
# OUTIL 3 : MARKET MONITOR (Inspiré de Session.py)
# ==========================================
elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor (Flux Direct)")
    h = datetime.now().hour
    
    st.info(f"Heure locale : {datetime.now().strftime('%H:%M:%S')} | Fuseau : UTC+4 (Réunion)")

    # Status des bourses
    c1, c2, c3 = st.columns(3)
    c1.metric("EUROPE (Paris)", "12:00 - 20:30", "OUVERT" if 12 <= h < 20 else "FERMÉ")
    c2.metric("USA (New York)", "18:30 - 01:00", "OUVERT" if (h >= 18 or h < 1) else "FERMÉ")
    c3.metric("ASIE (Hong Kong)", "05:30 - 12:00", "OUVERT" if 5 <= h < 12 else "FERMÉ")

    st.markdown("---")
    st.subheader("⚡ Indices Majeurs")
    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    
    cols = st.columns(len(indices))
    for i, (tk, nom) in enumerate(indices.items()):
        data = yf.Ticker(tk).history(period="2d")
        if not data.empty:
            p_close = data['Close'].iloc[-1]
            p_open = data['Open'].iloc[-1]
            var = ((p_close - p_open) / p_open) * 100
            cols[i].metric(nom, f"{p_close:,.2f}", f"{var:+.2f}%")

    st.subheader("💡 Conseil Stratégique")
    if 12 <= h < 18:
        st.write("👉 **Session Européenne :** Le CAC 40 est le maître. Attention au 'gap' de 15h30 avant l'ouverture US.")
    elif h >= 18 or h < 1:
        st.write("👉 **Session US :** C'est le gros volume. Surveillez le NASDAQ (Tech) pour la tendance globale.")
    else:
        st.write("👉 **Session Nocturne :** Le marché est calme, idéal pour analyser les clôtures US et préparer demain.")
