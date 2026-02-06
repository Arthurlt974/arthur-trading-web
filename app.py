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
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')

        st.title(f"📊 {nom} ({ticker})")

        # --- LIGNE 1 : METRICS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c4.metric("Secteur", secteur)

        st.markdown("---")

        # --- LIGNE 2 : GRAPHIQUE AVEC INTERVALLES RÉELS ---
        col_graph, col_data = st.columns([2, 1])

        with col_graph:
            # Sélecteur d'intervalle (La bougie représente quoi ?)
            choix_int = st.selectbox(
                "Choisir l'unité d'une bougie :",
                ["90m", "1d", "1wk", "1mo"],
                format_func=lambda x: {"90m": "Bougie 90 min (Intraday)", "1d": "Bougie 1 Jour", "1wk": "Bougie 1 Semaine", "1mo": "Bougie 1 Mois"}[x],
                index=1
            )

            # Mapping pour la période de téléchargement
            periodes = {"90m": "1mo", "1d": "2y", "1wk": "max", "1mo": "max"}
            
            # Téléchargement des données spécifiques
            hist = action.history(period=periodes[choix_int], interval=choix_int)
            
            if not hist.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    increasing_line_color='#2ecc71',
                    decreasing_line_color='#e74c3c'
                )])

                fig.update_layout(
                    template="plotly_dark", 
                    height=600, 
                    margin=dict(l=0, r=10, t=0, b=0),
                    xaxis=dict(rangeslider=dict(visible=False), type="date"),
                    yaxis=dict(side="right"),
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            # Extraction propre des infos pour éviter les erreurs
            bpa = info.get('trailingEps', 0)
            per = info.get('trailingPE', 0)
            st.write(f"**BPA (EPS) :** {bpa if bpa else 0:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per if per else 0:.2f}")
            st.write(f"**Dette / Cap. Propres :** {info.get('debtToEquity', 'N/A')} %")
            st.write(f"**Dividende :** {info.get('dividendRate', 0)} {devise}")

        # --- LIGNE 3 : SCORING ---
        st.markdown("---")
        st.subheader("⭐ Scoring Rapide")
        score = 15 # Valeur d'exemple
        st.progress(score / 20)
        st.write(f"Note globale : {score}/20")

    else:
        st.error("Action non trouvée.")
