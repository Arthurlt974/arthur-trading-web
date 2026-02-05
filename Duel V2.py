import yfinance as yf
import requests

def trouver_ticker(nom):
    """Traduit un nom en Ticker (ex: LVMH -> MC.PA)"""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={nom}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers).json()
        return response['quotes'][0]['symbol'] if response.get('quotes') else nom
    except: return nom

def formater_nom(nom):
    return (nom[:18] + '..') if len(nom) > 20 else nom

def recuperer_donnees(entree):
    try:
        # On cherche le ticker à partir de ce que tu as écrit
        ticker = trouver_ticker(entree)
        action = yf.Ticker(ticker)
        info = action.info
        if not info or 'currentPrice' not in info: return None
        
        prix = info.get('currentPrice')
        bpa = info.get('trailingEps', 0)
        div_cash = info.get('dividendRate', 0)
        
        rendement = (div_cash / prix * 100) if (div_cash and prix) else (info.get('dividendYield', 0) * 100)
        val_theorique = (max(0, bpa) * (8.5 + 2 * 7) * 4.4) / 3.5
        
        return {
            "nom": info.get('longName', ticker),
            "prix": prix,
            "valeur": val_theorique,
            "dette": info.get('debtToEquity', 1000),
            "rendement": rendement,
            "payout": info.get('payoutRatio', 0) * 100,
            "devise": info.get('currency', '$')
        }
    except: return None

def mode_duel():
    print("\n" + "⚔️  " * 20)
    # Tu peux maintenant taper "LVMH" ou "Hermes" ici
    t1 = input("Action n°1 : ").upper()
    t2 = input("Action n°2 : ").upper()
    
    d1, d2 = recuperer_donnees(t1), recuperer_donnees(t2)
    if not d1 or not d2:
        print("❌ Erreur : Impossible de récupérer l'un des tickers."); return

    m1 = ((d1['valeur'] - d1['prix']) / d1['valeur'] * 100) if d1['valeur'] > 0 else -100
    m2 = ((d2['valeur'] - d2['prix']) / d2['valeur'] * 100) if d2['valeur'] > 0 else -100

    print(f"\n{'COMPARATIF':<20} | {formater_nom(d1['nom']):<18} | {formater_nom(d2['nom']):<18}")
    print("-" * 65)
    
    med1 = lambda c1, c2, inv=False: "🥇" if (c1 > c2 if not inv else c1 < c2) else "  "
    med2 = lambda c1, c2, inv=False: "🥇" if (c2 > c1 if not inv else c2 < c1) else "  "

    print(f"{'Prix Actuel':<20} | {d1['prix']:>8.2f} {d1['devise']}      | {d2['prix']:>8.2f} {d2['devise']}")
    print(f"{'Valeur Théorique':<20} | {d1['valeur']:>8.2f} {d1['devise']}      | {d2['valeur']:>8.2f} {d2['devise']}")
    print(f"{'Marge Sécurité':<20} | {m1:>7.1f}% {med1(m1,m2)} | {m2:>7.1f}% {med2(m1,m2)}")
    print(f"{'Dette (Ratio)':<20} | {d1['dette']:>7.1f}% {med1(d1['dette'],d2['dette'],True)} | {d2['dette']:>7.1f}% {med2(d1['dette'],d2['dette'],True)}")
    print(f"{'Rendement Div.':<20} | {d1['rendement']:>7.1f}% {med1(d1['rendement'],d2['rendement'])} | {d2['rendement']:>7.1f}% {med2(d1['rendement'],d2['rendement'])}")
    print(f"{'Sécurité Payout':<20} | {d1['payout']:>7.1f}% {med1(d1['payout'],d2['payout'],True)} | {d2['payout']:>7.1f}% {med2(d1['payout'],d2['payout'],True)}")
    print("-" * 65)

    pts1 = 0
    if m1 > m2: pts1 += 1
    if d1['dette'] < d2['dette']: pts1 += 1
    if d1['rendement'] > d2['rendement']: pts1 += 1
    if d1['payout'] < d2['payout']: pts1 += 1
    
    nom_v = d1['nom'] if pts1 >= 2 else d2['nom']
    print(f"\n🏆 VERDICT : Selon les critères fondamentaux, {nom_v} remporte ce duel !")

if __name__ == "__main__":
    while True:
        mode_duel()
        if input("\nLancer un autre duel ? (o/n) : ").lower() != 'o':
            break
