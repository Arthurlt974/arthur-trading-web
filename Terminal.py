"""
AM.TERMINAL — Terminal Bloomberg Multi-Onglets
Permet d'ouvrir jusqu'à 6 onglets simultanés, chacun configuré sur un outil différent.
"""

import streamlit as st
import streamlit.components.v1 as components
import time
from utils import (
    show_onchain, show_liquidations, show_staking, show_order_book_ui,
    init_session_from_firebase,
)

# ══════════════════════════════════════════════════════════
#  CATALOGUE DES OUTILS DISPONIBLES
# ══════════════════════════════════════════════════════════

TOOLS_CATALOG = {
    # ── GRAPHIQUES ──
    "📈 Graphique Crypto":         {"cat": "GRAPHIQUES",   "id": "CHART_CRYPTO"},
    "📊 Graphique Actions":        {"cat": "GRAPHIQUES",   "id": "CHART_STOCK"},
    "📉 Multi-Charts":             {"cat": "GRAPHIQUES",   "id": "MULTI_CHARTS"},

    # ── CRYPTO ──
    "₿ Bitcoin Dominance":         {"cat": "CRYPTO",       "id": "BTC_DOMINANCE"},
    "🔥 Heatmap Liquidations":     {"cat": "CRYPTO",       "id": "HEATMAP_LIQ"},
    "📖 Order Book Live":          {"cat": "CRYPTO",       "id": "ORDER_BOOK"},
    "🐋 Whale Watcher":            {"cat": "CRYPTO",       "id": "WHALE"},
    "🔗 On-Chain Analytics":       {"cat": "CRYPTO",       "id": "ONCHAIN"},
    "⚡ Liquidations & Funding":   {"cat": "CRYPTO",       "id": "LIQ_FUNDING"},
    "💰 Staking & Yield":          {"cat": "CRYPTO",       "id": "STAKING"},

    # ── ANALYSE ──
    "🔬 Analyseur Pro":            {"cat": "ANALYSE",      "id": "ANALYSEUR_PRO"},
    "📐 Analyse Technique Pro":    {"cat": "ANALYSE",      "id": "TECH_PRO"},
    "🌀 Fibonacci Calculator":     {"cat": "ANALYSE",      "id": "FIBONACCI"},
    "🤖 Backtesting Engine":       {"cat": "ANALYSE",      "id": "BACKTEST"},
    "💎 Valorisation Fondamentale":{"cat": "ANALYSE",      "id": "VALORISATION"},
    "🧠 Expert System":            {"cat": "ANALYSE",      "id": "EXPERT"},
    "⚔️ Mode Duel":                {"cat": "ANALYSE",      "id": "DUEL"},

    # ── MARCHÉ ──
    "👁 Market Monitor":           {"cat": "MARCHÉ",       "id": "MARKET_MONITOR"},
    "🔭 Screener CAC 40":          {"cat": "MARCHÉ",       "id": "SCREENER_CAC"},
    "📅 Dividend Calendar":        {"cat": "MARCHÉ",       "id": "DIVIDEND_CAL"},
    "😨 Fear & Greed Index":       {"cat": "MARCHÉ",       "id": "FEAR_GREED"},
    "🔗 Corrélation Dash":         {"cat": "MARCHÉ",       "id": "CORRELATION"},
    "🗺 Heatmap Marché":           {"cat": "MARCHÉ",       "id": "HEATMAP_MKTF"},

    # ── MACRO ──
    "📰 Daily Brief":              {"cat": "MACRO",        "id": "DAILY_BRIEF"},
    "📅 Calendrier Éco":           {"cat": "MACRO",        "id": "CALENDRIER_ECO"},
    "📈 Intérêts Composés":        {"cat": "MACRO",        "id": "INTERETS"},
    "🔔 Alerts Manager":           {"cat": "MACRO",        "id": "ALERTS"},
}

TOOLS_BY_CAT = {}
for name, meta in TOOLS_CATALOG.items():
    TOOLS_BY_CAT.setdefault(meta["cat"], []).append(name)

MAX_TABS = 6

# ══════════════════════════════════════════════════════════
#  CSS TERMINAL
# ══════════════════════════════════════════════════════════

TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ── Topbar ── */
.term-topbar {
    display: flex; align-items: center;
    background: #000; border-bottom: 1px solid #1a1a1a;
    height: 34px; padding: 0 14px;
}
.term-logo {
    font-family: 'IBM Plex Mono', monospace; font-size: 13px;
    font-weight: 700; color: #ff6600; letter-spacing: 1px;
    margin-right: 14px;
}
.term-logo span { color: #4d9fff; }

/* ── Streamlit tabs → style Bloomberg ── */
[data-testid="stTabs"] {
    background: #000;
}
[data-testid="stTabsTabList"] {
    background: #000 !important;
    border-bottom: 2px solid #111 !important;
    gap: 0 !important;
    padding: 0 !important;
}
[data-testid="stTabsTab"] {
    background: #050505 !important;
    border: none !important;
    border-right: 1px solid #111 !important;
    border-top: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 0 16px !important;
    height: 34px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    color: #4d9fff !important;
    letter-spacing: 0.3px !important;
    transition: all .12s !important;
    white-space: nowrap !important;
}
[data-testid="stTabsTab"]:hover {
    background: #0d0d0d !important;
    color: #fff !important;
    border-top-color: #333 !important;
}
[data-testid="stTabsTab"][aria-selected="true"] {
    background: #000 !important;
    color: #ff6600 !important;
    border-top: 2px solid #ff6600 !important;
    font-weight: 600 !important;
}
/* Supprimer le soulignement rouge natif Streamlit */
[data-testid="stTabsTab"][aria-selected="true"]::after,
[data-testid="stTabsTab"]::after {
    display: none !important;
}
[data-testid="stTabsTabPanel"] {
    background: #000 !important;
    padding: 12px 0 0 !important;
}

/* ── Sidebar terminal ── */
[data-testid="stSidebar"] {
    background: #050505 !important;
    border-right: 1px solid #111 !important;
}
[data-testid="stSidebar"] button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    color: #4d9fff !important;
    border-radius: 3px !important;
}
[data-testid="stSidebar"] button:hover {
    border-color: #ff6600 !important;
    color: #ff6600 !important;
}

/* ── Padding général ── */
.block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
footer, header { display: none !important; }
</style>
"""

# ══════════════════════════════════════════════════════════
#  RENDU D'UN OUTIL
# ══════════════════════════════════════════════════════════

def _render_tool(tool_id: str, tool_name: str, tab_idx: int = 0):
    """Rend le contenu d'un outil dans un onglet."""

    # ── Imports paresseux ──
    import yfinance as yf
    import pandas as pd
    import plotly.graph_objects as go
    import requests
    import numpy as np

    if tool_id == "CHART_CRYPTO":
        from chart_module import render_chart
        CRYPTOS = {
            "BTC/USDT": "BTCUSDT", "ETH/USDT": "ETHUSDT", "SOL/USDT": "SOLUSDT",
            "BNB/USDT": "BNBUSDT", "XRP/USDT": "XRPUSDT", "ADA/USDT": "ADAUSDT",
            "AVAX/USDT": "AVAXUSDT", "DOGE/USDT": "DOGEUSDT", "LINK/USDT": "LINKUSDT",
        }
        c1, c2 = st.columns([3, 1])
        with c1:
            pair  = st.selectbox("Paire", list(CRYPTOS.keys()), key=f"tc_pair_{tool_id}_{tab_idx}", label_visibility="collapsed")
        with c2:
            tf    = st.selectbox("TF", ["1h","4h","1d","1w"], index=1, key=f"tc_tf_{tool_id}_{tab_idx}", label_visibility="collapsed")
        sym = CRYPTOS[pair]
        html = render_chart(symbol=sym, interval=tf, limit=200, height=640,
                            pair_label=pair, exchange="Binance · Spot", show_ma=True
                            ) + f"<!-- {sym}:{int(time.time()*1000)} -->"
        components.html(html, height=650, scrolling=False)

    elif tool_id == "CHART_STOCK":
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            sym = st.text_input("Ticker", value="AAPL", key=f"tc_stock_{tool_id}_{tab_idx}", label_visibility="collapsed").upper()
        with c2:
            tf_map = {"1m":"1","5m":"5","15m":"15","1h":"60","4h":"240","1J":"D","1S":"W","1M":"M"}
            tf_label = st.selectbox("TF", list(tf_map.keys()), index=5, key=f"tc_stf_{tool_id}_{tab_idx}", label_visibility="collapsed")
            tf = tf_map[tf_label]
        with c3:
            style_map = {"Chandeliers":"1","Barres":"0","Ligne":"2","Heikin Ashi":"8","Zone":"3"}
            style_label = st.selectbox("Style", list(style_map.keys()), index=0, key=f"tc_sst_{tool_id}_{tab_idx}", label_visibility="collapsed")
            chart_style = style_map[style_label]
        tv_html = f"""
        <div style="height:640px;border:1px solid #1a1a1a;border-radius:4px;overflow:hidden;">
          <div class="tradingview-widget-container" style="height:100%;width:100%;">
            <div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div>
            <script type="text/javascript"
              src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {{
              "autosize": true,
              "symbol": "{sym}",
              "interval": "{tf}",
              "timezone": "Europe/Paris",
              "theme": "dark",
              "style": "{chart_style}",
              "locale": "fr",
              "backgroundColor": "rgba(0,0,0,1)",
              "gridColor": "rgba(26,26,26,1)",
              "hide_top_toolbar": false,
              "allow_symbol_change": true,
              "save_image": false,
              "studies": ["STD;RSI","STD;MACD","STD;Volume"],
              "height": "640",
              "width": "100%"
            }}
            </script>
          </div>
        </div>
        """
        components.html(tv_html, height=650, scrolling=False)

    elif tool_id == "BTC_DOMINANCE":
        st.markdown("### ₿ Bitcoin Dominance")
        col1, col2, col3 = st.columns(3)
        try:
            r = requests.get("https://api.coingecko.com/api/v3/global", timeout=8)
            dom = r.json()["data"]["market_cap_percentage"]["btc"]
            col1.metric("BTC Dominance", f"{dom:.1f}%")
        except:
            col1.metric("BTC Dominance", "N/A")
        col2.info("💡 BTC.D ↑ + BTC ↑ = Altcoins souffrent")
        col3.info("💡 BTC.D ↓ + BTC stagne = Altseason")
        # TradingView — BTC.D natif
        btcd_html = """
        <div style="height:580px;border:1px solid #1a1a1a;border-radius:4px;overflow:hidden;">
          <div class="tradingview-widget-container" style="height:100%;width:100%;">
            <div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div>
            <script type="text/javascript"
              src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {
              "autosize": true,
              "symbol": "CRYPTOCAP:BTC.D",
              "interval": "D",
              "timezone": "Europe/Paris",
              "theme": "dark",
              "style": "1",
              "locale": "fr",
              "backgroundColor": "rgba(0,0,0,1)",
              "hide_top_toolbar": false,
              "allow_symbol_change": false,
              "save_image": false,
              "height": "580",
              "width": "100%"
            }
            </script>
          </div>
        </div>
        """
        components.html(btcd_html, height=590, scrolling=False)

    elif tool_id == "HEATMAP_LIQ":
        st.markdown("### 🔥 Liquidation Heatmap")
        components.html("""
        <div style="background:#000;border:1px solid #ff6600;border-radius:6px;overflow:hidden;">
            <iframe src="https://www.coinglass.com/fr/pro/futures/LiquidationHeatMap"
                    width="100%" height="820" style="border:none;" scrolling="yes"></iframe>
        </div>""", height=840)

    elif tool_id == "ORDER_BOOK":
        show_order_book_ui(tab_idx)

    elif tool_id == "WHALE":
        show_onchain(tab_idx)

    elif tool_id == "ONCHAIN":
        show_onchain(tab_idx)

    elif tool_id == "LIQ_FUNDING":
        show_liquidations(tab_idx)

    elif tool_id == "STAKING":
        show_staking(tab_idx)

    elif tool_id == "MULTI_CHARTS":
        c1, c2 = st.columns([3, 1])
        with c1:
            mode_multi = st.selectbox("Mode", ["📈 Actions US", "💱 Forex Majeurs", "🏦 Indices Mondiaux", "🥇 Matières Premières"],
                                      key=f"mc_mode_{tab_idx}", label_visibility="collapsed")
        with c2:
            tf_map_m = {"1h":"60","4h":"240","1J":"D","1S":"W"}
            tf_label_m = st.selectbox("TF", list(tf_map_m.keys()), index=2,
                                      key=f"mc_tf_terminal_{tab_idx}", label_visibility="collapsed")
            tf_m = tf_map_m[tf_label_m]

        MULTI_PRESETS = {
            "📈 Actions US":          [("AAPL","Apple"),("NVDA","Nvidia"),("TSLA","Tesla"),("MSFT","Microsoft"),("AMZN","Amazon"),("META","Meta")],
            "💱 Forex Majeurs":       [("FX:EURUSD","EUR/USD"),("FX:GBPUSD","GBP/USD"),("FX:USDJPY","USD/JPY"),("FX:USDCHF","USD/CHF"),("FX:AUDUSD","AUD/USD"),("FX:USDCAD","USD/CAD")],
            "🏦 Indices Mondiaux":    [("SPY","S&P 500"),("QQQ","Nasdaq"),("TVC:DJI","Dow Jones"),("EURONEXT:CAC40","CAC 40"),("INDEX:DAX","DAX"),("TVC:NI225","Nikkei")],
            "🥇 Matières Premières":  [("COMEX:GC1!","Or"),("NYMEX:CL1!","WTI"),("COMEX:SI1!","Argent"),("NYMEX:NG1!","Gaz Nat."),("CBOT:ZW1!","Blé"),("COMEX:HG1!","Cuivre")],
        }
        pairs_m = MULTI_PRESETS[mode_multi]
        cols_mc = st.columns(2)
        for i, (sym_m, label_m) in enumerate(pairs_m):
            with cols_mc[i % 2]:
                mini_html = f"""
                <div style="height:320px;border:1px solid #1a1a1a;border-radius:4px;overflow:hidden;margin-bottom:8px;">
                  <div class="tradingview-widget-container" style="height:100%;width:100%;">
                    <div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div>
                    <script type="text/javascript"
                      src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
                    {{
                      "autosize": true, "symbol": "{sym_m}", "interval": "{tf_m}",
                      "timezone": "Europe/Paris", "theme": "dark", "style": "1",
                      "locale": "fr", "backgroundColor": "rgba(0,0,0,1)",
                      "hide_top_toolbar": true, "hide_legend": false,
                      "allow_symbol_change": false, "save_image": false,
                      "height": "320", "width": "100%"
                    }}
                    </script>
                  </div>
                </div>
                """
                components.html(mini_html, height=330, scrolling=False)

    elif tool_id == "FEAR_GREED":
        st.markdown("### 😨 Fear & Greed Index")
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=30", timeout=8)
            data = r.json()["data"]
            current = data[0]
            val   = int(current["value"])
            label = current["value_classification"]
            color = "#00ff41" if val > 60 else "#ff6600" if val > 40 else "#ff2222"
            st.markdown(f"""
            <div style='text-align:center;padding:24px;'>
                <div style='font-size:72px;font-family:IBM Plex Mono,monospace;
                            font-weight:700;color:{color};'>{val}</div>
                <div style='color:{color};font-size:18px;letter-spacing:2px;
                            font-family:IBM Plex Mono,monospace;margin-top:8px;'>{label.upper()}</div>
            </div>
            """, unsafe_allow_html=True)
            hist = [(int(d["value"]), d["value_classification"]) for d in data[:14]]
            vals_h = [h[0] for h in hist][::-1]
            fig = go.Figure(go.Scatter(y=vals_h, mode="lines+markers",
                line=dict(color="#ff6600", width=2),
                marker=dict(size=6, color=["#00ff41" if v>60 else "#ff6600" if v>40 else "#ff2222" for v in vals_h])))
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000", plot_bgcolor="#0a0a0a",
                              height=220, margin=dict(l=20,r=20,t=20,b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur Fear & Greed : {e}")

    elif tool_id == "CORRELATION":
        st.markdown("### 🔗 Corrélation inter-actifs")
        SYMS = {"BTC":"BTC-USD","ETH":"ETH-USD","SOL":"SOL-USD","AAPL":"AAPL","NVDA":"NVDA","SPY":"SPY","GLD":"GLD"}
        try:
            df_all = yf.download(list(SYMS.values()), period="6mo", progress=False)["Close"]
            df_all.columns = list(SYMS.keys())
            corr = df_all.corr()
            fig = go.Figure(go.Heatmap(
                z=corr.values, x=list(corr.columns), y=list(corr.index),
                colorscale=[[0,"#ff2222"],[0.5,"#111"],[1,"#00ff41"]],
                zmin=-1, zmax=1, text=corr.round(2).values,
                texttemplate="%{text}", textfont={"size":11}
            ))
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000",
                              height=420, margin=dict(l=20,r=20,t=30,b=20))
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur corrélation : {e}")

    elif tool_id == "HEATMAP_MKTF":
        st.markdown("### 🗺 Heatmap Marché")
        components.html("""
        <div class="tradingview-widget-container" style="height:600px;">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
          {"exchanges":[],"dataSource":"S&P500","grouping":"sector","blockSize":"market_cap_basic",
           "blockColor":"change","locale":"fr","symbolUrl":"","colorTheme":"dark",
           "hasTopBar":false,"isDataSetEnabled":false,"isZoomEnabled":true,
           "hasSymbolTooltip":true,"width":"100%","height":"100%"}
          </script>
        </div>""", height=620)

    elif tool_id == "MARKET_MONITOR":
        st.markdown("### 👁 Market Monitor")
        WATCH = {
            "BTC":  ("BTC-USD",  "Crypto"),
            "ETH":  ("ETH-USD",  "Crypto"),
            "SPY":  ("SPY",      "ETF"),
            "QQQ":  ("QQQ",      "ETF"),
            "AAPL": ("AAPL",     "Action"),
            "NVDA": ("NVDA",     "Action"),
            "GLD":  ("GLD",      "Or"),
            "DX-Y.NYB": ("DX-Y.NYB", "USD Index"),
        }
        try:
            tickers = list(WATCH.values())
            data = yf.download([t[0] for t in tickers], period="2d", progress=False)["Close"]
            cols_m = st.columns(4)
            for i, (name, (sym, cat)) in enumerate(WATCH.items()):
                try:
                    series = data[sym] if sym in data.columns else data.iloc[:, 0]
                    last  = float(series.iloc[-1])
                    prev  = float(series.iloc[-2])
                    pct   = (last - prev) / prev * 100
                    color = "#00ff41" if pct >= 0 else "#ff2222"
                    with cols_m[i % 4]:
                        st.markdown(f"""
                        <div style='background:#080808;border:1px solid #1a1a1a;border-radius:4px;
                                    padding:10px;margin-bottom:8px;'>
                            <div style='font-size:9px;color:#4d9fff;font-family:IBM Plex Mono,monospace;
                                        letter-spacing:1px;'>{cat.upper()}</div>
                            <div style='font-size:14px;font-weight:700;font-family:IBM Plex Mono,monospace;
                                        margin:4px 0;'>{name}</div>
                            <div style='font-size:18px;font-weight:700;font-family:IBM Plex Mono,monospace;'>
                                ${last:,.2f}</div>
                            <div style='font-size:12px;color:{color};font-family:IBM Plex Mono,monospace;'>
                                {"▲" if pct>=0 else "▼"} {abs(pct):.2f}%</div>
                        </div>""", unsafe_allow_html=True)
                except:
                    pass
        except Exception as e:
            st.error(f"Erreur Market Monitor : {e}")

    elif tool_id == "INTERETS":
        st.markdown("### 📈 Calculateur Intérêts Composés")
        c1, c2, c3, c4 = st.columns(4)
        capital    = c1.number_input("Capital initial ($)", value=10000, min_value=0, key="ic_cap")
        mensuel    = c2.number_input("Apport mensuel ($)", value=500,   min_value=0, key="ic_mens")
        taux_an    = c3.number_input("Taux annuel (%)",    value=10.0,  min_value=0.0, key="ic_taux", step=0.5)
        annees     = c4.number_input("Durée (années)",     value=20,    min_value=1, max_value=50, key="ic_duree")
        taux_m = taux_an / 100 / 12
        vals, invests = [], []
        total = float(capital)
        invested = float(capital)
        for m in range(int(annees) * 12):
            total    = total * (1 + taux_m) + float(mensuel)
            invested = invested + float(mensuel)
            if m % 12 == 11:
                vals.append(round(total, 2))
                invests.append(round(invested, 2))
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=invests, name="Capital investi", line=dict(color="#4d9fff", width=1.5, dash="dot")))
        fig.add_trace(go.Scatter(y=vals, name="Valeur totale",
                                 line=dict(color="#ff6600", width=2), fill="tonexty",
                                 fillcolor="rgba(255,102,0,0.08)"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#000", plot_bgcolor="#0a0a0a",
                          height=380, margin=dict(l=20,r=20,t=20,b=40),
                          xaxis_title="Années", yaxis_title="Valeur ($)")
        st.plotly_chart(fig, use_container_width=True)
        profit = vals[-1] - invests[-1] if vals else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Valeur finale", f"${vals[-1]:,.0f}" if vals else "—")
        m2.metric("Total investi", f"${invests[-1]:,.0f}" if invests else "—")
        m3.metric("Gains", f"${profit:,.0f}", delta=f"+{profit/max(invests[-1],1)*100:.1f}%" if invests else None)

    elif tool_id == "DAILY_BRIEF":
        st.markdown("### 📰 Daily Brief — Actualités")
        import feedparser
        feeds = {
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "Investing.com": "https://fr.investing.com/rss/news.rss",
        }
        tabs_feed = st.tabs(list(feeds.keys()))
        for i, (src, url) in enumerate(feeds.items()):
            with tabs_feed[i]:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:8]:
                        st.markdown(f"""
                        <div style='border-left:2px solid #ff6600;padding:8px 12px;
                                    margin:6px 0;background:#080808;border-radius:0 4px 4px 0;'>
                            <a href='{entry.get("link","#")}' target='_blank'
                               style='color:#e8e8e8;text-decoration:none;font-family:IBM Plex Sans,sans-serif;
                                      font-size:13px;font-weight:600;'>{entry.get("title","")}</a>
                            <div style='color:#4d9fff;font-size:9px;font-family:IBM Plex Mono,monospace;
                                        margin-top:4px;'>{entry.get("published","")}</div>
                        </div>""", unsafe_allow_html=True)
                except:
                    st.error(f"Erreur flux {src}")

    elif tool_id == "CALENDRIER_ECO":
        st.markdown("### 📅 Calendrier Économique")
        components.html("""
        <div class="tradingview-widget-container" style="height:700px;">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript"
            src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {"colorTheme":"dark","isTransparent":false,"width":"100%","height":"100%",
           "locale":"fr","importanceFilter":"0,1","countryFilter":"us,eu,gb,jp,cn,fr,de"}
          </script>
        </div>""", height=720)

    elif tool_id == "ALERTS":
        st.markdown("### 🔔 Alerts Manager")
        st.info("Module Alerts — connectez-vous pour gérer vos alertes de prix.")

    elif tool_id in ("ANALYSEUR_PRO", "TECH_PRO", "FIBONACCI", "BACKTEST",
                     "VALORISATION", "EXPERT", "DUEL", "SCREENER_CAC",
                     "DIVIDEND_CAL"):
        # Mapping vers les outils dans app.py via session_state
        MAP = {
            "ANALYSEUR_PRO": "ANALYSEUR PRO",
            "TECH_PRO":      "ANALYSE TECHNIQUE PRO",
            "FIBONACCI":     "FIBONACCI CALCULATOR",
            "BACKTEST":      "BACKTESTING ENGINE",
            "VALORISATION":  "VALORISATION FONDAMENTALE",
            "EXPERT":        "EXPERT SYSTEM",
            "DUEL":          "MODE DUEL",
            "SCREENER_CAC":  "SCREENER CAC 40",
            "DIVIDEND_CAL":  "DIVIDEND CALENDAR",
        }
        st.info(f"💡 Cet outil est disponible dans **ACTIONS & BOURSE → {MAP[tool_id]}**")
        st.markdown(f"*Pour l'utiliser dans le Terminal, accédez-y via le menu principal puis revenez dans le Terminal.*")

    else:
        st.markdown(f"<div style='padding:40px;text-align:center;color:#4d9fff;"
                    f"font-family:IBM Plex Mono,monospace;'>Outil `{tool_name}` — À venir</div>",
                    unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  INTERFACE PRINCIPALE DU TERMINAL
# ══════════════════════════════════════════════════════════

def show_terminal():
    """Point d'entrée principal du Terminal Bloomberg."""

    # Charger watchlist/alertes/prefs depuis Firebase si user connecté
    init_session_from_firebase()

    # ── Inject CSS ──
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)

    # ── Session state ──
    if "term_tabs" not in st.session_state:
        st.session_state.term_tabs = [
            {"id": "CHART_CRYPTO", "name": "📈 Graphique Crypto", "key": "tab_0"},
        ]
    if "term_active" not in st.session_state:
        st.session_state.term_active = 0

    tabs      = st.session_state.term_tabs
    active    = st.session_state.term_active

    # ══════════════════════════════════════════
    # SIDEBAR — Ajouter un outil
    # ══════════════════════════════════════════
    st.sidebar.markdown(
        "<div style='font-family:IBM Plex Mono,monospace;font-size:11px;"
        "color:#ff6600;letter-spacing:2px;padding:8px 0 4px;'>» AJOUTER UN ONGLET</div>",
        unsafe_allow_html=True
    )

    # Sélecteur par catégorie
    cat_sel = st.sidebar.selectbox(
        "Catégorie", list(TOOLS_BY_CAT.keys()),
        key="term_cat_sel", label_visibility="collapsed"
    )
    tool_sel = st.sidebar.selectbox(
        "Outil", TOOLS_BY_CAT[cat_sel],
        key="term_tool_sel", label_visibility="collapsed"
    )

    col_add1, col_add2 = st.sidebar.columns(2)
    if col_add1.button("＋ Ouvrir", use_container_width=True, key="term_btn_add"):
        if len(tabs) < MAX_TABS:
            tool_meta = TOOLS_CATALOG[tool_sel]
            new_tab = {
                "id":   tool_meta["id"],
                "name": tool_sel,
                "key":  f"tab_{int(time.time()*1000)}",
            }
            tabs.append(new_tab)
            st.session_state.term_active = len(tabs) - 1
            st.rerun()
        else:
            st.sidebar.warning(f"Maximum {MAX_TABS} onglets.")

    if col_add2.button("Remplacer", use_container_width=True, key="term_btn_replace"):
        tool_meta = TOOLS_CATALOG[tool_sel]
        tabs[active] = {
            "id":   tool_meta["id"],
            "name": tool_sel,
            "key":  f"tab_{int(time.time()*1000)}",
        }
        st.session_state.term_tabs = tabs
        st.rerun()

    st.sidebar.markdown("---")

    # Onglets ouverts
    st.sidebar.markdown(
        "<div style='font-family:IBM Plex Mono,monospace;font-size:11px;"
        "color:#4d9fff;letter-spacing:1px;padding:4px 0;'>» ONGLETS OUVERTS</div>",
        unsafe_allow_html=True
    )
    for i, tab in enumerate(tabs):
        cols_t = st.sidebar.columns([4, 1])
        label = f"{'▶ ' if i==active else ''}{tab['name']}"
        if cols_t[0].button(label[:28], key=f"term_goto_{tab['key']}", use_container_width=True):
            st.session_state.term_active = i
            st.rerun()
        if cols_t[1].button("✕", key=f"term_close_{tab['key']}"):
            tabs.pop(i)
            st.session_state.term_active = max(0, active - 1)
            if not tabs:
                tabs.append({"id": "CHART_CRYPTO", "name": "📈 Graphique Crypto", "key": "tab_home"})
            st.session_state.term_tabs = tabs
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<div style='font-family:IBM Plex Mono,monospace;font-size:9px;color:#333;'>"
        f"{len(tabs)}/{MAX_TABS} onglets ouverts</div>",
        unsafe_allow_html=True
    )

    # ══════════════════════════════════════════
    # TOPBAR simple (une seule ligne)
    # ══════════════════════════════════════════
    st.markdown(f"""
    <div class="term-topbar">
      <div class="term-logo">AM<span>.</span>TERMINAL</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#4d9fff;letter-spacing:1px;">
        {len(tabs)} ONGLET{'S' if len(tabs)>1 else ''} OUVERT{'S' if len(tabs)>1 else ''}
      </div>
      <div style="margin-left:auto;font-family:'IBM Plex Mono',monospace;
                  font-size:9px;color:#333;">{time.strftime('%H:%M:%S')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # ONGLETS STREAMLIT NATIFS (une seule barre)
    # ══════════════════════════════════════════
    if not tabs:
        st.markdown("""
        <div class="term-welcome">
          <div class="logo-big">AM<span>.</span>TERMINAL</div>
          <div class="tagline">» BLOOMBERG-STYLE MULTI-PANEL TERMINAL «</div>
        </div>""", unsafe_allow_html=True)
        return

    tab_labels = [t["name"] for t in tabs]
    st_tabs = st.tabs(tab_labels)

    for i, (st_tab, tab) in enumerate(zip(st_tabs, tabs)):
        with st_tab:
            _render_tool(tab["id"], tab["name"], i)
