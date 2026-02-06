import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

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
    ["📊 Analyseur Pro", "⚔️ Mode Duel", "🌍 Market Monitor", "🔍 Screener CAC40", "😨 Fear & Greed", "💰 Simulateur Intérêts"])

# ==========================================
# OUTIL 1 : ANALYSEUR PRO (Ta Version)
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
        mode_graph = st.radio("Style :", ["Débutant (Ligne)", "Pro (Bougies)"], horizontal=True)

        col_graph, col_data = st.columns([2, 1])
        with col_graph:
            if mode_graph == "Pro (Bougies)":
                choix_int = st.selectbox("Unité :", ["90m", "1d", "1wk", "1mo"], index=1)
                p = {"90m": "1mo", "1d": "5y", "1wk": "max", "1mo": "max"}[choix_int]
                hist = action.history(period=p, interval=choix_int)
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
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

# ==========================================
# OUTIL 2 : MODE DUEL
# ==========================================
elif outil == "⚔️ Mode Duel":
    st.title("⚔️ Duel d'Actions")
    c1, c2 = st.columns(2)
    t1 = c1.text_input("Action 1", value="MC.PA")
    t2 = c2.text_input("Action 2", value="RMS.PA")
    
    if st.button("Lancer le Duel"):
        def get_d(t):
            i = yf.Ticker(trouver_ticker(t)).info
            p = i.get('currentPrice', 1)
            b = i.get('trailingEps', 0)
            v = (max(0, b) * (8.5 + 2 * 7) * 4.4) / 3.5
            return {"nom": i.get('shortName', t), "prix": p, "valeur": v, "dette": i.get('debtToEquity', 0), "yield": (i.get('dividendYield', 0) or 0)*100}
        d1, d2 = get_d(t1), get_d(t2)
        df = pd.DataFrame({
            "Critère": ["Prix", "Valeur Graham", "Dette/Eq", "Rendement"],
            d1['nom']: [f"{d1['prix']:.2f}", f"{d1['valeur']:.2f}", f"{d1['dette']}%", f"{d1['yield']:.2f}%"],
            d2['nom']: [f"{d2['prix']:.2f}", f"{d2['valeur']:.2f}", f"{d2['dette']}%", f"{d2['yield']:.2f}%"]
        })
        st.table(df)
        st.success(f"🏆 Gagnant (Potentiel) : {d1['nom'] if d1['valeur'] > d2['valeur'] else d2['nom']}")

# ==========================================
# OUTIL 3 : MARKET MONITOR (UTC+4)
# ==========================================
elif outil == "🌍 Market Monitor":
    maintenant = datetime.utcnow() + timedelta(hours=4)
    h = maintenant.hour
    st.title("🌍 Market Monitor (UTC+4)")
    st.subheader(f"🕒 Heure actuelle : {maintenant.strftime('%H:%M:%S')}")
    
    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    cols = st.columns(len(indices))
    if 'idx_sel' not in st.session_state: st.session_state.idx_sel = "^FCHI"
    for i, (tk, nom) in enumerate(indices.items()):
        d = yf.Ticker(tk).history(period="2d")
        if not d.empty:
            c = d['Close'].iloc[-1]
            var = ((c - d['Open'].iloc[-1]) / d['Open'].iloc[-1]) * 100
            cols[i].metric(nom, f"{c:,.2f}", f"{var:+.2f}%")
            if cols[i].button(f"Zoom {nom}", key=tk): st.session_state.idx_sel = tk
    
    st.markdown("---")
    hist_m = yf.Ticker(st.session_state.idx_sel).history(period="1mo")
    fig_m = go.Figure(data=[go.Scatter(x=hist_m.index, y=hist_m['Close'], fill='tozeroy', line=dict(color='#00d1ff'))])
    fig_m.update_layout(template="plotly_dark", height=450, yaxis_side="right")
    st.plotly_chart(fig_m, use_container_width=True)

# ==========================================
# OUTIL 4 : SCREENER CAC40
# ==========================================
elif outil == "🔍 Screener CAC40":
    st.title("🔍 Scanner Expert CAC 40")
    if st.button("🚀 Lancer le Scan Complet"):
        actions = ["AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EL.PA", "STLAP.PA", "RMS.PA", "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "SW.PA", "STMPA.PA", "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"]
        results = []
        bar = st.progress(0)
        for idx, t in enumerate(actions):
            try:
                inf = yf.Ticker(t).info
                bpa = inf.get('trailingEps', 0)
                px = inf.get('currentPrice', 1)
                val = (max(0, bpa) * 22.5 * 4.4) / 3.5
                pot = ((val - px) / px) * 100
                score = 10
                if pot > 30: score += 5
                if inf.get('debtToEquity', 150) < 80: score += 5
                results.append({"Ticker": t, "Score": min(20, score), "Potentiel": f"{pot:.1f}%"})
            except: pass
            bar.progress((idx + 1) / len(actions))
        st.table(pd.DataFrame(results).sort_values(by="Score", ascending=False))

# ==========================================
# OUTIL 5 : FEAR & GREED
# ==========================================
elif outil == "😨 Fear & Greed":
    st.title("🔍 Sentiment de Marché")
    marches = {"^GSPC": "S&P 500", "^FCHI": "CAC 40", "BTC-USD": "Bitcoin", "GC=F": "OR"}
    for tk, nom in marches.items():
        d = yf.Ticker(tk).history(period="1y")
        ma200 = d['Close'].rolling(window=200).mean().iloc[-1]
        prix = d['Close'].iloc[-1]
        ratio = (prix/ma200) - 1
        if ratio > 0.10: res, col = "EXTREME GREED 🚀", "#2ecc71"
        elif ratio < -0.10: res, col = "EXTREME FEAR 💀", "#e74c3c"
        else: res, col = "NEUTRAL ⚖️", "#f1c40f"
        st.markdown(f"### {nom} : <span style='color:{col}'>{res}</span>", unsafe_allow_html=True)

# ==========================================
# OUTIL 6 : SIMULATEUR INTÉRÊTS
# ==========================================
elif outil == "💰 Simulateur Intérêts":
    st.title("💰 Simulateur d'Intérêts Composés")
    col1, col2 = st.columns(2)
    cap = col1.number_input("Capital Initial (€)", value=1000)
    mensuel = col1.number_input("Versement mensuel (€)", value=100)
    taux = col2.number_input("Taux Annuel (%)", value=8.0)
    ans = col2.number_input("Durée (années)", value=10)
    
    total = cap
    data_sim = []
    for i in range(1, ans + 1):
        for _ in range(12):
            total += total * (taux / 100 / 12)
            total += mensuel
        data_sim.append({"Année": i, "Total": total})
    st.line_chart(pd.DataFrame(data_sim).set_index("Année"))
    st.success(f"Résultat final : {total:,.2f} €")
