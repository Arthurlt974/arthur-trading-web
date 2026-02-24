"""
data_provider.py
════════════════════════════════════════════════════════════
Couche d'abstraction des données — 100% légal pour service payant
Remplace yfinance (interdit commercialement) par :
  - Alpha Vantage  : prix, OHLCV, fondamentaux, dividendes (GRATUIT, commercial OK)
  - CoinGecko API  : crypto prix + OHLCV (GRATUIT, commercial OK)
  - SEC EDGAR      : insider trading réel (GRATUIT, données publiques officielles)

Limites Alpha Vantage gratuit : 500 req/jour, 25 req/min
→ Cache agressif pour rester dans les limites
════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime, timedelta

# ══════════════════════════════════════════════
#  CONFIG — remplace ta clé ici ou dans secrets
# ══════════════════════════════════════════════

def _get_av_key():
    """Récupère la clé Alpha Vantage depuis st.secrets ou variable d'env."""
    try:
        return st.secrets["ALPHA_VANTAGE_KEY"]
    except:
        return os.environ.get("ALPHA_VANTAGE_KEY", "demo")

AV_BASE = "https://www.alphavantage.co/query"
CG_BASE = "https://api.coingecko.com/api/v3"

COIN_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple",
    "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot", "AVAX": "avalanche-2",
    "LINK": "chainlink", "MATIC": "matic-network", "BNB": "binancecoin",
    "LTC": "litecoin", "UNI": "uniswap", "ATOM": "cosmos", "NEAR": "near",
}

# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def _av(params, retries=2):
    """Appel Alpha Vantage avec gestion rate limit."""
    params["apikey"] = _get_av_key()
    for attempt in range(retries):
        try:
            r = requests.get(AV_BASE, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                # Détecter rate limit
                if "Note" in data or "Information" in data:
                    time.sleep(12)  # Attendre 12s puis réessayer
                    if attempt < retries - 1:
                        continue
                return data
        except:
            pass
    return {}

def _cg(endpoint, params=None, retries=2):
    """Appel CoinGecko avec retry."""
    for attempt in range(retries):
        try:
            r = requests.get(f"{CG_BASE}{endpoint}", params=params, timeout=10)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code == 200:
                return r.json()
        except:
            pass
    return None

def _ticker_av(ticker):
    """Normalise le ticker pour Alpha Vantage (retire .PA, -USD, etc.)."""
    # Crypto → on utilise CoinGecko à la place
    if ticker.endswith("-USD"):
        return None
    # Actions françaises : MC.PA → MC.PAR sur AV
    if ticker.endswith(".PA"):
        return ticker.replace(".PA", ".PAR")
    return ticker

def _is_crypto(ticker):
    sym = ticker.upper().replace("-USD", "").replace("USDT", "")
    return sym in COIN_ID_MAP or ticker.endswith("-USD")

# ══════════════════════════════════════════════
#  1. PRIX EN TEMPS RÉEL
# ══════════════════════════════════════════════

@st.cache_data(ttl=60)
def get_price(ticker):
    """
    Prix actuel — remplace yf.Ticker(t).fast_info['last_price']
    Returns: float ou None
    """
    ticker = ticker.strip().upper()

    # Crypto → CoinGecko
    if _is_crypto(ticker):
        sym = ticker.replace("-USD", "").replace("USDT", "")
        coin_id = COIN_ID_MAP.get(sym, sym.lower())
        data = _cg(f"/simple/price", params={"ids": coin_id, "vs_currencies": "usd"})
        if data and coin_id in data:
            return float(data[coin_id]["usd"])
        return None

    # Actions → Alpha Vantage GLOBAL_QUOTE
    av_ticker = _ticker_av(ticker)
    if not av_ticker:
        return None
    data = _av({"function": "GLOBAL_QUOTE", "symbol": av_ticker})
    quote = data.get("Global Quote", {})
    price = quote.get("05. price")
    if price:
        return float(price)
    return None

@st.cache_data(ttl=60)
def get_quote(ticker):
    """
    Quote complète — remplace yf.Ticker(t).fast_info
    Returns: dict avec price, previous_close, change_pct, volume
    """
    ticker = ticker.strip().upper()

    if _is_crypto(ticker):
        sym = ticker.replace("-USD", "").replace("USDT", "")
        coin_id = COIN_ID_MAP.get(sym, sym.lower())
        data = _cg("/simple/price", params={
            "ids": coin_id, "vs_currencies": "usd",
            "include_24hr_change": "true", "include_24hr_vol": "true",
            "include_market_cap": "true"
        })
        if data and coin_id in data:
            d = data[coin_id]
            price = float(d.get("usd", 0))
            chg   = float(d.get("usd_24h_change", 0))
            prev  = price / (1 + chg / 100) if chg != -100 else price
            return {
                "ticker":         ticker,
                "price":          price,
                "previous_close": prev,
                "change_pct":     chg,
                "volume":         float(d.get("usd_24h_vol", 0)),
                "market_cap":     float(d.get("usd_market_cap", 0)),
            }
        return None

    av_ticker = _ticker_av(ticker)
    if not av_ticker:
        return None
    data = _av({"function": "GLOBAL_QUOTE", "symbol": av_ticker})
    q = data.get("Global Quote", {})
    if not q:
        return None
    price    = float(q.get("05. price", 0))
    prev     = float(q.get("08. previous close", 0))
    chg_pct  = float(q.get("10. change percent", "0%").replace("%", ""))
    return {
        "ticker":         ticker,
        "price":          price,
        "previous_close": prev,
        "change_pct":     chg_pct,
        "volume":         float(q.get("06. volume", 0)),
        "market_cap":     0,
    }

# ══════════════════════════════════════════════
#  2. HISTORIQUE OHLCV
# ══════════════════════════════════════════════

@st.cache_data(ttl=300)
def get_history(ticker, period="6mo", interval="1d"):
    """
    OHLCV historique — remplace yf.download() et yf.Ticker().history()
    Returns: DataFrame avec colonnes Open, High, Low, Close, Volume (index=date)
    """
    ticker = ticker.strip().upper()

    # Crypto → CoinGecko
    if _is_crypto(ticker):
        sym = ticker.replace("-USD", "").replace("USDT", "")
        coin_id = COIN_ID_MAP.get(sym, sym.lower())
        days_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
                    "1y": 365, "2y": 730, "5y": 1825}
        days = days_map.get(period, 180)
        data = _cg(f"/coins/{coin_id}/ohlc", params={"vs_currency": "usd", "days": days})
        if data and isinstance(data, list):
            df = pd.DataFrame(data, columns=["timestamp", "Open", "High", "Low", "Close"])
            df.index = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.drop("timestamp", axis=1)
            df["Volume"] = 0
            return df.dropna()
        return pd.DataFrame()

    # Actions → Alpha Vantage
    av_ticker = _ticker_av(ticker)
    if not av_ticker:
        return pd.DataFrame()

    # Choisir la fonction AV selon l'intervalle
    intraday = interval in ["1m", "5m", "15m", "30m", "1h", "60min"]
    if intraday:
        iv_map = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "60min"}
        av_interval = iv_map.get(interval, "60min")
        data = _av({
            "function": "TIME_SERIES_INTRADAY",
            "symbol": av_ticker,
            "interval": av_interval,
            "outputsize": "full"
        })
        key = f"Time Series ({av_interval})"
    elif interval == "1wk":
        data = _av({"function": "TIME_SERIES_WEEKLY_ADJUSTED", "symbol": av_ticker})
        key = "Weekly Adjusted Time Series"
    elif interval == "1mo":
        data = _av({"function": "TIME_SERIES_MONTHLY_ADJUSTED", "symbol": av_ticker})
        key = "Monthly Adjusted Time Series"
    else:
        # Daily — le plus courant
        data = _av({
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": av_ticker,
            "outputsize": "full"
        })
        key = "Time Series (Daily)"

    ts = data.get(key, {})
    if not ts:
        return pd.DataFrame()

    rows = []
    for date_str, vals in ts.items():
        try:
            rows.append({
                "date":   pd.to_datetime(date_str),
                "Open":   float(vals.get("1. open",   vals.get("1. adjusted open",  0))),
                "High":   float(vals.get("2. high",   vals.get("2. adjusted high",  0))),
                "Low":    float(vals.get("3. low",    vals.get("3. adjusted low",   0))),
                "Close":  float(vals.get("4. close",  vals.get("5. adjusted close", 0))),
                "Volume": float(vals.get("5. volume", vals.get("6. volume",         0))),
            })
        except:
            pass

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).set_index("date").sort_index()

    # Filtrer selon la période demandée
    period_days = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
                   "1y": 365, "2y": 730, "5y": 1825}
    cutoff = datetime.now() - timedelta(days=period_days.get(period, 180))
    df = df[df.index >= cutoff]
    return df.dropna()

@st.cache_data(ttl=300)
def get_history_multi(tickers, period="60d", interval="1d"):
    """
    OHLCV multi-tickers — remplace yf.download(list, ...)['Close']
    Returns: DataFrame avec une colonne par ticker (prix de clôture)
    """
    result = {}
    for ticker in tickers:
        df = get_history(ticker, period=period, interval=interval)
        if not df.empty:
            result[ticker] = df["Close"]
    if result:
        return pd.DataFrame(result)
    return pd.DataFrame()

# ══════════════════════════════════════════════
#  3. FONDAMENTAUX (INFO)
# ══════════════════════════════════════════════

@st.cache_data(ttl=3600)  # Cache 1h — données peu volatiles
def get_info(ticker):
    """
    Fondamentaux — remplace yf.Ticker(t).info
    Returns: dict avec currentPrice, trailingPE, trailingEps, dividendRate, etc.
    """
    ticker = ticker.strip().upper()

    if _is_crypto(ticker):
        sym = ticker.replace("-USD", "")
        coin_id = COIN_ID_MAP.get(sym, sym.lower())
        data = _cg(f"/coins/{coin_id}", params={
            "localization": "false", "tickers": "false",
            "community_data": "false", "developer_data": "false"
        })
        if not data:
            return {}
        md = data.get("market_data", {})
        price = md.get("current_price", {}).get("usd", 0)
        return {
            "longName":              data.get("name", ticker),
            "shortName":             data.get("symbol", "").upper(),
            "currentPrice":          price,
            "regularMarketPrice":    price,
            "marketCap":             md.get("market_cap", {}).get("usd", 0),
            "totalVolume":           md.get("total_volume", {}).get("usd", 0),
            "circulatingSupply":     md.get("circulating_supply", 0),
            "maxSupply":             md.get("max_supply", 0),
            "currency":              "USD",
            "sector":                "Cryptocurrency",
            "priceChangePercent24h": md.get("price_change_percentage_24h", 0),
        }

    av_ticker = _ticker_av(ticker)
    if not av_ticker:
        return {}

    # Alpha Vantage Company Overview
    data = _av({"function": "OVERVIEW", "symbol": av_ticker})
    if not data or "Symbol" not in data:
        # Fallback : juste le prix via GLOBAL_QUOTE
        q = get_quote(ticker)
        return {"currentPrice": q["price"], "currency": "USD"} if q else {}

    price = get_price(ticker) or 0
    eps   = float(data.get("EPS", 0) or 0)
    pe    = float(data.get("PERatio", 0) or 0)
    div   = float(data.get("DividendPerShare", 0) or 0)
    div_yield = float(data.get("DividendYield", 0) or 0)

    return {
        # Identité
        "longName":             data.get("Name", ticker),
        "shortName":            data.get("Name", ticker),
        "sector":               data.get("Sector", "N/A"),
        "industry":             data.get("Industry", "N/A"),
        "country":              data.get("Country", "N/A"),
        "currency":             data.get("Currency", "USD"),
        "exchange":             data.get("Exchange", "N/A"),
        "description":          data.get("Description", ""),
        # Prix
        "currentPrice":         price,
        "regularMarketPrice":   price,
        "previousClose":        float(data.get("52WeekLow", price) or price),
        "fiftyTwoWeekHigh":     float(data.get("52WeekHigh", 0) or 0),
        "fiftyTwoWeekLow":      float(data.get("52WeekLow", 0) or 0),
        # Valorisation
        "marketCap":            float(data.get("MarketCapitalization", 0) or 0),
        "trailingPE":           pe,
        "forwardPE":            float(data.get("ForwardPE", 0) or 0),
        "priceToBook":          float(data.get("PriceToBookRatio", 0) or 0),
        "priceToSalesTrailing12Months": float(data.get("PriceToSalesRatioTTM", 0) or 0),
        "enterpriseValue":      float(data.get("EVToEBITDA", 0) or 0),
        # Résultats
        "trailingEps":          eps,
        "forwardEps":           float(data.get("ForwardEPS", 0) or 0),
        "revenuePerShare":      float(data.get("RevenuePerShareTTM", 0) or 0),
        "returnOnEquity":       float(data.get("ReturnOnEquityTTM", 0) or 0),
        "returnOnAssets":       float(data.get("ReturnOnAssetsTTM", 0) or 0),
        "operatingMargins":     float(data.get("OperatingMarginTTM", 0) or 0),
        "profitMargins":        float(data.get("ProfitMargin", 0) or 0),
        "revenueGrowth":        float(data.get("QuarterlyRevenueGrowthYOY", 0) or 0),
        "earningsGrowth":       float(data.get("QuarterlyEarningsGrowthYOY", 0) or 0),
        # Dividendes
        "dividendRate":         div,
        "dividendYield":        div_yield,
        "payoutRatio":          float(data.get("PayoutRatio", 0) or 0),
        "exDividendDate":       data.get("ExDividendDate", ""),
        # Dette
        "debtToEquity":         float(data.get("DebtToEquityRatio", 0) or 0),
        "currentRatio":         float(data.get("CurrentRatio", 0) or 0),
        # Autres
        "beta":                 float(data.get("Beta", 1) or 1),
        "sharesOutstanding":    float(data.get("SharesOutstanding", 0) or 0),
        "floatShares":          float(data.get("SharesFloat", 0) or 0),
        "bookValue":            float(data.get("BookValue", 0) or 0),
        "totalRevenue":         float(data.get("RevenueTTM", 0) or 0),
        "ebitda":               float(data.get("EBITDA", 0) or 0),
        "totalDebt":            float(data.get("TotalDebt", 0) or 0),
    }

# ══════════════════════════════════════════════
#  4. RECHERCHE DE TICKER
# ══════════════════════════════════════════════

@st.cache_data(ttl=3600)
def search_ticker(query):
    """
    Recherche ticker depuis un nom — remplace trouver_ticker()
    Returns: str ticker symbol
    """
    # Tentative Alpha Vantage SYMBOL_SEARCH
    data = _av({"function": "SYMBOL_SEARCH", "keywords": query})
    matches = data.get("bestMatches", [])
    if matches:
        return matches[0].get("1. symbol", query)
    return query.upper()

# ══════════════════════════════════════════════
#  5. DIVIDENDES
# ══════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_dividends(ticker):
    """
    Historique des dividendes — remplace yf.Ticker(t).dividends
    Returns: DataFrame avec date et amount
    """
    av_ticker = _ticker_av(ticker.strip().upper())
    if not av_ticker:
        return pd.DataFrame()

    # TIME_SERIES_MONTHLY_ADJUSTED contient les dividendes ajustés
    data = _av({
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": av_ticker
    })
    ts = data.get("Monthly Adjusted Time Series", {})
    rows = []
    for date_str, vals in ts.items():
        div = float(vals.get("7. dividend amount", 0) or 0)
        if div > 0:
            rows.append({"date": pd.to_datetime(date_str), "dividend": div})

    if rows:
        df = pd.DataFrame(rows).set_index("date").sort_index()
        return df
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_upcoming_dividends(tickers):
    """
    Prochains dividendes pour une liste de tickers.
    Utilise Alpha Vantage OVERVIEW (exDividendDate + dividendRate)
    Returns: liste de dicts
    """
    results = []
    for ticker in tickers:
        info = get_info(ticker)
        if info and info.get("dividendRate", 0) > 0:
            results.append({
                "ticker":          ticker,
                "name":            info.get("longName", ticker),
                "dividendRate":    info.get("dividendRate", 0),
                "dividendYield":   info.get("dividendYield", 0),
                "exDividendDate":  info.get("exDividendDate", "N/A"),
                "payoutRatio":     info.get("payoutRatio", 0),
            })
    return results

# ══════════════════════════════════════════════
#  6. INSIDER TRADING — SEC EDGAR (OFFICIEL)
# ══════════════════════════════════════════════

@st.cache_data(ttl=3600)
def search_company_cik(ticker):
    """Trouve le CIK SEC d'une entreprise depuis son ticker."""
    try:
        # Mapping ticker → CIK via SEC EDGAR
        url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=4"
        r = requests.get(url, headers={"User-Agent": "AM-Trading contact@amtrading.fr"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            hits = data.get("hits", {}).get("hits", [])
            if hits:
                return hits[0].get("_source", {}).get("entity_id")
    except:
        pass

    # Fallback : chercher via le fichier company_tickers.json de la SEC
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "AM-Trading contact@amtrading.fr"}, timeout=10
        )
        if r.status_code == 200:
            companies = r.json()
            ticker_upper = ticker.upper().replace(".PA", "")
            for _, company in companies.items():
                if company.get("ticker", "").upper() == ticker_upper:
                    return str(company["cik_str"]).zfill(10)
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def get_insider_transactions(ticker):
    """
    Transactions d'initiés réelles via SEC EDGAR Form 4 (GRATUIT, officiel)
    Remplace les données hardcodées fictives.
    Returns: liste de dicts ou [] si non trouvé
    """
    # SEC EDGAR fonctionne uniquement pour les entreprises US cotées
    ticker_clean = ticker.upper().replace(".PA", "").replace("-USD", "")

    # 1. Trouver le CIK
    cik = None
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "AM-Trading contact@amtrading.fr"}, timeout=10
        )
        if r.status_code == 200:
            companies = r.json()
            for _, company in companies.items():
                if company.get("ticker", "").upper() == ticker_clean:
                    cik = str(company["cik_str"]).zfill(10)
                    break
    except:
        pass

    if not cik:
        return []

    # 2. Récupérer les Form 4 récents
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        r = requests.get(url, headers={"User-Agent": "AM-Trading contact@amtrading.fr"}, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
    except:
        return []

    company_name = data.get("name", ticker)
    filings = data.get("filings", {}).get("recent", {})
    forms   = filings.get("form", [])
    dates   = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])

    # Filtrer Form 4 des 6 derniers mois
    transactions = []
    cutoff = datetime.now() - timedelta(days=180)

    for i, form in enumerate(forms):
        if form != "4":
            continue
        try:
            filing_date = datetime.strptime(dates[i], "%Y-%m-%d")
            if filing_date < cutoff:
                continue

            # Récupérer le détail du filing Form 4
            acc = accessions[i].replace("-", "")
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{accessions[i]}-index.htm"

            # Parser le filing XML
            xml_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=40&search_text="
            transactions.append({
                "date":        filing_date,
                "insider":     "Voir SEC EDGAR",
                "position":    "Dirigeant",
                "transaction": "Form 4",
                "shares":      0,
                "price":       0,
                "value_usd":   0,
                "source":      "SEC EDGAR",
                "url":         f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=40",
            })

            if len(transactions) >= 10:
                break
        except:
            continue

    return transactions, company_name, cik

@st.cache_data(ttl=3600)
def get_insider_transactions_full(ticker):
    """
    Version complète avec parsing XML des Form 4.
    Retourne les vraies transactions avec noms, montants, etc.
    """
    ticker_clean = ticker.upper().replace(".PA", "").replace("-USD", "")

    # Trouver CIK
    cik = None
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "AM-Trading contact@amtrading.fr"}, timeout=10
        )
        if r.status_code == 200:
            for _, co in r.json().items():
                if co.get("ticker", "").upper() == ticker_clean:
                    cik = str(co["cik_str"]).zfill(10)
                    break
    except:
        pass

    if not cik:
        return [], ticker, None

    # Récupérer les filings via API SEC EDGAR officielle
    try:
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers={"User-Agent": "AM-Trading contact@amtrading.fr"}, timeout=10
        )
        data = r.json()
    except:
        return [], ticker, cik

    company_name = data.get("name", ticker)
    filings = data.get("filings", {}).get("recent", {})
    forms      = filings.get("form", [])
    dates      = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    reporters  = filings.get("reportingOwner", []) if "reportingOwner" in filings else []

    transactions = []
    cutoff = datetime.now() - timedelta(days=180)

    for i, form in enumerate(forms):
        if form != "4":
            continue
        try:
            filing_date = datetime.strptime(dates[i], "%Y-%m-%d")
            if filing_date < cutoff:
                continue

            acc_clean = accessions[i].replace("-", "")
            cik_int   = int(cik)

            # Construire l'URL du fichier XML principal
            xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accessions[i]}.txt"

            # Chercher le fichier XML dans l'index
            idx_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accessions[i]}-index.json"
            idx_r   = requests.get(idx_url,
                                   headers={"User-Agent": "AM-Trading contact@amtrading.fr"},
                                   timeout=8)
            if idx_r.status_code == 200:
                idx_data = idx_r.json()
                for doc in idx_data.get("documents", []):
                    if doc.get("type") == "4" and doc.get("document", "").endswith(".xml"):
                        xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{doc['document']}"
                        break

            # Parser le XML
            xml_r = requests.get(xml_url,
                                  headers={"User-Agent": "AM-Trading contact@amtrading.fr"},
                                  timeout=8)
            if xml_r.status_code != 200:
                continue

            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_r.text)

            # Nom de l'initié
            reporter_name = "N/A"
            reporter_title = "N/A"
            for rp in root.findall(".//reportingOwner"):
                n = rp.find(".//rptOwnerName")
                t = rp.find(".//officerTitle")
                if n is not None and n.text:
                    reporter_name  = n.text.strip()
                if t is not None and t.text:
                    reporter_title = t.text.strip()

            # Transactions
            for txn in root.findall(".//nonDerivativeTransaction"):
                try:
                    shares_el = txn.find(".//transactionShares/value")
                    price_el  = txn.find(".//transactionPricePerShare/value")
                    code_el   = txn.find(".//transactionCode")
                    date_el   = txn.find(".//transactionDate/value")

                    shares    = float(shares_el.text) if shares_el is not None and shares_el.text else 0
                    price     = float(price_el.text)  if price_el is not None  and price_el.text  else 0
                    code      = code_el.text if code_el is not None else "?"
                    txn_date  = datetime.strptime(date_el.text, "%Y-%m-%d") if date_el is not None else filing_date

                    code_map  = {
                        "P": "Achat", "S": "Vente", "A": "Attribution",
                        "D": "Cession", "G": "Don", "M": "Levée d'options"
                    }
                    type_txt = code_map.get(code, f"Code {code}")

                    transactions.append({
                        "date":        txn_date,
                        "insider":     reporter_name,
                        "position":    reporter_title,
                        "transaction": type_txt,
                        "code":        code,
                        "shares":      int(shares),
                        "price":       price,
                        "value_usd":   shares * price,
                        "source":      "SEC EDGAR Form 4",
                        "filing_url":  f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accessions[i]}-index.htm"
                    })
                except:
                    continue

        except Exception:
            continue

        if len(transactions) >= 25:
            break

    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions, company_name, cik

# ══════════════════════════════════════════════
#  7. SENTIMENT / SCORE MARCHÉ
# ══════════════════════════════════════════════

@st.cache_data(ttl=300)
def calculer_score_sentiment(ticker):
    """
    Score sentiment basé sur MA200 — remplace l'ancienne version yfinance
    Returns: (score, label, color)
    """
    df = get_history(ticker, period="1y", interval="1d")
    if len(df) < 200:
        return 50, "NEUTRE", "gray"
    prix_actuel = float(df["Close"].iloc[-1])
    ma200       = float(df["Close"].rolling(window=200).mean().iloc[-1])
    ratio       = (prix_actuel / ma200) - 1
    score       = max(10, min(90, 50 + ratio * 300))
    if score > 70:   return score, "EXTRÊME EUPHORIE 🚀", "#00ffad"
    elif score > 55: return score, "OPTIMISME 📈", "#2ecc71"
    elif score > 45: return score, "NEUTRE ➡️", "#f39c12"
    elif score > 30: return score, "PESSIMISME 📉", "#e67e22"
    else:            return score, "PANIQUE EXTRÊME 💀", "#ff4b4b"

# ══════════════════════════════════════════════
#  8. COMPATIBILITÉ — wrappers drop-in
# ══════════════════════════════════════════════
# Ces fonctions reproduisent exactement l'interface yfinance
# pour minimiser les modifications dans App.py

def get_ticker_info(ticker):
    """Drop-in replacement pour yf.Ticker(t).info"""
    return get_info(ticker)

def get_ticker_history(ticker, period="2d"):
    """Drop-in replacement pour yf.Ticker(t).history(period=...)"""
    return get_history(ticker, period=period)

def trouver_ticker(nom):
    """Drop-in replacement pour trouver_ticker()"""
    return search_ticker(nom)
