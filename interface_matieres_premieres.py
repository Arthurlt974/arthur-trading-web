"""
interface_matieres_premieres.py
Module MATIÈRES PREMIÈRES — AM Trading Terminal
Métaux précieux, énergie, agricole, indices matières premières
"""

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
                <span style="font-size:9px;color:#444;font-family:'Share Tech Mono',monospace;
                             letter-spacing:2px;text-transform:uppercase;">{item['emoji']} {item['name']}</span>
                <div style="font-size:20px;font-weight:700;color:#e8e8e8;
                            font-family:'Share Tech Mono',monospace;letter-spacing:-0.5px;margin-top:2px;">
                    {price_str}
                </div>
                <span style="font-size:9px;color:#333;font-family:'Share Tech Mono',monospace;">{item['unit']}</span>
            </div>
            <div style="text-align:right;">
                <div style="background:{bg};border:1px solid {border};
                            color:{color};font-family:'Share Tech Mono',monospace;
                            font-size:12px;font-weight:700;padding:4px 8px;letter-spacing:1px;">
                    {arrow} {sign}{change:.2f}%
                </div>
                <div style="font-size:9px;color:#333;margin-top:4px;font-family:'Share Tech Mono',monospace;">
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
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@700&display=swap" rel="stylesheet">
    <style>
        .section-header {
            color: #ff6600;
            font-family: 'Share Tech Mono', monospace;
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
            font-family: 'Share Tech Mono', monospace;
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
            font-family: 'Share Tech Mono', monospace;
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
                <div style="color:#444;font-size:9px;font-family:'Share Tech Mono',monospace;
                            letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">
                    {item['emoji']} {item['name']}
                </div>
                <div style="color:#e8e8e8;font-size:22px;font-family:'Share Tech Mono',monospace;
                            font-weight:700;letter-spacing:-1px;">
                    {d['price']:,.2f}
                </div>
                <div style="color:{color};font-size:12px;font-family:'Share Tech Mono',monospace;
                            margin-top:4px;">
                    {'▲' if up else '▼'} {sign}{d['change']:.2f}%
                </div>
                <div style="color:#222;font-size:8px;font-family:'Share Tech Mono',monospace;
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
                <span style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;
                             letter-spacing:1px;">ACTIF</span>
                <span style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;">PRIX</span>
                <span style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;">VARIATION</span>
                <span style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;">UNITÉ</span>
            </div>"""
            st.markdown(header_html, unsafe_allow_html=True)

            for item in items:
                d = prices[item["ticker"]]
                up = d["change"] >= 0
                color = "#00ff41" if up else "#ff2222"
                sign = "+" if up else ""
                arrow = "▲" if up else "▼"
                price_str = f"{d['price']:,.2f}" if d["ok"] else "—"

                st.markdown(f"""
                <div class="comm-row">
                    <span style="color:#e8e8e8;font-size:12px;font-family:'Share Tech Mono',monospace;
                                 width:130px;">{item['emoji']} {item['name']}</span>
                    <span style="color:#ffffff;font-size:13px;font-family:'Share Tech Mono',monospace;
                                 font-weight:700;width:100px;text-align:right;">{price_str}</span>
                    <span style="color:{color};font-size:12px;font-family:'Share Tech Mono',monospace;
                                 width:90px;text-align:right;">{arrow} {sign}{d['change']:.2f}%</span>
                    <span style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;
                                 width:70px;text-align:right;">{item['unit']}</span>
                </div>
                """, unsafe_allow_html=True)

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
                <span style="color:#aaa;font-family:'Share Tech Mono',monospace;font-size:11px;">
                    {item['emoji']} {item['name']}</span>
                <span style="color:#00ff41;font-family:'Share Tech Mono',monospace;
                             font-size:13px;font-weight:700;">+{d['change']:.2f}%</span>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="cat-header">▼ PLUS FORTES BAISSES</div>', unsafe_allow_html=True)
        baisses = [m for m in movers if m["data"]["change"] < 0][:5]
        for m in baisses:
            d = m["data"]
            item = m["item"]
            st.markdown(f"""
            <div class="comm-row">
                <span style="color:#aaa;font-family:'Share Tech Mono',monospace;font-size:11px;">
                    {item['emoji']} {item['name']}</span>
                <span style="color:#ff2222;font-family:'Share Tech Mono',monospace;
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
                    <span style="color:#ffcc00;font-family:'Share Tech Mono',monospace;
                                 font-size:10px;letter-spacing:1px;">{name}</span>
                    <span style="color:#e8e8e8;font-family:'Share Tech Mono',monospace;
                                 font-size:16px;font-weight:700;">{val:.1f}</span>
                </div>
                <div style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;
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

        # Graphique TradingView
        tv_sym = _get_tv_symbol(active_item["ticker"])
        tv_html = f"""
        <div style="background:#000;border:1px solid #1a1a1a;border-top:2px solid #ff6600;">
            <div class="tradingview-widget-container" style="height:420px;">
                <div class="tradingview-widget-container__widget"></div>
                <script type="text/javascript"
                    src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                {{
                    "symbol": "{tv_sym}",
                    "interval": "D",
                    "timezone": "Europe/Paris",
                    "theme": "dark",
                    "style": "1",
                    "locale": "fr",
                    "backgroundColor": "#000000",
                    "gridColor": "#0d0d0d",
                    "width": "100%",
                    "height": "420",
                    "hide_top_toolbar": false,
                    "hide_legend": false,
                    "save_image": false,
                    "calendar": false,
                    "support_host": "https://www.tradingview.com"
                }}
                </script>
            </div>
        </div>"""
        components.html(tv_html, height=430)

        # Infos fondamentales
        d = prices[active_item["ticker"]]
        _show_commodity_info(active_item, d)


def _get_tv_symbol(ticker):
    """Convertit ticker yfinance → symbole TradingView"""
    mapping = {
        "GC=F":  "COMEX:GC1!",
        "SI=F":  "COMEX:SI1!",
        "PL=F":  "NYMEX:PL1!",
        "PA=F":  "NYMEX:PA1!",
        "CL=F":  "NYMEX:CL1!",
        "BZ=F":  "NYMEX:BB1!",
        "NG=F":  "NYMEX:NG1!",
        "HG=F":  "COMEX:HG1!",
        "ZW=F":  "CBOT:ZW1!",
        "ZC=F":  "CBOT:ZC1!",
        "ZS=F":  "CBOT:ZS1!",
        "SB=F":  "ICEUS:SB1!",
        "KC=F":  "ICEUS:KC1!",
        "CC=F":  "ICEUS:CC1!",
        "ALI=F": "COMEX:ALI1!",
        "MTF=F": "ICEEUR:MTF1!",
    }
    return mapping.get(ticker, "COMEX:GC1!")


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
        <div style="color:#ff6600;font-family:'Share Tech Mono',monospace;font-size:10px;
                    letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">
            📖 ANALYSE FONDAMENTALE — {item['name']}
        </div>
        <p style="color:#888;font-size:11px;font-family:'Share Tech Mono',monospace;
                  line-height:1.7;margin-bottom:10px;">{info['desc']}</p>
        <div style="color:#ffcc00;font-size:9px;font-family:'Share Tech Mono',monospace;
                    letter-spacing:1px;margin-bottom:6px;">DRIVERS PRINCIPAUX</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">
            {''.join(f"<span style='background:#1a0800;border:1px solid #2a1400;color:#ff6600;font-size:9px;font-family:Share Tech Mono,monospace;padding:3px 8px;letter-spacing:1px;'>{d}</span>" for d in info['drivers'])}
        </div>
        <div style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;
                    letter-spacing:1px;">📅 SAISONNALITÉ : <span style="color:#555;">{info['saisonnalite']}</span>
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
            tv_sym = _get_tv_symbol(ticker)
            tv_html = f"""
            <div style="background:#000;border:1px solid #1a1a1a;border-top:2px solid #ff6600;">
                <div class="tradingview-widget-container">
                    <div class="tradingview-widget-container__widget"></div>
                    <script type="text/javascript"
                        src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                    {{
                        "symbol": "{tv_sym}",
                        "interval": "W",
                        "timezone": "Europe/Paris",
                        "theme": "dark",
                        "style": "1",
                        "locale": "fr",
                        "backgroundColor": "#000000",
                        "gridColor": "#0d0d0d",
                        "width": "100%",
                        "height": "380",
                        "hide_top_toolbar": false,
                        "save_image": false
                    }}
                    </script>
                </div>
            </div>"""
            components.html(tv_html, height=390)

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
                                <div style="color:#444;font-size:9px;font-family:'Share Tech Mono',monospace;
                                            letter-spacing:1px;margin-bottom:6px;">{label}</div>
                                <div style="color:{color};font-size:24px;font-family:'Share Tech Mono',monospace;
                                            font-weight:700;">{corr:+.2f}</div>
                                <div style="color:#333;font-size:8px;font-family:'Share Tech Mono',monospace;
                                            margin-top:4px;">corrélation 1 an</div>
                            </div>""", unsafe_allow_html=True)
            except:
                with col:
                    st.markdown(f"""<div style="background:#080808;border:1px solid #1a1a1a;
                                    padding:12px;text-align:center;">
                        <div style="color:#333;font-size:9px;font-family:'Share Tech Mono',monospace;">{label}</div>
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
                <div style="color:{a['color']};font-family:'Share Tech Mono',monospace;
                            font-size:10px;letter-spacing:1px;margin-bottom:6px;">{a['titre']}</div>
                <p style="color:#777;font-size:10px;font-family:'Share Tech Mono',monospace;
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
                <span style="color:#aaa;font-family:'Share Tech Mono',monospace;
                             font-size:10px;">{rapport}</span>
                <span style="color:{color};font-family:'Share Tech Mono',monospace;
                             font-size:9px;letter-spacing:1px;">{timing}</span>
            </div>""", unsafe_allow_html=True)
