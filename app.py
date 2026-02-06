import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION GLOBALE ---
st.set_page_config(page_title="Arthur Trading Hub", layout="wide")

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
# OUTIL 1 : ANALYSEUR PRO (Version Finale)
# ==========================================
if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="MC.PA")
    ticker = trouver_ticker(nom_entree)
    action = yf.Ticker(ticker)
    info = action.info

    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        per = info.get('trailingPE') or (prix/bpa if bpa > 0 else 0)

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
        mode_graph = st.radio("Style :", ["Ligne", "Bougies"], horizontal=True)

        col_graph, col_data = st.columns([2, 1])
        with col_graph:
            if mode_graph == "Bougies":
                choix_int = st.selectbox("Unité :", ["1d", "1wk", "1mo"], index=0)
                hist = action.history(period="5y", interval=choix_int)
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#2ecc71', decreasing_line_color='#e74c3c')])
            else:
                hist = action.history(period="5y")
                fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], fill='tozeroy', line=dict(color='#00d1ff'))])
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False, yaxis_side="right")
            st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette/Equity :** {dette_equity if ajoute := dette_equity else 'N/A'} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")

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
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende safe [+4]")
        if marge_pourcent > 30: score += 5; positifs.append("✅ Décote Graham [+5]")
        
        score_f = min(20, max(0, score))
        cs, cd = st.columns([1, 2])
        cs.write(f"## Note : {score_f}/20")
        cs.progress(score_f / 20)
        with cd:
            for p in positifs: st.markdown(f'<p style="color:#2ecc71;margin:0;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.markdown(f'<p style="color:#e74c3c;margin:0;">{n}</p>', unsafe_allow_html=True)

# ==========================================
# OUTIL 2 : MODE DUEL
# ==========================================
elif outil == "⚔️ Mode Duel":
    st.title("⚔️ Duel d'Actions")
    c1, c2 = st.columns(2)
    t1, t2 = c1.text_input("Action 1", "AAPL"), c2.text_input("Action 2", "MSFT")
    if st.button("Lancer le Duel"):
        # Logique de comparaison simplifiée
        st.info("Comparaison en cours...")

# ==========================================
# OUTIL 3 : MARKET MONITOR (Version Session.py)
# ==========================================
elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor UTC+4")
    maintenant = datetime.now()
    h = maintenant.hour
    
    st.write(f"🕒 **Heure actuelle :** {maintenant.strftime('%H:%M:%S')}")

    # 1. TABLEAU DES HORAIRES
    st.markdown("### 🕒 Horaires des Sessions (Réunion)")
    data_horaires = {
        "Session": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "Ouverture": ["05:30", "12:00", "18:30"],
        "Fermeture": ["12:00", "20:30", "01:00"],
        "Statut": [
            "🔴 FERMÉ" if not (5 <= h < 12) else "🟢 OUVERT",
            "🔴 FERMÉ" if not (12 <= h < 20) else "🟢 OUVERT",
            "🔴 FERMÉ" if not (h >= 18 or h < 1) else "🟢 OUVERT"
        ]
    }
    st.table(pd.DataFrame(data_horaires))

    # 2. INDICES MAJEURS
    st.markdown("---")
    st.subheader("⚡ Indices Majeurs")
    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    cols = st.columns(len(indices))
    
    for i, (tk, nom) in enumerate(indices.items()):
        try:
            d = yf.Ticker(tk).history(period="2d")
            if not d.empty:
                c = d['Close'].iloc[-1]
                o = d['Open'].iloc[-1]
                var = ((c - o) / o) * 100
                cols[i].metric(nom, f"{c:,.2f}", f"{var:+.2f}%")
        except: pass

    # 3. CONSEILS STRATÉGIQUES (Exactement comme Session.py)
    st.markdown("---")
    st.subheader("💡 Conseils de Session (UTC+4)")
    if 5 <= h < 12:
        st.warning("**Chine (HK)** : Surveille la clôture de Hong Kong, elle impacte souvent l'ouverture de Paris à midi.")
    elif 12 <= h < 18:
        st.info("**Europe (Paris)** : Observe le DAX. S'il ne suit pas le CAC, la hausse est suspecte. Le 'Gap' de midi est souvent testé avant les US.")
    elif h >= 18 or h < 1:
        st.success("**USA (NY)** : C'est le gros volume. Regarde le NASDAQ pour la Tech. Attention aux inversions de tendance après 22h.")
    else:
        st.write("🌑 **Nuit** : Le marché est calme. Idéal pour préparer ta watchlist de demain.")

    st.markdown("---")
    st.caption("Note : Les horaires sont configurés pour le fuseau de l'île de la Réunion (UTC+4).")
