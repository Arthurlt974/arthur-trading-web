import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta

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
# OUTIL 1 : ANALYSEUR PRO (VERSION INTEGRALE)
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
            # CORRECTION LIGNE 75 (Pas de :=)
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

        st.markdown("---")
        st.subheader("⭐ Scoring Qualité (sur 20)")
        score, positifs, negatifs = 0, [], []
        if bpa > 0:
            if per < 12: score += 5; positifs.append("✅ P/E attractif [+5]")
            elif per < 20: score += 4; positifs.append("✅ Valorisation raisonnable [+4]")
            else: score += 1; positifs.append("🟡 P/E élevé [+1]")
        else: score -= 5; negatifs.append("🚨 Entreprise en PERTE [-5]")
        if dette_equity is not None:
            if dette_equity < 50: score += 4; positifs.append("✅ Bilan très solide [+4]")
            elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")
        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende solide [+4]")
        if marge_pourcent > 30: score += 5; positifs.append("✅ Forte décote Graham [+5]")
        if cash_action > (prix * 0.15): score += 2; positifs.append("💰 Bonus : Trésorerie abondante [+2]")

        score_f = min(20, max(0, score))
        c_s, c_d = st.columns([1, 2])
        with c_s:
            st.write(f"## Note : {score_f}/20")
            st.progress(score_f / 20)
            if score_f >= 15: st.success("🚀 ACHAT FORT")
            elif score_f >= 10: st.info("⚖️ À SURVEILLER")
            else: st.error("⚠️ ÉVITER")
        with c_d:
            for p in positifs: st.markdown(f'<p style="color:#2ecc71;margin:0;font-weight:bold;">{p}</p>', unsafe_allow_html=True)
            for n in negatifs: st.markdown(f'<p style="color:#e74c3c;margin:0;font-weight:bold;">{n}</p>', unsafe_allow_html=True)

# ==========================================
# OUTIL 2 : MODE DUEL (VERSION INTEGRALE AVEC 🥇)
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
            v = (max(0, b) * 22.5 * 4.4) / 3.5
            return {"nom": i.get('shortName', t), "prix": p, "valeur": v, "dette": i.get('debtToEquity', 0), "yield": (i.get('dividendYield', 0) or 0)*100}
        
        d1, d2 = get_d(t1), get_d(t2)
        m1, m2 = ((d1['valeur']-d1['prix'])/d1['prix']*100), ((d2['valeur']-d2['prix'])/d2['prix']*100)
        
        # Affichage avec tes médailles logic
        df = pd.DataFrame({
            "Critère": ["Prix", "Valeur Graham", "Marge Sécurité 🥇", "Dette/Equity 🥇", "Rendement 🥇"],
            d1['nom']: [f"{d1['prix']:.2f}", f"{d1['valeur']:.2f}", f"{m1:.1f}% {'🥇' if m1>m2 else ''}", f"{d1['dette']}% {'🥇' if d1['dette']<d2['dette'] else ''}", f"{d1['yield']:.2f}% {'🥇' if d1['yield']>d2['yield'] else ''}"],
            d2['nom']: [f"{d2['prix']:.2f}", f"{d2['valeur']:.2f}", f"{m2:.1f}% {'🥇' if m2>m1 else ''}", f"{d2['dette']}% {'🥇' if d2['dette']<d1['dette'] else ''}", f"{d2['yield']:.2f}% {'🥇' if d2['yield']>d1['yield'] else ''}"]
        })
        st.table(df)

# ==========================================
# OUTIL 3 : MARKET MONITOR (VERSION INTEGRALE UTC+4)
# ==========================================
elif outil == "🌍 Market Monitor":
    maintenant = datetime.utcnow() + timedelta(hours=4)
    h = maintenant.hour
    st.title("🌍 Market Monitor (UTC+4)")
    st.subheader(f"🕒 Heure aux Avirons : {maintenant.strftime('%H:%M:%S')}")

    st.markdown("### 🕒 Statut des Bourses")
    data_h = {
        "Session": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "Horaires (REU)": ["05:30 - 12:00", "12:00 - 20:30", "18:30 - 01:00"],
        "Statut": ["🟢 OUVERT" if 5 <= h < 12 else "🔴 FERMÉ", "🟢 OUVERT" if 12 <= h < 20 else "🔴 FERMÉ", "🟢 OUVERT" if (h >= 18 or h < 1) else "🔴 FERMÉ"]
    }
    st.table(pd.DataFrame(data_h))

    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    cols = st.columns(len(indices))
    if 'idx_sel' not in st.session_state: st.session_state.idx_sel = "^FCHI"

    for i, (tk, nom) in enumerate(indices.items()):
        d_idx = yf.Ticker(tk).history(period="2d")
        if not d_idx.empty:
            v_act = d_idx['Close'].iloc[-1]
            var = ((v_act - d_idx['Close'].iloc[-2]) / d_idx['Close'].iloc[-2]) * 100
            cols[i].metric(nom, f"{v_act:,.2f}", f"{var:+.2f}%")
            if cols[i].button(f"Zoom {nom}", key=tk): st.session_state.idx_sel = tk

    st.markdown("---")
    hist_m = yf.Ticker(st.session_state.idx_sel).history(period="1mo", interval="1d")
    fig = go.Figure(data=[go.Scatter(x=hist_m.index, y=hist_m['Close'], fill='tozeroy', line=dict(color='#00d1ff'))])
    fig.update_layout(template="plotly_dark", height=450, yaxis_side="right")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# OUTILS SUPPLEMENTAIRES (TES SCRIPTS ADDITIONNELS)
# ==========================================
elif outil == "🔍 Screener CAC40":
    st.title("🔍 Screener Expert CAC 40")
    if st.button("🚀 Lancer le Scan"):
        actions = ["AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EL.PA", "STLAP.PA", "RMS.PA", "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "SW.PA", "STMPA.PA", "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"]
        res = []
        p = st.progress(0)
        for i, t in enumerate(actions):
            try:
                inf = yf.Ticker(t).info
                bpa = inf.get('trailingEps', 0)
                px = inf.get('currentPrice', 1)
                val = (max(0, bpa) * 22.5 * 4.4) / 3.5
                pot = ((val - px) / px) * 100
                res.append({"Ticker": t, "Nom": inf.get('shortName', t), "Potentiel": f"{pot:.1f}%", "Score": 10 + (5 if pot > 30 else 0)})
            except: pass
            p.progress((i + 1) / len(actions))
        st.table(pd.DataFrame(res).sort_values(by="Score", ascending=False))

elif outil == "😨 Fear & Greed":
    st.title("🔍 Sentiment Fear & Greed")
    marches = {"^GSPC": "USA (S&P 500)", "^FCHI": "EUROPE (CAC 40)", "BTC-USD": "Bitcoin"}
    for tk, nom in marches.items():
        d = yf.Ticker(tk).history(period="1y")
        ma200 = d['Close'].rolling(window=200).mean().iloc[-1]
        r = (d['Close'].iloc[-1] / ma200) - 1
        txt, col = ("GREED 🚀", "#2ecc71") if r > 0.05 else (("FEAR 💀", "#e74c3c") if r < -0.05 else ("NEUTRAL ⚖️", "#f1c40f"))
        st.markdown(f"### {nom} : <span style='color:{col}'>{txt}</span>", unsafe_allow_html=True)

elif outil == "💰 Simulateur Intérêts":
    st.title("💰 Simulateur d'Intérêts Composés")
    c1, c2 = st.columns(2)
    cap = c1.number_input("Départ (€)", value=1000)
    mens = c1.number_input("Mensuel (€)", value=100)
    tx = c2.number_input("Taux (%)", value=8.0)
    ans = c2.number_input("Ans", value=10)
    total = cap
    for i in range(ans * 12): total = (total + mens) * (1 + (tx/100/12))
    st.success(f"Somme finale : {total:,.2f} €")
