"""
interface_matieres_premieres.py
Module MATIÈRES PREMIÈRES — AM Trading Terminal
Métaux précieux, énergie, agricole, indices matières premières
"""

import json
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import feedparser
import requests
from datetime import datetime, timedelta


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ============================================================
#  1. DONNÉES MATIÈRES PREMIÈRES
# ============================================================

COMMODITIES = {
    "MÉTAUX PRÉCIEUX": [
        {"name": "OR",       "ticker": "GC=F",  "symbol": "GOLD",  "unit": "$/oz",  "emoji": "🥇"},
        {"name": "ARGENT",   "ticker": "SI=F",  "symbol": "SILVER","unit": "$/oz",  "emoji": "🥈"},
        {"name": "PLATINE",  "ticker": "PL=F",  "symbol": "PLAT",  "unit": "$/oz",  "emoji": "⚪"},
        {"name": "PALLADIUM","ticker": "PA=F",  "symbol": "PALL",  "unit": "$/oz",  "emoji": "🔘"},
    ],
    "ÉNERGIE": [
        {"name": "PÉTROLE WTI",  "ticker": "CL=F",  "symbol": "WTI",   "unit": "$/bbl", "emoji": "🛢️"},
        {"name": "BRENT",        "ticker": "BZ=F",  "symbol": "BRENT", "unit": "$/bbl", "emoji": "⚫"},
        {"name": "GAZ NATUREL",  "ticker": "NG=F",  "symbol": "GAS",   "unit": "$/MMBtu","emoji": "🔥"},
        {"name": "CHARBON",      "ticker": "MTF=F", "symbol": "COAL",  "unit": "$/t",   "emoji": "⬛"},
    ],
    "MÉTAUX INDUSTRIELS": [
        {"name": "CUIVRE",   "ticker": "HG=F",  "symbol": "COPPER","unit": "$/lb",  "emoji": "🟤"},
        {"name": "ALUMINIUM","ticker": "ALI=F", "symbol": "ALU",   "unit": "$/t",   "emoji": "🔩"},
        {"name": "ZINC",     "ticker": "ZNC=F", "symbol": "ZINC",  "unit": "$/t",   "emoji": "🔲"},
        {"name": "NICKEL",   "ticker": "NKL=F", "symbol": "NICKEL","unit": "$/t",   "emoji": "🔵"},
    ],
    "AGRICOLE": [
        {"name": "BLÉ",     "ticker": "ZW=F",  "symbol": "WHEAT", "unit": "¢/bu",  "emoji": "🌾"},
        {"name": "MAÏS",    "ticker": "ZC=F",  "symbol": "CORN",  "unit": "¢/bu",  "emoji": "🌽"},
        {"name": "SOJA",    "ticker": "ZS=F",  "symbol": "SOYA",  "unit": "¢/bu",  "emoji": "🟡"},
        {"name": "SUCRE",   "ticker": "SB=F",  "symbol": "SUGAR", "unit": "¢/lb",  "emoji": "🍬"},
        {"name": "CAFÉ",    "ticker": "KC=F",  "symbol": "COFFEE","unit": "¢/lb",  "emoji": "☕"},
        {"name": "CACAO",   "ticker": "CC=F",  "symbol": "COCOA", "unit": "$/t",   "emoji": "🍫"},
    ],
}

@st.cache_data(ttl=120)
def get_commodity_price(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price      = info['last_price']
        prev_close = info['previous_close']
        change     = ((price - prev_close) / prev_close) * 100
        return {"price": price, "change": change, "prev": prev_close, "ok": True}
    except:
        return {"price": 0, "change": 0, "prev": 0, "ok": False}

@st.cache_data(ttl=300)
def get_commodity_history(ticker, period="3mo"):
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        if hasattr(df.columns, 'get_level_values'):
            df.columns = df.columns.get_level_values(0)
        return df.reset_index()
    except:
        return None

@st.cache_data(ttl=300)
def get_commodities_news():
    items = []
    feeds = [
        ("Reuters Commodities", "https://feeds.reuters.com/reuters/businessNews"),
        ("FT Commodities",      "https://www.ft.com/commodities?format=rss"),
        ("Bloomberg Commodity", "https://feeds.bloomberg.com/markets/news.rss"),
    ]
    # Fallback RSS fiables
    fallback_feeds = [
        ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
        ("Investing.com",    "https://www.investing.com/rss/news_commodities.rss"),
    ]
    for name, url in fallback_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                try:
                    dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = "--:--"
                title = entry.get('title', '')
                # Filtrer sur matières premières
                keywords = ['gold','oil','copper','silver','wheat','gas','commodity','commodities',
                           'or ','pétrole','cuivre','blé','énergie','mineral','metal']
                if any(k in title.lower() for k in keywords) or True:  # tout afficher
                    items.append({
                        "title": title[:80],
                        "link":  entry.get('link', '#'),
                        "time":  time_str,
                        "source": name
                    })
            if items:
                break
        except:
            continue
    return items[:12]


# ============================================================
#  2. GRAPHIQUE SPARKLINE HTML
# ============================================================

def make_sparkline(values, color="#ff6600", width=120, height=40):
    if not values or len(values) < 2:
        return "<div style='width:120px;height:40px;'></div>"
    mn = min(values)
    mx = max(values)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(values):
        x = i / (len(values)-1) * width
        y = height - ((v - mn) / rng * (height - 4)) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    last_up = values[-1] >= values[-2]
    c = "#00ff41" if last_up else "#ff2222"
    return f"""<svg width="{width}" height="{height}" style="display:block;">
        <polyline points="{polyline}" fill="none" stroke="{c}" stroke-width="1.5" opacity="0.9"/>
        <circle cx="{width}" cy="{height - ((values[-1]-mn)/rng*(height-4)) - 2:.1f}"
                r="2.5" fill="{c}"/>
    </svg>"""


# ============================================================
#  3. CARTE PRIX PRINCIPALE (grand format)
# ============================================================

def render_price_card(item, data):
    price   = data.get("price", 0)
    change  = data.get("change", 0)
    ok      = data.get("ok", False)
    up      = change >= 0
    color   = "#00ff41" if up else "#ff2222"
    sign    = "+" if up else ""
    bg      = "rgba(0,255,65,0.04)" if up else "rgba(255,34,34,0.04)"
    border  = "rgba(0,255,65,0.2)"  if up else "rgba(255,34,34,0.2)"
    arrow   = "▲" if up else "▼"

    price_str = f"{price:,.2f}" if ok else "N/A"

    st.markdown(f"""
    <div style="background:#080808;border:1px solid #1a1a1a;border-top:2px solid {color if ok else '#333'};
                padding:12px 14px;margin-bottom:6px;position:relative;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
            <div>
                <span style="font-size:9px;color:#444;font-family:'DM Sans', Arial, sans-serif;
                             letter-spacing:0.8px;text-transform:uppercase;">{item['emoji']} {item['name']}</span>
                <div style="font-size:18px;font-weight:700;color:#e8e8e8;
                            font-family:'DM Sans', Arial, sans-serif;letter-spacing:-0.5px;margin-top:2px;">
                    {price_str}
                </div>
                <span style="font-size:9px;color:#333;font-family:'DM Sans', Arial, sans-serif;">{item['unit']}</span>
            </div>
            <div style="text-align:right;">
                <div style="background:{bg};border:1px solid {border};
                            color:{color};font-family:'DM Sans', Arial, sans-serif;
                            font-size:12px;font-weight:700;padding:4px 8px;letter-spacing:0.4px;">
                    {arrow} {sign}{change:.2f}%
                </div>
                <div style="font-size:9px;color:#333;margin-top:4px;font-family:'DM Sans', Arial, sans-serif;">
                    CLÔTURE: {data.get('prev',0):,.2f}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
#  4. INTERFACE PRINCIPALE
# ============================================================

def show_matieres_premieres():

    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        .section-header {
            color: #ff6600;
            font-family: 'DM Sans', Arial, sans-serif;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 3px;
            padding: 5px 0 5px 10px;
            border-left: 3px solid #ff6600;
            border-bottom: 1px solid #1a1a1a;
            margin: 10px 0 10px 0;
        }
        .cat-header {
            color: #ffcc00;
            font-family: 'DM Sans', Arial, sans-serif;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
            padding: 4px 8px;
            border-left: 2px solid #ffcc00;
            background: #0a0800;
            margin: 12px 0 8px 0;
        }
        .comm-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid #0d0d0d;
            font-family: 'DM Sans', Arial, sans-serif;
            transition: background 0.1s;
        }
        .comm-row:hover { background: #0a0500; }
        .news-item {
            padding: 8px 10px;
            border-bottom: 1px solid #0d0d0d;
            cursor: pointer;
        }
        .news-item:hover { background: #0a0500; }
    </style>
    """, unsafe_allow_html=True)

    # ── HEADER ──────────────────────────────────────────────
    st.markdown('<div class="section-header">⛏️ MATIÈRES PREMIÈRES — TERMINAL</div>',
                unsafe_allow_html=True)

    # ── MODULE SELECTOR ─────────────────────────────────────
    if "mp_module" not in st.session_state:
        st.session_state.mp_module = "TABLEAU DE BORD"

    modules = ["TABLEAU DE BORD", "MÉTAUX PRÉCIEUX", "ÉNERGIE",
               "MÉTAUX INDUSTRIELS", "AGRICOLE", "GRAPHIQUES", "ANALYSES & NEWS"]
    cols = st.columns(len(modules))
    for i, mod in enumerate(modules):
        with cols[i]:
            active = st.session_state.mp_module == mod
            if st.button(mod, key=f"mp_{i}", use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state.mp_module = mod
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    module = st.session_state.mp_module

    # ════════════════════════════════════════════════════════
    #  MODULE 1 — TABLEAU DE BORD
    # ════════════════════════════════════════════════════════
    if module == "TABLEAU DE BORD":
        _show_dashboard()

    # ════════════════════════════════════════════════════════
    #  MODULES CATÉGORIES
    # ════════════════════════════════════════════════════════
    elif module in ["MÉTAUX PRÉCIEUX", "ÉNERGIE", "MÉTAUX INDUSTRIELS", "AGRICOLE"]:
        _show_category(module)

    # ════════════════════════════════════════════════════════
    #  MODULE GRAPHIQUES
    # ════════════════════════════════════════════════════════
    elif module == "GRAPHIQUES":
        _show_charts()

    # ════════════════════════════════════════════════════════
    #  MODULE ANALYSES & NEWS
    # ════════════════════════════════════════════════════════
    elif module == "ANALYSES & NEWS":
        _show_news()


# ============================================================
#  DASHBOARD — VUE GLOBALE
# ============================================================

def _show_dashboard():

    if "mp_selected" not in st.session_state:
        st.session_state.mp_selected = None

    # ── Init actif sélectionné ──
    if "mp_selected" not in st.session_state:
        st.session_state.mp_selected = None

    # ── Chargement de toutes les données ──
    all_items = []
    for cat, items in COMMODITIES.items():
        for item in items:
            all_items.append((cat, item))

    with st.spinner("Chargement des prix..."):
        prices = {}
        for _, item in all_items:
            prices[item["ticker"]] = get_commodity_price(item["ticker"])

    # ── KPI TOP ROW ──
    st.markdown('<div class="section-header">📊 MARCHÉS EN TEMPS RÉEL</div>',
                unsafe_allow_html=True)

    # 4 grands indicateurs
    key_items = [
        next(i for _, i in all_items if i["symbol"] == "GOLD"),
        next(i for _, i in all_items if i["symbol"] == "WTI"),
        next(i for _, i in all_items if i["symbol"] == "COPPER"),
        next(i for _, i in all_items if i["symbol"] == "WHEAT"),
    ]
    k_cols = st.columns(4)
    for col, item in zip(k_cols, key_items):
        d = prices[item["ticker"]]
        up = d["change"] >= 0
        color = "#00ff41" if up else "#ff2222"
        sign = "+" if up else ""
        with col:
            st.markdown(f"""
            <div style="background:#080808;border:1px solid #1a1a1a;
                        border-top:3px solid {color};padding:12px;text-align:center;">
                <div style="color:#444;font-size:9px;font-family:'DM Sans', Arial, sans-serif;
                            letter-spacing:0.8px;text-transform:uppercase;margin-bottom:4px;">
                    {item['emoji']} {item['name']}
                </div>
                <div style="color:#e8e8e8;font-size:22px;font-family:'DM Mono', monospace;
                            font-weight:500;letter-spacing:-0.5px;">
                    {d['price']:,.2f}
                </div>
                <div style="color:{color};font-size:12px;font-family:'DM Sans', Arial, sans-serif;
                            margin-top:4px;">
                    {'▲' if up else '▼'} {sign}{d['change']:.2f}%
                </div>
                <div style="color:#222;font-size:8px;font-family:'DM Sans', Arial, sans-serif;
                            margin-top:2px;">{item['unit']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── TABLEAU COMPLET ──
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<div class="section-header">📋 TOUTES LES MATIÈRES PREMIÈRES</div>',
                    unsafe_allow_html=True)

        for cat, items in COMMODITIES.items():
            st.markdown(f'<div class="cat-header">▸ {cat}</div>', unsafe_allow_html=True)

            header_html = """
            <div style="display:flex;justify-content:space-between;padding:4px 12px;
                        border-bottom:1px solid #1a1a1a;">
                <span style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;
                             letter-spacing:0.4px;">ACTIF</span>
                <span style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;">PRIX</span>
                <span style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;">VARIATION</span>
                <span style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;">UNITÉ</span>
            </div>"""
            st.markdown(header_html, unsafe_allow_html=True)

            for item in items:
                d = prices[item["ticker"]]
                up = d["change"] >= 0
                color = "#00ff41" if up else "#ff2222"
                sign = "+" if up else ""
                arrow = "▲" if up else "▼"
                price_str = f"{d['price']:,.2f}" if d["ok"] else "—"
                is_sel = st.session_state.mp_selected == item["ticker"]
                c1, c2, c3, c4 = st.columns([3, 2.5, 2, 1.5])
                with c1:
                    label = f"📊 {item['emoji']} {item['name']}" if is_sel else f"{item['emoji']} {item['name']}"
                    if st.button(label, key=f"btn_d_{item['ticker']}", use_container_width=True,
                                 type="primary" if is_sel else "secondary"):
                        st.session_state.mp_selected = None if is_sel else item["ticker"]
                        st.rerun()
                with c2:
                    st.markdown(f"<p style='text-align:right;font-family:DM Mono,monospace;font-size:13px;font-weight:600;color:#fff;margin:6px 0;'>{price_str}</p>", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"<p style='text-align:right;font-size:12px;color:{color};margin:6px 0;'>{arrow} {sign}{d['change']:.2f}%</p>", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"<p style='text-align:right;font-size:9px;color:#444;margin:8px 0;'>{item['unit']}</p>", unsafe_allow_html=True)

    # ── GRAPHIQUE ACTIF SÉLECTIONNÉ ──
    if st.session_state.get("mp_selected"):
        sel_ticker = st.session_state.mp_selected
        sel_item   = next((i for _, i in all_items if i["ticker"] == sel_ticker), None)
        if sel_item:
            sel_d  = prices.get(sel_ticker, {"price": 0, "change": 0, "ok": False})
            up     = sel_d["change"] >= 0
            c      = "#00ff41" if up else "#ff2222"
            sign   = "+" if up else ""
            st.markdown(f"""
            <div style="background:#080808;border:1px solid #1a1a1a;border-top:3px solid #ff6600;
                        padding:10px 16px;margin:10px 0 4px 0;display:flex;
                        justify-content:space-between;align-items:center;">
                <span style="color:#ff6600;font-family:DM Sans,Arial,sans-serif;font-size:14px;
                             font-weight:700;">{sel_item["emoji"]} {sel_item["name"]}</span>
                <div style="display:flex;gap:16px;align-items:center;">
                    <span style="color:#e8e8e8;font-family:DM Mono,monospace;font-size:20px;
                                 font-weight:600;">{sel_d["price"]:,.2f}</span>
                    <span style="color:{c};font-size:13px;font-weight:600;">
                        {"▲" if up else "▼"} {sign}{sel_d["change"]:.2f}%
                    </span>
                    <span style="color:#333;font-size:10px;">{sel_item["unit"]}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            components.html(
                render_commodity_chart(sel_ticker, pair_label=f"{sel_item['emoji']} {sel_item['name']}", height=460),
                height=470, scrolling=False
            )
            _show_commodity_info(sel_item, sel_d)
            st.markdown("<hr style=\'border:none;border-top:1px solid #111;margin:16px 0;\'>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-header">🏆 TOP MOVERS</div>', unsafe_allow_html=True)

        # Trier par variation absolue
        movers = []
        for _, item in all_items:
            d = prices[item["ticker"]]
            if d["ok"]:
                movers.append({"item": item, "data": d})
        movers.sort(key=lambda x: abs(x["data"]["change"]), reverse=True)

        st.markdown('<div class="cat-header">▲ PLUS FORTES HAUSSES</div>', unsafe_allow_html=True)
        hausses = [m for m in movers if m["data"]["change"] > 0][:5]
        for m in hausses:
            d = m["data"]
            item = m["item"]
            st.markdown(f"""
            <div class="comm-row">
                <span style="color:#aaa;font-family:'DM Sans', Arial, sans-serif;font-size:11px;">
                    {item['emoji']} {item['name']}</span>
                <span style="color:#00ff41;font-family:'DM Sans', Arial, sans-serif;
                             font-size:13px;font-weight:700;">+{d['change']:.2f}%</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="cat-header">▼ PLUS FORTES BAISSES</div>', unsafe_allow_html=True)
        baisses = [m for m in movers if m["data"]["change"] < 0][:5]
        for m in baisses:
            d = m["data"]
            item = m["item"]
            st.markdown(f"""
            <div class="comm-row">
                <span style="color:#aaa;font-family:'DM Sans', Arial, sans-serif;font-size:11px;">
                    {item['emoji']} {item['name']}</span>
                <span style="color:#ff2222;font-family:'DM Sans', Arial, sans-serif;
                             font-size:13px;font-weight:700;">{d['change']:.2f}%</span>
            </div>""", unsafe_allow_html=True)

        # ── Ratio Or/Argent ──
        st.markdown('<div class="section-header">📐 RATIOS CLÉS</div>', unsafe_allow_html=True)
        gold_p   = prices["GC=F"]["price"]
        silver_p = prices["SI=F"]["price"]
        wti_p    = prices["CL=F"]["price"]
        brent_p  = prices["BZ=F"]["price"]
        copper_p = prices["HG=F"]["price"]

        ratios = []
        if gold_p and silver_p:
            ratios.append(("Or / Argent", gold_p/silver_p if silver_p else 0, "oz Ag / oz Au", "normal: 60-80"))
        if brent_p and wti_p:
            ratios.append(("Brent / WTI", brent_p/wti_p if wti_p else 0, "spread", "normal: >1"))
        if gold_p and copper_p:
            ratios.append(("Or / Cuivre", gold_p/copper_p if copper_p else 0, "oz Au / lb Cu", "baromètre éco"))

        for name, val, unit, note in ratios:
            st.markdown(f"""
            <div style="background:#080808;border:1px solid #1a1a1a;padding:10px 12px;
                        margin-bottom:6px;border-left:3px solid #ffcc00;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#ffcc00;font-family:'DM Sans', Arial, sans-serif;
                                 font-size:10px;letter-spacing:0.4px;">{name}</span>
                    <span style="color:#e8e8e8;font-family:'DM Sans', Arial, sans-serif;
                                 font-size:16px;font-weight:700;">{val:.1f}</span>
                </div>
                <div style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;
                            margin-top:3px;">{unit} — {note}</div>
            </div>""", unsafe_allow_html=True)


# ============================================================
#  VUE PAR CATÉGORIE
# ============================================================

def _show_category(category):
    items = COMMODITIES.get(category, [])

    st.markdown(f'<div class="section-header">⛏️ {category}</div>', unsafe_allow_html=True)

    with st.spinner("Chargement..."):
        prices = {item["ticker"]: get_commodity_price(item["ticker"]) for item in items}

    col_cards, col_detail = st.columns([1, 2])

    with col_cards:
        st.markdown('<div class="section-header">💹 PRIX LIVE</div>', unsafe_allow_html=True)
        for item in items:
            render_price_card(item, prices[item["ticker"]])

    with col_detail:
        # Sélecteur actif
        if f"mp_active_{category}" not in st.session_state:
            st.session_state[f"mp_active_{category}"] = items[0]["name"]

        active_name = st.session_state[f"mp_active_{category}"]
        active_item = next((i for i in items if i["name"] == active_name), items[0])

        tab_cols = st.columns(len(items))
        for col, item in zip(tab_cols, items):
            with col:
                active = item["name"] == active_name
                if st.button(item["emoji"] + " " + item["name"],
                             key=f"cat_{category}_{item['name']}",
                             use_container_width=True,
                             type="primary" if active else "secondary"):
                    st.session_state[f"mp_active_{category}"] = item["name"]
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # Graphique AM.Terminal
        components.html(
            render_commodity_chart(active_item["ticker"], pair_label=f"{active_item['emoji']} {active_item['name']}", height=420),
            height=430, scrolling=False
        )

        # Infos fondamentales
        d = prices[active_item["ticker"]]
        _show_commodity_info(active_item, d)


# _get_tv_symbol remplacé par render_commodity_chart


@st.cache_data(ttl=300)
@st.cache_data(ttl=300)
def _fetch_candles(ticker: str, period: str = "6mo", interval: str = "1d") -> list:
    """Fetch OHLCV via yfinance."""
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return []
        if hasattr(df.columns, 'get_level_values'):
            df.columns = df.columns.get_level_values(0)
        df = df.tail(300).reset_index()
        ts_col = "Datetime" if "Datetime" in df.columns else "Date"
        out = []
        for _, row in df.iterrows():
            try:
                out.append({
                    "t": int(row[ts_col].timestamp()),
                    "o": float(row["Open"]),
                    "h": float(row["High"]),
                    "l": float(row["Low"]),
                    "c": float(row["Close"]),
                    "v": float(row.get("Volume", 0) or 0),
                })
            except Exception:
                continue
        return out
    except Exception as e:
        print(f"[MP chart] {ticker}: {e}")
        return []


def render_commodity_chart(ticker: str, pair_label: str = "", height: int = 420) -> str:
    """Graphique Canvas AM.Terminal complet pour matières premières (yfinance).
    Inclut : toolbar TF, MA/BB/Vol, dropdown Mode, crosshair, tooltip, volume panel.
    """
    candles = _fetch_candles(ticker, period="6mo", interval="1d")

    # Pré-fetch tous les TFs côté Python → injectés en JSON dans le JS
    import json as _json
    def _tf_json(period, interval):
        c = _fetch_candles(ticker, period=period, interval=interval)
        return _json.dumps(c) if c else "[]"

    d_1h  = _tf_json("60d",  "1h")
    d_4h  = _tf_json("180d", "1h")   # yfinance pas de 4h, on simule avec 1h sur 180j
    d_1d  = _json.dumps(candles)     # déjà fetché
    d_1wk = _tf_json("5y",   "1wk")
    d_1mo = _tf_json("max",  "1mo")

    if not candles:
        return (f'<div style="background:#131722;height:{height}px;display:flex;'
                f'align-items:center;justify-content:center;color:#50535e;'
                f'font-family:IBM Plex Mono,monospace;font-size:12px;'
                f'border:1px solid #1e222d;">Données indisponibles — {ticker}</div>')

    import json as _json
    cd   = _json.dumps(candles)
    last = candles[-1]["c"]
    frst = candles[0]["o"]
    pct  = (last - frst) / frst * 100 if frst else 0
    bull = last >= frst
    pc   = "#26a69a" if bull else "#ef5350"
    cc   = "up"      if bull else "dn"
    arr  = "▲"       if bull else "▼"
    oh   = candles[-1]["o"]
    hh_  = candles[-1]["h"]
    lh   = candles[-1]["l"]
    ch   = candles[-1]["c"]

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:#131722;color:#d1d4dc;font-family:'IBM Plex Mono',monospace;
  font-size:11px;width:100%;height:{height}px;overflow:hidden;display:flex;flex-direction:column;}}

/* ── HEADER ── */
.hdr{{display:flex;align-items:center;flex-wrap:wrap;gap:10px;background:#1e222d;
  border-bottom:1px solid #2a2e39;height:42px;padding:0 12px;flex-shrink:0;}}
.pair{{font-size:13px;font-weight:700;white-space:nowrap;}}
.price{{font-size:17px;font-weight:700;white-space:nowrap;transition:color .15s;}}
.chg{{font-size:10px;padding:2px 7px;border-radius:3px;font-weight:600;white-space:nowrap;}}
.chg.up{{background:rgba(38,166,154,.15);color:#26a69a;}}
.chg.dn{{background:rgba(239,83,80,.15);color:#ef5350;}}
.ohlc{{display:flex;gap:10px;margin-left:4px;}}
.oi{{display:flex;flex-direction:column;gap:1px;}}
.ol{{font-size:7px;color:#50535e;letter-spacing:1px;text-transform:uppercase;}}
.ov{{font-size:10px;font-weight:600;}}

/* ── TOOLBAR ── */
.toolbar{{display:flex;align-items:center;background:#1e222d;
  border-bottom:1px solid #2a2e39;height:30px;padding:0 8px;gap:2px;flex-shrink:0;}}
.tf-btn{{padding:2px 8px;border:none;background:transparent;color:#787b86;
  font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;
  cursor:pointer;border-radius:3px;transition:all .1s;text-transform:uppercase;letter-spacing:.5px;}}
.tf-btn:hover{{background:#2a2e39;color:#d1d4dc;}}
.tf-btn.active{{background:rgba(255,152,0,.12);color:#ff9800;}}
.tb-sep{{width:1px;height:16px;background:#2a2e39;margin:0 3px;}}
.ind-btn{{padding:2px 8px;border:1px solid #2a2e39;background:transparent;color:#787b86;
  font-family:'IBM Plex Mono',monospace;font-size:9px;cursor:pointer;border-radius:3px;transition:all .1s;}}
.ind-btn:hover{{background:#2a2e39;color:#d1d4dc;}}
.ind-btn.on{{color:#ff9800;border-color:rgba(255,152,0,.4);}}

/* ── MODE DROPDOWN ── */
.mode-wrap{{position:relative;margin-left:auto;}}
.mode-btn{{display:flex;align-items:center;gap:6px;padding:0 10px;height:30px;
  cursor:pointer;background:transparent;border:none;border-left:1px solid #2a2e39;
  font-family:'IBM Plex Mono',monospace;transition:background .12s;}}
.mode-btn:hover{{background:#2a2e39;}}
.mode-lbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#b2b5be;}}
.mode-caret{{font-size:7px;color:#50535e;transition:transform .15s;}}
.mode-caret.open{{transform:rotate(180deg);}}
.mode-dd{{display:none;position:absolute;top:100%;right:0;background:#1e222d;
  border:1px solid #2a2e39;min-width:180px;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,.7);}}
.mode-dd.open{{display:block;}}
.mode-opt{{display:flex;align-items:center;gap:10px;padding:9px 12px;cursor:pointer;
  border-bottom:1px solid #131722;transition:background .1s;}}
.mode-opt:last-child{{border-bottom:none;}}
.mode-opt:hover{{background:#2a2e39;}}
.mode-opt.active{{background:rgba(255,152,0,.05);}}
.mo-icon{{font-size:14px;min-width:18px;}}
.mo-text{{flex:1;}}
.mo-lbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;}}
.mo-desc{{font-size:8px;color:#50535e;margin-top:1px;}}
.mo-check{{font-size:10px;color:#ff9800;opacity:0;}}
.mode-opt.active .mo-check{{opacity:1;}}
.mo-badge{{font-size:7px;padding:1px 4px;border-radius:2px;
  background:rgba(255,152,0,.1);color:#ff9800;border:1px solid rgba(255,152,0,.2);}}

/* ── CHART ── */
.chart-zone{{flex:1;position:relative;overflow:hidden;display:flex;flex-direction:column;}}
#cv{{display:block;cursor:crosshair;flex:1;}}
.vol-sep{{height:1px;background:#2a2e39;flex-shrink:0;}}
#cvVol{{display:block;background:#131722;flex-shrink:0;}}

/* ── TOOLTIP ── */
#tt{{position:fixed;pointer-events:none;z-index:9999;background:#1e222d;
  border:1px solid #2a2e39;padding:7px 11px;border-radius:4px;font-size:10px;
  box-shadow:0 4px 16px rgba(0,0,0,.6);display:none;min-width:145px;}}
.td{{color:#787b86;font-size:8px;margin-bottom:5px;letter-spacing:1px;}}
.tr{{display:flex;justify-content:space-between;gap:14px;margin:2px 0;}}
.tl{{color:#50535e;font-size:9px;}}.tv{{font-weight:600;font-size:10px;}}
</style></head><body>

<!-- HEADER -->
<div class="hdr">
  <div class="pair">{pair_label}</div>
  <div class="price" id="prc" style="color:{pc}">{last:,.2f}</div>
  <div class="chg {cc}" id="pchg">{arr} {abs(pct):.2f}%</div>
  <div class="ohlc">
    <div class="oi"><div class="ol">O</div><div class="ov" id="ho">{oh:,.2f}</div></div>
    <div class="oi"><div class="ol">H</div><div class="ov" id="hh" style="color:#26a69a">{hh_:,.2f}</div></div>
    <div class="oi"><div class="ol">L</div><div class="ov" id="hl" style="color:#ef5350">{lh:,.2f}</div></div>
    <div class="oi"><div class="ol">C</div><div class="ov" id="hc">{ch:,.2f}</div></div>
  </div>
</div>

<!-- TOOLBAR -->
<div class="toolbar">
  <button class="tf-btn" onclick="setTF(this,'1h')">1H</button>
  <button class="tf-btn" onclick="setTF(this,'4h')">4H</button>
  <button class="tf-btn active" id="tfD" onclick="setTF(this,'1d')">1D</button>
  <button class="tf-btn" onclick="setTF(this,'1wk')">1W</button>
  <button class="tf-btn" onclick="setTF(this,'1mo')">1M</button>
  <div class="tb-sep"></div>
  <button class="ind-btn on" id="btnMA"  onclick="toggleMA()">MA</button>
  <button class="ind-btn on" id="btnVol" onclick="toggleVol()">Vol</button>
  <button class="ind-btn"    id="btnBB"  onclick="toggleBB()">BB</button>
  <!-- MODE -->
  <div class="mode-wrap">
    <button class="mode-btn" id="modeBtn" onclick="toggleDD()">
      <span class="mode-icon" id="modeIcon">📊</span>
      <span class="mode-lbl" id="modeLbl">Normal</span>
      <span class="mode-caret" id="modeCaret">&#9660;</span>
    </button>
    <div class="mode-dd" id="modeDD">
      <div class="mode-opt active" onclick="pickMode('normal','Normal','📊')">
        <span class="mo-icon">📊</span>
        <div class="mo-text"><div class="mo-lbl" style="color:#b2b5be">Normal</div><div class="mo-desc">Bougies · MA · Volume</div></div>
        <span class="mo-check">✓</span>
      </div>
      <div class="mode-opt" onclick="pickMode('pro','Pro','⚡')">
        <span class="mo-icon">⚡</span>
        <div class="mo-text"><div class="mo-lbl" style="color:#ff9800">Pro</div><div class="mo-desc">Indicateurs avancés</div></div>
        <span class="mo-badge">Bientôt</span><span class="mo-check">✓</span>
      </div>
      <div class="mode-opt" onclick="pickMode('quant','Quant','🤖')">
        <span class="mo-icon">🤖</span>
        <div class="mo-text"><div class="mo-lbl" style="color:#f0b429">Quant</div><div class="mo-desc">Signaux algo · Patterns</div></div>
        <span class="mo-badge">Bientôt</span><span class="mo-check">✓</span>
      </div>
    </div>
  </div>
</div>

<!-- CHART -->
<div class="chart-zone">
  <canvas id="cv"></canvas>
  <div class="vol-sep" id="volSep"></div>
  <canvas id="cvVol" id="cvVolEl"></canvas>
</div>

<!-- TOOLTIP -->
<div id="tt">
  <div class="td" id="ttD"></div>
  <div class="tr"><span class="tl">Open</span><span class="tv" id="ttO"></span></div>
  <div class="tr"><span class="tl">High</span><span class="tv" id="ttH" style="color:#26a69a"></span></div>
  <div class="tr"><span class="tl">Low</span><span class="tv" id="ttL" style="color:#ef5350"></span></div>
  <div class="tr"><span class="tl">Close</span><span class="tv" id="ttC"></span></div>
</div>

<script>
// ════════════════════════════════════════════════════════
//  DONNÉES & CONFIG
// ════════════════════════════════════════════════════════
const TF_DATA = {{
  '1h':  {d_1h},
  '4h':  {d_4h},
  '1d':  {d_1d},
  '1wk': {d_1wk},
  '1mo': {d_1mo},
}};
const PAD = {{l:0,r:70,t:8,b:22}};
const VPAH = 60;

let showMA  = true;
let showVol = true;
let showBB  = false;
let CHART_MODE = 'normal';

function makeD(raw) {{
  return {{
    t:raw.map(r=>r.t), o:raw.map(r=>r.o), h:raw.map(r=>r.h),
    l:raw.map(r=>r.l), c:raw.map(r=>r.c), v:raw.map(r=>r.v),
  }};
}}

let D = makeD(TF_DATA['1d'].length ? TF_DATA['1d'] : []);
let VS=Math.max(0,D.t.length-120), VE=D.t.length;
let HX=-1, HY=-1, MX=0, MY=0;
let drag=false, dragX=0, dragVS=0;

const cv    = document.getElementById('cv');
const cvVol = document.querySelector('#cvVol, canvas:last-of-type');
const ctx   = cv.getContext('2d');
const ctxV  = cvVol ? cvVol.getContext('2d') : null;
const $     = id => document.getElementById(id);
const st    = (id,v) => {{ const e=$(id); if(e) e.textContent=v; }};
const sc    = (id,c) => {{ const e=$(id); if(e) e.style.color=c; }};

const fmt = v => {{
  if(v==null||isNaN(v)) return '—';
  if(v>=10000) return v.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
  if(v>=100)   return v.toFixed(2);
  if(v>=1)     return v.toFixed(4);
  return v.toFixed(6);
}};
const fmtD = ts => new Date(ts*1000).toLocaleDateString('fr-FR',{{day:'2-digit',month:'short',year:'2-digit'}});
const maCalc = (arr,p) => arr.map((_,i) => i<p-1 ? null : arr.slice(i-p+1,i+1).reduce((a,b)=>a+b,0)/p);

// ════════════════════════════════════════════════════════
//  SETUP CANVAS
// ════════════════════════════════════════════════════════
function setup() {{
  const W = cv.parentElement.clientWidth || 700;
  const totalH = cv.parentElement.clientHeight || {height}-72;
  const volH = showVol ? VPAH : 0;
  const mainH = Math.max(totalH - volH - (showVol?1:0), 100);

  cv.width=W; cv.height=mainH;
  cv.style.width=W+'px'; cv.style.height=mainH+'px';

  if(cvVol) {{
    cvVol.width=W; cvVol.height=volH;
    cvVol.style.width=W+'px'; cvVol.style.height=volH+'px';
    cvVol.style.display = showVol ? 'block' : 'none';
  }}
  const sep = document.getElementById('volSep');
  if(sep) sep.style.display = showVol ? 'block' : 'none';
}}

// ════════════════════════════════════════════════════════
//  CALCULS INDICATEURS
// ════════════════════════════════════════════════════════
function calcBB(arr, p=20, mult=2) {{
  const ma = maCalc(arr, p);
  return arr.map((_, i) => {{
    if(ma[i]===null) return {{u:null,l:null,m:null}};
    let v=0; for(let j=i-p+1;j<=i;j++) v+=Math.pow(arr[j]-ma[i],2);
    const sd = Math.sqrt(v/p);
    return {{u:ma[i]+mult*sd, l:ma[i]-mult*sd, m:ma[i]}};
  }});
}}

// ════════════════════════════════════════════════════════
//  DESSIN PRINCIPAL
// ════════════════════════════════════════════════════════
function drawMain() {{
  const W=cv.width, H=cv.height;
  ctx.fillStyle='#131722'; ctx.fillRect(0,0,W,H);
  const N=VE-VS; if(N<2) return;

  const ts=D.t.slice(VS,VE), os=D.o.slice(VS,VE), hs=D.h.slice(VS,VE);
  const ls=D.l.slice(VS,VE), cs=D.c.slice(VS,VE);

  const mn=Math.min(...ls), mx2=Math.max(...hs);
  const pd=(mx2-mn)*0.05 || mx2*0.001;
  const lo=mn-pd, hi=mx2+pd, rng=hi-lo||1;
  const CW=(W-PAD.l-PAD.r)/N, BW=Math.max(1,CW*0.72);
  const toX = i => PAD.l+i*CW+CW/2;
  const toY = p => PAD.t+(hi-p)/rng*(H-PAD.t-PAD.b);

  // Grille horizontale
  for(let s=0;s<=5;s++) {{
    const y=PAD.t+s*(H-PAD.t-PAD.b)/5;
    ctx.strokeStyle='#1e222d'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    ctx.fillStyle='#787b86'; ctx.font='9px IBM Plex Mono,monospace';
    ctx.textAlign='left'; ctx.fillText(fmt(hi-s*rng/5), W-PAD.r+4, y+3);
  }}

  // Axe temps
  const nT=Math.min(8,Math.max(3,Math.floor(N/15)));
  ctx.fillStyle='#787b86'; ctx.font='8px IBM Plex Mono,monospace'; ctx.textAlign='center';
  for(let t=0;t<=nT;t++) {{
    const i=Math.floor(t*(N-1)/Math.max(nT,1));
    ctx.strokeStyle='#1e222d'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(toX(i),PAD.t); ctx.lineTo(toX(i),H-PAD.b); ctx.stroke();
    ctx.fillText(new Date(ts[i]*1000).toLocaleDateString('fr-FR',{{day:'2-digit',month:'short'}}), toX(i), H-5);
  }}

  // Bollinger Bands
  if(showBB) {{
    const bb = calcBB(D.c, 20, 2).slice(VS, VE);
    ctx.beginPath(); let s=false;
    for(let i=0;i<N;i++) {{ if(bb[i].u===null) continue; s?ctx.lineTo(toX(i),toY(bb[i].u)):ctx.moveTo(toX(i),toY(bb[i].u)); s=true; }}
    for(let i=N-1;i>=0;i--) {{ if(bb[i].l===null) continue; ctx.lineTo(toX(i),toY(bb[i].l)); }}
    ctx.closePath(); ctx.fillStyle='rgba(255,152,0,.04)'; ctx.fill();
    ['u','l'].forEach(k => {{
      ctx.beginPath(); s=false;
      for(let i=0;i<N;i++) {{ if(bb[i][k]===null) continue; s?ctx.lineTo(toX(i),toY(bb[i][k])):ctx.moveTo(toX(i),toY(bb[i][k])); s=true; }}
      ctx.strokeStyle='rgba(255,152,0,.4)'; ctx.lineWidth=1; ctx.setLineDash([3,3]); ctx.stroke(); ctx.setLineDash([]);
    }});
    ctx.beginPath(); s=false;
    for(let i=0;i<N;i++) {{ if(bb[i].m===null) continue; s?ctx.lineTo(toX(i),toY(bb[i].m)):ctx.moveTo(toX(i),toY(bb[i].m)); s=true; }}
    ctx.strokeStyle='rgba(255,152,0,.5)'; ctx.lineWidth=1; ctx.stroke();
  }}

  // MA 20 / 50 / 200
  if(showMA) {{
    [{{p:20,c:'rgba(255,200,50,.85)'}},{{p:50,c:'rgba(33,150,243,.85)'}},{{p:200,c:'rgba(255,82,82,.85)'}}].forEach((m,mi) => {{
      const ma=maCalc(D.c,m.p).slice(VS,VE);
      ctx.beginPath(); let s=false;
      for(let i=0;i<N;i++) {{ if(ma[i]==null) continue; s?ctx.lineTo(toX(i),toY(ma[i])):ctx.moveTo(toX(i),toY(ma[i])); s=true; }}
      ctx.strokeStyle=m.c; ctx.lineWidth=1.2; ctx.stroke();
      ctx.fillStyle=m.c; ctx.font='8px IBM Plex Mono,monospace'; ctx.textAlign='left';
      ctx.fillText('MA'+m.p, 4+mi*46, 16);
    }});
  }}

  // Bougies
  for(let i=0;i<N;i++) {{
    const x=toX(i), oy=toY(os[i]), hy2=toY(hs[i]), ly=toY(ls[i]), cy2=toY(cs[i]);
    const bull=cs[i]>=os[i], col=bull?'#26a69a':'#ef5350';
    const hw=Math.max(1,BW/2), top=Math.min(oy,cy2), bH=Math.max(1,Math.abs(cy2-oy));
    ctx.strokeStyle=col; ctx.lineWidth=Math.max(1,BW*.1);
    ctx.beginPath(); ctx.moveTo(x,hy2); ctx.lineTo(x,ly); ctx.stroke();
    ctx.fillStyle=col; ctx.fillRect(x-hw,top,hw*2,bH);
    if(i===N-1) {{
      const g=1.5+Math.sin(Date.now()/300);
      ctx.strokeStyle=bull?'rgba(38,166,154,.5)':'rgba(239,83,80,.5)'; ctx.lineWidth=1;
      ctx.strokeRect(x-hw-g,top-g,hw*2+g*2,bH+g*2);
    }}
  }}

  // Ligne dernier prix
  const lc=cs[N-1], lb=lc>=os[N-1];
  const py=toY(lc);
  ctx.strokeStyle=lb?'rgba(38,166,154,.4)':'rgba(239,83,80,.4)';
  ctx.lineWidth=1; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(0,py); ctx.lineTo(W-PAD.r,py); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle=lb?'#26a69a':'#ef5350';
  ctx.beginPath(); ctx.roundRect(W-PAD.r+2,py-8,PAD.r-4,16,2); ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold 8px IBM Plex Mono,monospace'; ctx.textAlign='left';
  ctx.fillText(fmt(lc), W-PAD.r+5, py+4);

  // Crosshair
  if(HX>=0 && HX<N) {{
    const x=toX(HX);
    ctx.strokeStyle='rgba(132,142,156,.35)'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(x,PAD.t); ctx.lineTo(x,H); ctx.stroke();
    if(HY>0) {{
      ctx.beginPath(); ctx.moveTo(0,HY); ctx.lineTo(W-PAD.r,HY); ctx.stroke();
      const hp=hi-(HY-PAD.t)/((H-PAD.t-PAD.b))*rng;
      ctx.fillStyle='#363a45'; ctx.beginPath(); ctx.roundRect(W-PAD.r+2,HY-8,PAD.r-4,16,2); ctx.fill();
      ctx.fillStyle='#d1d4dc'; ctx.font='8px IBM Plex Mono,monospace'; ctx.textAlign='left';
      ctx.fillText(fmt(hp), W-PAD.r+5, HY+4);
    }}
    const ri=VS+HX, b2=D.c[ri]>=D.o[ri];
    st('ho',fmt(D.o[ri])); sc('ho',b2?'#26a69a':'#ef5350');
    st('hh',fmt(D.h[ri])); st('hl',fmt(D.l[ri]));
    st('hc',fmt(D.c[ri])); sc('hc',b2?'#26a69a':'#ef5350');
    const tt=$('tt');
    if(tt) {{
      tt.style.display='block';
      let tx=MX+14, ty=MY-80;
      if(tx+160>window.innerWidth) tx=MX-174; if(ty<0) ty=MY+10;
      tt.style.left=tx+'px'; tt.style.top=ty+'px';
      st('ttD',fmtD(D.t[ri]));
      st('ttO',fmt(D.o[ri])); st('ttH',fmt(D.h[ri]));
      st('ttL',fmt(D.l[ri])); st('ttC',fmt(D.c[ri])); sc('ttC',b2?'#26a69a':'#ef5350');
    }}
  }} else {{ const tt=$('tt'); if(tt) tt.style.display='none'; }}
}}

// ════════════════════════════════════════════════════════
//  VOLUME PANEL
// ════════════════════════════════════════════════════════
function drawVol() {{
  if(!showVol || !cvVol || !ctxV) return;
  const W=cvVol.width, H=cvVol.height;
  ctxV.fillStyle='#131722'; ctxV.fillRect(0,0,W,H);
  const N=VE-VS; if(!N||H<4) return;
  const vs=D.v.slice(VS,VE), maxV=Math.max(...vs)||1;
  const CW=(W-PAD.l-PAD.r)/N;
  const maV=maCalc(D.v,20).slice(VS,VE);
  for(let i=0;i<N;i++) {{
    const bh=Math.max(1,(vs[i]/maxV)*(H-4));
    const bull=D.c[VS+i]>=D.o[VS+i];
    ctxV.fillStyle=bull?'rgba(38,166,154,.5)':'rgba(239,83,80,.5)';
    ctxV.fillRect(PAD.l+i*CW+1, H-bh, Math.max(1,CW-2), bh);
  }}
  ctxV.beginPath(); let s=false;
  for(let i=0;i<N;i++) {{
    if(maV[i]==null) continue;
    const x=PAD.l+i*CW+CW/2, y=H-(maV[i]/maxV)*(H-4);
    s?ctxV.lineTo(x,y):ctxV.moveTo(x,y); s=true;
  }}
  ctxV.strokeStyle='rgba(255,152,0,.7)'; ctxV.lineWidth=1; ctxV.stroke();
  ctxV.fillStyle='#50535e'; ctxV.font='7px IBM Plex Mono,monospace';
  ctxV.textAlign='left'; ctxV.fillText('VOL',4,9);
}}

function render() {{ drawMain(); drawVol(); }}

// ════════════════════════════════════════════════════════
//  INTERACTIONS SOURIS
// ════════════════════════════════════════════════════════
cv.addEventListener('mousemove', e => {{
  const r=cv.getBoundingClientRect(); MX=e.clientX; MY=e.clientY;
  HY=e.clientY-r.top;
  if(drag) {{
    const N=VE-VS, CW=(cv.width-PAD.l-PAD.r)/N;
    const sh=Math.round(-(e.clientX-dragX)/CW);
    let s=Math.max(0,Math.min(D.t.length-N,dragVS+sh));
    VS=s; VE=s+N; render(); return;
  }}
  const N=VE-VS, CW=(cv.width-PAD.l-PAD.r)/N;
  HX=Math.max(0,Math.min(N-1,Math.floor((e.clientX-r.left-PAD.l)/CW)));
  render();
}});
cv.addEventListener('mousedown', e => {{ drag=true; dragX=e.clientX; dragVS=VS; cv.style.cursor='grabbing'; }});
window.addEventListener('mouseup', () => {{ drag=false; cv.style.cursor='crosshair'; }});
cv.addEventListener('mouseleave', () => {{
  HX=-1; HY=-1; const tt=$('tt'); if(tt) tt.style.display='none';
  const n=D.c.length;
  if(n) {{ st('ho',fmt(D.o[n-1])); st('hh',fmt(D.h[n-1])); st('hl',fmt(D.l[n-1])); st('hc',fmt(D.c[n-1])); }}
  render();
}});
cv.addEventListener('wheel', e => {{
  e.preventDefault();
  const N=VE-VS, f=e.deltaY>0?1.1:0.9;
  const nN=Math.max(20,Math.min(D.t.length,Math.round(N*f)));
  const c=HX>=0?VS+HX:Math.floor((VS+VE)/2);
  let s=Math.max(0,c-Math.floor(nN/2));
  let en=s+nN; if(en>D.t.length){{en=D.t.length;s=Math.max(0,en-nN);}}
  VS=s; VE=en; render();
}}, {{passive:false}});

// ════════════════════════════════════════════════════════
//  TIMEFRAMES — rechargement via yfinance (API Streamlit workaround)
// ════════════════════════════════════════════════════════
const TF_YAHOO = {{
  '1h':  {{'interval':'1h',  'period':'60d'}},
  '4h':  {{'interval':'1h',  'period':'90d'}},   // yfinance n'a pas de 4h natif
  '1d':  {{'interval':'1d',  'period':'6mo'}},
  '1wk': {{'interval':'1wk', 'period':'5y'}},
  '1mo': {{'interval':'1mo', 'period':'max'}},
}};

// On passe par l'API yfinance via un fetch Streamlit (si l'app expose un endpoint)
// Sinon on fait un rechargement en réutilisant les données injectées et en les filtrant
function setTF(btn, tf) {{
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const raw = TF_DATA[tf];
  if(!raw || !raw.length) {{ console.warn('[MP] Pas de données pour TF:', tf); return; }}
  D = makeD(raw);
  VS = Math.max(0, D.t.length-120);
  VE = D.t.length;
  // Mettre à jour header
  const lc=D.c[D.c.length-1], lo=D.o[0];
  const pct=lo?((lc-lo)/lo*100):0, bull=pct>=0;
  const clr=bull?'#26a69a':'#ef5350';
  const pe=$('prc'); if(pe){{ pe.textContent=fmt(lc); pe.style.color=clr; }}
  const ce=$('pchg'); if(ce){{ ce.textContent=(bull?'▲ +':'▼ ')+Math.abs(pct).toFixed(2)+'%'; ce.className='chg '+(bull?'up':'dn'); }}
  const n=D.c.length;
  if(n){{ st('ho',fmt(D.o[n-1])); st('hh',fmt(D.h[n-1])); st('hl',fmt(D.l[n-1])); st('hc',fmt(D.c[n-1])); }}
  render();
  console.log('[MP Chart] TF',tf,'→',D.t.length,'bougies');
}}

// ════════════════════════════════════════════════════════
//  INDICATEURS & MODE
// ════════════════════════════════════════════════════════
function toggleMA()  {{ showMA=!showMA;  $('btnMA').classList.toggle('on',showMA);  render(); }}
function toggleVol() {{ showVol=!showVol; $('btnVol').classList.toggle('on',showVol); setup(); render(); }}
function toggleBB()  {{ showBB=!showBB;  $('btnBB').classList.toggle('on',showBB);  render(); }}

function toggleDD() {{
  $('modeDD').classList.toggle('open');
  $('modeCaret').classList.toggle('open');
}}
function pickMode(key, lbl, icon) {{
  CHART_MODE=key;
  $('modeLbl').textContent=lbl; $('modeIcon').textContent=icon;
  document.querySelectorAll('.mode-opt').forEach(el=>{{
    el.classList.remove('active');
    el.querySelector('.mo-check').style.opacity='0';
  }});
  const idx=['normal','pro','quant'].indexOf(key);
  const opts=document.querySelectorAll('.mode-opt');
  if(idx>=0) {{ opts[idx].classList.add('active'); opts[idx].querySelector('.mo-check').style.opacity='1'; }}
  $('modeDD').classList.remove('open'); $('modeCaret').classList.remove('open');
  console.log('[MP Chart] Mode →', key); render();
}}
document.addEventListener('click', e => {{
  const w=document.querySelector('.mode-wrap');
  if(w&&!w.contains(e.target)) {{ $('modeDD').classList.remove('open'); $('modeCaret').classList.remove('open'); }}
}});

// ════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════
function init() {{
  setup(); render();
  setInterval(()=>{{if(HX<0)render();}},200);
}}
window.addEventListener('load', init);
window.addEventListener('resize', ()=>{{setup();render();}});
</script></body></html>"""


def _show_commodity_info(item, data):
    """Affiche les infos fondamentales d'une matière première"""
    infos = {
        "GOLD":   {"desc": "Valeur refuge par excellence. Corrélé négativement au dollar et aux taux réels.",
                   "drivers": ["Dollar US (DXY)", "Taux réels US", "Inflation", "Géopolitique", "Banques centrales"],
                   "saisonnalite": "Fort en Jan-Fév, Sep-Nov"},
        "SILVER": {"desc": "Mi-métal précieux mi-industriel. Plus volatil que l'or. Ratio Or/Argent clé.",
                   "drivers": ["Ratio Or/Argent", "Demande solaire", "Dollar", "Inflation"],
                   "saisonnalite": "Suit l'or avec amplification"},
        "WTI":    {"desc": "Référence pétrole américain. Stockages Cushing Oklahoma déterminants.",
                   "drivers": ["OPEP+", "Stockages US (EIA)", "Dollar", "Croissance mondiale", "Géopolitique ME"],
                   "saisonnalite": "Pic été (drive season), Pic hiver (chauffage)"},
        "BRENT":  {"desc": "Référence pétrole mondial. Produit en Mer du Nord. Spread Brent-WTI important.",
                   "drivers": ["OPEP+", "Géopolitique", "Dollar", "Demande Asie"],
                   "saisonnalite": "Similaire WTI"},
        "COPPER": {"desc": "Baromètre de l'économie mondiale. Utilisé dans électrique, construction, EV.",
                   "drivers": ["Croissance Chine", "Transition énergétique", "Inventaires LME", "Dollar"],
                   "saisonnalite": "Fort T1 (reprise construction)"},
        "WHEAT":  {"desc": "Céréale stratégique. Très sensible aux conditions météo et géopolitique.",
                   "drivers": ["Météo (sécheresse, gel)", "Géopolitique Ukraine/Russie", "Dollar", "Énergie"],
                   "saisonnalite": "Forte volatilité Mai-Juil (récoltes NH)"},
    }
    info = infos.get(item["symbol"], {
        "desc": "Matière première suivie sur les marchés à terme internationaux.",
        "drivers": ["Offre/Demande", "Dollar US", "Conditions météo", "Géopolitique"],
        "saisonnalite": "Variable selon les cycles de production"
    })

    st.markdown(f"""
    <div style="background:#060606;border:1px solid #1a1a1a;border-left:3px solid #ff6600;
                padding:12px 14px;margin-top:8px;">
        <div style="color:#ff6600;font-family:'DM Sans', Arial, sans-serif;font-size:10px;
                    letter-spacing:0.8px;text-transform:uppercase;margin-bottom:8px;">
            📖 ANALYSE FONDAMENTALE — {item['name']}
        </div>
        <p style="color:#888;font-size:11px;font-family:'DM Sans', Arial, sans-serif;
                  line-height:1.7;margin-bottom:10px;">{info['desc']}</p>
        <div style="color:#ffcc00;font-size:9px;font-family:'DM Sans', Arial, sans-serif;
                    letter-spacing:0.4px;margin-bottom:6px;">DRIVERS PRINCIPAUX</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">
            {''.join(f"<span style='background:#1a0800;border:1px solid #2a1400;color:#ff6600;font-size:9px;font-family:DM Sans, Arial, sans-serif;padding:3px 8px;letter-spacing:0.4px;'>{d}</span>" for d in info['drivers'])}
        </div>
        <div style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;
                    letter-spacing:0.4px;">📅 SAISONNALITÉ : <span style="color:#555;">{info['saisonnalite']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
#  MODULE GRAPHIQUES — MULTI-CHARTS
# ============================================================

def _show_charts():
    st.markdown('<div class="section-header">📈 GRAPHIQUES MATIÈRES PREMIÈRES</div>',
                unsafe_allow_html=True)

    # Sélecteur
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    all_flat = [(item["name"], item["ticker"], item["emoji"])
                for items in COMMODITIES.values() for item in items]
    names = [f"{e} {n}" for n, t, e in all_flat]
    tickers_map = {f"{e} {n}": t for n, t, e in all_flat}

    with col_sel1:
        sel1 = st.selectbox("GRAPHIQUE 1", names, index=0, key="mp_chart1")
    with col_sel2:
        sel2 = st.selectbox("GRAPHIQUE 2", names, index=4, key="mp_chart2")
    with col_sel3:
        period = st.selectbox("PÉRIODE", ["1W","1M","3M","6M","1Y","2Y","5Y"],
                              index=2, key="mp_period")

    period_map = {"1W":"5d","1M":"1mo","3M":"3mo","6M":"6mo","1Y":"1y","2Y":"2y","5Y":"5y"}

    col1, col2 = st.columns(2)
    for col, sel in [(col1, sel1), (col2, sel2)]:
        with col:
            ticker = tickers_map[sel]
            components.html(
                render_commodity_chart(ticker, pair_label=sel, height=380),
                height=390, scrolling=False
            )

    # ── Graphique corrélation or/pétrole ──
    st.markdown('<div class="section-header">🔗 CORRÉLATIONS MATIÈRES PREMIÈRES</div>',
                unsafe_allow_html=True)

    corr_pairs = [
        ("GC=F", "SI=F",  "Or vs Argent"),
        ("CL=F", "BZ=F",  "WTI vs Brent"),
        ("GC=F", "CL=F",  "Or vs Pétrole"),
        ("HG=F", "CL=F",  "Cuivre vs Pétrole"),
    ]

    with st.spinner("Calcul des corrélations..."):
        corr_cols = st.columns(4)
        for col, (t1, t2, label) in zip(corr_cols, corr_pairs):
            try:
                df1 = get_commodity_history(t1, "1y")
                df2 = get_commodity_history(t2, "1y")
                if df1 is not None and df2 is not None:
                    c1 = df1["Close"].pct_change().dropna()
                    c2 = df2["Close"].pct_change().dropna()
                    merged = pd.concat([c1, c2], axis=1).dropna()
                    if len(merged) > 10:
                        corr = merged.iloc[:, 0].corr(merged.iloc[:, 1])
                        color = "#00ff41" if corr > 0.5 else "#ff2222" if corr < -0.3 else "#ffcc00"
                        with col:
                            st.markdown(f"""
                            <div style="background:#080808;border:1px solid #1a1a1a;
                                        border-top:2px solid {color};padding:12px;text-align:center;">
                                <div style="color:#444;font-size:9px;font-family:'DM Sans', Arial, sans-serif;
                                            letter-spacing:0.4px;margin-bottom:6px;">{label}</div>
                                <div style="color:{color};font-size:24px;font-family:'DM Sans', Arial, sans-serif;
                                            font-weight:700;">{corr:+.2f}</div>
                                <div style="color:#333;font-size:8px;font-family:'DM Sans', Arial, sans-serif;
                                            margin-top:4px;">corrélation 1 an</div>
                            </div>""", unsafe_allow_html=True)
            except:
                with col:
                    st.markdown(f"""<div style="background:#080808;border:1px solid #1a1a1a;
                                    padding:12px;text-align:center;">
                        <div style="color:#333;font-size:9px;font-family:'DM Sans', Arial, sans-serif;">{label}</div>
                        <div style="color:#333;font-size:20px;">—</div></div>""",
                        unsafe_allow_html=True)


# ============================================================
#  MODULE NEWS
# ============================================================

def _show_news():
    st.markdown('<div class="section-header">📰 ANALYSES & ACTUALITÉS</div>',
                unsafe_allow_html=True)

    col_news, col_analysis = st.columns([1.5, 1])

    with col_news:
        st.markdown('<div class="section-header">📡 FLUX ACTUALITÉS</div>',
                    unsafe_allow_html=True)
        with st.spinner("Chargement des news..."):
            news = get_commodities_news()

        if not news:
            st.info("Aucune actualité disponible pour le moment.")
        else:
            for n in news:
                with st.expander(f"{n['time']} | {n['title'][:65]}..."):
                    st.markdown(f"**{n['title']}**")
                    st.caption(f"Source : {n['source']} • {n['time']}")
                    st.link_button("LIRE L'ARTICLE ↗", n["link"])

    with col_analysis:
        st.markdown('<div class="section-header">🧠 ANALYSE DE MARCHÉ</div>',
                    unsafe_allow_html=True)

        analyses = [
            {
                "titre": "📊 CYCLE OR — PHASE ACTUELLE",
                "contenu": """L'or évolue dans un contexte de taux réels encore élevés mais en baisse anticipée.
Les banques centrales (Chine, Inde, Turquie) continuent d'accumuler.
**Signal** : Accumulation graduelle recommandée sur replis vers 1900-1950 $/oz.""",
                "color": "#ffcc00"
            },
            {
                "titre": "🛢️ PÉTROLE — OPEP+ VS DEMANDE",
                "contenu": """L'OPEP+ maintient des coupes de production volontaires.
La demande chinoise déçoit mais US reste robuste.
**Signal** : Range 70-90$ WTI attendu. Volatilité géopolitique ME à surveiller.""",
                "color": "#ff6600"
            },
            {
                "titre": "🟤 CUIVRE — TRANSITION ÉNERGÉTIQUE",
                "contenu": """Le cuivre bénéficie de la demande EV et énergies renouvelables.
Offre contrainte par manque d'investissements miniers.
**Signal** : Tendance haussière structurelle long terme. Sensible à la Chine CT.""",
                "color": "#00ff41"
            },
            {
                "titre": "🌾 AGRICOLE — MÉTÉO & GÉOPOLITIQUE",
                "contenu": """Le conflit Ukraine-Russie maintient une prime géopolitique sur le blé.
El Niño impacte les productions d'Asie-Pacifique.
**Signal** : Surveiller les récoltes NH (Mai-Juil) et la météo brésilienne.""",
                "color": "#00ccff"
            },
        ]

        for a in analyses:
            st.markdown(f"""
            <div style="background:#060606;border:1px solid #1a1a1a;
                        border-left:3px solid {a['color']};padding:12px 14px;margin-bottom:8px;">
                <div style="color:{a['color']};font-family:'DM Sans', Arial, sans-serif;
                            font-size:10px;letter-spacing:0.4px;margin-bottom:6px;">{a['titre']}</div>
                <p style="color:#777;font-size:10px;font-family:'DM Sans', Arial, sans-serif;
                          line-height:1.7;margin:0;">{a['contenu']}</p>
            </div>
            """, unsafe_allow_html=True)

        # ── Calendrier des rapports clés ──
        st.markdown('<div class="section-header">📅 RAPPORTS CLÉS À SURVEILLER</div>',
                    unsafe_allow_html=True)
        rapports = [
            ("EIA Petroleum Status",     "Mercredi 16h30 CET", "#ff6600"),
            ("CFTC Commitment of Traders","Vendredi 21h30 CET", "#ffcc00"),
            ("API Crude Oil Stock",       "Mardi 22h30 CET",    "#ff6600"),
            ("USDA WASDE Report",         "Mensuel - 2e semaine","#00ff41"),
            ("LME Inventories",           "Quotidien 7h CET",   "#00ccff"),
            ("OPEP Monthly Report",       "Mensuel - mi-mois",  "#ff6600"),
        ]
        for rapport, timing, color in rapports:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:6px 10px;border-bottom:1px solid #0d0d0d;">
                <span style="color:#aaa;font-family:'DM Sans', Arial, sans-serif;
                             font-size:10px;">{rapport}</span>
                <span style="color:{color};font-family:'DM Sans', Arial, sans-serif;
                             font-size:9px;letter-spacing:0.4px;">{timing}</span>
            </div>""", unsafe_allow_html=True)
