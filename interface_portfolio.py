"""
interface_portfolio.py
Portfolio Tracker — AM-Trading Terminal
Gère : Actions/ETF, Crypto, Forex, Matières premières
Stockage : Firebase Firestore (via firebase_auth)
P&L : Détaillé par position, historique, graphiques
"""

import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import json


# ══════════════════════════════════════════════════════════════
#  CONFIG ACTIFS
# ══════════════════════════════════════════════════════════════

ASSET_TYPES = ["Actions / ETF", "Crypto", "Forex", "Matières premières"]

ASSET_TYPE_CONFIG = {
    "Actions / ETF":      {"emoji": "📈", "color": "#4d9fff", "suffix": ""},
    "Crypto":             {"emoji": "₿",  "color": "#ff9800", "suffix": "-USD"},
    "Forex":              {"emoji": "💱", "color": "#00e5ff", "suffix": "=X"},
    "Matières premières": {"emoji": "🥇", "color": "#ffd700", "suffix": "=F"},
}

# Suggestions rapides par type
QUICK_SYMBOLS = {
    "Actions / ETF":      ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "META", "SPY", "QQQ", "MC.PA", "TTE.PA"],
    "Crypto":             ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "LINK"],
    "Forex":              ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"],
    "Matières premières": ["GC", "CL", "SI", "NG", "HG", "ZW", "ZC"],
}

FOREX_LABELS = {
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF", "AUDUSD": "AUD/USD", "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD", "EURGBP": "EUR/GBP", "EURJPY": "EUR/JPY",
}

COMMODITY_LABELS = {
    "GC": "Or ($/oz)", "CL": "WTI ($/bbl)", "SI": "Argent ($/oz)",
    "NG": "Gaz Nat.", "HG": "Cuivre", "ZW": "Blé", "ZC": "Maïs",
    "BZ": "Brent", "PA": "Palladium", "PL": "Platine",
}


# ══════════════════════════════════════════════════════════════
#  FIREBASE — LECTURE / ÉCRITURE PORTFOLIO
# ══════════════════════════════════════════════════════════════

def _is_logged_in() -> bool:
    return (st.session_state.get("user_logged_in", False)
            and not st.session_state.get("guest_mode", False))


def _save_portfolio(positions: list):
    """Sauvegarde le portfolio dans session_state + Firebase si connecté."""
    st.session_state["portfolio_v2"] = positions
    if not _is_logged_in():
        return
    try:
        from firebase_auth import _firestore_headers, _to_firestore, FIRESTORE_URL
        uid      = st.session_state.get("user_uid", "")
        id_token = st.session_state.get("user_id_token", "")
        if not uid or not id_token:
            return
        url = f"{FIRESTORE_URL}/users/{uid}?updateMask.fieldPaths=portfolio_v2"
        payload = {"fields": {"portfolio_v2": _to_firestore(positions)}}
        requests.patch(url, headers=_firestore_headers(id_token), json=payload, timeout=8)
    except Exception as e:
        st.warning(f"Erreur sauvegarde Firebase : {e}")


def _load_portfolio() -> list:
    """Charge le portfolio depuis Firebase ou session_state."""
    # Déjà en session
    if "portfolio_v2" in st.session_state:
        return st.session_state["portfolio_v2"]

    if _is_logged_in():
        try:
            from firebase_auth import load_user_config
            uid      = st.session_state.get("user_uid", "")
            id_token = st.session_state.get("user_id_token", "")
            if uid and id_token:
                config = load_user_config(id_token, uid)
                if config and "portfolio_v2" in config:
                    data = config["portfolio_v2"]
                    st.session_state["portfolio_v2"] = data
                    return data
        except Exception as e:
            print(f"[portfolio] load: {e}")

    st.session_state["portfolio_v2"] = []
    return []


# ══════════════════════════════════════════════════════════════
#  PRIX EN TEMPS RÉEL
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def _get_price(ticker_yf: str) -> float | None:
    try:
        t = yf.Ticker(ticker_yf)
        hist = t.history(period="2d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _get_price_history(ticker_yf: str, period: str = "1y") -> pd.DataFrame:
    try:
        df = yf.download(ticker_yf, period=period, progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Close"]].dropna()
    except:
        return pd.DataFrame()


def _yf_ticker(symbol: str, asset_type: str) -> str:
    """Convertit le symbole utilisateur en ticker Yahoo Finance."""
    s = symbol.upper().strip()
    if asset_type == "Actions / ETF":
        return s
    elif asset_type == "Crypto":
        base = s.replace("-USD", "").replace("USDT", "").replace("USD", "")
        return f"{base}-USD"
    elif asset_type == "Forex":
        clean = s.replace("/", "").replace("-", "")
        if not clean.endswith("=X"):
            return f"{clean}=X"
        return clean
    elif asset_type == "Matières premières":
        base = s.replace("=F", "")
        return f"{base}=F"
    return s


def _display_symbol(symbol: str, asset_type: str) -> str:
    """Symbole lisible pour l'affichage."""
    s = symbol.upper().strip()
    if asset_type == "Crypto":
        base = s.replace("-USD", "").replace("USDT", "").replace("USD", "")
        return f"{base}/USD"
    elif asset_type == "Forex":
        clean = s.replace("=X", "").replace("/", "").replace("-", "")
        return FOREX_LABELS.get(clean, clean[:3] + "/" + clean[3:] if len(clean) >= 6 else clean)
    elif asset_type == "Matières premières":
        base = s.replace("=F", "")
        return COMMODITY_LABELS.get(base, base)
    return s


# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════

PORTFOLIO_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

.port-header {
    display: flex; align-items: center; gap: 12px;
    background: linear-gradient(135deg, #0a0a0a, #050505);
    border: 1px solid #1a1a1a; border-left: 3px solid #ff6600;
    border-radius: 6px; padding: 16px 20px; margin-bottom: 16px;
}
.port-title {
    font-family: 'IBM Plex Mono', monospace; font-size: 18px;
    font-weight: 700; color: #ff6600; letter-spacing: 2px;
}
.port-sub {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px;
    color: #333; letter-spacing: 1px; margin-top: 2px;
}

/* KPI Cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px; }
.kpi-card {
    background: #080808; border: 1px solid #1a1a1a;
    border-radius: 6px; padding: 14px 16px;
    font-family: 'IBM Plex Mono', monospace;
}
.kpi-label { font-size: 9px; color: #444; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; color: #e8e8e8; }
.kpi-delta { font-size: 11px; margin-top: 4px; }
.kpi-delta.up   { color: #26a69a; }
.kpi-delta.dn   { color: #ef5350; }
.kpi-delta.flat { color: #555; }

/* Position rows */
.pos-row {
    display: flex; align-items: center; gap: 0;
    background: #050505; border: 1px solid #111;
    border-radius: 4px; padding: 10px 14px;
    margin-bottom: 4px; font-family: 'IBM Plex Mono', monospace;
    transition: border-color .15s;
}
.pos-row:hover { border-color: #2a2e39; }
.pos-badge {
    font-size: 8px; padding: 2px 6px; border-radius: 3px;
    font-weight: 600; letter-spacing: 0.8px; margin-right: 10px;
    white-space: nowrap;
}

/* Section headers */
.section-bar {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px;
    color: #444; letter-spacing: 2px; text-transform: uppercase;
    border-bottom: 1px solid #111; padding-bottom: 6px;
    margin: 16px 0 10px;
}

/* Add form */
.add-form {
    background: #080808; border: 1px solid #1a1a1a;
    border-radius: 6px; padding: 16px; margin-bottom: 16px;
}
</style>
"""


# ══════════════════════════════════════════════════════════════
#  CALCUL P&L
# ══════════════════════════════════════════════════════════════

def _compute_positions(positions: list) -> list:
    """Enrichit chaque position avec prix actuel, P&L, etc."""
    enriched = []
    for pos in positions:
        ticker_yf = _yf_ticker(pos["symbol"], pos["asset_type"])
        current   = _get_price(ticker_yf)
        qty       = float(pos.get("qty", 0))
        buy_price = float(pos.get("buy_price", 0))
        fees      = float(pos.get("fees", 0))

        if current is None:
            current = buy_price  # fallback

        cost_basis   = qty * buy_price + fees
        market_value = qty * current
        pnl_abs      = market_value - cost_basis
        pnl_pct      = (pnl_abs / cost_basis * 100) if cost_basis else 0

        enriched.append({
            **pos,
            "ticker_yf":    ticker_yf,
            "current_price": current,
            "market_value":  market_value,
            "cost_basis":    cost_basis,
            "pnl_abs":       pnl_abs,
            "pnl_pct":       pnl_pct,
            "display_sym":   _display_symbol(pos["symbol"], pos["asset_type"]),
        })
    return enriched


def _portfolio_kpis(enriched: list) -> dict:
    total_value  = sum(p["market_value"] for p in enriched)
    total_cost   = sum(p["cost_basis"]   for p in enriched)
    total_pnl    = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0
    best  = max(enriched, key=lambda p: p["pnl_pct"],  default=None)
    worst = min(enriched, key=lambda p: p["pnl_pct"],  default=None)
    return {
        "total_value":   total_value,
        "total_cost":    total_cost,
        "total_pnl":     total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "best":          best,
        "worst":         worst,
        "n_positions":   len(enriched),
    }


# ══════════════════════════════════════════════════════════════
#  VUE KPI HEADER
# ══════════════════════════════════════════════════════════════

def _render_kpis(kpis: dict):
    pnl_class = "up" if kpis["total_pnl"] >= 0 else "dn"
    pnl_sign  = "+" if kpis["total_pnl"] >= 0 else ""
    best_str  = f"{kpis['best']['display_sym']} {kpis['best']['pnl_pct']:+.2f}%"  if kpis["best"]  else "—"
    worst_str = f"{kpis['worst']['display_sym']} {kpis['worst']['pnl_pct']:+.2f}%" if kpis["worst"] else "—"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">Valeur totale</div>
          <div class="kpi-value">${kpis['total_value']:,.0f}</div>
          <div class="kpi-delta flat">{kpis['n_positions']} position{'s' if kpis['n_positions']>1 else ''}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">P&L Total</div>
          <div class="kpi-value" style="color:{'#26a69a' if kpis['total_pnl']>=0 else '#ef5350'}">
            {pnl_sign}${kpis['total_pnl']:,.0f}
          </div>
          <div class="kpi-delta {pnl_class}">{pnl_sign}{kpis['total_pnl_pct']:.2f}%</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">🏆 Meilleure position</div>
          <div class="kpi-value" style="font-size:14px;color:#26a69a;">{best_str}</div>
          <div class="kpi-delta flat">performance</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-label">📉 Moins bonne</div>
          <div class="kpi-value" style="font-size:14px;color:#ef5350;">{worst_str}</div>
          <div class="kpi-delta flat">performance</div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  TABLEAU DES POSITIONS
# ══════════════════════════════════════════════════════════════

def _render_positions_table(enriched: list) -> int | None:
    """Affiche le tableau des positions. Retourne l'index à supprimer si demandé."""
    if not enriched:
        st.markdown("""
        <div style="text-align:center;padding:40px;color:#333;
                    font-family:'IBM Plex Mono',monospace;font-size:12px;border:1px dashed #1a1a1a;border-radius:6px;">
            Aucune position — Ajoutez votre première position ci-dessous
        </div>""", unsafe_allow_html=True)
        return None

    st.markdown('<div class="section-bar">» POSITIONS OUVERTES</div>', unsafe_allow_html=True)

    # En-tête
    hcols = st.columns([0.4, 1.8, 1, 1, 1, 1.2, 1.2, 1.2, 0.6])
    for col, label in zip(hcols, ["", "ACTIF", "TYPE", "QTÉ", "PRX ACHAT", "PRX ACTUEL", "VALEUR", "P&L", ""]):
        col.markdown(f"<div style='font-size:9px;color:#333;font-family:IBM Plex Mono,monospace;"
                     f"letter-spacing:1px;padding-bottom:4px;border-bottom:1px solid #111;'>{label}</div>",
                     unsafe_allow_html=True)

    to_delete = None
    for i, pos in enumerate(enriched):
        cfg   = ASSET_TYPE_CONFIG[pos["asset_type"]]
        pnl_c = "#26a69a" if pos["pnl_abs"] >= 0 else "#ef5350"
        sign  = "+" if pos["pnl_abs"] >= 0 else ""

        row = st.columns([0.4, 1.8, 1, 1, 1, 1.2, 1.2, 1.2, 0.6])
        row[0].markdown(f"<div style='font-size:14px;'>{cfg['emoji']}</div>", unsafe_allow_html=True)
        row[1].markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px;"
                        f"font-weight:600;color:#e8e8e8;'>{pos['display_sym']}</div>"
                        f"<div style='font-size:9px;color:#333;'>{pos.get('note','')}</div>",
                        unsafe_allow_html=True)
        _ac = cfg["color"]
        _at = pos['asset_type'].split('/')[0].strip()[:6]
        row[2].markdown(f"<div style='font-size:9px;padding:2px 6px;border-radius:3px;"
                        f"background:{_ac}22;color:{_ac};display:inline-block;"
                        f"font-family:IBM Plex Mono,monospace;font-weight:600;'>"
                        f"{_at}</div>", unsafe_allow_html=True)
        row[3].markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px;'>{pos['qty']}</div>",
                        unsafe_allow_html=True)
        row[4].markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px;'>${pos['buy_price']:,.4g}</div>",
                        unsafe_allow_html=True)
        row[5].markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px;"
                        f"color:#d1d4dc;'>${pos['current_price']:,.4g}</div>", unsafe_allow_html=True)
        row[6].markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px;"
                        f"font-weight:600;'>${pos['market_value']:,.2f}</div>", unsafe_allow_html=True)
        row[7].markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px;"
                        f"font-weight:600;color:{pnl_c};'>{sign}${pos['pnl_abs']:,.2f}"
                        f"<br><span style='font-size:10px;'>{sign}{pos['pnl_pct']:.2f}%</span></div>",
                        unsafe_allow_html=True)
        if row[8].button("✕", key=f"del_pos_{i}", help="Supprimer"):
            to_delete = i

    return to_delete


# ══════════════════════════════════════════════════════════════
#  GRAPHIQUE CAMEMBERT ALLOCATION
# ══════════════════════════════════════════════════════════════

def _render_allocation_chart(enriched: list):
    if not enriched:
        return

    # Allocation par actif
    labels = [p["display_sym"] for p in enriched]
    values = [max(p["market_value"], 0) for p in enriched]
    colors_map = {t: ASSET_TYPE_CONFIG[t]["color"] for t in ASSET_TYPES}
    colors = [colors_map[p["asset_type"]] for p in enriched]

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=["Allocation par actif", "P&L par position ($)"]
    )

    # Donut
    fig.add_trace(go.Pie(
        labels=labels, values=values,
        hole=0.55, marker=dict(colors=colors, line=dict(color="#000", width=1)),
        textfont=dict(family="IBM Plex Mono", size=10),
        showlegend=True,
    ), row=1, col=1)

    # Bar P&L
    pnl_vals  = [p["pnl_abs"]  for p in enriched]
    bar_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in pnl_vals]
    fig.add_trace(go.Bar(
        x=labels, y=pnl_vals,
        marker=dict(color=bar_colors, line=dict(color="#000", width=0.5)),
        text=[f"{'+'if v>=0 else ''}${v:,.0f}" for v in pnl_vals],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=9),
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505",
        height=320, margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="IBM Plex Mono", color="#787b86"),
        legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_annotations(font=dict(size=10, color="#444"))
    st.plotly_chart(fig, use_container_width=True)

    # Allocation par type
    type_alloc = {}
    for p in enriched:
        type_alloc[p["asset_type"]] = type_alloc.get(p["asset_type"], 0) + p["market_value"]
    total = sum(type_alloc.values()) or 1

    cols_alloc = st.columns(len(type_alloc))
    for col, (atype, val) in zip(cols_alloc, type_alloc.items()):
        cfg = ASSET_TYPE_CONFIG[atype]
        pct = val / total * 100
        col.markdown(f"""
        <div style="background:#080808;border:1px solid #1a1a1a;border-top:2px solid {cfg['color']};
                    border-radius:4px;padding:10px;text-align:center;">
          <div style="font-size:9px;color:#444;font-family:IBM Plex Mono,monospace;margin-bottom:4px;">
            {cfg['emoji']} {atype.split('/')[0].strip()}</div>
          <div style="font-size:18px;font-weight:700;font-family:IBM Plex Mono,monospace;
                      color:{cfg['color']};">{pct:.1f}%</div>
          <div style="font-size:10px;color:#555;font-family:IBM Plex Mono,monospace;">${val:,.0f}</div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  GRAPHIQUE HISTORIQUE PORTFOLIO
# ══════════════════════════════════════════════════════════════

def _render_history_chart(enriched: list):
    if not enriched:
        return

    st.markdown('<div class="section-bar">» ÉVOLUTION DU PORTEFEUILLE</div>', unsafe_allow_html=True)

    period_opt = st.selectbox("Période historique", ["1mo", "3mo", "6mo", "1y", "2y"],
                              index=2, key="port_hist_period",
                              format_func=lambda x: {"1mo":"1 Mois","3mo":"3 Mois","6mo":"6 Mois","1y":"1 An","2y":"2 Ans"}[x])

    with st.spinner("Calcul de l'historique..."):
        all_series = {}
        for pos in enriched:
            df = _get_price_history(pos["ticker_yf"], period=period_opt)
            if not df.empty:
                all_series[pos["display_sym"]] = df["Close"] * float(pos["qty"])

    if not all_series:
        st.warning("Impossible de récupérer l'historique des prix.")
        return

    # Aligner les séries sur le même index
    df_all = pd.DataFrame(all_series).fillna(method="ffill").fillna(method="bfill").dropna()
    if df_all.empty:
        return

    portfolio_total = df_all.sum(axis=1)
    cost_total = sum(float(p["qty"]) * float(p["buy_price"]) + float(p.get("fees", 0))
                     for p in enriched)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.06, row_heights=[0.7, 0.3],
        subplot_titles=["Valeur totale du portefeuille", "P&L ($)"]
    )

    # Valeur totale
    fig.add_trace(go.Scatter(
        x=portfolio_total.index, y=portfolio_total.values,
        name="Valeur portfolio",
        line=dict(color="#ff6600", width=2),
        fill="tozeroy", fillcolor="rgba(255,102,0,0.05)"
    ), row=1, col=1)

    # Ligne cost basis
    fig.add_hline(y=cost_total, line_color="#4d9fff", line_dash="dash",
                  line_width=1, row=1, col=1,
                  annotation_text="Coût d'acquisition",
                  annotation_font=dict(color="#4d9fff", size=9))

    # P&L
    pnl_series = portfolio_total - cost_total
    pnl_color  = ["#26a69a" if v >= 0 else "#ef5350" for v in pnl_series.values]
    fig.add_trace(go.Bar(
        x=pnl_series.index, y=pnl_series.values,
        name="P&L", marker_color=pnl_color,
        showlegend=False,
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505",
        height=460, margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="IBM Plex Mono", color="#787b86"),
        xaxis_rangeslider_visible=False,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Graphiques individuels
    st.markdown('<div class="section-bar">» PERFORMANCE PAR POSITION</div>', unsafe_allow_html=True)
    cols_ind = st.columns(2)
    for i, pos in enumerate(enriched):
        if pos["ticker_yf"] in [p["ticker_yf"] for p in enriched]:
            df_pos = _get_price_history(pos["ticker_yf"], period=period_opt)
            if df_pos.empty:
                continue
            val_series = df_pos["Close"] * float(pos["qty"])
            cost_line  = float(pos["qty"]) * float(pos["buy_price"])
            ret_pct    = (val_series.iloc[-1] - cost_line) / cost_line * 100 if cost_line else 0
            line_c     = "#26a69a" if ret_pct >= 0 else "#ef5350"
            with cols_ind[i % 2]:
                fig_ind = go.Figure()
                fig_ind.add_trace(go.Scatter(
                    x=val_series.index, y=val_series.values,
                    line=dict(color=line_c, width=1.5),
                    fill="tozeroy", fillcolor=f"{'rgba(38,166,154,0.05)' if ret_pct>=0 else 'rgba(239,83,80,0.05)'}",
                    name=pos["display_sym"]
                ))
                fig_ind.add_hline(y=cost_line, line_color="#4d9fff", line_dash="dot", line_width=1)
                fig_ind.update_layout(
                    template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505",
                    height=200, margin=dict(l=10, r=10, t=30, b=10),
                    title=dict(text=f"{pos['display_sym']}  {'+' if ret_pct>=0 else ''}{ret_pct:.2f}%",
                               font=dict(size=11, color=line_c, family="IBM Plex Mono")),
                    showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_ind, use_container_width=True)


# ══════════════════════════════════════════════════════════════
#  FORMULAIRE AJOUT DE POSITION
# ══════════════════════════════════════════════════════════════

def _render_add_form(positions: list) -> list | None:
    """Affiche le formulaire d'ajout. Retourne la liste mise à jour ou None."""
    st.markdown('<div class="section-bar">» AJOUTER UNE POSITION</div>', unsafe_allow_html=True)

    with st.container():
        c1, c2 = st.columns([2, 3])

        with c1:
            asset_type = st.selectbox("Type d'actif", ASSET_TYPES, key="add_asset_type")

        with c2:
            suggestions = QUICK_SYMBOLS.get(asset_type, [])
            quick_sel = st.selectbox("Suggestion rapide", ["— Saisir manuellement —"] + suggestions,
                                     key="add_quick_sel")

        col_sym, col_qty, col_price, col_fees, col_date = st.columns([2, 1.2, 1.2, 1, 1.5])

        with col_sym:
            default_sym = quick_sel if quick_sel != "— Saisir manuellement —" else ""
            symbol = st.text_input("Symbole", value=default_sym,
                                   placeholder="ex: AAPL, BTC, EURUSD",
                                   key="add_symbol").strip().upper()
        with col_qty:
            qty = st.number_input("Quantité", min_value=0.0, value=1.0,
                                  step=0.001, format="%.6g", key="add_qty")
        with col_price:
            buy_price = st.number_input("Prix d'achat", min_value=0.0, value=0.0,
                                        step=0.01, format="%.6g", key="add_price")
        with col_fees:
            fees = st.number_input("Frais ($)", min_value=0.0, value=0.0,
                                   step=0.1, key="add_fees")
        with col_date:
            buy_date = st.date_input("Date d'achat", value=datetime.today(),
                                     key="add_date")

        col_note, col_btn = st.columns([3, 1])
        with col_note:
            note = st.text_input("Note (optionnel)", placeholder="ex: DCA, Long terme...",
                                 key="add_note")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            add_clicked = st.button("＋ AJOUTER", use_container_width=True, key="btn_add_pos",
                                    type="primary")

        if add_clicked:
            if not symbol:
                st.error("Entrez un symbole.")
                return None
            if qty <= 0:
                st.error("La quantité doit être > 0.")
                return None

            # Auto-fetch prix si buy_price = 0
            actual_price = buy_price
            if actual_price == 0:
                ticker_yf = _yf_ticker(symbol, asset_type)
                with st.spinner(f"Récupération du prix de {symbol}..."):
                    fetched = _get_price(ticker_yf)
                if fetched:
                    actual_price = fetched
                    st.info(f"Prix actuel utilisé : ${fetched:,.4g}")
                else:
                    st.error("Prix introuvable. Entrez le prix manuellement.")
                    return None

            new_pos = {
                "symbol":     symbol,
                "asset_type": asset_type,
                "qty":        round(qty, 8),
                "buy_price":  round(actual_price, 8),
                "fees":       round(fees, 4),
                "buy_date":   buy_date.isoformat(),
                "note":       note,
                "added_at":   datetime.now().isoformat(),
            }
            updated = positions + [new_pos]
            return updated

    return None


# ══════════════════════════════════════════════════════════════
#  ONGLET ANALYSE DÉTAILLÉE
# ══════════════════════════════════════════════════════════════

def _render_detail_tab(enriched: list):
    if not enriched:
        st.info("Aucune position à analyser.")
        return

    sym_sel = st.selectbox(
        "Choisir une position",
        [p["display_sym"] for p in enriched],
        key="detail_pos_sel"
    )
    pos = next(p for p in enriched if p["display_sym"] == sym_sel)
    cfg = ASSET_TYPE_CONFIG[pos["asset_type"]]

    # Métriques détaillées
    c1, c2, c3, c4, c5 = st.columns(5)
    sign = "+" if pos["pnl_abs"] >= 0 else ""
    c1.metric("Prix d'achat",  f"${pos['buy_price']:,.4g}")
    c2.metric("Prix actuel",   f"${pos['current_price']:,.4g}")
    c3.metric("Valeur marché", f"${pos['market_value']:,.2f}")
    c4.metric("P&L ($)",       f"{sign}${pos['pnl_abs']:,.2f}", f"{sign}{pos['pnl_pct']:.2f}%",
              delta_color="normal" if pos["pnl_abs"] >= 0 else "inverse")
    c5.metric("Coût total",    f"${pos['cost_basis']:,.2f}")

    st.markdown("---")

    # Graphique TradingView (Actions, Indices, Matières Premières, Forex)
    # Pour Crypto : on garde yfinance car TradingView crypto = hors scope
    tv_symbol = None
    if pos["asset_type"] == "Actions / ETF":
        tv_symbol = pos["symbol"].upper()
    elif pos["asset_type"] == "Forex":
        clean = pos["symbol"].replace("=X","").replace("/","").replace("-","").upper()
        tv_symbol = f"FX:{clean}"
    elif pos["asset_type"] == "Matières premières":
        base = pos["symbol"].replace("=F","").upper()
        tv_map_mp = {
            "GC":"COMEX:GC1!","SI":"COMEX:SI1!","PL":"NYMEX:PL1!","PA":"NYMEX:PA1!",
            "CL":"NYMEX:CL1!","BZ":"NYMEX:BB1!","NG":"NYMEX:NG1!",
            "HG":"COMEX:HG1!","ZW":"CBOT:ZW1!","ZC":"CBOT:ZC1!","ZS":"CBOT:ZS1!",
        }
        tv_symbol = tv_map_mp.get(base, f"TVC:{base}")

    if tv_symbol:
        st.markdown(f"#### 📊 Graphique {sym_sel} — TradingView")
        tv_html = f"""
        <div style="height:500px;border:1px solid #1a1a1a;border-radius:6px;overflow:hidden;">
          <div class="tradingview-widget-container" style="height:100%;width:100%;">
            <div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div>
            <script type="text/javascript"
              src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {{
              "autosize": true, "symbol": "{tv_symbol}", "interval": "D",
              "timezone": "Europe/Paris", "theme": "dark", "style": "1",
              "locale": "fr", "backgroundColor": "rgba(5,5,5,1)",
              "hide_top_toolbar": false, "allow_symbol_change": false,
              "studies": ["STD;RSI","STD;MACD","STD;BB"],
              "save_image": false, "height": "500", "width": "100%"
            }}
            </script>
          </div>
        </div>"""
        components.html(tv_html, height=510, scrolling=False)
    else:
        # Crypto → graphique Plotly yfinance
        st.markdown(f"#### 📊 Graphique {sym_sel}")
        df_det = _get_price_history(pos["ticker_yf"], period="6mo")
        if not df_det.empty:
            fig_det = go.Figure(go.Candlestick(
                x=df_det.index,
                open=df_det["Close"], high=df_det["Close"],
                low=df_det["Close"],  close=df_det["Close"],
                name=sym_sel, increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350"
            ))
            # Simplifier en ligne pour la crypto (OHLC non dispo via history simple)
            fig_det = go.Figure(go.Scatter(
                x=df_det.index, y=df_det["Close"],
                line=dict(color=cfg["color"], width=2),
                fill="tozeroy", fillcolor=f"{cfg['color']}11"
            ))
            fig_det.add_hline(y=pos["buy_price"], line_color="#4d9fff",
                              line_dash="dash", line_width=1,
                              annotation_text=f"Prix d'achat ${pos['buy_price']:,.4g}",
                              annotation_font=dict(size=9, color="#4d9fff"))
            fig_det.update_layout(
                template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505",
                height=400, margin=dict(l=20,r=20,t=20,b=20),
                showlegend=False, xaxis_rangeslider_visible=False,
            )
            st.plotly_chart(fig_det, use_container_width=True)

    # Infos supplémentaires
    st.markdown("---")
    st.markdown("#### 📋 Détails de la position")
    info_cols = st.columns(4)
    info_cols[0].markdown(f"**Type** : {pos['asset_type']}")
    info_cols[1].markdown(f"**Quantité** : {pos['qty']}")
    info_cols[2].markdown(f"**Date d'achat** : {pos.get('buy_date', '—')}")
    info_cols[3].markdown(f"**Frais** : ${pos.get('fees', 0):.2f}")
    if pos.get("note"):
        st.caption(f"📝 Note : {pos['note']}")


# ══════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════

def show_portfolio():
    st.markdown(PORTFOLIO_CSS, unsafe_allow_html=True)

    # ── Header ──
    st.markdown("""
    <div class="port-header">
      <div>
        <div class="port-title">💼 PORTFOLIO TRACKER</div>
        <div class="port-sub">P&L EN TEMPS RÉEL · ACTIONS · CRYPTO · FOREX · MATIÈRES PREMIÈRES</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Warning mode invité ──
    if st.session_state.get("guest_mode"):
        st.warning("⚠️ Mode invité — vos positions ne seront pas sauvegardées. Connectez-vous pour activer la persistance Firebase.")

    # ── Chargement ──
    positions = _load_portfolio()

    # ── Bouton export PDF ──
    col_exp1, col_exp2, col_exp3 = st.columns([1,1,2])
    with col_exp1:
        import export_pdf as _epdf
        positions_for_pdf = st.session_state.get("positions_computed", [])
        _epdf.download_button_portfolio(positions_for_pdf, key="pdf_portfolio_main")

    # ── Onglets ──
    tab_vue, tab_analyse, tab_historique, tab_ajouter = st.tabs([
        "📊 VUE D'ENSEMBLE",
        "🔬 ANALYSE DÉTAILLÉE",
        "📈 HISTORIQUE",
        "➕ GÉRER LES POSITIONS",
    ])

    # ── Calcul enrichi (commun à tous les onglets) ──
    with st.spinner("Mise à jour des prix..."):
        enriched = _compute_positions(positions)
    kpis = _portfolio_kpis(enriched)

    # ══════════════════
    #  ONGLET 1 — VUE
    # ══════════════════
    with tab_vue:
        if enriched:
            _render_kpis(kpis)
            st.markdown("---")
            _render_allocation_chart(enriched)
            st.markdown("---")

        to_delete = _render_positions_table(enriched)
        if to_delete is not None:
            positions.pop(to_delete)
            _save_portfolio(positions)
            st.rerun()

    # ══════════════════════
    #  ONGLET 2 — ANALYSE
    # ══════════════════════
    with tab_analyse:
        _render_detail_tab(enriched)

    # ══════════════════════
    #  ONGLET 3 — HISTORIQUE
    # ══════════════════════
    with tab_historique:
        if enriched:
            _render_history_chart(enriched)
        else:
            st.info("Ajoutez des positions pour voir l'historique.")

    # ═══════════════════════════
    #  ONGLET 4 — GÉRER
    # ═══════════════════════════
    with tab_ajouter:
        updated = _render_add_form(positions)
        if updated is not None:
            _save_portfolio(updated)
            st.success("✅ Position ajoutée et sauvegardée !")
            st.rerun()

        # Liste actuelle avec suppression
        if positions:
            st.markdown('<div class="section-bar">» POSITIONS ACTUELLES</div>', unsafe_allow_html=True)
            for i, pos in enumerate(positions):
                cfg = ASSET_TYPE_CONFIG[pos["asset_type"]]
                col_a, col_b, col_c = st.columns([4, 2, 1])
                col_a.markdown(f"{cfg['emoji']} **{_display_symbol(pos['symbol'], pos['asset_type'])}** "
                               f"— {pos['qty']} @ ${pos['buy_price']:,.4g}")
                col_b.caption(f"{pos['asset_type']} · {pos.get('buy_date','')}")
                if col_c.button("🗑️", key=f"del_manage_{i}"):
                    positions.pop(i)
                    _save_portfolio(positions)
                    st.rerun()

        # Bouton sauvegarde manuelle
        st.markdown("---")
        col_sv1, col_sv2 = st.columns([3, 1])
        with col_sv2:
            if st.button("💾 SAUVEGARDER", use_container_width=True, key="btn_manual_save"):
                _save_portfolio(positions)
                st.success("Sauvegardé ✅")
