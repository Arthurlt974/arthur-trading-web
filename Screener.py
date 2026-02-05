import yfinance as yf
import time
import os

def obtenir_score_expert(ticker):
    try:
        action = yf.Ticker(ticker)
        info = action.info
        
        # --- RÉCUPÉRATION AVEC SÉCURITÉ ---
        prix = info.get('currentPrice') or info.get('regularMarketPrice') or 1
        
        # Sécurité BPA (Bénéfice par action actuel ou prévisionnel)
        bpa_actuel = info.get('trailingEps') or 0
        bpa_prev = info.get('forwardEps') or 0
        bpa = bpa_actuel if bpa_actuel > 0 else bpa_prev
        
        per = info.get('trailingPE') or (prix / bpa if bpa > 0 else 50)
        dette_equity = info.get('debtToEquity')
        payout = (info.get('payoutRatio') or 0) * 100
        cash_action = info.get('totalCashPerShare', 0)

        # --- CALCUL VALEUR (AVEC LIMITES) ---
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        
        # Plafond de sécurité à 250% du prix (soit +150% de potentiel)
        if val_theorique > prix * 2.5:
            val_theorique = prix * 2.5
            
        marge_pourcent = ((val_theorique - prix) / prix) * 100
        
        # --- SCORING SUR 20 ---
        score = 0
        
        # 1. Rentabilité (5 pts)
        if bpa > 0:
            if per < 15: score += 5
            elif per < 25: score += 3
            else: score += 1

        # 2. Dette (5 pts)
        if dette_equity is not None:
            if dette_equity < 60: score += 5
            elif dette_equity < 120: score += 3
            elif dette_equity > 200: score -= 2

        # 3. Dividende (4 pts)
        if 5 < payout <= 85: score += 4
        elif 0 < payout <= 5: score += 1

        # 4. Marge Graham (6 pts)
        if marge_pourcent > 50: score += 6
        elif marge_pourcent > 15: score += 4
        elif marge_pourcent < -10: score -= 2
            
        # 5. Bonus Cash
        if cash_action > (prix * 0.15): score += 2

        score = min(20, max(0, score))
        return score, info.get('longName', ticker), marge_pourcent
    except:
        return -1, "Erreur", 0

def mode_screener():
    mes_actions = [
        "AC.PA", "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", 
        "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EL.PA", "STLAP.PA", "RMS.PA", 
        "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", 
        "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "SW.PA", "STMPA.PA", 
        "TEP.PA", "HO.PA", "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
    ]

    os.system('clear' if os.name == 'posix' else 'cls')
    print("\n" + "📊 " * 10)
    print(f"LANCEMENT DU SCANNER V5.5")
    print(f"Analyse de {len(mes_actions)} actions en cours...")
    print("📊 " * 10 + "\n")
    
    resultats = []
    for t in mes_actions:
        # Affichage ligne par ligne au fur et à mesure
        print(f"🔄 Analyse en cours : {t:<8} ...", end=" ", flush=True)
        
        score, nom, marge = obtenir_score_expert(t)
        
        if score != -1:
            print(f"✅ Terminé ({score}/20)")
            resultats.append((score, t, nom, marge))
        else:
            print(f"❌ Échec")
            
        time.sleep(0.1) # Rapidité augmentée

    # Tri final
    resultats.sort(key=lambda x: x[0], reverse=True)

    print("\n\n" + "="*75)
    print(f"{'RANG':<4} | {'TICKER':<9} | {'SCORE':<7} | {'POTENTIEL':<10} | {'NOM'}")
    print("-" * 75)
    
    # Couleurs terminal
    G = "\033[92m" 
    Y = "\033[93m" 
    R = "\033[91m" 
    W = "\033[0m"  

    for i, (score, t, nom, marge) in enumerate(resultats, 1):
        color = G if score >= 14 else Y if score >= 8 else R
        marge_str = f"{marge:>+7.1f}%"
        print(f"{i:<4} | {t:<9} | {color}{score:>2}/20{W} | {marge_str} | {nom[:25]}")
    
    print("="*75)

if __name__ == "__main__":
    mode_screener()
