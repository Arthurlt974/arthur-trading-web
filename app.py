import streamlit as st
import yfinance as yf
import requests
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px

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

# --- FONCTION GRAPHIQUE TRADINGVIEW (VERSION GÉANTE) ---
def afficher_graphique_tradingview(symbol):
    # Traduction des tickers Yahoo -> TradingView
    tv_symbol = symbol.upper()
    if ".PA" in tv_symbol:
        tv_symbol = f"EURONEXT:{tv_symbol.replace('.PA', '')}"
    elif ".L" in tv_symbol:
        tv_symbol = f"LSE:{tv_symbol.replace('.L', '')}"
    elif ".MI" in tv_symbol:
        tv_symbol = f"MILAN:{tv_symbol.replace('.MI', '')}"
    
    # Hauteur fixée à 800px pour un rendu professionnel
    html_code = f"""
    <div class="tradingview-widget-container" style="width:100%; height:800px;">
      <div id="tradingview_chart" style="width:100%; height:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%",
        "height": "100%",
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Europe/Paris",
        "theme": "dark",
        "style": "1",
        "locale": "fr",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=800)

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
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
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

        # --- TITRE ET METRICS ---
        st.title(f"📊 {nom} ({ticker})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)

        st.markdown("---")

        # --- GRAPHIQUE INTERACTIF (TOUTE LA LARGEUR) ---
        st.subheader("📈 Graphique Interactif Professionnel")
        afficher_graphique_tradingview(ticker)

        st.markdown("---")

        # --- DÉTAILS ET SCORING ---
        col_data, col_score_ui = st.columns([1, 1])

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette / Cap. Propres :** {dette_equity if dette_equity else 'N/A'} %")
            st.write(f"**Dividende :** {div_rate:.2f} {devise} ({div_yield:.2f}%)")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash par Action :** {cash_action:.2f} {devise}")

        with col_score_ui:
            st.subheader("⭐ Scoring Qualité (sur 20)")
            score = 0
            positifs, negatifs = [], []

            if bpa > 0:
                if per < 12: score += 5; positifs.append("✅ P/E attractif (Value) [+5]")
                elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
                else: score += 1; positifs.append("🟡 P/E élevé [+1]")
            else: score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")

            if dette_equity is not None:
                if dette_equity < 50: score += 4; positifs.append("✅ Bilan très solide [+4]")
                elif借ette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
                elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

            if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende solide/safe [+4]")
            elif payout > 95: score -= 4; negatifs.append("🚨 Payout Ratio risqué [-4]")
            
            if marge_pourcent > 100: score += 7; positifs.append("🔥 DÉCOTE EXCEPTIONNELLE [+7]")
            elif marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")
                
            if cash_action > (prix * 0.2): score += 2; positifs.append("💰 Bonus : Trésorerie abondante [+2]")

            score = min(20, max(0, score))
            
            st.write(f"## Note : {score}/20")
            st.progress(score / 20)
            if score >= 17: st.success("🔥 ACHAT FORT")
            elif score >= 14: st.info("🚀 ACHAT")
            elif score >= 10: st.warning("⚖️ À SURVEILLER")
            else: st.error("⚠️ ÉVITER")

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
                        r_bpa = rival_info.get('trailingEps', 0)
                        
                        # Fix Rendement
                        r_yield_raw = rival_info.get('dividendYield')
                        if r_yield_raw is not None:
                            r_yield = r_yield_raw if r_yield_raw > 0.2 else r_yield_raw * 100
                        else: r_yield = 0
                        
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

            fig_comp = px.bar(df_comp, x='Action', y='P/E Ratio', color='Action', 
                             title="Comparaison des Valorisations (P/E Ratio)",
                             template="plotly_dark")
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.error("Action non trouvée. Vérifiez le nom ou le ticker.")
