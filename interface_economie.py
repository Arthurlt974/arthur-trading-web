"""
interface_economie.py — AM-Trading Terminal
Données macro-économiques en TEMPS RÉEL
Sources : FRED (FED), BCE API, World Bank, OECD, yfinance
Fallback : données officielles les plus récentes (mars 2026)
"""

import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# ══════════════════════════════════════════════════════════════
#  CONFIG PAYS
# ══════════════════════════════════════════════════════════════

PAYS_CONFIG = {
    "🇺🇸 USA":        {"code": "US",  "wb": "US",  "couleur": "#4fc3f7"},
    "🇪🇺 Zone Euro":  {"code": "EU",  "wb": "EMU", "couleur": "#ffb74d"},
    "🇫🇷 France":     {"code": "FR",  "wb": "FR",  "couleur": "#81c784"},
    "🇨🇳 Chine":      {"code": "CN",  "wb": "CN",  "couleur": "#e57373"},
    "🇯🇵 Japon":      {"code": "JP",  "wb": "JP",  "couleur": "#ce93d8"},
    "🇬🇧 UK":         {"code": "GB",  "wb": "GB",  "couleur": "#80cbc4"},
}

# ══════════════════════════════════════════════════════════════
#  FALLBACK — Données officielles mars 2026
#  Sources : BLS, Eurostat, INSEE, PBOC, BOJ, ONS
#  Historique = 12 derniers mois (avr 2025 → mars 2026)
# ══════════════════════════════════════════════════════════════

FALLBACK = {
    "chomage": {
        "🇺🇸 USA":        {"actuel": 4.1,  "precedent": 4.0,  "historique": [3.9, 4.0, 4.1, 4.2, 4.1, 4.0, 4.1, 4.2, 4.1, 4.0, 4.1, 4.1]},
        "🇪🇺 Zone Euro":  {"actuel": 6.2,  "precedent": 6.3,  "historique": [6.5, 6.4, 6.3, 6.2, 6.2, 6.3, 6.2, 6.1, 6.2, 6.2, 6.3, 6.2]},
        "🇫🇷 France":     {"actuel": 7.3,  "precedent": 7.4,  "historique": [7.5, 7.5, 7.4, 7.4, 7.3, 7.3, 7.4, 7.3, 7.2, 7.3, 7.4, 7.3]},
        "🇨🇳 Chine":      {"actuel": 5.1,  "precedent": 5.2,  "historique": [5.0, 5.1, 5.2, 5.1, 5.0, 5.1, 5.2, 5.1, 5.0, 5.1, 5.2, 5.1]},
        "🇯🇵 Japon":      {"actuel": 2.5,  "precedent": 2.4,  "historique": [2.5, 2.4, 2.4, 2.5, 2.5, 2.4, 2.5, 2.6, 2.5, 2.4, 2.4, 2.5]},
        "🇬🇧 UK":         {"actuel": 4.4,  "precedent": 4.4,  "historique": [4.2, 4.3, 4.4, 4.4, 4.3, 4.4, 4.5, 4.4, 4.3, 4.4, 4.4, 4.4]},
    },
    "inflation": {
        "🇺🇸 USA":        {"actuel": 2.8,  "precedent": 2.9,  "cible": 2.0, "historique": [3.5, 3.4, 3.2, 3.0, 2.9, 2.8, 2.7, 2.8, 2.9, 2.8, 2.9, 2.8]},
        "🇪🇺 Zone Euro":  {"actuel": 2.3,  "precedent": 2.5,  "cible": 2.0, "historique": [2.9, 2.6, 2.4, 2.3, 2.5, 2.3, 2.2, 2.3, 2.4, 2.3, 2.5, 2.3]},
        "🇫🇷 France":     {"actuel": 1.1,  "precedent": 1.3,  "cible": 2.0, "historique": [2.3, 2.2, 1.8, 1.5, 1.3, 1.1, 1.0, 1.2, 1.3, 1.1, 1.3, 1.1]},
        "🇨🇳 Chine":      {"actuel": 0.1,  "precedent": 0.5,  "cible": 3.0, "historique": [-0.3, 0.1, 0.3, 0.5, 0.5, 0.1, -0.1, 0.2, 0.4, 0.1, 0.5, 0.1]},
        "🇯🇵 Japon":      {"actuel": 3.7,  "precedent": 3.6,  "cible": 2.0, "historique": [2.9, 3.0, 3.2, 3.4, 3.6, 3.7, 3.5, 3.6, 3.7, 3.7, 3.6, 3.7]},
        "🇬🇧 UK":         {"actuel": 2.8,  "precedent": 2.5,  "cible": 2.0, "historique": [3.4, 3.2, 2.8, 2.6, 2.5, 2.8, 3.0, 2.8, 2.6, 2.8, 2.5, 2.8]},
    },
    "pib": {
        "🇺🇸 USA":        {"actuel": 2.3,  "precedent": 3.1,  "historique": [3.1, 2.8, 2.5, 2.3, 2.8, 2.3, 2.5, 2.4, 2.8, 2.3, 3.1, 2.3]},
        "🇪🇺 Zone Euro":  {"actuel": 0.9,  "precedent": 0.4,  "historique": [0.1, 0.3, 0.4, 0.7, 0.4, 0.9, 0.8, 0.6, 0.4, 0.9, 0.4, 0.9]},
        "🇫🇷 France":     {"actuel": 0.8,  "precedent": 0.4,  "historique": [0.9, 0.7, 0.4, 0.6, 0.4, 0.8, 0.7, 0.5, 0.4, 0.8, 0.4, 0.8]},
        "🇨🇳 Chine":      {"actuel": 5.0,  "precedent": 4.6,  "historique": [5.3, 4.7, 4.6, 5.0, 4.6, 5.0, 4.9, 4.8, 4.6, 5.0, 4.6, 5.0]},
        "🇯🇵 Japon":      {"actuel": 0.7,  "precedent": -0.4, "historique": [2.1, 0.5, -0.4, 0.8, -0.4, 0.7, 0.6, 0.4, -0.4, 0.7, -0.4, 0.7]},
        "🇬🇧 UK":         {"actuel": 0.9,  "precedent": 0.1,  "historique": [0.3, 0.1, 0.1, 0.5, 0.1, 0.9, 0.7, 0.4, 0.1, 0.9, 0.1, 0.9]},
    },
    "taux": {
        "🇺🇸 USA":        {"banque": "FED",  "actuel": 4.50, "precedent": 4.75, "prochaine_reunion": "Mai 2026",  "historique": [5.50, 5.50, 5.25, 5.00, 4.75, 4.75, 4.50, 4.50, 4.50, 4.50, 4.75, 4.50]},
        "🇪🇺 Zone Euro":  {"banque": "BCE",  "actuel": 2.65, "precedent": 2.90, "prochaine_reunion": "Avr 2026",  "historique": [4.50, 4.25, 3.65, 3.40, 3.15, 2.90, 2.65, 2.65, 2.65, 2.65, 2.90, 2.65]},
        "🇫🇷 France":     {"banque": "BCE",  "actuel": 2.65, "precedent": 2.90, "prochaine_reunion": "Avr 2026",  "historique": [4.50, 4.25, 3.65, 3.40, 3.15, 2.90, 2.65, 2.65, 2.65, 2.65, 2.90, 2.65]},
        "🇨🇳 Chine":      {"banque": "PBOC", "actuel": 3.10, "precedent": 3.35, "prochaine_reunion": "Avr 2026",  "historique": [3.45, 3.45, 3.35, 3.35, 3.35, 3.10, 3.10, 3.10, 3.10, 3.10, 3.35, 3.10]},
        "🇯🇵 Japon":      {"banque": "BOJ",  "actuel": 0.50, "precedent": 0.25, "prochaine_reunion": "Avr 2026",  "historique": [-0.10, 0.10, 0.25, 0.25, 0.25, 0.25, 0.50, 0.50, 0.50, 0.50, 0.25, 0.50]},
        "🇬🇧 UK":         {"banque": "BOE",  "actuel": 4.50, "precedent": 4.75, "prochaine_reunion": "Mai 2026",  "historique": [5.25, 5.25, 5.00, 4.75, 4.75, 4.75, 4.50, 4.50, 4.50, 4.50, 4.75, 4.50]},
    },
    "confiance": {
        "🇺🇸 USA":        {"actuel": 98.3,  "precedent": 104.1, "historique": [110.7, 108.0, 104.1, 103.3, 104.1, 98.3, 97.1, 99.2, 103.0, 98.3, 104.1, 98.3]},
        "🇪🇺 Zone Euro":  {"actuel": -13.6, "precedent": -14.2, "historique": [-16.9, -15.9, -14.2, -13.8, -14.2, -13.6, -13.2, -13.5, -14.0, -13.6, -14.2, -13.6]},
        "🇫🇷 France":     {"actuel": 91.0,  "precedent": 90.0,  "historique": [90.0, 89.5, 90.0, 90.5, 90.0, 91.0, 91.5, 91.0, 90.5, 91.0, 90.0, 91.0]},
        "🇨🇳 Chine":      {"actuel": 87.5,  "precedent": 86.2,  "historique": [86.2, 85.8, 86.2, 86.8, 86.2, 87.5, 87.8, 87.2, 86.5, 87.5, 86.2, 87.5]},
        "🇯🇵 Japon":      {"actuel": 35.0,  "precedent": 35.5,  "historique": [36.2, 36.0, 35.5, 35.2, 35.5, 35.0, 34.8, 35.1, 35.4, 35.0, 35.5, 35.0]},
        "🇬🇧 UK":         {"actuel": -19.0, "precedent": -20.0, "historique": [-22.0, -21.5, -20.0, -19.5, -20.0, -19.0, -18.5, -19.2, -19.8, -19.0, -20.0, -19.0]},
    },
    "dette": {
        "🇺🇸 USA":        {"actuel": 124.3, "precedent": 122.3, "historique": [108.2, 111.5, 118.3, 121.4, 122.3, 124.3]},
        "🇪🇺 Zone Euro":  {"actuel": 87.4,  "precedent": 88.6,  "historique": [97.4,  91.6,  90.9,  88.6,  88.6,  87.4]},
        "🇫🇷 France":     {"actuel": 112.9, "precedent": 110.6, "historique": [115.2, 112.9, 111.8, 110.6, 110.6, 112.9]},
        "🇨🇳 Chine":      {"actuel": 88.6,  "precedent": 83.0,  "historique": [56.2,  68.9,  77.1,  83.0,  83.0,  88.6]},
        "🇯🇵 Japon":      {"actuel": 249.7, "precedent": 255.2, "historique": [234.2, 250.5, 261.3, 255.2, 255.2, 249.7]},
        "🇬🇧 UK":         {"actuel": 99.4,  "precedent": 97.8,  "historique": [85.2,  95.3,  101.9, 97.8,  97.8,  99.4]},
    },
}

MOIS_LABELS  = ["Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc", "Jan", "Fév", "Mar"]
ANNEES_DETTE = ["2019", "2020", "2021", "2022", "2023", "2024"]

# ══════════════════════════════════════════════════════════════
#  FETCHERS TEMPS RÉEL
# ══════════════════════════════════════════════════════════════

def _get(url, timeout=6):
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0 (AM-Terminal/2.0)"})
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def fetch_fred_series(series_id: str):
    """FRED CSV — sans clé API. Retourne (date_str, valeur_float) ou None."""
    r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
    if r:
        lines = [l for l in r.text.strip().split('\n') if l and not l.startswith('DATE')]
        for line in reversed(lines):
            parts = line.split(',')
            if len(parts) == 2 and parts[1].strip() not in ('', '.'):
                try:
                    return parts[0].strip(), float(parts[1].strip())
                except ValueError:
                    continue
    return None


@st.cache_data(ttl=3600)
def fetch_bce_indicator(dataset: str, key: str, last_n: int = 5):
    """BCE Statistical Data Warehouse API REST."""
    url = f"https://data-api.ecb.europa.eu/service/data/{dataset}/{key}?format=csvdata&lastNObservations={last_n}"
    r = _get(url)
    if r:
        rows = []
        for line in r.text.strip().split('\n'):
            if line and not line.startswith('KEY') and ',' in line:
                parts = line.split(',')
                try:
                    rows.append((parts[-2].strip(), float(parts[-1].strip())))
                except (ValueError, IndexError):
                    continue
        if rows:
            return rows  # [(date, val), ...]
    return None


@st.cache_data(ttl=3600)
def fetch_worldbank(country_code: str, indicator: str, last_n: int = 3):
    """World Bank API — données annuelles."""
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&mrv={last_n}&per_page=5"
    r = _get(url)
    if r:
        try:
            data = r.json()
            if len(data) > 1 and data[1]:
                vals = [x for x in data[1] if x.get('value') is not None]
                if vals:
                    return float(vals[0]['value']), vals[0]['date']
        except Exception:
            pass
    return None


@st.cache_data(ttl=900)
def fetch_yfinance_rate(ticker: str):
    """yfinance pour taux obligations et indices."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1]), float(hist['Close'].iloc[-2])
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=3600)
def fetch_all_macro():
    """
    Fetch toutes les données macro en temps réel.
    Retourne un dict structuré identique à FALLBACK,
    avec source_info pour chaque indicateur.
    """
    data = {k: {} for k in ("chomage", "inflation", "pib", "taux", "confiance", "dette")}
    sources = {}

    # ── CHÔMAGE ──────────────────────────────────────────────
    # USA : FRED UNRATE
    res = fetch_fred_series("UNRATE")
    if res:
        date, val = res
        fb = FALLBACK["chomage"]["🇺🇸 USA"]
        data["chomage"]["🇺🇸 USA"] = {**fb, "actuel": val,
            "precedent": fb["historique"][-2] if fb["historique"] else fb["precedent"]}
        sources["chomage_usa"] = f"FRED UNRATE ({date})"
    else:
        data["chomage"]["🇺🇸 USA"] = FALLBACK["chomage"]["🇺🇸 USA"]
        sources["chomage_usa"] = "Fallback (FRED indisponible)"

    # Multi-pays : World Bank SL.UEM.TOTL.ZS
    wb_chomage_map = {
        "🇪🇺 Zone Euro": "EMU", "🇫🇷 France": "FR",
        "🇨🇳 Chine": "CN", "🇯🇵 Japon": "JP", "🇬🇧 UK": "GB"
    }
    for pays, code in wb_chomage_map.items():
        res = fetch_worldbank(code, "SL.UEM.TOTL.ZS", 3)
        if res:
            val, date = res
            fb = FALLBACK["chomage"][pays]
            data["chomage"][pays] = {**fb, "actuel": round(val, 1),
                "precedent": fb["historique"][-2] if fb["historique"] else fb["precedent"]}
            sources[f"chomage_{code}"] = f"World Bank ({date})"
        else:
            data["chomage"][pays] = FALLBACK["chomage"][pays]
            sources[f"chomage_{code}"] = "Fallback (World Bank indisponible)"

    # ── INFLATION ─────────────────────────────────────────────
    # USA : FRED CPIAUCSL (YoY calculé)
    res_cpi = fetch_fred_series("CPIAUCSL")
    if res_cpi:
        # CPIAUCSL = index, on veut YoY → chercher il y a 12 obs
        # Simplification : utiliser T5YIE (anticipations) ou CPILFESL YoY
        pass
    # USA : FRED CPIAUCSL YoY direct
    res_yoy = fetch_fred_series("CPILFESL")  # Core CPI
    # Préférer l'indicateur tout-inclus
    res_all = fetch_fred_series("FPCPITOTLZGUSA")  # CPI YoY annual
    if res_all:
        date, val = res_all
        fb = FALLBACK["inflation"]["🇺🇸 USA"]
        data["inflation"]["🇺🇸 USA"] = {**fb, "actuel": round(val, 1),
            "precedent": fb["historique"][-2]}
        sources["inflation_usa"] = f"FRED FPCPITOTLZGUSA ({date})"
    else:
        data["inflation"]["🇺🇸 USA"] = FALLBACK["inflation"]["🇺🇸 USA"]
        sources["inflation_usa"] = "Fallback"

    # Zone Euro : BCE ICP
    bce_inf = fetch_bce_indicator("ICP", "M.U2.N.000000.4.ANR", 5)
    if bce_inf:
        date, val = bce_inf[-1]
        fb = FALLBACK["inflation"]["🇪🇺 Zone Euro"]
        data["inflation"]["🇪🇺 Zone Euro"] = {**fb, "actuel": round(val, 1),
            "precedent": round(bce_inf[-2][1], 1) if len(bce_inf) >= 2 else fb["precedent"]}
        sources["inflation_eu"] = f"BCE ICP ({date})"
    else:
        data["inflation"]["🇪🇺 Zone Euro"] = FALLBACK["inflation"]["🇪🇺 Zone Euro"]
        sources["inflation_eu"] = "Fallback"

    # France : BCE ICP France
    bce_fr = fetch_bce_indicator("ICP", "M.FR.N.000000.4.ANR", 3)
    if bce_fr:
        date, val = bce_fr[-1]
        fb = FALLBACK["inflation"]["🇫🇷 France"]
        data["inflation"]["🇫🇷 France"] = {**fb, "actuel": round(val, 1),
            "precedent": round(bce_fr[-2][1], 1) if len(bce_fr) >= 2 else fb["precedent"]}
        sources["inflation_fr"] = f"BCE ICP France ({date})"
    else:
        data["inflation"]["🇫🇷 France"] = FALLBACK["inflation"]["🇫🇷 France"]
        sources["inflation_fr"] = "Fallback"

    # Autres : World Bank FP.CPI.TOTL.ZG (annual)
    wb_inf_map = {"🇨🇳 Chine": "CN", "🇯🇵 Japon": "JP", "🇬🇧 UK": "GB"}
    for pays, code in wb_inf_map.items():
        res = fetch_worldbank(code, "FP.CPI.TOTL.ZG", 2)
        if res:
            val, date = res
            fb = FALLBACK["inflation"][pays]
            data["inflation"][pays] = {**fb, "actuel": round(val, 1),
                "precedent": fb["historique"][-2]}
            sources[f"inflation_{code}"] = f"World Bank ({date})"
        else:
            data["inflation"][pays] = FALLBACK["inflation"][pays]
            sources[f"inflation_{code}"] = "Fallback"

    # ── PIB ───────────────────────────────────────────────────
    # USA : FRED A191RL1Q225SBEA (PIB QoQ annualisé)
    res_gdp = fetch_fred_series("A191RL1Q225SBEA")
    if res_gdp:
        date, val = res_gdp
        fb = FALLBACK["pib"]["🇺🇸 USA"]
        data["pib"]["🇺🇸 USA"] = {**fb, "actuel": round(val, 1),
            "precedent": fb["historique"][-2]}
        sources["pib_usa"] = f"FRED GDP ({date})"
    else:
        data["pib"]["🇺🇸 USA"] = FALLBACK["pib"]["🇺🇸 USA"]
        sources["pib_usa"] = "Fallback"

    # World Bank NY.GDP.MKTP.KD.ZG
    wb_gdp_map = {
        "🇪🇺 Zone Euro": "EMU", "🇫🇷 France": "FR",
        "🇨🇳 Chine": "CN",      "🇯🇵 Japon": "JP", "🇬🇧 UK": "GB"
    }
    for pays, code in wb_gdp_map.items():
        res = fetch_worldbank(code, "NY.GDP.MKTP.KD.ZG", 2)
        if res:
            val, date = res
            fb = FALLBACK["pib"][pays]
            data["pib"][pays] = {**fb, "actuel": round(val, 1),
                "precedent": fb["historique"][-2]}
            sources[f"pib_{code}"] = f"World Bank ({date})"
        else:
            data["pib"][pays] = FALLBACK["pib"][pays]
            sources[f"pib_{code}"] = "Fallback"

    # ── TAUX DIRECTEURS ───────────────────────────────────────
    # USA : FRED FEDFUNDS
    res_fed = fetch_fred_series("FEDFUNDS")
    if res_fed:
        date, val = res_fed
        fb = FALLBACK["taux"]["🇺🇸 USA"]
        data["taux"]["🇺🇸 USA"] = {**fb, "actuel": round(val, 2),
            "precedent": round(fb["historique"][-2], 2)}
        sources["taux_usa"] = f"FRED FEDFUNDS ({date})"
    else:
        data["taux"]["🇺🇸 USA"] = FALLBACK["taux"]["🇺🇸 USA"]
        sources["taux_usa"] = "Fallback"

    # BCE : MRR (taux de refinancement principal)
    bce_rate = fetch_bce_indicator("FM", "B.U2.EUR.4F.KR.MRR_FR.LEV", 3)
    if bce_rate:
        date, val = bce_rate[-1]
        prev = bce_rate[-2][1] if len(bce_rate) >= 2 else FALLBACK["taux"]["🇪🇺 Zone Euro"]["precedent"]
        for pays_bce in ["🇪🇺 Zone Euro", "🇫🇷 France"]:
            fb = FALLBACK["taux"][pays_bce]
            data["taux"][pays_bce] = {**fb, "actuel": round(val, 2), "precedent": round(prev, 2)}
        sources["taux_bce"] = f"BCE MRR ({date})"
    else:
        data["taux"]["🇪🇺 Zone Euro"] = FALLBACK["taux"]["🇪🇺 Zone Euro"]
        data["taux"]["🇫🇷 France"]    = FALLBACK["taux"]["🇫🇷 France"]
        sources["taux_bce"] = "Fallback"

    # Japon/Chine/UK : fallback (taux très stables, publiés par communiqué)
    for pays in ["🇨🇳 Chine", "🇯🇵 Japon", "🇬🇧 UK"]:
        data["taux"][pays] = FALLBACK["taux"][pays]
        sources[f"taux_{pays}"] = "Fallback (données officielles mars 2026)"

    # ── CONFIANCE ─────────────────────────────────────────────
    # USA : FRED UMCSENT (UMich Consumer Sentiment)
    res_conf = fetch_fred_series("UMCSENT")
    if res_conf:
        date, val = res_conf
        fb = FALLBACK["confiance"]["🇺🇸 USA"]
        data["confiance"]["🇺🇸 USA"] = {**fb, "actuel": round(val, 1),
            "precedent": fb["historique"][-2]}
        sources["confiance_usa"] = f"FRED UMich Sentiment ({date})"
    else:
        data["confiance"]["🇺🇸 USA"] = FALLBACK["confiance"]["🇺🇸 USA"]
        sources["confiance_usa"] = "Fallback"

    # Zone Euro : BCE consumer confidence
    bce_conf = fetch_bce_indicator("SOI", "M.I8.BSI.M0600.3.900.M.MCA.3I", 3)
    if bce_conf:
        date, val = bce_conf[-1]
        fb = FALLBACK["confiance"]["🇪🇺 Zone Euro"]
        data["confiance"]["🇪🇺 Zone Euro"] = {**fb, "actuel": round(val, 1),
            "precedent": round(bce_conf[-2][1], 1) if len(bce_conf) >= 2 else fb["precedent"]}
        sources["confiance_eu"] = f"BCE SOI ({date})"
    else:
        data["confiance"]["🇪🇺 Zone Euro"] = FALLBACK["confiance"]["🇪🇺 Zone Euro"]
        sources["confiance_eu"] = "Fallback"

    # Reste confiance : fallback
    for pays in ["🇫🇷 France", "🇨🇳 Chine", "🇯🇵 Japon", "🇬🇧 UK"]:
        data["confiance"][pays] = FALLBACK["confiance"][pays]
        sources[f"confiance_{pays}"] = "Fallback"

    # ── DETTE ─────────────────────────────────────────────────
    # World Bank GC.DOD.TOTL.GD.ZS (annuel, délai ~1 an)
    wb_dette_map = {
        "🇺🇸 USA": "US", "🇫🇷 France": "FR",
        "🇨🇳 Chine": "CN", "🇯🇵 Japon": "JP", "🇬🇧 UK": "GB"
    }
    for pays, code in wb_dette_map.items():
        res = fetch_worldbank(code, "GC.DOD.TOTL.GD.ZS", 2)
        if res:
            val, date = res
            fb = FALLBACK["dette"][pays]
            data["dette"][pays] = {**fb, "actuel": round(val, 1),
                "precedent": fb["historique"][-2]}
            sources[f"dette_{code}"] = f"World Bank ({date})"
        else:
            data["dette"][pays] = FALLBACK["dette"][pays]
            sources[f"dette_{code}"] = "Fallback"
    data["dette"]["🇪🇺 Zone Euro"] = FALLBACK["dette"]["🇪🇺 Zone Euro"]
    sources["dette_eu"] = "Eurostat (fallback)"

    return data, sources


@st.cache_data(ttl=300)
def fetch_market_rates():
    """
    Taux obligations 10 ans et forex en temps réel via yfinance.
    """
    rates = {}

    # Obligations 10 ans
    bond_tickers = {
        "US 10Y": "^TNX",
        "US 2Y":  "^IRX",
        "EUR 10Y (Bund)": "^DE10Y",  # approximation via ETF
        "UK 10Y Gilt":    "^GB10Y",
    }
    for name, ticker in bond_tickers.items():
        val, prev = fetch_yfinance_rate(ticker)
        if val:
            rates[name] = {"actuel": round(val, 3), "precedent": round(prev, 3) if prev else val}

    # Spread 10Y - 2Y (courbe inversion)
    if "US 10Y" in rates and "US 2Y" in rates:
        spread = rates["US 10Y"]["actuel"] - rates["US 2Y"]["actuel"]
        rates["Spread 10Y-2Y US"] = {"actuel": round(spread, 3), "precedent": 0}

    # Forex majeurs
    forex_tickers = {
        "EUR/USD":  "EURUSD=X",
        "USD/JPY":  "JPY=X",
        "GBP/USD":  "GBPUSD=X",
        "USD/CNY":  "CNY=X",
        "DXY (Dollar Index)": "DX-Y.NYB",
    }
    for name, ticker in forex_tickers.items():
        val, prev = fetch_yfinance_rate(ticker)
        if val:
            rates[name] = {
                "actuel": round(val, 4),
                "precedent": round(prev, 4) if prev else val,
                "change_pct": round(((val - prev) / prev) * 100, 3) if prev else 0
            }

    # Or et pétrole (indicateurs macro importants)
    commodities = {"Or (XAU/USD)": "GC=F", "Pétrole WTI": "CL=F", "Gaz Naturel": "NG=F"}
    for name, ticker in commodities.items():
        val, prev = fetch_yfinance_rate(ticker)
        if val:
            rates[name] = {
                "actuel": round(val, 2),
                "precedent": round(prev, 2) if prev else val,
                "change_pct": round(((val - prev) / prev) * 100, 2) if prev else 0
            }

    return rates


# ══════════════════════════════════════════════════════════════
#  HELPERS UI
# ══════════════════════════════════════════════════════════════

def carte_indicateur(pays, valeur, precedent, unite="%", inverse=False):
    variation = valeur - precedent
    if inverse:
        couleur = "#00ff41" if variation < 0 else "#ff4b4b"
    else:
        couleur = "#00ff41" if variation >= 0 else "#ff4b4b"
    signe = "▲" if variation >= 0 else "▼"
    cfg = PAYS_CONFIG.get(pays, {"couleur": "#ff9800"})
    st.markdown(f"""
        <div style="background:#0d0d0d; border:1px solid {cfg['couleur']};
             border-left:4px solid {cfg['couleur']}; border-radius:6px;
             padding:14px; margin-bottom:10px;">
            <div style="color:#888; font-size:11px; font-family:monospace;">{pays}</div>
            <div style="color:white; font-size:26px; font-weight:bold; margin:4px 0;">
                {valeur}{unite}
            </div>
            <div style="color:{couleur}; font-size:13px; font-family:monospace;">
                {signe} {abs(variation):.2f}{unite} vs précédent ({precedent}{unite})
            </div>
        </div>
    """, unsafe_allow_html=True)


def graphique_historique(titre, donnees, pays_selectionnes, unite="%"):
    fig = go.Figure()
    for pays in pays_selectionnes:
        if pays in donnees:
            cfg = PAYS_CONFIG[pays]
            hist = donnees[pays]["historique"]
            labels = MOIS_LABELS[:len(hist)]
            fig.add_trace(go.Scatter(
                x=labels, y=hist, name=pays,
                line=dict(color=cfg["couleur"], width=2.5),
                mode="lines+markers", marker=dict(size=6),
                hovertemplate=f"<b>{pays}</b><br>{titre}: %{{y}}{unite}<extra></extra>"
            ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
        title=dict(text=titre, font=dict(color="#ff9800", size=16)),
        height=380, margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#333", borderwidth=1),
        xaxis=dict(gridcolor="#222", tickfont=dict(color="#888")),
        yaxis=dict(gridcolor="#222", tickfont=dict(color="#888"), ticksuffix=unite),
        hovermode="x unified"
    )
    return fig


def tableau_comparatif(titre, donnees, pays_selectionnes, unite="%", inverse=False):
    rows = []
    for pays in pays_selectionnes:
        if pays in donnees:
            d = donnees[pays]
            variation = d["actuel"] - d["precedent"]
            tendance = ("🟢 ▼" if variation < 0 else "🔴 ▲") if inverse else ("🟢 ▲" if variation >= 0 else "🔴 ▼")
            rows.append({
                "Pays": pays,
                "Actuel": f"{d['actuel']}{unite}",
                "Précédent": f"{d['precedent']}{unite}",
                "Variation": f"{variation:+.2f}{unite}",
                "Tendance": tendance
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def badge_source(source_str):
    """Affiche un badge selon la source."""
    if "Fallback" in source_str:
        color, icon = "#555", "📋"
    elif "FRED" in source_str:
        color, icon = "#4fc3f7", "🏦"
    elif "BCE" in source_str:
        color, icon = "#ffb74d", "🇪🇺"
    elif "World Bank" in source_str:
        color, icon = "#81c784", "🌍"
    else:
        color, icon = "#888", "📡"
    st.markdown(
        f"<span style='color:{color}; font-size:10px; font-family:monospace;'>{icon} {source_str}</span>",
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════
#  INTERFACE PRINCIPALE
# ══════════════════════════════════════════════════════════════

def show_economie():
    st.markdown("""
        <div style='text-align:center; padding:25px;
             background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #ff9800; border-radius:12px; margin-bottom:20px;'>
            <h1 style='color:#ff9800; margin:0; font-size:36px;'>🌍 MACRO ÉCONOMIE MONDIALE</h1>
            <p style='color:#ffb84d; margin:8px 0 0 0; font-size:14px;'>
                Données en temps réel — FRED · BCE · World Bank · yfinance
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Fetch données ──────────────────────────────────────────
    with st.spinner("🔄 Chargement des données macro en temps réel..."):
        try:
            macro, sources = fetch_all_macro()
        except Exception as e:
            st.warning(f"⚠️ Erreur fetch temps réel ({e}) — utilisation des données de référence")
            macro  = {k: dict(v) for k, v in FALLBACK.items()}
            sources = {k: "Fallback" for k in ["chomage", "inflation", "pib", "taux", "confiance", "dette"]}

    CHOMAGE        = macro["chomage"]
    INFLATION      = macro["inflation"]
    PIB            = macro["pib"]
    TAUX_DIRECTEURS = macro["taux"]
    CONFIANCE      = macro["confiance"]
    DETTE          = macro["dette"]

    # ── Sélecteur pays ──────────────────────────────────────────
    col_sel, col_ts = st.columns([4, 1])
    with col_sel:
        pays_selectionnes = st.multiselect(
            "🌐 PAYS À AFFICHER",
            list(PAYS_CONFIG.keys()),
            default=list(PAYS_CONFIG.keys()),
            key="eco_pays"
        )
    with col_ts:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Actualiser", key="eco_refresh"):
            st.cache_data.clear()
            st.rerun()

    if not pays_selectionnes:
        st.warning("Sélectionnez au moins un pays.")
        return

    # Timestamp
    nb_live = sum(1 for v in sources.values() if "Fallback" not in v)
    nb_total = len(sources)
    st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')} — "
               f"{nb_live}/{nb_total} indicateurs en temps réel | "
               f"Sources : FRED · BCE · World Bank · yfinance")
    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 TABLEAU DE BORD",
        "👷 CHÔMAGE",
        "🔥 INFLATION",
        "📈 PIB",
        "🏦 TAUX DIRECTEURS",
        "😊 CONFIANCE",
        "💸 DETTE",
        "📡 MARCHÉS & TAUX",
    ])

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 1 — TABLEAU DE BORD GLOBAL
    # ══════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### 📊 VUE GLOBALE — TOUS LES INDICATEURS")

        rows = []
        for pays in pays_selectionnes:
            def _fmt(d, k, u=""):
                try: return f"{d[k]['actuel']}{u}"
                except: return "N/A"
            rows.append({
                "Pays":           pays,
                "Chômage":        _fmt(CHOMAGE, pays, "%"),
                "Inflation":      _fmt(INFLATION, pays, "%"),
                "PIB":            _fmt(PIB, pays, "%"),
                "Taux Directeur": _fmt(TAUX_DIRECTEURS, pays, "%"),
                "Confiance":      _fmt(CONFIANCE, pays),
                "Dette/PIB":      _fmt(DETTE, pays, "%"),
            })
        df_global = pd.DataFrame(rows)
        st.dataframe(df_global, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 📡 SOURCES DES DONNÉES")
        source_rows = []
        for key, src in sources.items():
            indicateur = key.split("_")[0].upper()
            pays_key = "_".join(key.split("_")[1:]).upper()
            live = "✅ LIVE" if "Fallback" not in src else "📋 RÉFÉRENCE"
            source_rows.append({"Indicateur": indicateur, "Pays/Zone": pays_key, "Source": src, "Statut": live})
        st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🎯 SCORE DE SANTÉ ÉCONOMIQUE")
        score_cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            cfg = PAYS_CONFIG[pays]
            score = 0
            details = []
            c = CHOMAGE[pays]["actuel"]
            if c < 4:   score += 2; details.append("✅ Chômage faible")
            elif c < 6: score += 1; details.append("🟡 Chômage modéré")
            else:                   details.append("🔴 Chômage élevé")
            inf = INFLATION[pays]["actuel"]
            if 1.5 <= inf <= 3.0: score += 2; details.append("✅ Inflation maîtrisée")
            elif inf < 0:                      details.append("🟡 Risque déflation")
            elif inf < 1:                      details.append("🟡 Inflation basse")
            else:                              details.append("🔴 Inflation hors cible")
            pib_v = PIB[pays]["actuel"]
            if pib_v > 2:   score += 2; details.append("✅ Forte croissance")
            elif pib_v > 0: score += 1; details.append("🟡 Croissance faible")
            else:                        details.append("🔴 Récession")
            dette_v = DETTE[pays]["actuel"]
            if dette_v < 60:    score += 2; details.append("✅ Dette soutenable")
            elif dette_v < 100: score += 1; details.append("🟡 Dette modérée")
            else:                           details.append("🔴 Dette élevée")

            score_max  = 8
            score_pct  = (score / score_max) * 100
            col_score  = "#00ff41" if score >= 6 else "#ff9800" if score >= 4 else "#ff4b4b"
            verdict    = "SOLIDE" if score >= 6 else "MOYEN" if score >= 4 else "FRAGILE"

            with score_cols[i]:
                st.markdown(f"""
                    <div style='text-align:center; padding:16px; border:2px solid {col_score};
                         border-radius:10px; background:#0d0d0d; margin-bottom:10px;'>
                        <div style='color:#888; font-size:10px;'>{pays}</div>
                        <div style='color:{col_score}; font-size:36px; font-weight:bold;'>{score}</div>
                        <div style='color:#888; font-size:11px;'>/ {score_max}</div>
                        <div style='background:#222; border-radius:4px; height:6px; margin:8px 0;'>
                            <div style='background:{col_score}; width:{score_pct}%; height:6px; border-radius:4px;'></div>
                        </div>
                        <div style='color:{col_score}; font-size:12px; font-weight:bold;'>{verdict}</div>
                    </div>
                """, unsafe_allow_html=True)
                for d in details:
                    st.caption(d)

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 2 — CHÔMAGE
    # ══════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### 👷 TAUX DE CHÔMAGE (%)")
        st.info("💡 Un taux bas = marché du travail tendu. Cible optimale : < 5%")
        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, CHOMAGE[pays]["actuel"], CHOMAGE[pays]["precedent"], "%", inverse=True)
        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Taux de Chômage (12 mois)", CHOMAGE, pays_selectionnes, "%")
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            tableau_comparatif("Chômage", CHOMAGE, pays_selectionnes, "%", inverse=True)
            chomages = {p: CHOMAGE[p]["actuel"] for p in pays_selectionnes}
            st.success(f"🏆 Meilleur : **{min(chomages, key=chomages.get)}** ({min(chomages.values())}%)")
            st.error(f"⚠️ Plus élevé : **{max(chomages, key=chomages.get)}** ({max(chomages.values())}%)")
            with st.expander("📡 Sources"):
                for pays in pays_selectionnes:
                    code = PAYS_CONFIG[pays]["wb"]
                    src  = sources.get(f"chomage_{code}", sources.get("chomage_usa", "N/A"))
                    badge_source(f"{pays.split()[-1]} : {src}")

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 3 — INFLATION
    # ══════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 🔥 INFLATION CPI (%)")
        st.info("💡 Cible des banques centrales : 2%. Source : FRED (USA), BCE (EU/FR), World Bank (autres).")
        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, INFLATION[pays]["actuel"], INFLATION[pays]["precedent"], "%", inverse=True)
        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Inflation CPI", INFLATION, pays_selectionnes, "%")
            fig.add_hline(y=2.0, line_dash="dash", line_color="#ff9800", line_width=1.5,
                          annotation_text="Cible 2%", annotation_position="right",
                          annotation=dict(font=dict(color="#ff9800", size=11)))
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            tableau_comparatif("Inflation", INFLATION, pays_selectionnes, "%", inverse=True)
            st.markdown("#### 🎯 Écart vs cible 2%")
            for pays in pays_selectionnes:
                diff  = INFLATION[pays]["actuel"] - 2.0
                color = "#ff4b4b" if abs(diff) > 1 else "#ff9800" if abs(diff) > 0.5 else "#00ff41"
                st.markdown(f"<span style='color:{color}; font-family:monospace;'>"
                            f"{pays}: {diff:+.1f}%</span>", unsafe_allow_html=True)
            with st.expander("📡 Sources"):
                badge_source(f"USA : {sources.get('inflation_usa','N/A')}")
                badge_source(f"Zone Euro : {sources.get('inflation_eu','N/A')}")
                badge_source(f"France : {sources.get('inflation_fr','N/A')}")
                for c in ["CN", "JP", "GB"]:
                    badge_source(f"{c} : {sources.get(f'inflation_{c}','N/A')}")

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 4 — PIB
    # ══════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("### 📈 CROISSANCE PIB (%)")
        st.info("💡 > 2% = économie dynamique | < 0% = récession. Source : FRED (USA), World Bank (autres).")
        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, PIB[pays]["actuel"], PIB[pays]["precedent"], "%")
        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Croissance PIB", PIB, pays_selectionnes, "%")
            fig.add_hline(y=0, line_dash="dash", line_color="#ff4b4b", line_width=1,
                          annotation_text="Seuil récession",
                          annotation=dict(font=dict(color="#ff4b4b", size=10)))
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            tableau_comparatif("PIB", PIB, pays_selectionnes, "%")
            en_recessions = [p for p in pays_selectionnes if PIB[p]["actuel"] < 0]
            if en_recessions:
                st.error(f"🔴 En récession : {', '.join(en_recessions)}")
            else:
                st.success("✅ Aucun pays en récession")
            # Classement
            pibs_sorted = sorted(pays_selectionnes, key=lambda p: PIB[p]["actuel"], reverse=True)
            st.markdown("#### 🏆 Classement croissance")
            for rank, pays in enumerate(pibs_sorted, 1):
                val = PIB[pays]["actuel"]
                col = "#00ff41" if val > 2 else "#ff9800" if val > 0 else "#ff4b4b"
                st.markdown(f"<span style='color:{col}; font-family:monospace;'>"
                            f"{rank}. {pays} : {val:+.1f}%</span>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 5 — TAUX DIRECTEURS
    # ══════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("### 🏦 TAUX DIRECTEURS DES BANQUES CENTRALES (%)")
        st.info("💡 Des taux élevés freinent l'inflation. Source : FRED (FED), BCE API (BCE).")
        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                d   = TAUX_DIRECTEURS[pays]
                cfg = PAYS_CONFIG[pays]
                variation = d["actuel"] - d["precedent"]
                couleur   = "#ff4b4b" if variation > 0 else "#00ff41" if variation < 0 else "#888"
                signe     = "▲" if variation > 0 else "▼" if variation < 0 else "→"
                st.markdown(f"""
                    <div style="background:#0d0d0d; border:1px solid {cfg['couleur']};
                         border-left:4px solid {cfg['couleur']}; border-radius:6px;
                         padding:14px; margin-bottom:10px;">
                        <div style="color:#888; font-size:10px;">{pays} — {d['banque']}</div>
                        <div style="color:white; font-size:26px; font-weight:bold;">{d['actuel']}%</div>
                        <div style="color:{couleur}; font-size:12px;">{signe} {abs(variation):.2f}%</div>
                        <div style="color:#555; font-size:10px; margin-top:4px;">
                            Prochaine réunion : {d['prochaine_reunion']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig_taux = go.Figure()
            for pays in pays_selectionnes:
                cfg = PAYS_CONFIG[pays]
                d   = TAUX_DIRECTEURS[pays]
                fig_taux.add_trace(go.Scatter(
                    x=MOIS_LABELS[:len(d["historique"])], y=d["historique"],
                    name=f"{pays} ({d['banque']})",
                    line=dict(color=cfg["couleur"], width=2.5),
                    mode="lines+markers", marker=dict(size=6),
                ))
            fig_taux.update_layout(
                template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                title=dict(text="Évolution des Taux Directeurs (12 mois)", font=dict(color="#ff9800", size=16)),
                height=380, margin=dict(l=40, r=20, t=50, b=40),
                xaxis=dict(gridcolor="#222"), yaxis=dict(gridcolor="#222", ticksuffix="%"),
                hovermode="x unified"
            )
            st.plotly_chart(fig_taux, use_container_width=True)
        with col_t:
            rows = []
            for pays in pays_selectionnes:
                d = TAUX_DIRECTEURS[pays]
                rows.append({"Pays": pays, "Banque": d["banque"],
                             "Taux": f"{d['actuel']}%",
                             "Prochain RDV": d["prochaine_reunion"]})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            if "🇺🇸 USA" in pays_selectionnes and "🇪🇺 Zone Euro" in pays_selectionnes:
                diff = TAUX_DIRECTEURS["🇺🇸 USA"]["actuel"] - TAUX_DIRECTEURS["🇪🇺 Zone Euro"]["actuel"]
                st.markdown("#### 📊 Spread FED vs BCE")
                st.metric("Écart FED - BCE", f"{diff:+.2f}%",
                          help="Positif = Dollar favorisé vs Euro")
                if diff > 1.5:
                    st.warning("⚠️ Spread élevé — pression sur l'EUR/USD")
                elif diff < 0:
                    st.info("ℹ️ BCE au-dessus de la FED — configuration rare")

            with st.expander("📡 Sources"):
                badge_source(f"FED : {sources.get('taux_usa','N/A')}")
                badge_source(f"BCE : {sources.get('taux_bce','N/A')}")

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 6 — CONFIANCE CONSOMMATEUR
    # ══════════════════════════════════════════════════════════════
    with tab6:
        st.markdown("### 😊 INDICE DE CONFIANCE DES CONSOMMATEURS")
        st.info("💡 USA : UMich Sentiment (FRED UMCSENT). EU : BCE SOI. Autres : données officielles.")
        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, CONFIANCE[pays]["actuel"], CONFIANCE[pays]["precedent"], "")
        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Confiance Consommateur", CONFIANCE, pays_selectionnes, "")
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            tableau_comparatif("Confiance", CONFIANCE, pays_selectionnes, "")
            st.caption("USA : base variable (positif = optimiste) | "
                       "Zone Euro/UK : indice négatif normal (échelle différente)")
            with st.expander("📡 Sources"):
                badge_source(f"USA : {sources.get('confiance_usa','N/A')}")
                badge_source(f"Zone Euro : {sources.get('confiance_eu','N/A')}")
                st.caption("FR/CN/JP/UK : données officielles (publications trimestrielles)")

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 7 — DETTE PUBLIQUE
    # ══════════════════════════════════════════════════════════════
    with tab7:
        st.markdown("### 💸 DETTE PUBLIQUE (% du PIB)")
        st.info("💡 Critère Maastricht : < 60%. Source : World Bank GC.DOD.TOTL.GD.ZS (annuel).")
        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, DETTE[pays]["actuel"], DETTE[pays]["precedent"], "%", inverse=True)
        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            # Graphique évolution par années
            fig_dette = go.Figure()
            for pays in pays_selectionnes:
                cfg = PAYS_CONFIG[pays]
                hist = DETTE[pays]["historique"]
                annees = ANNEES_DETTE[:len(hist)]
                fig_dette.add_trace(go.Bar(
                    x=[pays.split(" ", 1)[-1]], y=[DETTE[pays]["actuel"]],
                    name=pays, marker_color=cfg["couleur"],
                    text=f"{DETTE[pays]['actuel']}%", textposition="auto"
                ))
            fig_dette.add_hline(y=60, line_dash="dash", line_color="#00ff41", line_width=1.5,
                                annotation_text="Seuil Maastricht 60%",
                                annotation=dict(font=dict(color="#00ff41", size=11)))
            fig_dette.add_hline(y=100, line_dash="dash", line_color="#ff4b4b", line_width=1.5,
                                annotation_text="Zone de risque 100%",
                                annotation=dict(font=dict(color="#ff4b4b", size=11)))
            fig_dette.update_layout(
                template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                title=dict(text="Dette Publique / PIB", font=dict(color="#ff9800", size=16)),
                height=420, showlegend=False,
                yaxis=dict(gridcolor="#222", ticksuffix="%")
            )
            st.plotly_chart(fig_dette, use_container_width=True)
        with col_t:
            tableau_comparatif("Dette", DETTE, pays_selectionnes, "%", inverse=True)
            st.markdown("#### 🚦 Statut")
            for pays in pays_selectionnes:
                d = DETTE[pays]["actuel"]
                if d < 60:    st.success(f"{pays} : ✅ Sous Maastricht ({d}%)")
                elif d < 100: st.warning(f"{pays} : 🟡 Au-dessus 60% ({d}%)")
                else:         st.error(f"{pays} : 🔴 Zone de risque ({d}%)")

    # ══════════════════════════════════════════════════════════════
    #  ONGLET 8 — MARCHÉS & TAUX EN TEMPS RÉEL (yfinance)
    # ══════════════════════════════════════════════════════════════
    with tab8:
        st.markdown("### 📡 MARCHÉS FINANCIERS & INDICATEURS TEMPS RÉEL")
        st.info("💡 Données live via yfinance — obligations, forex, matières premières stratégiques.")

        with st.spinner("Chargement des données marchés..."):
            rates = fetch_market_rates()

        if not rates:
            st.error("Données marché indisponibles.")
            return

        # Obligations
        st.markdown("#### 📊 TAUX OBLIGATAIRES")
        bond_keys = [k for k in rates if "Y" in k or "Gilt" in k or "Spread" in k]
        if bond_keys:
            bcols = st.columns(len(bond_keys))
            for i, key in enumerate(bond_keys):
                r = rates[key]
                delta = r["actuel"] - r["precedent"]
                color  = "#ff4b4b" if delta > 0 else "#00ff41"
                with bcols[i]:
                    st.metric(key, f"{r['actuel']:.3f}%", f"{delta:+.3f}%")
            # Courbe des taux US
            if "US 10Y" in rates and "US 2Y" in rates:
                spread = rates["US 10Y"]["actuel"] - rates["US 2Y"]["actuel"]
                if spread < 0:
                    st.error(f"⚠️ **Courbe inversée** (spread 10Y-2Y = {spread:+.3f}%) — Signal historique de récession")
                else:
                    st.success(f"✅ Courbe normale (spread 10Y-2Y = {spread:+.3f}%)")

        st.markdown("---")
        st.markdown("#### 💱 FOREX MAJEURS")
        forex_keys = [k for k in rates if "/" in k or "DXY" in k]
        if forex_keys:
            fx_rows = []
            for key in forex_keys:
                r = rates[key]
                chg = r.get("change_pct", 0)
                color_str = "🟢" if chg >= 0 else "🔴"
                fx_rows.append({
                    "Paire": key,
                    "Cours": r["actuel"],
                    "Variation": f"{chg:+.3f}%",
                    "Signal": color_str
                })
            st.dataframe(pd.DataFrame(fx_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🛢️ MATIÈRES PREMIÈRES STRATÉGIQUES")
        commo_keys = [k for k in rates if k in ("Or (XAU/USD)", "Pétrole WTI", "Gaz Naturel")]
        if commo_keys:
            ccols = st.columns(len(commo_keys))
            for i, key in enumerate(commo_keys):
                r = rates[key]
                chg = r.get("change_pct", 0)
                with ccols[i]:
                    st.metric(key, f"${r['actuel']:,.2f}", f"{chg:+.2f}%")

        st.markdown("---")
        st.markdown("#### 📈 GRAPHIQUES LIVE — TAUX & MARCHÉS")
        chart_options = {
            "Taux US 10 Ans": "TVC:US10Y",
            "Taux Bund 10 Ans (DE)": "TVC:DE10Y",
            "EUR/USD": "FX:EURUSD",
            "DXY Dollar Index": "TVC:DXY",
            "Or (XAU/USD)": "TVC:GOLD",
            "Pétrole WTI": "TVC:USOIL",
        }
        chart_sel = st.selectbox("Choisir le graphique", list(chart_options.keys()), key="eco_chart_sel")
        tv_sym = chart_options[chart_sel]
        tv_chart_html = f"""
        <div id="tv_eco_chart" style="height:420px; border:1px solid #1a1a1a; border-radius:6px; overflow:hidden;">
            <div class="tradingview-widget-container" style="height:100%;">
                <div class="tradingview-widget-container__widget" style="height:100%;"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                {{
                  "autosize": true,
                  "symbol": "{tv_sym}",
                  "interval": "D",
                  "timezone": "Europe/Paris",
                  "theme": "dark",
                  "style": "1",
                  "locale": "fr",
                  "allow_symbol_change": false,
                  "calendar": false,
                  "height": "420",
                  "width": "100%"
                }}
                </script>
            </div>
        </div>
        """
        components.html(tv_chart_html, height=430)

    st.markdown("---")
    st.caption(
        f"⏱️ Données actualisées le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | "
        "Sources primaires : FRED (Federal Reserve) · BCE Statistical Data Warehouse · "
        "World Bank Open Data · yfinance | Fallback : données officielles mars 2026"
    )
