import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests
import pandas as pd
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Arthur Trading Pro", layout="wide")

# Dictionnaire des concurrents par secteur
CONCURRENTS = {
    "Consumer Cyclical": ["RMS.PA", "KER.PA", "OR.PA", "CAP.PA"],
    "Financial Services": ["GLE.PA", "ACA.PA", "CS.PA"],
    "Industrials": ["SAF.PA", "HO.PA", "AIR.PA"],
    "Energy": ["BP.L", "SHEL.L", "ENI.MI"],
    "Technology": ["STMPA.PA", "DSY.PA", "WLN.PA"]
}

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
        # --- RÉCUPÉRATION DES DONNÉES COMPLÈTES ---
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or 1
        bpa = info.get('trailingEps') or 0
        per = info.get('trailingPE') or (prix / bpa if bpa > 0 else 0)
        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate', 0)
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare', 0)
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')

        # Calculs Graham
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge_pourcent = ((val_theorique - prix) / prix) * 100
        div_yield = (div_rate / prix * 100) if (div_rate > 0) else 0

        st.title(f"📊 {nom} ({ticker})")

        # --- LIGNE 1 : METRICS PRINCIPALES ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)

        st.markdown("---")

        # --- SÉLECTION DU MODE DE GRAPHIQUE ---
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
                # Mode Débutant : Ligne épurée
                hist = action.history(period="5y", interval="1d")
                fig = go.Figure(data=[go.Scatter(
                    x=hist.index, y=hist['Close'],
                    fill='tozeroy', line=dict(color='#00d1ff', width=2),
                    name="Prix de clôture"
                )])
            
            fig.update_layout(
                template="plotly_dark", height=600, margin=dict(l=0, r=10, t=0, b=0),
                xaxis=dict(rangeslider=dict(visible=False), type="date"),
                yaxis=dict(side="right"),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette / Cap. Propres :** {dette_equity if dette_equity else 'N/A'} %")
            st.write(f"**Dividende :** {div_rate:.2f} {devise} ({div_yield:.2f}%)")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash par Action :** {cash_action:.2f} {devise}")

        # --- LIGNE 3 : SCORING QUALITÉ ---
        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        
        score = 0
        positifs, negatifs = [], []

        # Calcul du score (Logic précédente)
        if bpa > 0:
            if per < 12: score += 5; positifs.append("✅ P/E attractif (Value) [+5]")
            elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
            else: score += 1; positifs.append("🟡 P/E élevé [+1]")
        else: score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")

        if dette_equity is not None:
            if dette_equity < 50: score += 4; positifs.append("✅ Bilan très solide [+4]")
            elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende solide/safe [+4]")
        if marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")
        if cash_action > (prix * 0.2): score += 2; positifs.append("💰 Bonus : Cash abondant [+2]")

        score = min(20, max(0, score))
        
        c_s, c_d = st.columns([1, 2])
        with c_s:
            st.write(f"## Note : {score}/20")
            st.progress(score / 20)
            if score >= 15: st.success("🔥 ANALYSE TRÈS POSITIVE")
            elif score >= 10: st.info("⚖️ PROFIL CORRECT")
            else: st.error("⚠️ PROFIL RISQUÉ")

        with c_d:
            for p in positifs: st.write(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.write(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)

        # --- SECTION COMPARATIF SECTEUR ---
        st.markdown("---")
        st.subheader(f"🏢 Comparatif du secteur : {secteur}")
        liste_rivaux = CONCURRENTS.get(secteur, [])
        if liste_rivaux:
            tous_les_tickers = list(set([ticker] + liste_rivaux))
            donnees_comp = []
            
            with st.spinner('Chargement du comparatif...'):
                for t in tous_les_tickers:
                    try:
                        rival_info = yf.Ticker(t).info
                        r_prix = rival_info.get('currentPrice', 1)
                        r_bpa = rival_info.get('trailingEps', 1)
                        r_yield = (rival_info.get('dividendYield', 0) or 0) * 100
                        
                        donnees_comp.append({
                            "Action": rival_info.get('shortName', t),
                            "Ticker": t,
                            "P/E Ratio": round(r_prix / r_bpa, 2) if r_bpa > 0 else 0,
                            "Rendement": f"{r_yield:.2f} %",
                            "Dette/Equity": f"{rival_info.get('debtToEquity', 0)} %"
                        })
                    except: continue
                    
            df_comp = pd.DataFrame(donnees_comp)
            st.dataframe(df_comp, use_container_width=True)

    else:
        st.error("Action non trouvée.")
