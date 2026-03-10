# ============================================================
#  chart_module/data.py
#  CoinGecko par défaut — fallback Twelve Data pour les actions
# ============================================================

import time
import random
from .config import DATA_SOURCE, DEFAULT_LIMIT, FALLBACK_TO_MOCK, COINGECKO_IDS

# ── Clé Twelve Data (depuis st.secrets ou variable d'env) ──
def _get_td_key() -> str:
    try:
        import streamlit as st
        return st.secrets.get("TWELVE_DATA_KEY", "")
    except Exception:
        import os
        return os.environ.get("TWELVE_DATA_KEY", "")


def _is_stock(symbol: str) -> bool:
    """Détecte si le symbole est une action (pas une crypto)."""
    s = symbol.upper().strip()
    if s.endswith("USDT") or s.endswith("BUSD") or s.endswith("BTC") or s.endswith("ETH"):
        return False
    if "." in s:
        return True
    known_cryptos = {
        "BTC","ETH","SOL","XRP","ADA","DOT","AVAX","DOGE","MATIC","LINK",
        "UNI","ATOM","LTC","BCH","NEAR","FTM","SAND","MANA","AAVE","CRV",
        "BNB","TRX","SHIB","PEPE","TON","SUI","APT","ARB","OP","INJ",
        "BITCOIN","ETHEREUM","SOLANA","RIPPLE","CARDANO","POLKADOT",
    }
    if s in known_cryptos:
        return False
    import re
    if re.match(r'^[A-Z]{1,5}$', s):
        return True
    return False


def fetch_ohlcv(symbol: str, interval: str, limit: int = DEFAULT_LIMIT) -> tuple[list[dict], bool]:
    """
    Retourne (candles, is_live).
    candles  : [{t, o, h, l, c, v}, ...]
    is_live  : True si données réelles
    Auto-détecte les actions et route vers Twelve Data → yfinance → mock.
    """
    src = DATA_SOURCE.lower()

    # ── Auto-routing : si c'est une action ──
    if _is_stock(symbol) and src not in ("yfinance",):

        # 1. Twelve Data en priorité (fiable sur Streamlit Cloud)
        td_key = _get_td_key()
        if td_key:
            try:
                data = _from_twelvedata(symbol, interval, limit, td_key)
                if data and len(data) > 0:
                    print(f"[chart_module] Twelve Data OK pour {symbol}")
                    return data, True
            except Exception as e:
                print(f"[chart_module] Twelve Data échoué ({symbol}): {e} → yfinance")
        else:
            print(f"[chart_module] Clé Twelve Data manquante → yfinance")

        # 2. Fallback yfinance
        try:
            data = _from_yfinance(symbol, interval, limit)
            if data and len(data) > 0:
                print(f"[chart_module] yfinance OK pour {symbol}")
                return data, True
            raise ValueError("Données vides")
        except Exception as e2:
            print(f"[chart_module] yfinance échoué ({symbol}): {e2}")

        # 3. Fallback mock
        if FALLBACK_TO_MOCK:
            return _mock(symbol, interval, limit), False
        raise RuntimeError(f"Impossible de charger les données pour {symbol}")

    try:
        if src == "coingecko":
            return _from_coingecko(symbol, interval, limit), True
        elif src == "binance":
            return _from_binance(symbol, interval, limit), True
        elif src == "bybit":
            return _from_bybit(symbol, interval, limit), True
        elif src == "yfinance":
            # yfinance direct → fallback Twelve Data si besoin
            try:
                data = _from_yfinance(symbol, interval, limit)
                if data and len(data) > 0:
                    return data, True
                raise ValueError("Données vides")
            except Exception as e:
                print(f"[chart_module] yfinance échoué ({symbol}): {e} → Twelve Data")
                td_key = _get_td_key()
                if td_key:
                    return _from_twelvedata(symbol, interval, limit, td_key), True
                if FALLBACK_TO_MOCK:
                    return _mock(symbol, interval, limit), False
                raise
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


# ── TWELVE DATA ──────────────────────────────────────────
# Correspondance interval AM-Trading → Twelve Data
_TD_IV = {
    "1m":  "1min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "1h":  "1h",
    "4h":  "4h",
    "1d":  "1day",
    "1w":  "1week",
    "1wk": "1week",
}

def _from_twelvedata(symbol: str, interval: str, limit: int, api_key: str) -> list[dict]:
    """Récupère les bougies OHLCV depuis Twelve Data."""
    import requests

    iv = _TD_IV.get(interval.lower(), "1day")

    # Twelve Data : les tickers européens s'écrivent avec : (ex MC:XPAR pour LVMH)
    # On essaie d'abord le symbole brut, puis avec exchange si besoin
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol":     symbol.upper(),
        "interval":   iv,
        "outputsize": min(limit, 5000),
        "apikey":     api_key,
        "format":     "JSON",
        "order":      "ASC",
    }

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    # Gestion des erreurs Twelve Data
    if data.get("status") == "error":
        raise ValueError(f"Twelve Data: {data.get('message', 'erreur inconnue')}")

    values = data.get("values", [])
    if not values:
        raise ValueError(f"Twelve Data: aucune donnée pour {symbol}")

    candles = []
    for row in values:
        try:
            # Twelve Data retourne datetime string → timestamp
            from datetime import datetime
            dt_str = row["datetime"]
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
            candles.append({
                "t": int(dt.timestamp()),
                "o": float(row["open"]),
                "h": float(row["high"]),
                "l": float(row["low"]),
                "c": float(row["close"]),
                "v": float(row.get("volume", 0) or 0),
            })
        except Exception:
            continue

    return candles[-limit:]


# ── COINGECKO ────────────────────────────────────────────
def _resolve_id(symbol: str) -> str:
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
    headers = {"User-Agent": "Mozilla/5.0 (Arthur-Trading-Chart/1.0)", "Accept": "application/json"}
    ohlc_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    r_ohlc   = requests.get(ohlc_url, params={"vs_currency": "usd", "days": days}, headers=headers, timeout=15)
    r_ohlc.raise_for_status()
    ohlc_raw = r_ohlc.json()
    if not isinstance(ohlc_raw, list) or len(ohlc_raw) == 0:
        raise ValueError(f"CoinGecko OHLC vide pour {coin_id}")
    vol_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    try:
        r_vol   = requests.get(vol_url, params={"vs_currency": "usd", "days": days}, headers=headers, timeout=15)
        vol_map = {int(v[0])//1000: float(v[1]) for v in r_vol.json().get("total_volumes", [])}
    except Exception:
        vol_map = {}
    candles = []
    for row in ohlc_raw[-limit:]:
        ts  = int(row[0]) // 1000
        vol = 0.0
        if vol_map:
            closest = min(vol_map.keys(), key=lambda k: abs(k-ts))
            if abs(closest - ts) < 14400:
                vol = vol_map[closest]
        candles.append({"t": ts, "o": float(row[1]), "h": float(row[2]), "l": float(row[3]), "c": float(row[4]), "v": vol})
    return candles


# ── BINANCE ──────────────────────────────────────────────
_BINANCE_IV = {"1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d","1w":"1w"}

def _from_binance(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests
    iv = _BINANCE_IV.get(interval.lower(), interval)
    r  = requests.get("https://api.binance.com/api/v3/klines",
        params={"symbol": symbol.upper(), "interval": iv, "limit": min(limit, 1000)},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or not data:
        raise ValueError("Binance: réponse vide")
    return [{"t": int(c[0])//1000, "o": float(c[1]), "h": float(c[2]),
             "l": float(c[3]), "c": float(c[4]), "v": float(c[5])} for c in data]


# ── BYBIT ────────────────────────────────────────────────
_BYBIT_IV = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"240","1d":"D","1w":"W"}

def _from_bybit(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests
    iv = _BYBIT_IV.get(interval.lower(), "240")
    r  = requests.get("https://api.bybit.com/v5/market/kline",
        params={"category": "spot", "symbol": symbol.upper(), "interval": iv, "limit": min(limit, 1000)}, timeout=15)
    r.raise_for_status()
    raw = r.json()
    if raw.get("retCode", 1) != 0:
        raise ValueError(f"Bybit: {raw.get('retMsg')}")
    return [{"t": int(c[0])//1000, "o": float(c[1]), "h": float(c[2]),
             "l": float(c[3]), "c": float(c[4]), "v": float(c[5])}
            for c in reversed(raw["result"]["list"])]


# ── YFINANCE ─────────────────────────────────────────────
def _from_yfinance(symbol: str, interval: str, limit: int) -> list[dict]:
    import yfinance as yf
    _period = {"1m":"7d","5m":"60d","15m":"60d","30m":"60d",
               "1h":"730d","4h":"730d","1d":"5y","1w":"10y","1wk":"10y"}
    df = yf.download(symbol, period=_period.get(interval.lower(), "60d"),
                     interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        raise ValueError(f"yFinance: vide pour {symbol}")
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df  = df.tail(limit).reset_index()
    ts  = "Datetime" if "Datetime" in df.columns else "Date"
    out = []
    for _, row in df.iterrows():
        try:
            out.append({"t": int(row[ts].timestamp()),
                "o": float(row["Open"]),  "h": float(row["High"]),
                "l": float(row["Low"]),   "c": float(row["Close"]),
                "v": float(row.get("Volume", 0))})
        except Exception:
            continue
    return out


# ── KRAKEN ───────────────────────────────────────────────
_KRAKEN_IV = {"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440,"1w":10080}

def _from_kraken(symbol: str, interval: str, limit: int) -> list[dict]:
    import requests
    iv = _KRAKEN_IV.get(interval.lower(), 240)
    r  = requests.get("https://api.kraken.com/0/public/OHLC",
        params={"pair": symbol.upper(), "interval": iv}, timeout=15)
    r.raise_for_status()
    res = r.json()
    if res.get("error"):
        raise ValueError(f"Kraken: {res['error']}")
    raw = list(res["result"].values())[0][-limit:]
    return [{"t": int(c[0]), "o": float(c[1]), "h": float(c[2]),
             "l": float(c[3]), "c": float(c[4]), "v": float(c[6])} for c in raw]


# ── MOCK (fallback ultime) ───────────────────────────────
_MOCK_STEP = {"1m":60,"5m":300,"15m":900,"30m":1800,"1h":3600,"4h":14400,"1d":86400,"1w":604800}

def _mock(symbol: str, interval: str, limit: int) -> list[dict]:
    step  = _MOCK_STEP.get(interval.lower(), 14400)
    now   = int(time.time())
    price = 67000.0
    out   = []
    random.seed(42)
    for i in range(limit):
        o = price + (random.random() - .5) * 300
        c = o     + (random.random() - .47) * 500
        h = max(o, c) + random.random() * 250
        l = min(o, c) - random.random() * 250
        v = 600 + random.random() * 5000
        out.append({"t": now - (limit - i) * step,
                    "o": round(o,2), "h": round(h,2),
                    "l": round(l,2), "c": round(c,2), "v": round(v,2)})
        price = c
    return out
