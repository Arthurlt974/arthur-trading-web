# ============================================================
#  chart_module/data.py
#  CoinGecko par défaut — fallback mock automatique
# ============================================================

import time
import random
from .config import DATA_SOURCE, DEFAULT_LIMIT, FALLBACK_TO_MOCK, COINGECKO_IDS


def _is_stock(symbol: str) -> bool:
    """Détecte si le symbole est une action (pas une crypto).
    Logique : pas de suffixe USDT/BTC, pas dans la liste crypto connue,
    et ressemble à un ticker boursier (lettres + éventuellement .PA, .L, etc.)
    """
    s = symbol.upper().strip()
    # Suffixes crypto évidents
    if s.endswith("USDT") or s.endswith("BUSD") or s.endswith("BTC") or s.endswith("ETH"):
        return False
    # Suffixes yfinance boursiers
    if "." in s:  # AAPL, MC.PA, BNP.PA, TSLA, etc.
        return True
    # Cryptos connues (symboles courts)
    known_cryptos = {
        "BTC","ETH","SOL","XRP","ADA","DOT","AVAX","DOGE","MATIC","LINK",
        "UNI","ATOM","LTC","BCH","NEAR","FTM","SAND","MANA","AAVE","CRV",
        "BNB","TRX","SHIB","PEPE","TON","SUI","APT","ARB","OP","INJ",
        "BITCOIN","ETHEREUM","SOLANA","RIPPLE","CARDANO","POLKADOT",
    }
    if s in known_cryptos:
        return False
    # Si ça ressemble à un ticker US (2-5 lettres majuscules sans chiffres) → action
    import re
    if re.match(r'^[A-Z]{1,5}$', s):
        return True
    return False


def fetch_ohlcv(symbol: str, interval: str, limit: int = DEFAULT_LIMIT) -> tuple[list[dict], bool]:
    """
    Retourne (candles, is_live).
    candles  : [{t, o, h, l, c, v}, ...]
    is_live  : True si données réelles
    Auto-détecte les actions et route vers yfinance.
    """
    src = DATA_SOURCE.lower()

    # ── Auto-routing : si c'est une action → yfinance direct ──
    if _is_stock(symbol) and src not in ("yfinance",):
        print(f"[chart_module] {symbol} détecté comme action → yfinance")
        try:
            return _from_yfinance(symbol, interval, limit), True
        except Exception as e:
            print(f"[chart_module] yfinance erreur ({symbol}): {e}")
            if FALLBACK_TO_MOCK:
                return _mock(symbol, interval, limit), False
            raise

    try:
        if src == "coingecko":
            return _from_coingecko(symbol, interval, limit), True
        elif src == "binance":
            return _from_binance(symbol, interval, limit), True
        elif src == "bybit":
            return _from_bybit(symbol, interval, limit), True
        elif src == "yfinance":
            return _from_yfinance(symbol, interval, limit), True
        elif src == "kraken":
            return _from_kraken(symbol, interval, limit), True
        else:
            return _mock(symbol, interval, limit), False

    except Exception as e:
        print(f"[chart_module] Erreur {src} ({symbol} {interval}): {e}")
        if FALLBACK_TO_MOCK:
            print(f"[chart_module] → Fallback mock")
            return _mock(symbol, interval, limit), False
        raise


# ── COINGECKO (défaut) ───────────────────────────────────
# Endpoint OHLC : /coins/{id}/ohlc?vs_currency=usd&days=N
# Endpoint market_chart pour le volume : /coins/{id}/market_chart
#
# Correspondance interval → jours CoinGecko :
#   1h  → days=2   (granularité 1h auto si days<=90)
#   4h  → days=30  (granularité 4h auto si days<=30... en pratique 1h)
#   1d  → days=365
#   7d  → days=max
#
# NOTE : CoinGecko OHLC donne des bougies de 30min, 4h ou 4j
#        selon la plage demandée. On adapte le découpage.
#
# CoinGecko ID : "bitcoin", "ethereum", "solana"...
# Pour les symboles courts (BTC, ETH...) → table COINGECKO_IDS dans config.py

def _resolve_id(symbol: str) -> str:
    """Convertit BTC / BTCUSDT / bitcoin → ID CoinGecko."""
    s = symbol.upper().replace("USDT","").replace("USD","").replace("-","")
    return COINGECKO_IDS.get(s, symbol.lower())

def _coingecko_days(interval: str) -> int:
    return {
        "1m": 1, "5m": 1, "15m": 1, "30m": 2,
        "1h": 7, "4h": 30, "1d": 365, "7d": 1825,
    }.get(interval.lower(), 30)

def _from_coingecko(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests

    coin_id = _resolve_id(symbol)
    days    = _coingecko_days(interval)

    headers = {
        "User-Agent": "Mozilla/5.0 (Arthur-Trading-Chart/1.0)",
        "Accept":     "application/json",
    }

    # ── 1. OHLC (Open/High/Low/Close) ──
    ohlc_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    r_ohlc   = requests.get(ohlc_url,
        params={"vs_currency": "usd", "days": days},
        headers=headers, timeout=15)
    r_ohlc.raise_for_status()
    ohlc_raw = r_ohlc.json()

    if not isinstance(ohlc_raw, list) or len(ohlc_raw) == 0:
        raise ValueError(f"CoinGecko OHLC vide pour {coin_id}")

    # ── 2. VOLUME (market_chart) ──
    vol_url  = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    try:
        r_vol    = requests.get(vol_url,
            params={"vs_currency": "usd", "days": days},
            headers=headers, timeout=15)
        vol_data = r_vol.json().get("total_volumes", [])
        # Construire dict timestamp→volume
        vol_map  = {int(v[0])//1000: float(v[1]) for v in vol_data}
    except Exception:
        vol_map  = {}

    # ── 3. Assembler les candles ──
    candles = []
    for row in ohlc_raw[-limit:]:
        # row = [timestamp_ms, open, high, low, close]
        ts = int(row[0]) // 1000
        # Chercher le volume le plus proche
        vol = 0.0
        if vol_map:
            closest = min(vol_map.keys(), key=lambda k: abs(k-ts))
            if abs(closest - ts) < 14400:   # moins de 4h d'écart
                vol = vol_map[closest]
        candles.append({
            "t": ts,
            "o": float(row[1]),
            "h": float(row[2]),
            "l": float(row[3]),
            "c": float(row[4]),
            "v": vol,
        })

    return candles


# ── BINANCE ──────────────────────────────────────────────
_BINANCE_IV = {
    "1m":"1m","5m":"5m","15m":"15m","30m":"30m",
    "1h":"1h","4h":"4h","1d":"1d","1w":"1w",
}

def _from_binance(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests
    iv = _BINANCE_IV.get(interval.lower(), interval)
    r  = requests.get("https://api.binance.com/api/v3/klines",
        params={"symbol":symbol.upper(),"interval":iv,"limit":min(limit,1000)},
        headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data,list) or not data:
        raise ValueError("Binance: réponse vide")
    return [{"t":int(c[0])//1000,"o":float(c[1]),"h":float(c[2]),
             "l":float(c[3]),"c":float(c[4]),"v":float(c[5])} for c in data]


# ── BYBIT ────────────────────────────────────────────────
_BYBIT_IV = {
    "1m":"1","5m":"5","15m":"15","30m":"30",
    "1h":"60","4h":"240","1d":"D","1w":"W",
}

def _from_bybit(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests
    iv = _BYBIT_IV.get(interval.lower(),"240")
    r  = requests.get("https://api.bybit.com/v5/market/kline",
        params={"category":"spot","symbol":symbol.upper(),
                "interval":iv,"limit":min(limit,1000)}, timeout=15)
    r.raise_for_status()
    raw = r.json()
    if raw.get("retCode",1)!=0:
        raise ValueError(f"Bybit: {raw.get('retMsg')}")
    return [{"t":int(c[0])//1000,"o":float(c[1]),"h":float(c[2]),
             "l":float(c[3]),"c":float(c[4]),"v":float(c[5])}
            for c in reversed(raw["result"]["list"])]


# ── YFINANCE ─────────────────────────────────────────────
def _from_yfinance(symbol: str, interval: str, limit: int) -> list[dict]:
    import yfinance as yf
    _period = {"1m":"7d","5m":"60d","15m":"60d","30m":"60d",
               "1h":"730d","4h":"730d","1d":"5y","1w":"10y"}
    df = yf.download(symbol, period=_period.get(interval.lower(),"60d"),
                     interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError(f"yFinance: vide pour {symbol}")
    if hasattr(df.columns,"get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df.tail(limit).reset_index()
    ts  = "Datetime" if "Datetime" in df.columns else "Date"
    out = []
    for _,row in df.iterrows():
        try:
            out.append({"t":int(row[ts].timestamp()),
                "o":float(row["Open"]), "h":float(row["High"]),
                "l":float(row["Low"]),  "c":float(row["Close"]),
                "v":float(row.get("Volume",0))})
        except Exception:
            continue
    return out


# ── KRAKEN ───────────────────────────────────────────────
_KRAKEN_IV = {"1m":1,"5m":5,"15m":15,"30m":30,
              "1h":60,"4h":240,"1d":1440,"1w":10080}

def _from_kraken(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests
    iv = _KRAKEN_IV.get(interval.lower(),240)
    r  = requests.get("https://api.kraken.com/0/public/OHLC",
        params={"pair":symbol.upper(),"interval":iv}, timeout=15)
    r.raise_for_status()
    res = r.json()
    if res.get("error"):
        raise ValueError(f"Kraken: {res['error']}")
    raw = list(res["result"].values())[0][-limit:]
    return [{"t":int(c[0]),"o":float(c[1]),"h":float(c[2]),
             "l":float(c[3]),"c":float(c[4]),"v":float(c[6])} for c in raw]


# ── MOCK (fallback) ──────────────────────────────────────
_MOCK_STEP = {"1m":60,"5m":300,"15m":900,"30m":1800,
              "1h":3600,"4h":14400,"1d":86400,"1w":604800}

def _mock(symbol: str, interval: str, limit: int) -> list[dict]:
    step  = _MOCK_STEP.get(interval.lower(),14400)
    now   = int(time.time())
    price = 67000.0
    out   = []
    random.seed(42)
    for i in range(limit):
        o = price + (random.random()-.5)*300
        c = o     + (random.random()-.47)*500
        h = max(o,c)+random.random()*250
        l = min(o,c)-random.random()*250
        v = 600+random.random()*5000
        out.append({"t":now-(limit-i)*step,
                    "o":round(o,2),"h":round(h,2),
                    "l":round(l,2),"c":round(c,2),"v":round(v,2)})
        price = c
    return out
