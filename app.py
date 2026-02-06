import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests

# Configuration large
st.set_page_config(page_title="Arthur Trading Pro", layout="wide")

def trouver_ticker(nom):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

# Barre latérale
st.sidebar.title("💎 Arthur Trading")
nom_action = st.sidebar.text_input("Nom de l'action", value="MC.PA")

if nom_action:
    ticker = trouver_ticker(nom_action)
    action = yf.Ticker(ticker)
    info = action.info
    
    if info and 'currentPrice' in info:
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or 1
        bpa = info.get('trailingEps') or 0
        per = info.get('trailingPE') or (prix / bpa if bpa > 0 else 0)
        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare', 0)
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')

        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge_pourcent = ((val_theorique - prix) / prix) * 100
        div_yield = (div_rate / prix * 100) if (div_rate > 0) else 0

        st.title(f"📊 {nom} ({ticker})")

        # --- LIGNE 1 : METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)

        st.markdown("---")

        # --- LIGNE 2 : GRAPHIQUE BOUGIES + TIME FRAMES ---
        col_graph, col_data = st.columns([2, 1])

        with col_graph:
            st.subheader("📈 Analyse en Bougies Japonaises")
            
            # Récupération des données (on prend 'max' pour avoir tout l'historique)
            # Note: Le 4h n'est dispo que sur un historique limité
            hist = action.history(period="max", interval="1d")
            
            if not hist.empty:
                # Création du graphique en Bougies (Candlestick)
                fig = go.Figure(data=[go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    name="Prix",
                    increasing_line_color='#2ecc71', # Vert
                    decreasing_line_color='#e74c3c'  # Rouge
                )])

                # AJOUT DES BOUTONS DE TIME FRAME DEMANDÉS
                fig.update_layout(
                    template="plotly_dark", 
                    height=600, 
                    margin=dict(l=0, r=10, t=40, b=0),
                    xaxis=dict(
                        rangeselector=dict(
                            buttons=list([
                                dict(count=4, label="4h", step="hour", stepmode="backward"),
                                dict(count=1, label="1d", step="day", stepmode="backward"),
                                dict(count=7, label="1W", step="day", stepmode="backward"),
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=12, label="12m", step="month", stepmode="backward"),
                                dict(label="MAX", step="all")
                            ]),
                            bgcolor="#1e2130",
                            activecolor="#00d1ff",
                            font=dict(color="white")
                        ),
                        rangeslider=dict(visible=False), # Désactivé pour plus de clarté
                        type="date"
                    ),
                    yaxis=dict(title=f"Prix ({devise})", side="right"),
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

        # --- LIGNE 3 : SCORING ---
        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        
        score = 0
        positifs, negatifs = [], []

        if bpa > 0:
            if per < 12: score += 5; positifs.append("✅ P/E attractif [+5]")
            elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
            else: score += 1; positifs.append("🟡 P/E élevé [+1]")
        else: score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")

        if dette_equity is not None:
            if dette_equity < 50: score += 4; positifs.append("✅ Bilan solide [+4]")
            elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

        score = min(20, max(0, score))
        
        col_score, col_details = st.columns([1, 2])
        with col_score:
            st.write(f"## Note : {score}/20")
            st.progress(score / 20)
            if score >= 14: st.success("🚀 ANALYSE POSITIVE")
            else: st.warning("⚖️ À SURVEILLER")

        with col_details:
            for p in positifs: st.write(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.write(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)

    else:
        st.error("Action non trouvée.")
