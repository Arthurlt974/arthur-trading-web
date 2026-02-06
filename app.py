import streamlit as st
import yfinance as yf
import requests
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Arthur Trading Pro", layout="wide")

# Dictionnaire des concurrents
CONCURRENTS = {
    "Consumer Cyclical": ["RMS.PA", "KER.PA", "OR.PA", "CAP.PA"],
    "Financial Services": ["GLE.PA", "ACA.PA", "CS.PA"],
    "Industrials": ["SAF.PA", "HO.PA", "AIR.PA"],
    "Energy": ["BP.L", "SHEL.L", "ENI.MI"],
    "Technology": ["STMPA.PA", "DSY.PA", "WLN.PA"]
}

# --- FONCTION GRAPHIQUE TRADINGVIEW (FORCE CARRE / LARGE) ---
def afficher_graphique_tradingview(symbol):
    tv_symbol = symbol.upper()
    if ".PA" in tv_symbol:
        tv_symbol = f"EURONEXT:{tv_symbol.replace('.PA', '')}"
    elif ".L" in tv_symbol:
        tv_symbol = f"LSE:{tv_symbol.replace('.L', '')}"
    elif ".MI" in tv_symbol:
        tv_symbol = f"MILAN:{tv_symbol.replace('.MI', '')}"
    
    # ID unique pour forcer le rafraîchissement
    chart_id = f"tv_chart_{int(time.time())}"
    
    # Force la hauteur à 1000px pour un rendu massif
    html_code = f"""
    <div id="wrapper_{chart_id}" style="width:100%; height:1000px; background-color: #131722; border-radius: 8px; overflow: hidden;">
      <div id="{chart_id}" style="width:100%; height:100%;"></div>
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
        "container_id": "{chart_id}"
      }});
      </script>
    </div>
    """
    components.html(html_code, height=1010, scrolling=False)

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
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)

        st.markdown("---")

        # --- LE GRAPHIQUE FORCE EN FORMAT LARGE/CARRE ---
        st.subheader("📈 Vue Graphique Étendue")
        with st.container():
            afficher_graphique_tradingview(ticker)

        st.markdown("---")

        # --- INFOS ET SCORING ---
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
                if per < 12: score += 5; positifs.append("✅ P/E attractif [+5]")
                elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
                else: score += 1; positifs.append("🟡 P/E élevé [+1]")
            else: score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")

            if dette_equity is not None:
                if dette_equity < 50: score += 4; positifs.append("✅ Bilan très solide [+4]")
                elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
                elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

            if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende safe [+4]")
            elif payout > 95: score -= 4; negatifs.append("🚨 Payout Ratio risqué [-4]")
            
            if marge_pourcent > 30: score += 5; positifs.append("✅ Décote Graham [+5]")
            if cash_action > (prix * 0.2): score += 2; positifs.append("💰 Bonus : Cash abondant [+2]")

            score = min(20, max(0, score))
            st.write(f"## Note : {score}/20")
            st.progress(score / 20)
            
            for p in positifs: st.write(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.write(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)

    else:
        st.error("Action non trouvée.")
