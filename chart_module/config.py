# ============================================================
#  chart_module/config.py  — Configuration centrale
# ============================================================

# ── SOURCE DE DONNÉES ─────────────────────────────────────
# "coingecko" | "binance" | "bybit" | "yfinance" | "kraken" | "mock"
DATA_SOURCE = "binance"    # ← CoinGecko, gratuit, sans clé API

# ── PARAMÈTRES PAR DÉFAUT ─────────────────────────────────
DEFAULT_SYMBOL   = "BTCUSDT"  # ID CoinGecko : bitcoin, ethereum, solana...
DEFAULT_INTERVAL = "4h"       # 1h | 4h | 1d | 7d
DEFAULT_LIMIT    = 150

# ── FALLBACK ──────────────────────────────────────────────
FALLBACK_TO_MOCK = True      # Si CoinGecko échoue → mock auto

# ── DIMENSIONS ────────────────────────────────────────────
CHART_HEIGHT  = 420
VOLUME_HEIGHT = 70
BOTTOM_BAR_H  = 52

# ── STYLE Arthur Trading ──────────────────────────────────
COLORS = {
    "bg":       "#000000",
    "surface":  "#0A0A0A",
    "surface2": "#111111",
    "border":   "#1A1A1A",
    "border2":  "#2D2D30",
    "text":     "#FFFFFF",
    "text2":    "#CCCCCC",
    "muted":    "#999999",
    "faint":    "#666666",
    "fainter":  "#444444",
    "orange":   "#FF9500",
    "yellow":   "#FABE2C",
    "green":    "#00C853",
    "green2":   "#00ffad",
    "red":      "#FF3B30",
    "red2":     "#ff4b4b",
}

# ── TABLE ID COINGECKO ────────────────────────────────────
# Correspondance symbole court → ID CoinGecko
COINGECKO_IDS = {
    "BTC":  "bitcoin",
    "ETH":  "ethereum",
    "SOL":  "solana",
    "BNB":  "binancecoin",
    "XRP":  "ripple",
    "ADA":  "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "DOT":  "polkadot",
    "MATIC":"matic-network",
    "UNI":  "uniswap",
    "LTC":  "litecoin",
    "ATOM": "cosmos",
    "NEAR": "near",
}
