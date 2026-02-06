import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Arthur Trading Pro V5.2", layout="wide")

def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

# --- BARRE LATÉRALE ---
st.sidebar.title("💎 Arthur Trading")
nom_entree = st.sidebar.text_input("Nom de l'action", value="MC.PA")

if nom_entree:
    ticker = trouver_ticker(nom_entree)
    action = yf.Ticker(ticker)
    info = action.info
    
    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        # --- RÉCUPÉRATION DES DONNÉES ---
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')
        
        # Récupération BPA Robuste
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        
        # PER
        per = info.get('trailingPE')
        if not per and bpa > 0:
            per = prix / bpa
        per = per or 0

        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare') or 0

        # Calcul Graham
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 else 0

        st.title(f"📊 {nom} ({ticker})")

        # --- LIGNE 1 : METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)

        st.markdown("---")
        mode_graph = st.radio("Style de graphique :", ["Débutant (Ligne)", "Pro (Bougies)"], horizontal=True)

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
                hist = action.history(period="5y", interval="1d")
                fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], fill='tozeroy', line=dict(color='#00d1ff'))])
            
            fig.update_layout(template="plotly_dark", height=550, margin=dict(l=0, r=10, t=0, b=0), xaxis=dict(rangeslider=dict(visible=False)), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

        # --- LIGNE 3 : SCORING (RETOUR FORMAT AVANT) ---
        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        
        score = 0
        positifs, negatifs = [], []

        # Calcul du score
        if bpa > 0:
            if per < 12: score += 5; positifs.append("✅ P/E attractif (Value) [+5]")
            elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
            else: score += 1; positifs.append("🟡 P/E élevé [+1]")
        else:
            score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")

        if dette_equity is not None:
            if dette_equity < 50: score += 4; positifs.append("✅ Bilan très solide [+4]")
            elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende solide/safe [+4]")
        elif payout > 95: score -= 4; negatifs.append("🚨 Payout Ratio risqué [-4]")
        
        if marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")
        if cash_action > (prix * 0.15): score += 2; positifs.append("💰 Bonus : Trésorerie abondante [+2]")

        score_final = min(20, max(0, score))
        
        c_score, c_details = st.columns([1, 2])
        with c_score:
            st.write(f"## Note : {score_final}/20")
            st.progress(score_final / 20)
            if score_final >= 15: st.success("🚀 ACHAT FORT")
            elif score_final >= 10: st.info("⚖️ À SURVEILLER")
            else: st.error("⚠️ ÉVITER")

        with c_details:
            st.write("**Détails de l'analyse :**")
            for p in positifs:
                st.markdown(f'<p style="color:#2ecc71; margin:0; font-weight:bold;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs:
                st.markdown(f'<p style="color:#e74c3c; margin:0; font-weight:bold;">{n}</p>', unsafe_allow_html=True)

    else:
        st.error("Données indisponibles. Vérifiez le ticker.")

st.markdown("---")
st.caption("Arthur Trading Pro - Analyse basée sur les données fondamentales Yahoo Finance.")
