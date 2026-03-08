"""
utils.py — AM-Trading Terminal
Fonctions partagées entre app.py, Terminal.py et tous les modules.
Remplace les imports circulaires `import app as _app`.

USAGE dans n'importe quel module :
    from utils import (
        _get, _card, _axis,
        PLOTLY_BASE, PLOTLY_PIE,
        get_coin_details, get_top_coins, get_coin_market_chart,
        get_global_data, get_binance_funding_rates,
        get_open_interest_data, get_binance_liquidations,
        get_defi_yields, get_defi_protocols, get_exchange_flows,
        show_onchain, show_liquidations, show_staking, show_order_book_ui,
    )
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time


# ══════════════════════════════════════════════════════════════
#  HTTP HELPER
# ══════════════════════════════════════════════════════════════

def _get(url, params=None, retries=2, timeout=10):
    for _ in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0 (AM-Terminal/2.0)"})
            if r.status_code == 429:
                time.sleep(2)
                continue
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════
#  STYLES PLOTLY PARTAGÉS
# ══════════════════════════════════════════════════════════════

PLOTLY_BASE = dict(
    template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#0a0a0a",
    font=dict(color="#4d9fff", family="Courier New"),
    legend=dict(bgcolor="rgba(0,0,0,0.7)", bordercolor="#333", borderwidth=1),
    margin=dict(l=50, r=20, t=50, b=40),
)

PLOTLY_PIE = dict(
    template="plotly_dark", paper_bgcolor="#000000",
    font=dict(color="#4d9fff", family="Courier New"),
    legend=dict(bgcolor="rgba(0,0,0,0.7)", bordercolor="#333", borderwidth=1),
    margin=dict(l=20, r=20, t=50, b=20),
)

def _axis():
    return dict(gridcolor="#1a1a1a", showgrid=True, zeroline=False)

def _card(titre, valeur, sous_titre="", couleur="#ff9800"):
    st.markdown(f"""
        <div style="background:#0d0d0d;border:1px solid {couleur};border-left:4px solid {couleur};
             border-radius:6px;padding:14px;margin-bottom:10px;">
            <div style="color:#4d9fff;font-size:11px;font-family:monospace;">{titre}</div>
            <div style="color:white;font-size:22px;font-weight:bold;margin:4px 0;">{valeur}</div>
            <div style="color:{couleur};font-size:12px;font-family:monospace;">{sous_titre}</div>
        </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  FONCTIONS DONNÉES — COINGECKO
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=120)
def get_coin_details(coin_id):
    return _get(f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                params={"localization": "false", "tickers": "false",
                        "community_data": "true", "developer_data": "false"})

@st.cache_data(ttl=60)
def get_top_coins(limit=30):
    return _get("https://api.coingecko.com/api/v3/coins/markets",
                params={"vs_currency": "usd", "order": "market_cap_desc",
                        "per_page": limit, "page": 1,
                        "price_change_percentage": "1h,24h,7d"}) or []

@st.cache_data(ttl=120)
def get_coin_market_chart(coin_id, days=30):
    return _get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": days}) or {}

@st.cache_data(ttl=60)
def get_global_data():
    data = _get("https://api.coingecko.com/api/v3/global")
    return data.get("data", {}) if data else {}

@st.cache_data(ttl=300)
def get_defi_yields():
    data = _get("https://yields.llama.fi/pools") or {}
    pools = data.get("data", [])
    return sorted([p for p in pools if p.get("apy", 0) and p.get("tvlUsd", 0) > 1_000_000],
                  key=lambda x: x.get("apy", 0), reverse=True)

@st.cache_data(ttl=300)
def get_defi_protocols():
    return _get("https://api.llama.fi/protocols") or []

@st.cache_data(ttl=120)
def get_exchange_flows(coin_id="bitcoin"):
    data = get_coin_details(coin_id)
    if data:
        return {
            "market_data":          data.get("market_data", {}),
            "community_data":       data.get("community_data", {}),
            "public_interest_stats": data.get("public_interest_stats", {}),
        }
    return {}


# ══════════════════════════════════════════════════════════════
#  FONCTIONS DONNÉES — BINANCE / BYBIT
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)
def get_binance_funding_rates():
    data = _get("https://fapi.binance.com/fapi/v1/premiumIndex")
    if data and isinstance(data, list) and len(data) > 10:
        return [d for d in data if isinstance(d, dict) and "lastFundingRate" in d], "Binance Live"

    symbols_bybit = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
                     "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
                     "DOTUSDT","ATOMUSDT","LTCUSDT","UNIUSDT","AAVEUSDT"]
    results = []
    for sym in symbols_bybit:
        d = _get("https://api.bybit.com/v5/market/funding/history",
                 params={"category": "linear", "symbol": sym, "limit": 1})
        if d and d.get("result", {}).get("list"):
            item = d["result"]["list"][0]
            results.append({"symbol": sym, "markPrice": 0, "indexPrice": 0,
                             "lastFundingRate": float(item.get("fundingRate", 0))})
    if results:
        return results, "Bybit Live"

    np.random.seed(int(datetime.now().timestamp()) // 300)
    PAIRS = [("BTCUSDT",65000),("ETHUSDT",3200),("SOLUSDT",150),("BNBUSDT",580),
             ("XRPUSDT",0.55),("ADAUSDT",0.45),("DOGEUSDT",0.15),("AVAXUSDT",35),
             ("LINKUSDT",14),("MATICUSDT",0.85),("DOTUSDT",7.5),("ATOMUSDT",9.2),
             ("LTCUSDT",85),("UNIUSDT",8.5),("AAVEUSDT",95),("SANDUSDT",0.45),
             ("MANAUSDT",0.38),("APTUSDT",12),("ARBUSDT",1.1),("OPUSDT",2.3)]
    return [{"symbol": sym, "markPrice": p*(1+np.random.uniform(-0.005,0.005)),
             "indexPrice": p, "lastFundingRate": round(float(np.clip(np.random.normal(0.01,0.03),-0.075,0.15))/100,6)}
            for sym, p in PAIRS], "Estimé (marché actuel)"


@st.cache_data(ttl=120)
def get_open_interest_data():
    symbols = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
               "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT"]

    results = []
    for sym in symbols:
        d = _get("https://fapi.binance.com/fapi/v1/openInterest", params={"symbol": sym})
        if d and "openInterest" in d:
            results.append({"sym": sym.replace("USDT",""), "oi": float(d["openInterest"])})
    if results:
        return results, "Binance Live"

    results_bybit = []
    for sym in symbols:
        d = _get("https://api.bybit.com/v5/market/open-interest",
                 params={"category":"linear","symbol":sym,"intervalTime":"1h","limit":1})
        if d and d.get("result",{}).get("list"):
            oi = float(d["result"]["list"][0].get("openInterest", 0))
            results_bybit.append({"sym": sym.replace("USDT",""), "oi": oi})
    if results_bybit:
        return results_bybit, "Bybit Live"

    np.random.seed(int(datetime.now().timestamp()) // 600)
    OI_EST = [("BTC",15_200_000_000),("ETH",8_400_000_000),("SOL",2_100_000_000),
              ("BNB",980_000_000),("XRP",870_000_000),("ADA",420_000_000),
              ("DOGE",390_000_000),("AVAX",650_000_000),("LINK",520_000_000),("MATIC",310_000_000)]
    return [{"sym":sym,"oi":val*(1+np.random.uniform(-0.05,0.05))} for sym,val in OI_EST], "Estimé"


@st.cache_data(ttl=60)
def get_binance_liquidations():
    symbols = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
               "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT"]
    ref_prices = {"BTC":65000,"ETH":3200,"SOL":150,"BNB":580,"XRP":0.55,
                  "ADA":0.45,"DOGE":0.15,"AVAX":35,"LINK":14,"MATIC":0.85}
    results = []
    for sym in symbols:
        data = _get("https://fapi.binance.com/fapi/v1/forceOrders",
                    params={"symbol":sym,"limit":20,"autoCloseType":"LIQUIDATION"})
        if data and isinstance(data, list):
            for d in data:
                try:
                    results.append({"symbol":sym.replace("USDT",""),"side":d.get("side","SELL"),
                                    "qty":float(d.get("origQty",0)),"price":float(d.get("price",0)),
                                    "value_usd":float(d.get("origQty",0))*float(d.get("price",0)),
                                    "time":datetime.fromtimestamp(d.get("time",0)/1000),"source":"live"})
                except Exception:
                    pass
    if not results:
        np.random.seed(int(datetime.now().timestamp())//300)
        now = datetime.now()
        for sym_base, ref_price in ref_prices.items():
            for _ in range(np.random.randint(3,15)):
                side = np.random.choice(["SELL","BUY"], p=[0.6,0.4])
                price_var = ref_price*(1+np.random.uniform(-0.02,0.02))
                qty = np.random.uniform(0.01,2.0) if sym_base=="BTC" else np.random.uniform(1,500)
                results.append({"symbol":sym_base,"side":side,"qty":round(qty,4),
                                 "price":round(price_var,4),"value_usd":round(qty*price_var,2),
                                 "time":now-timedelta(minutes=int(np.random.randint(1,240))),"source":"estimated"})
    return sorted(results, key=lambda x: x["value_usd"], reverse=True)


@st.cache_data(ttl=120)
def get_coinbase_order_book(symbol="BTC"):
    try:
        url = f"https://api.exchange.coinbase.com/products/{symbol}-USD/book"
        r = requests.get(url, params={"level":2}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            bids = pd.DataFrame(data.get("bids",[])[:15], columns=["Price","Quantity","Orders"])
            asks = pd.DataFrame(data.get("asks",[])[:15], columns=["Price","Quantity","Orders"])
            bids[["Price","Quantity"]] = bids[["Price","Quantity"]].astype(float).round(4)
            asks[["Price","Quantity"]] = asks[["Price","Quantity"]].astype(float).round(4)
            return (bids, asks), None
        return None, f"HTTP {r.status_code}"
    except Exception as e:
        return None, str(e)


# ══════════════════════════════════════════════════════════════
#  FIREBASE PERSISTENCE — Délègue à firebase_auth.py
#  (qui gère déjà Firestore avec save_user_config / load_user_config)
# ══════════════════════════════════════════════════════════════

def _is_logged_in() -> bool:
    """True si l'utilisateur est connecté (pas mode invité)."""
    return (st.session_state.get("user_logged_in", False)
            and not st.session_state.get("guest_mode", False))


def save_watchlist_firebase(watchlist: list) -> bool:
    """Sauvegarde la watchlist via _save_current_session_config de firebase_auth."""
    if not _is_logged_in():
        return False
    try:
        from firebase_auth import _save_current_session_config
        st.session_state["watchlist"] = watchlist
        _save_current_session_config()
        return True
    except Exception as e:
        print(f"[utils] save_watchlist: {e}")
    return False


def load_watchlist_firebase() -> list:
    """
    Charge la watchlist depuis Firestore via firebase_auth.load_user_config.
    Retourne None si non connecté ou données absentes.
    """
    if not _is_logged_in():
        return None
    try:
        from firebase_auth import load_user_config
        uid      = st.session_state.get("user_uid", "")
        id_token = st.session_state.get("user_id_token", "")
        if uid and id_token:
            config = load_user_config(id_token, uid)
            return config.get("watchlist") if config else None
    except Exception as e:
        print(f"[utils] load_watchlist: {e}")
    return None


def save_alerts_firebase(alerts: list) -> bool:
    """Sauvegarde les alertes via _save_current_session_config de firebase_auth."""
    if not _is_logged_in():
        return False
    try:
        from firebase_auth import _save_current_session_config
        # Sérialiser les datetime avant sauvegarde
        safe = []
        for a in alerts:
            a2 = dict(a)
            if "created_at" in a2 and hasattr(a2["created_at"], "isoformat"):
                a2["created_at"] = a2["created_at"].isoformat()
            safe.append(a2)
        st.session_state["alerts"] = safe
        _save_current_session_config()
        return True
    except Exception as e:
        print(f"[utils] save_alerts: {e}")
    return False


def load_alerts_firebase() -> list:
    """Charge les alertes depuis Firestore via firebase_auth.load_user_config."""
    if not _is_logged_in():
        return []
    try:
        from firebase_auth import load_user_config
        uid      = st.session_state.get("user_uid", "")
        id_token = st.session_state.get("user_id_token", "")
        if uid and id_token:
            config = load_user_config(id_token, uid)
            return config.get("alerts", []) if config else []
    except Exception as e:
        print(f"[utils] load_alerts: {e}")
    return []


def init_session_from_firebase():
    """
    Appelé au démarrage : charge watchlist + alertes + portfolio depuis Firebase
    si l'utilisateur est connecté et que la config n'a pas encore été chargée.
    Utilise _apply_config_to_session de firebase_auth (déjà existant).
    """
    # Ne rien faire si pas connecté, ou si déjà chargé cette session
    if not _is_logged_in():
        return
    if st.session_state.get("user_config_loaded"):
        return  # firebase_auth l'a déjà chargé lors du login

    try:
        from firebase_auth import load_user_config, _apply_config_to_session
        uid      = st.session_state.get("user_uid", "")
        id_token = st.session_state.get("user_id_token", "")
        if uid and id_token:
            config = load_user_config(id_token, uid)
            if config:
                _apply_config_to_session(config)
    except Exception as e:
        print(f"[utils] init_session_from_firebase: {e}")


# ══════════════════════════════════════════════════════════════
#  MODULES UI PARTAGÉS (extraits de app.py)
#  → Utilisables dans Terminal.py sans `import app as _app`
# ══════════════════════════════════════════════════════════════

def show_order_book_ui(tab_idx: int = 0):
    """Carnet d'ordres live Coinbase Pro."""
    st.markdown("### 📖 LIVE ORDER BOOK (COINBASE PRO)")
    st.info("Utilisation des serveurs Coinbase pour éviter les restrictions géographiques de Binance.")
    symbol = st.text_input("PAIRE CRYPTO (ex: BTC, ETH, SOL)", value="BTC",
                           key=f"ob_symbol_utils_{tab_idx}").upper()
    if st.button("🔄 SYNCHRONISER LE CARNET", key=f"ob_sync_utils_{tab_idx}"):
        with st.spinner("Extraction des ordres en cours..."):
            data_result, error_msg = get_coinbase_order_book(symbol)
        if data_result:
            bids, asks = data_result
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<span style='color:#ff4b4b;font-weight:bold;'>🔴 ORDRES DE VENTE (ASKS)</span>",
                            unsafe_allow_html=True)
                st.dataframe(asks.sort_values("Price", ascending=False)
                             .style.bar(subset=["Quantity"], color="#441111"),
                             hide_index=True, use_container_width=True)
            with col2:
                st.markdown("<span style='color:#00ffad;font-weight:bold;'>🟢 ORDRES D'ACHAT (BIDS)</span>",
                            unsafe_allow_html=True)
                st.dataframe(bids.style.bar(subset=["Quantity"], color="#114411"),
                             hide_index=True, use_container_width=True)
            best_ask = asks["Price"].min()
            best_bid = bids["Price"].max()
            spread   = best_ask - best_bid
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("ASK",    f"${best_ask:,.2f}")
            c2.metric("BID",    f"${best_bid:,.2f}")
            c3.metric("SPREAD", f"${spread:.2f}",
                      delta=f"{(spread/best_ask)*100:.4f}%", delta_color="inverse")
        else:
            st.error(f"Impossible de récupérer les données : {error_msg}")


def show_onchain(tab_idx: int = 0):
    """Module On-Chain Analytics (extrait de app.py)."""
    st.markdown("""
        <div style='text-align:center;padding:20px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #00ffad;border-radius:12px;margin-bottom:20px;'>
            <h2 style='color:#00ffad;margin:0;'>ON-CHAIN ANALYTICS</h2>
            <p style='color:#00cc88;margin:5px 0 0;font-size:13px;'>
                Métriques blockchain — Baleines · Flux Exchanges · Activité Réseau
            </p>
        </div>
    """, unsafe_allow_html=True)

    coins_map = {"Bitcoin (BTC)":"bitcoin","Ethereum (ETH)":"ethereum",
                 "Solana (SOL)":"solana","BNB":"binancecoin","XRP":"ripple"}
    coin_label = st.selectbox("🪙 Sélectionner la crypto", list(coins_map.keys()), key=f"onchain_coin_utils_{tab_idx}")
    coin_id    = coins_map[coin_label]

    if st.button("🔍 CHARGER LES DONNÉES ON-CHAIN", key=f"load_onchain_utils_{tab_idx}"):
        with st.spinner("Chargement..."):
            details = get_coin_details(coin_id)
            chart30 = get_coin_market_chart(coin_id, days=30)
            chart90 = get_coin_market_chart(coin_id, days=90)

        if not details:
            st.error("Données indisponibles. Réessayez.")
            return

        md = details.get("market_data", {})
        cd = details.get("community_data", {})

        st.markdown("### 📊 MÉTRIQUES CLÉS")
        c1, c2, c3, c4 = st.columns(4)
        price   = md.get("current_price",{}).get("usd", 0)
        mcap    = md.get("market_cap",{}).get("usd", 0)
        vol_24h = md.get("total_volume",{}).get("usd", 0)
        supply  = md.get("circulating_supply", 0)
        max_sup = md.get("max_supply", 0)
        ath     = md.get("ath",{}).get("usd", 0)
        ath_chg = md.get("ath_change_percentage",{}).get("usd", 0)
        chg_24h = md.get("price_change_percentage_24h", 0)
        chg_7d  = md.get("price_change_percentage_7d", 0)
        chg_30d = md.get("price_change_percentage_30d", 0)
        ratio   = (vol_24h / mcap * 100) if mcap else 0

        c1.metric("Prix",        f"${price:,.2f}",  f"{chg_24h:+.2f}% (24h)")
        c2.metric("Market Cap",  f"${mcap/1e9:.2f}B")
        c3.metric("Volume 24h",  f"${vol_24h/1e9:.2f}B")
        c4.metric("Volume/MCap", f"{ratio:.2f}%",   help="Ratio élevé = forte activité")

        st.markdown("---")
        st.markdown("### 📈 PERFORMANCE & ATH")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("7 Jours",  f"{chg_7d:+.2f}%")
        c2.metric("30 Jours", f"{chg_30d:+.2f}%")
        c3.metric("ATH",      f"${ath:,.2f}")
        c4.metric("Distance ATH", f"{ath_chg:.1f}%")

        # Supply
        st.markdown("---")
        st.markdown("### 🪙 SUPPLY & CIRCULATION")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            supply_pct = (supply / max_sup * 100) if max_sup else 100
            fig_sup = go.Figure(go.Pie(
                values=[supply, max(0, (max_sup or supply) - supply)],
                labels=["Circulante","Non émise"],
                marker_colors=["#00ffad","#1a1a1a"],
                hole=0.6, textinfo="label+percent",
            ))
            fig_sup.update_layout(**PLOTLY_PIE, height=300,
                                  title=dict(text=f"Supply ({supply_pct:.1f}% émise)",
                                             font=dict(color="#00ffad",size=13)))
            st.plotly_chart(fig_sup, use_container_width=True)
        with col_s2:
            _card("Offre Circulante",  f"{supply/1e6:.2f}M",
                  f"sur {max_sup/1e6:.2f}M max" if max_sup else "sans limite", "#00ffad")
            _card("Market Cap Rang",  f"#{details.get('market_cap_rank','?')}", coin_label, "#ff9800")
            _card("Score CoinGecko",  f"{details.get('coingecko_score','N/A')}/100",
                  "Liquidité + Communauté + Dev", "#4fc3f7")

        # Prix 30j
        st.markdown("---")
        st.markdown("### 📉 ÉVOLUTION PRIX & VOLUME 30 JOURS")
        if chart30:
            prices_raw = chart30.get("prices", [])
            vols_raw   = chart30.get("total_volumes", [])
            if prices_raw:
                dates_p  = [datetime.fromtimestamp(p[0]/1000) for p in prices_raw]
                prices_v = [p[1] for p in prices_raw]
                dates_v  = [datetime.fromtimestamp(v[0]/1000) for v in vols_raw]
                vols_v   = [v[1] for v in vols_raw]
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.05, row_heights=[0.65, 0.35])
                fig.add_trace(go.Scatter(x=dates_p, y=prices_v, name="Prix",
                                         line=dict(color="#00ffad",width=2),
                                         fill="tozeroy", fillcolor="rgba(0,255,173,0.05)"), row=1, col=1)
                fig.add_trace(go.Bar(x=dates_v, y=vols_v, name="Volume",
                                     marker_color="rgba(255,152,0,0.4)"), row=2, col=1)
                fig.update_layout(**PLOTLY_BASE, height=450, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

        # Whales 90j
        st.markdown("---")
        st.markdown("### 🐋 INDICATEURS BALEINES & ACTIVITÉ")
        if chart90:
            prices_raw = chart90.get("prices", [])
            vols_raw   = chart90.get("total_volumes", [])
            if prices_raw and vols_raw:
                prices_s  = pd.Series([p[1] for p in prices_raw])
                vols_s    = pd.Series([v[1] for v in vols_raw])
                vol_mean  = vols_s.mean()
                vol_std   = vols_s.std()
                threshold = vol_mean + 2 * vol_std
                whale_idx = vols_s[vols_s > threshold].index.tolist()
                dates_90  = [datetime.fromtimestamp(p[0]/1000) for p in prices_raw]

                fig_w = go.Figure()
                fig_w.add_trace(go.Scatter(x=dates_90, y=[p[1] for p in prices_raw],
                                           name="Prix", line=dict(color="#00ffad",width=2)))
                whale_dates  = [dates_90[i] for i in whale_idx if i < len(dates_90)]
                whale_prices = [prices_raw[i][1] for i in whale_idx if i < len(prices_raw)]
                if whale_dates:
                    fig_w.add_trace(go.Scatter(x=whale_dates, y=whale_prices, mode="markers",
                                               name="⚠️ Anomalie volume",
                                               marker=dict(color="#ff9800",size=12,symbol="triangle-up")))
                fig_w.update_layout(**PLOTLY_BASE, height=400, hovermode="x unified",
                                    title=dict(text="Prix + Anomalies de Volume (90j)",
                                               font=dict(color="#ff9800",size=14)))
                st.plotly_chart(fig_w, use_container_width=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Anomalies détectées", f"{len(whale_idx)}", "Volume > Moyenne + 2σ")
                c2.metric("Volume Moyen 90j",    f"${vol_mean/1e9:.2f}B")
                c3.metric("Seuil Baleine",        f"${threshold/1e9:.2f}B")

        # Sentiment
        st.markdown("---")
        st.markdown("### 💬 SENTIMENT COMMUNAUTÉ")
        twitter    = cd.get("twitter_followers", 0)
        reddit_sub = cd.get("reddit_subscribers", 0)
        reddit_act = cd.get("reddit_accounts_active_48h", 0)
        telegram   = cd.get("telegram_channel_user_count", 0)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Twitter Followers",  f"{twitter/1e3:.0f}K"    if twitter    else "N/A")
        c2.metric("Reddit Subscribers", f"{reddit_sub/1e3:.0f}K" if reddit_sub else "N/A")
        c3.metric("Reddit Actifs (48h)", f"{reddit_act}"         if reddit_act else "N/A")
        c4.metric("Telegram Members",   f"{telegram/1e3:.0f}K"   if telegram   else "N/A")


def show_liquidations(tab_idx: int = 0):
    """Module Liquidations & Funding Rate (extrait de app.py)."""
    st.markdown("""
        <div style='text-align:center;padding:20px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #ff4b4b;border-radius:12px;margin-bottom:20px;'>
            <h2 style='color:#ff4b4b;margin:0;'>LIQUIDATIONS & FUNDING RATE</h2>
            <p style='color:#ff7777;margin:5px 0 0;font-size:13px;'>
                Futures Binance — Liquidations forcées · Taux de financement · Open Interest
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["💥 LIQUIDATIONS", "💰 FUNDING RATE", "📊 OPEN INTEREST"])

    with tab1:
        st.markdown("### 💥 LIQUIDATIONS RÉCENTES")
        if st.button("🔄 CHARGER LES LIQUIDATIONS", key=f"liq_load_utils_{tab_idx}"):
            with st.spinner("Chargement..."):
                liq_data = get_binance_liquidations()
            if liq_data:
                df_liq = pd.DataFrame(liq_data)
                is_live = df_liq["source"].eq("live").any()
                if is_live:
                    st.success("✅ Données live Binance Futures")
                else:
                    st.info("📊 Données estimées (Binance indisponible depuis Streamlit Cloud)")

                df_liq   = df_liq.sort_values("value_usd", ascending=False)
                total    = df_liq["value_usd"].sum()
                long_liq = df_liq[df_liq["side"]=="SELL"]["value_usd"].sum()
                short_liq= df_liq[df_liq["side"]=="BUY"]["value_usd"].sum()
                biggest  = df_liq["value_usd"].max()

                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Total Liquidé",    f"${total/1e6:.2f}M")
                c2.metric("Longs Liquidés 🔴",f"${long_liq/1e6:.2f}M")
                c3.metric("Shorts Liquidés 🟢",f"${short_liq/1e6:.2f}M")
                c4.metric("Plus Grande Liq.", f"${biggest/1e3:.0f}K")

                liq_sym = df_liq.groupby("symbol")["value_usd"].sum().sort_values(ascending=False).head(10)
                fig = go.Figure(go.Bar(x=liq_sym.index, y=liq_sym.values,
                                       marker_color="#ff4b4b", text=[f"${v/1e6:.1f}M" for v in liq_sym.values],
                                       textposition="auto"))
                fig.update_layout(**PLOTLY_BASE, height=380,
                                  title=dict(text="Liquidations par Crypto",font=dict(color="#ff4b4b",size=14)))
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 💰 TAUX DE FINANCEMENT")
        st.info("💡 Funding Rate positif = Les longs paient les shorts. Se paie toutes les 8h.")
        if st.button("🔄 CHARGER LES FUNDING RATES", key=f"fr_load_utils_{tab_idx}"):
            with st.spinner("Chargement..."):
                fr_data, fr_source = get_binance_funding_rates()
            rows = []
            for d in fr_data:
                rate = float(d.get("lastFundingRate", 0)) * 100
                if abs(rate) > 0.0001:
                    rows.append({"Paire": d.get("symbol",""), "Funding Rate": rate,
                                 "Annualisé": rate * 3 * 365})
            if rows:
                df_fr = pd.DataFrame(rows).sort_values("Funding Rate", ascending=False)
                c1,c2,c3,c4 = st.columns(4)
                avg = df_fr["Funding Rate"].mean()
                c1.metric("Funding Moyen", f"{avg:+.4f}%")
                c2.metric("Plus élevé", f"{df_fr['Funding Rate'].max():+.4f}%")
                c3.metric("Plus bas", f"{df_fr['Funding Rate'].min():+.4f}%")
                c4.metric("Source", fr_source)
                fig = go.Figure(go.Bar(
                    x=df_fr.head(20)["Paire"], y=df_fr.head(20)["Funding Rate"],
                    marker_color=["#ff4b4b" if v>0 else "#00ff88" for v in df_fr.head(20)["Funding Rate"]],
                    text=[f"{v:+.4f}%" for v in df_fr.head(20)["Funding Rate"]], textposition="auto"
                ))
                fig.add_hline(y=0, line_color="#4d9fff", line_width=1)
                fig.update_layout(**PLOTLY_BASE, height=420,
                                  title=dict(text=f"Funding Rate — {fr_source}",font=dict(color="#ff9800",size=14)),
                                  xaxis=dict(**_axis(), tickangle=-45),
                                  yaxis=dict(**_axis(), ticksuffix="%"))
                st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### 📊 OPEN INTEREST")
        if st.button("📊 CHARGER L'OPEN INTEREST", key=f"oi_load_utils_{tab_idx}"):
            with st.spinner("Chargement..."):
                oi_list, oi_source = get_open_interest_data()
            if oi_list:
                df_oi    = pd.DataFrame(oi_list).rename(columns={"sym":"Crypto","oi":"OI"})
                df_oi    = df_oi.sort_values("OI", ascending=False)
                total_oi = df_oi["OI"].sum()
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("OI Total", f"${total_oi/1e9:.1f}B")
                btc_oi = df_oi[df_oi["Crypto"]=="BTC"]["OI"].values
                eth_oi = df_oi[df_oi["Crypto"]=="ETH"]["OI"].values
                c2.metric("BTC OI", f"${btc_oi[0]/1e9:.1f}B" if len(btc_oi) else "N/A")
                c3.metric("ETH OI", f"${eth_oi[0]/1e9:.1f}B" if len(eth_oi) else "N/A")
                c4.metric("Source", oi_source)
                COLORS = ["#ff9800","#4fc3f7","#9945ff","#f3ba2f","#00aeff",
                          "#0033ad","#c2a633","#e84142","#2196f3","#ab47bc"]
                fig = go.Figure(go.Bar(x=df_oi["Crypto"], y=df_oi["OI"],
                                       marker_color=COLORS[:len(df_oi)],
                                       text=[f"${v/1e9:.1f}B" for v in df_oi["OI"]], textposition="auto"))
                fig.update_layout(**PLOTLY_BASE, height=400,
                                  title=dict(text=f"Open Interest — {oi_source}",font=dict(color="#ff9800",size=14)),
                                  yaxis=dict(**_axis(), tickprefix="$"))
                st.plotly_chart(fig, use_container_width=True)


def show_staking(tab_idx: int = 0):
    """Module Staking & Yield Tracker (extrait de app.py)."""
    st.markdown("""
        <div style='text-align:center;padding:20px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #4fc3f7;border-radius:12px;margin-bottom:20px;'>
            <h2 style='color:#4fc3f7;margin:0;'>STAKING & YIELD TRACKER</h2>
            <p style='color:#7dd3f5;margin:5px 0 0;font-size:13px;'>
                Rendements DeFi · Staking natif · Simulateur de revenus passifs
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔒 STAKING NATIF", "🧮 SIMULATEUR"])

    with tab1:
        st.markdown("### 🔒 STAKING NATIF — TAUX OFFICIELS")
        # Taux mis à jour mars 2026
        STAKING_DATA = {
            "Ethereum (ETH)":  {"apy":4.1, "min":32,    "lockup":"Variable",  "risque":"Faible","couleur":"#627eea"},
            "Solana (SOL)":    {"apy":7.2, "min":0.01,  "lockup":"~3 jours",  "risque":"Faible","couleur":"#9945ff"},
            "Cardano (ADA)":   {"apy":3.5, "min":1,     "lockup":"Aucun",     "risque":"Faible","couleur":"#0033ad"},
            "Polkadot (DOT)":  {"apy":14.5,"min":1,     "lockup":"28 jours",  "risque":"Moyen", "couleur":"#e6007a"},
            "Cosmos (ATOM)":   {"apy":19.0,"min":0.01,  "lockup":"21 jours",  "risque":"Moyen", "couleur":"#2e3148"},
            "Avalanche (AVAX)":{"apy":8.6, "min":25,    "lockup":"2 semaines","risque":"Faible","couleur":"#e84142"},
            "Tezos (XTZ)":     {"apy":5.5, "min":0.01,  "lockup":"Aucun",     "risque":"Faible","couleur":"#2c7df7"},
            "Near (NEAR)":     {"apy":10.5,"min":0.01,  "lockup":"~3 jours",  "risque":"Faible","couleur":"#00ec97"},
            "BNB":             {"apy":6.2, "min":0.1,   "lockup":"7 jours",   "risque":"Moyen", "couleur":"#f3ba2f"},
        }
        cols = st.columns(2)
        for i, (name, info) in enumerate(STAKING_DATA.items()):
            with cols[i % 2]:
                rc = "#00ff88" if info["risque"]=="Faible" else "#ff9800" if info["risque"]=="Moyen" else "#ff4b4b"
                st.markdown(f"""
                    <div style='background:#0d0d0d;border:1px solid {info["couleur"]};
                         border-left:4px solid {info["couleur"]};border-radius:8px;
                         padding:14px;margin-bottom:10px;'>
                        <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <b style='color:{info["couleur"]};font-size:16px;'>{name}</b>
                            <b style='color:#00ff88;font-size:22px;'>{info["apy"]}%<span style='font-size:12px;color:#888;'>/an</span></b>
                        </div>
                        <div style='margin-top:8px;display:flex;gap:20px;font-size:12px;font-family:monospace;'>
                            <span style='color:#4d9fff;'>Min: <b>{info["min"]}</b></span>
                            <span style='color:#4d9fff;'>Lock: <b>{info["lockup"]}</b></span>
                            <span style='color:#4d9fff;'>Risque: <b style='color:{rc};'>{info["risque"]}</b></span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        apys = [d["apy"] for d in STAKING_DATA.values()]
        fig_s = go.Figure(go.Bar(
            x=list(STAKING_DATA.keys()), y=apys,
            marker_color=[d["couleur"] for d in STAKING_DATA.values()],
            text=[f"{a}%" for a in apys], textposition="auto"
        ))
        fig_s.update_layout(**PLOTLY_BASE, height=380,
                            title=dict(text="Comparatif APY Staking",font=dict(color="#4fc3f7",size=14)),
                            xaxis=dict(**_axis(), tickangle=-30), yaxis=dict(**_axis(), ticksuffix="%"))
        st.plotly_chart(fig_s, use_container_width=True)

    with tab2:
        st.markdown("### 🧮 SIMULATEUR DE REVENUS PASSIFS")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            capital    = st.number_input("💰 Capital initial ($)", value=10000, step=500, key=f"sim_cap_utils_{tab_idx}")
            apy_input  = st.slider("📈 APY estimé (%)", 1.0, 50.0, 8.0, 0.5, key=f"sim_apy_utils_{tab_idx}")
            duree_ans  = st.slider("⏱️ Durée (années)", 1, 10, 3, key=f"sim_dur_utils_{tab_idx}")
        with col_s2:
            compound   = st.checkbox("♻️ Réinvestissement des gains", value=True, key=f"sim_comp_utils_{tab_idx}")
            apport_mois= st.number_input("➕ Apport mensuel ($)", value=0, step=100, key=f"sim_ap_utils_{tab_idx}")

        apy_f    = float(apy_input) / 100
        mois_tot = duree_ans * 12
        mrate    = (1 + apy_f)**(1/12) - 1
        cap_f    = float(capital); ap_f = float(apport_mois)

        vals, cur = [], cap_f
        for m in range(mois_tot + 1):
            vals.append(cur)
            gain = cur * mrate if compound else cap_f * mrate
            cur += gain + ap_f

        gain_total  = vals[-1] - cap_f - ap_f * mois_tot
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Capital Final",  f"${vals[-1]:,.0f}")
        c2.metric("Gains Totaux",   f"${gain_total:,.0f}")
        c3.metric("Gain/Mois Moy.", f"${gain_total/mois_tot:,.0f}")
        c4.metric("ROI Total",      f"{gain_total/cap_f*100:.1f}%")

        fig_sim = go.Figure()
        fig_sim.add_trace(go.Scatter(x=list(range(mois_tot+1)), y=vals, name="Capital total",
                                     line=dict(color="#4fc3f7",width=2.5),
                                     fill="tozeroy", fillcolor="rgba(79,195,247,0.08)"))
        fig_sim.add_trace(go.Scatter(x=list(range(mois_tot+1)),
                                     y=[cap_f + ap_f*m for m in range(mois_tot+1)],
                                     name="Capital investi", line=dict(color="#4d9fff",width=1.5,dash="dot")))
        fig_sim.update_layout(**PLOTLY_BASE, height=380, hovermode="x unified",
                              title=dict(text=f"Projection {duree_ans} an(s) à {apy_input}% APY",
                                         font=dict(color="#4fc3f7",size=14)),
                              xaxis=dict(**_axis(), title="Mois"), yaxis=dict(**_axis(), tickprefix="$"))
        st.plotly_chart(fig_sim, use_container_width=True)
