import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests
import pandas as pd

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Arthur Trading Pro", layout="wide")

def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

# --- BARRE LATÉRALE ---
st.sidebar.title("💎 Arthur Trading")
nom_action = st.sidebar.text_input("Nom de l'action", value="MC.PA")

if nom_action:
    ticker = trouver_ticker(nom_action)
    action = yf.Ticker(ticker)
    info = action.info
    
    if info and 'currentPrice' in info:
        # --- RÉCUPÉRATION DES DONNÉES ---
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or 1
        bpa = info.get('trailingEps') or 0
        per = info.get('trailingPE') or (prix / bpa if bpa > 0 else 0)
        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        marge_pourcent = ((( (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5) - prix) / prix) * 100
        devise = info.get('currency', 'EUR')

        st.title(f"📊 {nom} ({ticker})")

        # --- CHOIX DU MODE D'AFFICHAGE ---
        mode_graph = st.radio("Style de graphique :", ["Débutant (Linéaire)", "Pro (Bougies)"], horizontal=True)

        st.markdown("---")

        # --- LIGNE 2 : GRAPHIQUE + INFOS ---
        col_graph, col_data = st.columns([2, 1])

        with col_graph:
            if mode_graph == "Pro (Bougies)":
                choix_int = st.selectbox("Unité de la bougie :", ["90m", "1d", "1wk", "1mo"], index=1)
                p = {"90m": "1mo", "1d": "5y", "1wk": "max", "1mo": "max"}[choix_int]
                hist = action.history(period=p, interval=choix_int)
                
                fig = go.Figure(data=[go.Candlestick(
                    x=hist.index, open=hist['Open'], high=hist['High'],
                    low=hist['Low'], close=hist['Close'],
                    increasing_line_color='#2ecc71', decreasing_line_color='#e74c3c'
                )])
            else:
                # Mode Débutant : Courbe simple et épurée
                hist = action.history(period="5y", interval="1d")
                fig = go.Figure(data=[go.Scatter(
                    x=hist.index, y=hist['Close'],
                    fill='tozeroy', line=dict(color='#00d1ff', width=2)
                )])
            
            fig.update_layout(
                template="plotly_dark", height=600, margin=dict(l=0, r=10, t=0, b=0),
                xaxis=dict(rangeslider=dict(visible=False)),
                yaxis=dict(side="right")
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette / Cap. Propres :** {dette_equity if dette_equity else 'N/A'} %")
            st.write(f"**Dividende :** {div_rate:.2f} {devise}")
            st.write(f"**Payout Ratio :** {payout:.2f} %")

        # --- LIGNE 3 : SCORING ---
        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        
        score = 0
        positifs, negatifs = [], []
        if bpa > 0:
            if per < 12: score += 5; positifs.append("✅ P/E attractif [+5]")
            elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
        else: score -= 5; negatifs.append("🚨 En perte [-5]")

        if dette_equity is not None and dette_equity < 100: score += 4; positifs.append("✅ Dette maîtrisée [+4]")
        
        score = min(20, max(0, score))
        col_s, col_d = st.columns([1, 2])
        with col_s:
            st.write(f"## Note : {score}/20")
            st.progress(score / 20)
        with col_d:
            for p in positifs: st.write(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.write(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)

    else:
        st.error("Action non trouvée.")
