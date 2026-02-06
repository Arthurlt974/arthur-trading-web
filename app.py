import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Arthur Trading Pro V5", layout="wide")

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
    
    if info and 'currentPrice' in info or 'regularMarketPrice' in info:
        # --- RÉCUPÉRATION ROBUSTE DES DONNÉES ---
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')
        
        # BPA : on cherche partout pour éviter le "Faux Négatif"
        bpa = info.get('trailingEps') or info.get('forwardEps') or info.get('defaultKeyStatistics', {}).get('trailingEps', 0)
        
        # PER : calcul manuel si Yahoo fait défaut
        per = info.get('trailingPE')
        if not per and bpa and bpa > 0:
            per = prix / bpa
        per = per or 0

        dette_equity = info.get('debtToEquity') # Souvent en % (ex: 50 pour 50%)
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare') or 0

        # Calcul Graham (Conservateur)
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

        # --- LIGNE 2 : GRAPHIQUE ---
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
            
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=10, t=0, b=0), xaxis=dict(rangeslider=dict(visible=False)), yaxis=dict(side="right"))
            st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette/Equity :** {dette_equity if ajoute := dette_equity else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

        # --- LIGNE 3 : SCORING COHÉRENT SUR 20 ---
        st.markdown("---")
        col_score_final, col_bareme = st.columns([1, 1])

        with col_score_final:
            st.subheader("⭐ Analyse du Score")
            score = 0
            details = []

            # 1. Analyse BPA & PER (Max 5 pts)
            if bpa > 0:
                if 0 < per < 12: 
                    score += 5; details.append("✅ P/E Excellent (<12) [+5]")
                elif 12 <= per < 20: 
                    score += 4; details.append("✅ P/E Raisonnable (12-20) [+4]")
                else: 
                    score += 1; details.append("🟡 P/E Élevé (>20) [+1]")
            else:
                score -= 5; details.append("🚨 BPA Négatif (Pertes) [-5]")

            # 2. Analyse Dette (Max 4 pts)
            if dette_equity is not None:
                if dette_equity < 50: 
                    score += 4; details.append("✅ Bilan très sain (<50%) [+4]")
                elif dette_equity < 100: 
                    score += 3; details.append("✅ Dette sous contrôle (<100%) [+3]")
                elif dette_equity > 200: 
                    score -= 4; details.append("❌ Surendettement (>200%) [-4]")

            # 3. Dividende (Max 4 pts)
            if 10 < payout <= 80: 
                score += 4; details.append("✅ Dividende soutenable [+4]")
            elif payout > 95:
                score -= 4; details.append("🚨 Dividende à risque [-4]")

            # 4. Décote Graham (Max 5 pts)
            if marge_pourcent > 30: 
                score += 5; details.append("✅ Forte décote Graham (>30%) [+5]")
            elif marge_pourcent > 0:
                score += 2; details.append("🟡 Légère décote [+2]")

            # 5. Cash (Max 2 pts)
            if cash_action > (prix * 0.15): 
                score += 2; details.append("💰 Trésorerie abondante [+2]")

            # On bloque le score entre 0 et 20
            score_final = min(20, max(0, score))
            st.write(f"## Note Finale : {score_final}/20")
            st.progress(score_final / 20)
            
            for d in details:
                color = "#2ecc71" if "+" in d else ("#f1c40f" if "🟡" in d else "#e74c3c")
                st.markdown(f'<p style="color:{color}; margin:0; font-weight:bold;">{d}</p>', unsafe_allow_html=True)

        with col_bareme:
            st.subheader("📋 Barème de Calcul")
            data_bareme = {
                "Critère": ["P/E < 12", "P/E 12-20", "Dette < 50%", "Dette < 100%", "Payout 10-80%", "Décote Graham > 30%", "Cash abondant", "BPA Négatif", "Surendettement"],
                "Points Max": ["+5", "+4", "+4", "+3", "+4", "+5", "+2", "-5", "-4"]
            }
            st.table(pd.DataFrame(data_bareme))

    else:
        st.error("Données indisponibles. Vérifiez le ticker (ex: MC.PA, AAPL).")

st.info("Note : Ce score est une aide à l'analyse basée sur des critères fondamentaux. Il ne constitue pas un conseil financier.")
