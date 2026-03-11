# ============================================================
#  chart_module — AM Trading
#  Graphique uPlot modulaire (remplace TradingView)
#
#  UTILISATION DANS STREAMLIT :
#  ─────────────────────────────
#  from chart_module import render_chart
#  import streamlit.components.v1 as components
#
#  html = render_chart(symbol="BTCUSDT", interval="4h")
#  components.html(html, height=600)
# ============================================================

from .chart import render_chart
# quant/__init__.py
from .monte_carlo import estimate_params, merton_jd

__all__ = ["estimate_params", "merton_jd", "render_chart"]



def test_coingecko():
    """
    Lance ce test dans ton terminal pour vérifier si CoinGecko fonctionne :
        from chart_module import test_coingecko
        test_coingecko()
    """
    import requests
    print("[test] Connexion à CoinGecko...")
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc",
            params={"vs_currency": "usd", "days": 1},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            print(f"[test] ✅ CoinGecko OK — {len(data)} bougies reçues")
            print(f"[test] Dernière bougie : {data[-1]}")
            print("[test] → Mettre DATA_SOURCE = 'coingecko' dans config.py")
        else:
            print(f"[test] ⚠️  CoinGecko répond mais données vides : {data}")
    except requests.exceptions.ConnectionError:
        print("[test] ❌ Connexion impossible — vérifier le réseau")
    except requests.exceptions.HTTPError as e:
        print(f"[test] ❌ Erreur HTTP {e.response.status_code} — rate limit?")
        if e.response.status_code == 429:
            print("[test] → Trop de requêtes, attendre 1 minute")
    except Exception as e:
        print(f"[test] ❌ Erreur : {e}")

