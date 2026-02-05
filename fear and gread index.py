import yfinance as yf
import os
import time
from datetime import datetime

# Couleurs pour ton terminal noir
G = '\033[92m'  # Greed
R = '\033[91m'  # Fear
Y = '\033[93m'  # Neutral
B = '\033[94m'  # Blue
W = '\033[0m'   # Reset

def calculer_sentiment(ticker):
    try:
        # Récupération des données sur 1 an pour la Moyenne Mobile 200
        data = yf.Ticker(ticker).history(period="1y")
        if len(data) < 200: 
            return "DONNÉES INSUFFISANTES", Y
        
        prix_actuel = data['Close'].iloc[-1]
        ma200 = data['Close'].rolling(window=200).mean().iloc[-1]
        
        # Calcul de l'écart (Ratio)
        ratio = (prix_actuel / ma200) - 1
        
        # Logique Fear & Greed
        if ratio > 0.10: 
            return "EXTREME GREED 🚀🚀", G
        elif 0.03 < ratio <= 0.10: 
            return "GREED 📈", G
        elif -0.03 <= ratio <= 0.03: 
            return "NEUTRAL ⚖️", Y
        elif -0.10 <= ratio < -0.03: 
            return "FEAR 📉", R
        else: 
            return "EXTREME FEAR 💀💀", R
    except Exception:
        return "ERREUR CONNEXION", W

def afficher_fear_greed():
    os.system('clear' if os.name == 'posix' else 'cls')
    maintenant = datetime.now()
    
    print(f"🔍 {B}SENTIMENT DES MARCHÉS MONDIAUX (Fear & Greed){W}")
    print(f"🕒 Mis à jour à : {maintenant.strftime('%H:%M:%S')} (Heure Réunion)")
    print("="*60)
    print(f"{'MARCHÉ / INDICE':<25} | {'SENTIMENT ACTUEL':<20}")
    print("-" * 60)

    marches = {
        "^GSPC": "USA (S&P 500)",
        "^FCHI": "EUROPE (CAC 40)",
        "^HSI":  "ASIE (Hong Kong)",
        "BTC-USD": "CRYPTO (Bitcoin)",
        "GC=F": "OR (Métal Précieux)"
    }

    for ticker, nom in marches.items():
        label, couleur = calculer_sentiment(ticker)
        print(f"{nom:<25} | {couleur}{label}{W}")

    print("-" * 60)
    print(f"\n💡 {Y}Interprétation stratégique :{W}")
    print(f"- {R}Extreme Fear{W}  : Panique. Souvent un signal d'achat long terme.")
    print(f"- {G}Extreme Greed{W} : Euphorie. Attention aux retournements brutaux.")
    
    print(f"\n{B}Actualisation toutes les heures...{W} (Ctrl+C pour arrêter)")

if __name__ == "__main__":
    while True:
        afficher_fear_greed()
        time.sleep(3600)
