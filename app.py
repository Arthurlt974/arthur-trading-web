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
# OUTIL 1 : ANALYSEUR PRO (Version Finale Conclue)
# ==========================================
if outil == "📊 Analyseur Pro":
    nom_entree = st.sidebar.text_input("Nom de l'action", value="MC.PA")
    ticker = trouver_ticker(nom_entree)
    action = yf.Ticker(ticker)
    info = action.info

    if info and ('currentPrice' in info or 'regularMarketPrice' in info):
        # Récupération Robuste
        nom = info.get('longName') or info.get('shortName') or ticker
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        devise = info.get('currency', 'EUR')
        secteur = info.get('sector', 'N/A')
        bpa = info.get('trailingEps') or info.get('forwardEps') or 0
        
        per = info.get('trailingPE')
        if not per and bpa > 0: per = prix / bpa
        per = per or 0

        dette_equity = info.get('debtToEquity')
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare') or 0

        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        marge_pourcent = ((val_theorique - prix) / prix) * 100 if prix > 0 else 0

        st.title(f"📊 {nom} ({ticker})")

        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Prix Actuel", f"{prix:.2f} {devise}")
        c2.metric("Valeur Graham", f"{val_theorique:.2f} {devise}")
        c3.metric("Potentiel", f"{marge_pourcent:+.2f}%")
        c4.metric("Secteur", secteur)

        st.markdown("---")
        mode_graph = st.radio("Style de graphique :", ["Débutant (Ligne)", "Pro (Bougies)"], horizontal=True)

        col_graph, col_data = st.columns([2, 1])
        with col_graph:
            if mode_graph == "Pro (Bougies)":
                choix_int = st.selectbox("Unité de la bougie :", ["90m", "1d", "1wk", "1mo"], index=1)
                p = {"90m": "1mo", "1d": "5y", "1wk": "max", "1mo": "max"}[choix_int]
                hist = action.history(period=p, interval=choix_int)
                fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], increasing_line_color='#2ecc71', decreasing_line_color='#e74c3c')])
            else:
                hist = action.history(period="5y")
                fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'], fill='tozeroy', line=dict(color='#00d1ff'))])
            
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=10, t=0, b=0), xaxis_rangeslider_visible=False, yaxis_side="right")
            st.plotly_chart(fig, use_container_width=True)

        with col_data:
            st.subheader("📑 Détails Financiers")
            st.write(f"**BPA (EPS) :** {bpa:.2f} {devise}")
            st.write(f"**Ratio P/E :** {per:.2f}")
            st.write(f"**Dette/Equity :** {dette_equity if dette_equity is not None else 'N/A'} %")
            st.write(f"**Rendement Div. :** {(div_rate/prix*100 if prix>0 else 0):.2f} %")
            st.write(f"**Payout Ratio :** {payout:.2f} %")
            st.write(f"**Cash/Action :** {cash_action:.2f} {devise}")

        # Scoring
        st.markdown("---")
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
            elif dette_equity < 100: score += 3; positifs.append("✅ Dette maîtrisée [+3]")
            elif dette_equity > 200: score -= 4; negatifs.append("❌ Surendettement [-4]")

        if 10 < payout <= 80: score += 4; positifs.append("✅ Dividende solide/safe [+4]")
        elif payout > 95: score -= 4; negatifs.append("🚨 Payout Ratio risqué [-4]")
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
# OUTIL 2 : MODE DUEL (Fusion de Duel V2.py)
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
        m1, m2 = ((d1['valeur']-d1['prix'])/d1['prix']), ((d2['valeur']-d2['prix'])/d2['prix'])
        gagnant = d1['nom'] if m1 > m2 else d2['nom']
        st.success(f"🏆 Gagnant sur la marge de sécurité : {gagnant}")

# ==========================================
# OUTIL 3 : MARKET MONITOR (Version Session.py Complète)
# ==========================================
elif outil == "🌍 Market Monitor":
    st.title("🌍 Market Monitor (UTC+4)")
    maintenant = datetime.now()
    h = maintenant.hour
    
    st.write(f"🕒 **Heure Réunion :** {maintenant.strftime('%H:%M:%S')}")

    # 1. TABLEAU DES HORAIRES (Inspiré de Session.py)
    st.markdown("### 🕒 Statut des Bourses")
    data_horaires = {
        "Session": ["CHINE (HK)", "EUROPE (PARIS)", "USA (NY)"],
        "Ouverture (REU)": ["05:30", "12:00", "18:30"],
        "Fermeture (REU)": ["12:00", "20:30", "01:00"],
        "Statut": [
            "🟢 OUVERT" if 5 <= h < 12 else "🔴 FERMÉ",
            "🟢 OUVERT" if 12 <= h < 20 else "🔴 FERMÉ",
            "🟢 OUVERT" if (h >= 18 or h < 1) else "🔴 FERMÉ"
        ]
    }
    st.table(pd.DataFrame(data_horaires))

    # 2. INDICES MAJEURS AVEC VARIATION
    st.markdown("---")
    st.subheader("⚡ Moteurs du Marché")
    indices = {"^FCHI": "CAC 40", "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "BTC-USD": "Bitcoin"}
    cols = st.columns(len(indices))
    
    for i, (tk, nom) in enumerate(indices.items()):
        try:
            # Récupération sur 2 jours pour avoir la variation
            data_idx = yf.Ticker(tk).history(period="2d")
            if not data_idx.empty:
                val_actuelle = data_idx['Close'].iloc[-1]
                val_prec = data_idx['Close'].iloc[-2]
                variation = ((val_actuelle - val_prec) / val_prec) * 100
                cols[i].metric(nom, f"{val_actuelle:,.2f}", f"{variation:+.2f}%")
        except:
            cols[i].write(f"{nom} : N/A")

    # 3. CONSEILS STRATÉGIQUES (Exactement comme ton Session.py)
    st.markdown("---")
    st.subheader("💡 Conseils de Session (UTC+4)")
    if 5 <= h < 12:
        st.warning("**Chine (HK)** : Surveille la clôture de Hong Kong, elle impacte souvent l'ouverture de Paris à midi.")
    elif 12 <= h < 19:
        st.info("**Europe (Paris)** : Observe le DAX. S'il ne suit pas le CAC, la hausse est suspecte. Le 'Gap' de midi est souvent testé avant l'arrivée des Américains.")
    elif h >= 19 or h < 2:
        st.success("**USA (NY)** : C'est le gros volume. Regarde le NASDAQ pour la Tech. Attention aux retournements de tendance après 22h (Réunion).")
    else:
        st.write("🌑 **Session Nocturne** : Les marchés majeurs sont fermés. Analyse les clôtures US et prépare ta watchlist pour demain.")

    st.markdown("---")
    st.caption("Note : Les horaires et conseils sont calibrés pour le fuseau de l'île de la Réunion.")
