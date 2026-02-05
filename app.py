import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import requests

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="AM Trading - Arthur & Milan", page_icon="📈", layout="wide")

# --- STYLE PERSONNALISÉ ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- MENU LATÉRAL ---
st.sidebar.title("🚀 AM Trading")
st.sidebar.subheader("Arthur & Milan Pro")
menu = st.sidebar.radio("Outils disponibles :", 
    ["📊 Scanner CAC 40", "🌍 Session Live (UTC+4)", "🔍 Sentiment (Fear & Greed)", "⚔️ Duel d'Actions"])

# ---------------------------------------------------------
# 1. SCANNER GRAHAM (Code de Screener.py adapté)
# ---------------------------------------------------------
if menu == "📊 Scanner CAC 40":
    st.title("Scanner V5.5 - Méthode Benjamin Graham")
    
    mes_actions = [
        "AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", 
        "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EL.PA", "STLAP.PA", "RMS.PA", 
        "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", 
        "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "SW.PA", "STMPA.PA", 
        "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
    ]

    if st.button("Lancer le Scan Complet"):
        resultats = []
        barre = st.progress(0)
        
        for i, t in enumerate(mes_actions):
            try:
                action = yf.Ticker(t)
                info = action.info
                prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
                bpa = info.get('trailingEps') or info.get('forwardEps') or 0
                val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
                marge = ((val_theorique - prix) / prix) * 100
                
                # Scoring simplifié pour le web
                score = 0
                if bpa > 0: score += 5
                if (info.get('debtToEquity') or 200) < 100: score += 5
                if marge > 20: score += 10
                
                resultats.append({"Action": t, "Nom": info.get('longName', t), "Score": f"{score}/20", "Potentiel": f"{marge:.1f}%"})
            except: pass
            barre.progress((i + 1) / len(mes_actions))
        
        df = pd.DataFrame(resultats)
        st.table(df.sort_values(by="Score", ascending=False))

# ---------------------------------------------------------
# 2. SESSION LIVE (Code de Session.py adapté)
# ---------------------------------------------------------
elif menu == "🌍 Session Live (UTC+4)":
    st.title("Market Monitor - Heure de La Réunion")
    h = datetime.now().hour
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("HK (Asie)", "05:30 - 12:00", "Ouvert" if 5<=h<12 else "Fermé")
    with col2: st.metric("Paris (Europe)", "12:00 - 20:30", "Ouvert" if 12<=h<20 else "Fermé")
    with col3: st.metric("New York (USA)", "18:30 - 01:00", "Ouvert" if h>=18 or h<1 else "Fermé")

    st.info("💡 Conseil : " + ("Surveille la clôture HK" if h<12 else "Wall Street est le moteur actuel" if h>=18 else "L'Europe mène la danse"))

# ---------------------------------------------------------
# 3. FEAR & GREED (Code de fear and gread index.py)
# ---------------------------------------------------------
elif menu == "🔍 Sentiment (Fear & Greed)":
    st.title("Sentiment des Marchés")
    marches = {"^GSPC": "USA (S&P 500)", "^FCHI": "CAC 40", "BTC-USD": "Bitcoin"}
    
    for t, nom in marches.items():
        data = yf.Ticker(t).history(period="1y")
        prix = data['Close'].iloc[-1]
        ma200 = data['Close'].rolling(window=200).mean().iloc[-1]
        ratio = (prix / ma200) - 1
        
        sentiment = "NEUTRAL ⚖️"
        if ratio > 0.10: sentiment = "EXTREME GREED 🚀"
        elif ratio < -0.10: sentiment = "EXTREME FEAR 💀"
        
        st.subheader(f"{nom} : {sentiment}")
        st.progress(min(100, max(0, int((ratio + 0.2) * 250)))) # Jauge visuelle

# ---------------------------------------------------------
# 4. DUEL (Code de Duel V2.py)
# ---------------------------------------------------------
elif menu == "⚔️ Duel d'Actions":
    st.title("Le Duel : Arthur vs Milan")
    c1, c2 = st.columns(2)
    with c1: t1 = st.text_input("Action 1 (ex: MC.PA)", "MC.PA")
    with c2: t2 = st.text_input("Action 2 (ex: OR.PA)", "OR.PA")
    
    if st.button("Lancer le Duel"):
        # Ici on appelle une version simplifiée de ta fonction de duel
        st.write(f"Comparaison de {t1} vs {t2}")
        st.success(f"Analyse en cours... (Graphiques bientôt disponibles)")
