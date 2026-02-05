import yfinance as yf
from datetime import datetime
import os
import time

# Couleurs pour ton terminal noir
G = '\033[92m'  # Vert
R = '\033[91m'  # Rouge
Y = '\033[93m'  # Jaune
B = '\033[94m'  # Bleu
W = '\033[0m'   # Reset

def biper_alerte():
    # Son système Mac
    os.system('afplay /System/Library/Sounds/Glass.aiff')

def analyser_bourse_reunion():
    maintenant = datetime.now()
    h = maintenant.hour

    os.system('clear')
    print(f"🌍 {B}MARKET MONITOR UTC+4{W} | 🕒 {maintenant.strftime('%H:%M:%S')}")
    
    # 1. TABLEAU DES HORAIRES (UTC+4)
    print("="*60)
    print(f"{Y}SESSION          OUVERTURE (REU)   FERMETURE (REU){W}")
    print(f"CHINE (HK)       05:30             12:00")
    print(f"EUROPE (PARIS)   12:00             20:30")
    print(f"USA (NY)         18:30             01:00")
    print("="*60)

    indices = {
        "^HSI":   ["Chine (Hong Kong)", 5, 12],
        "^FCHI":  ["France (CAC 40)", 12, 20],
        "^GDAXI": ["Allemagne (DAX)", 12, 20],
        "^GSPC":  ["USA (S&P 500)", 19, 1] # Fermeture à 01h00 REU
    }

    alertes_actives = []

    for ticker, info in indices.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) < 2: continue

            prix_actuel = hist['Close'].iloc[-1]
            prix_open = hist['Open'].iloc[-1]
            cloture_veille = hist['Close'].iloc[-2]

            var_veille = ((prix_actuel - cloture_veille) / cloture_veille) * 100
            var_session = ((prix_actuel - prix_open) / prix_open) * 100

            if abs(var_veille) >= 2.0:
                biper_alerte()
                alertes_actives.append(f"⚠️ MOUVEMENT FORT SUR {info[0]}")

            # Statut de session (UTC+4)
            ouvert = False
            if ticker == "^HSI" and 5 <= h < 12: ouvert = True
            elif (ticker == "^FCHI" or ticker == "^GDAXI") and 12 <= h < 20: ouvert = True
            elif ticker == "^GSPC" and (h >= 19 or h < 1): ouvert = True
            
            statut = f"{G}● OUVERT{W}" if ouvert else f"{R}○ FERMÉ{W}"
            c_v = G if var_veille > 0 else R
            c_s = G if var_session > 0 else R

            print(f"{B}{info[0]:<20}{W} | {statut}")
            print(f"   Prix : {prix_actuel:,.2f} | Veille : {c_v}{var_veille:>+6.2f}%{W} | Session : {c_s}{var_session:>+6.2f}%{W}")
            print("-" * 45)

        except Exception:
            print(f"❌ Erreur de connexion : {info[0]}")

    # --- FOCUS SECTEURS USA ---
    print(f"\n⚡ {Y}MOTEURS DU MARCHÉ (Secteurs USA){W}")
    secteurs = {"XLK": "Tech", "XLF": "Finance", "XLE": "Énergie"}
    for tk, nom in secteurs.items():
        try:
            s_data = yf.Ticker(tk).history(period="1d")
            if not s_data.empty:
                s_o = s_data['Open'].iloc[-1]
                s_c = s_data['Close'].iloc[-1]
                s_v = ((s_c - s_o) / s_o) * 100
                print(f"   {nom:<8}: {G if s_v > 0 else R}{s_v:>+5.2f}%{W}", end=" ")
        except:
            pass

    # --- NOTES ET CONSEILS STRATÉGIQUES ---
    print("\n\n" + "="*60)
    print(f"💡 {B}CONSEILS DE SESSION (UTC+4){W}")
    if 5 <= h < 12:
        print(f"- {Y}Chine{W} : Surveille la clôture de HK, elle impacte l'ouverture de midi.")
    elif 12 <= h < 19:
        print(f"- {Y}Europe{W} : Observe le DAX. S'il ne suit pas le CAC, la hausse est suspecte.")
        print("- Le 'Gap' de midi est souvent testé avant l'arrivée des Américains.")
    elif h >= 19 or h < 2:
        print(f"- {Y}USA{W} : C'est le 'Prime Time'. Regarde si la Tech (XLK) tire le marché.")
        print("- Wall Street ferme à 01h00 (REU). La dernière heure est souvent volatile.")
    
    if alertes_actives:
        print("-" * 20)
        for alerte in alertes_actives:
            print(f"{R}{alerte}{W}")

    print("\n" + "="*60)
    print(f"Actualisation dans 60s... (Ctrl+C pour quitter)")

if __name__ == "__main__":
    while True:
        analyser_bourse_reunion()
        time.sleep(60)
