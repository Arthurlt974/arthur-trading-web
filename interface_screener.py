"""
interface_screener.py — AM-Trading | Screener Avancé
Filtres : P/E, P/B, EPS, Secteur, Performance, Volume, Market Cap, RSI, Dividende
Univers : liste personnalisée + presets CAC40 / S&P500
Affichage : tableau triable + mini graphiques Plotly
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════
#  UNIVERS PAR DÉFAUT
# ══════════════════════════════════════════

CAC40 = [
    "AI.PA","AIR.PA","ALO.PA","MT.AS","ATO.PA","CS.PA","BNP.PA","EN.PA","CAP.PA",
    "CA.PA","ACA.PA","BN.PA","DSY.PA","ENGI.PA","EL.PA","ERF.PA","RMS.PA","KER.PA",
    "LR.PA","OR.PA","MC.PA","ML.PA","ORA.PA","RI.PA","PUB.PA","RNO.PA","SAF.PA",
    "SGO.PA","SAN.PA","SU.PA","GLE.PA","STLAM.MI","STM.PA","TEP.PA","HO.PA",
    "TTE.PA","URW.AS","VIE.PA","DG.PA","WLN.PA"
]

SP500_TOP50 = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","JPM","V",
    "UNH","XOM","LLY","JNJ","MA","PG","HD","AVGO","MRK","ABBV",
    "CVX","COST","WMT","BAC","PEP","NFLX","KO","TMO","ACN","CSCO",
    "CRM","MCD","ABT","ADBE","DHR","NEE","TXN","VZ","PM","INTC",
    "DIS","WFC","AMD","MS","RTX","QCOM","AMGN","SPGI","HON","CAT"
]

# ══════════════════════════════════════════
#  CALCULS TECHNIQUES
# ══════════════════════════════════════════

def _rsi(closes: pd.Series, period=14) -> float:
    try:
        delta = closes.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, np.nan)
        return round(float(100 - 100 / (1 + rs.iloc[-1])), 1)
    except Exception:
        return float("nan")

def _perf(closes: pd.Series, days: int) -> float:
    try:
        if len(closes) < days + 1:
            return float("nan")
        return round((closes.iloc[-1] / closes.iloc[-days] - 1) * 100, 2)
    except Exception:
        return float("nan")

# ══════════════════════════════════════════
#  FETCH UN TICKER
# ══════════════════════════════════════════

def _fetch_ticker(symbol: str) -> dict | None:
    try:
        t  = yf.Ticker(symbol)
        fi = t.fast_info

        # Prix & market data
        price   = getattr(fi, "last_price",       None)
        prev    = getattr(fi, "previous_close",   None)
        mktcap  = getattr(fi, "market_cap",       None)
        shares  = getattr(fi, "shares",           None)
        currency= getattr(fi, "currency",         "USD")

        if not price or price == 0:
            return None

        # Historique pour RSI + performance
        hist = t.history(period="3mo", progress=False, auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None
        closes = hist["Close"].squeeze()
        volume = float(hist["Volume"].iloc[-1]) if "Volume" in hist else 0

        # Info fondamentaux
        info = {}
        try:
            import requests as _req
            s = _req.Session()
            s.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            info = yf.Ticker(symbol, session=s).info or {}
        except Exception:
            try:
                info = t.info or {}
            except Exception:
                pass

        chg_1d  = _perf(closes, 1)
        chg_5d  = _perf(closes, 5)
        chg_1m  = _perf(closes, 21)
        rsi_val = _rsi(closes)

        pe      = info.get("trailingPE")   or info.get("forwardPE")
        pb      = info.get("priceToBook")
        eps     = info.get("trailingEps")  or info.get("forwardEps")
        div_y   = info.get("dividendYield", 0) or 0
        sector  = info.get("sector",   "—")
        name    = info.get("shortName") or info.get("longName") or symbol

        # EPS depuis income_stmt si absent
        if not eps and shares:
            try:
                inc = t.income_stmt
                if inc is not None and not inc.empty:
                    for lbl in ["Net Income", "NetIncome", "Net Income Common Stockholders"]:
                        if lbl in inc.index:
                            eps = round(float(inc.loc[lbl].iloc[0]) / float(shares), 3)
                            break
            except Exception:
                pass

        # Stocker l'historique comme liste JSON-sérialisable
        hist_prices = closes.tolist()[-63:]  # 3 mois max

        return {
            "symbol":    symbol,
            "name":      name[:28],
            "price":     round(float(price), 2),
            "currency":  currency,
            "mktcap":    float(mktcap) if mktcap else None,
            "volume":    volume,
            "chg_1d":    chg_1d,
            "chg_5d":    chg_5d,
            "chg_1m":    chg_1m,
            "rsi":       rsi_val,
            "pe":        round(float(pe), 1)  if pe  else None,
            "pb":        round(float(pb), 2)  if pb  else None,
            "eps":       round(float(eps), 3) if eps else None,
            "div_yield": round(div_y * 100, 2) if div_y else 0.0,
            "sector":    sector,
            "hist":      hist_prices,
        }
    except Exception:
        return None

# ══════════════════════════════════════════
#  MINI GRAPHIQUE
# ══════════════════════════════════════════

def _mini_chart(closes: pd.Series, symbol: str, chg: float) -> go.Figure:
    color = "#00ff88" if chg >= 0 else "#ff4444"
    fig = go.Figure(go.Scatter(
        x=closes.index, y=closes.values,
        mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in color else f"rgba({'0,255,136' if chg>=0 else '255,68,68'},0.08)",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=50, showlegend=False,
    )
    return fig

# ══════════════════════════════════════════
#  SCREENER PRINCIPAL
# ══════════════════════════════════════════

def _run_screener(symbols: tuple) -> pd.DataFrame:
    """Fetch tous les tickers en parallèle et retourne le DataFrame brut."""
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_fetch_ticker, s): s for s in symbols}
        for fut in as_completed(futures):
            try:
                data = fut.result(timeout=15)
                if data:
                    results.append(data)
            except Exception:
                continue
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df = df.sort_values("mktcap", ascending=False, na_position="last")
    return df

# ══════════════════════════════════════════
#  UI
# ══════════════════════════════════════════

def show_screener():
    st.markdown("""
        <div style='text-align:center;padding:28px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
                    border:3px solid #ff9800;border-radius:15px;margin-bottom:20px;'>
            <h1 style='color:#ff9800;margin:0;font-size:44px;text-shadow:0 0 20px #ff9800;'>🔎 SCREENER AVANCÉ</h1>
            <p style='color:#ffb84d;margin:8px 0 0 0;font-size:16px;'>
                Filtrez par fondamentaux · Techniques · Performance · Secteur
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Univers ──────────────────────────────────────
    st.markdown("### 📋 UNIVERS D'ACTIONS")
    col_u1, col_u2, col_u3 = st.columns([1,1,2])
    with col_u1:
        preset = st.selectbox("Preset", ["Liste personnalisée", "CAC 40", "S&P 500 Top 50", "CAC 40 + S&P 500"], key="sc_preset")
    with col_u2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("🚀 LANCER LE SCREENER", key="sc_run", type="primary", use_container_width=True)

    # Gestion de la liste perso
    if "sc_custom_list" not in st.session_state:
        st.session_state.sc_custom_list = ["AAPL","MSFT","NVDA","TSLA","MC.PA","TTE.PA","BNP.PA","GOOGL","AMZN","META"]

    if preset == "Liste personnalisée":
        with col_u3:
            raw = st.text_input(
                "Tickers (séparés par virgule)",
                value=", ".join(st.session_state.sc_custom_list),
                key="sc_custom_input"
            )
            symbols_list = [s.strip().upper() for s in raw.split(",") if s.strip()]
            st.session_state.sc_custom_list = symbols_list
    elif preset == "CAC 40":
        symbols_list = CAC40
        with col_u3:
            st.info(f"📊 {len(CAC40)} actions du CAC 40")
    elif preset == "S&P 500 Top 50":
        symbols_list = SP500_TOP50
        with col_u3:
            st.info(f"📊 Top {len(SP500_TOP50)} du S&P 500 par market cap")
    else:
        symbols_list = CAC40 + SP500_TOP50
        with col_u3:
            st.info(f"📊 {len(CAC40 + SP500_TOP50)} actions combinées")

    st.markdown("---")

    # ── Filtres ──────────────────────────────────────
    st.markdown("### ⚙️ FILTRES")

    with st.expander("📐 Fondamentaux — P/E · P/B · EPS · Dividende", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            pe_min, pe_max = st.slider("P/E Ratio", 0.0, 100.0, (0.0, 60.0), step=1.0, key="f_pe")
        with f2:
            pb_min, pb_max = st.slider("P/B Ratio", 0.0, 30.0, (0.0, 20.0), step=0.5, key="f_pb")
        with f3:
            eps_min = st.number_input("EPS min", value=-10.0, step=0.5, key="f_eps")
        with f4:
            div_min = st.number_input("Dividende min (%)", value=0.0, step=0.5, key="f_div")

    with st.expander("📈 Performance & Technique — RSI · Variation %", expanded=True):
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            rsi_min, rsi_max = st.slider("RSI (14)", 0, 100, (0, 100), key="f_rsi")
        with t2:
            chg1d_min, chg1d_max = st.slider("Variation 1j (%)", -20.0, 20.0, (-20.0, 20.0), step=0.5, key="f_chg1d")
        with t3:
            chg1m_min, chg1m_max = st.slider("Variation 1 mois (%)", -50.0, 50.0, (-50.0, 50.0), step=1.0, key="f_chg1m")
        with t4:
            rsi_signal = st.selectbox("Signal RSI", ["Tous", "Survente (<30)", "Neutre (30-70)", "Surachat (>70)"], key="f_rsi_sig")

    with st.expander("💰 Taille & Volume — Market Cap · Volume", expanded=False):
        m1, m2 = st.columns(2)
        with m1:
            mc_min = st.selectbox("Market Cap minimum", ["Toutes", ">100M", ">1Md", ">10Md", ">100Md"], key="f_mc")
        with m2:
            vol_min = st.selectbox("Volume minimum", ["Tous", ">100K", ">500K", ">1M", ">10M"], key="f_vol")

    with st.expander("🏭 Secteur / Industrie", expanded=False):
        secteurs_dispo = [
            "Tous", "Technology", "Financial Services", "Consumer Cyclical",
            "Consumer Defensive", "Healthcare", "Energy", "Industrials",
            "Basic Materials", "Communication Services", "Real Estate", "Utilities"
        ]
        secteur_filtre = st.multiselect("Secteurs", secteurs_dispo[1:], default=[], key="f_sector",
                                         placeholder="Tous les secteurs")

    # ── Lancement ────────────────────────────────────
    if run_btn or "sc_df" in st.session_state:

        if run_btn:
            if not symbols_list:
                st.warning("Ajoutez au moins un ticker.")
                return
            # Vider le cache précédent
            st.session_state.pop("sc_df", None)
            prog = st.progress(0, text="Initialisation...")
            status = st.empty()
            
            results = []
            total = len(symbols_list)
            with ThreadPoolExecutor(max_workers=6) as ex:
                futures = {ex.submit(_fetch_ticker, s): s for s in symbols_list}
                done = 0
                for fut in as_completed(futures):
                    sym = futures[fut]
                    try:
                        data = fut.result(timeout=15)
                        if data:
                            results.append(data)
                    except Exception:
                        pass
                    done += 1
                    prog.progress(done / total, text=f"Analyse {sym}... ({done}/{total})")
            
            prog.empty()
            status.empty()
            
            if not results:
                st.error("Aucune donnée récupérée. Vérifiez votre connexion ou les tickers.")
                return
            
            df_raw = pd.DataFrame(results)
            df_raw = df_raw.sort_values("mktcap", ascending=False, na_position="last")
            st.session_state.sc_df = df_raw
            st.session_state.sc_symbols = tuple(symbols_list)
            st.success(f"✅ {len(results)}/{total} actions chargées")

        df = st.session_state.get("sc_df", pd.DataFrame())
        if df.empty:
            return

        # ── Application des filtres ──
        df_f = df.copy()

        # P/E
        mask_pe = df_f["pe"].isna() | ((df_f["pe"] >= pe_min) & (df_f["pe"] <= pe_max))
        df_f = df_f[mask_pe]
        # P/B
        mask_pb = df_f["pb"].isna() | ((df_f["pb"] >= pb_min) & (df_f["pb"] <= pb_max))
        df_f = df_f[mask_pb]
        # EPS
        mask_eps = df_f["eps"].isna() | (df_f["eps"] >= eps_min)
        df_f = df_f[mask_eps]
        # Dividende
        df_f = df_f[df_f["div_yield"] >= div_min]
        # RSI
        mask_rsi = df_f["rsi"].isna() | ((df_f["rsi"] >= rsi_min) & (df_f["rsi"] <= rsi_max))
        df_f = df_f[mask_rsi]
        if rsi_signal == "Survente (<30)":
            df_f = df_f[df_f["rsi"] < 30]
        elif rsi_signal == "Neutre (30-70)":
            df_f = df_f[(df_f["rsi"] >= 30) & (df_f["rsi"] <= 70)]
        elif rsi_signal == "Surachat (>70)":
            df_f = df_f[df_f["rsi"] > 70]
        # Variation 1j
        mask_c1 = df_f["chg_1d"].isna() | ((df_f["chg_1d"] >= chg1d_min) & (df_f["chg_1d"] <= chg1d_max))
        df_f = df_f[mask_c1]
        # Variation 1m
        mask_cm = df_f["chg_1m"].isna() | ((df_f["chg_1m"] >= chg1m_min) & (df_f["chg_1m"] <= chg1m_max))
        df_f = df_f[mask_cm]
        # Market Cap
        mc_map = {"Toutes": 0, ">100M": 1e8, ">1Md": 1e9, ">10Md": 1e10, ">100Md": 1e11}
        mc_threshold = mc_map.get(mc_min, 0)
        if mc_threshold > 0:
            df_f = df_f[df_f["mktcap"].notna() & (df_f["mktcap"] >= mc_threshold)]
        # Volume
        vol_map = {"Tous": 0, ">100K": 1e5, ">500K": 5e5, ">1M": 1e6, ">10M": 1e7}
        vol_threshold = vol_map.get(vol_min, 0)
        if vol_threshold > 0:
            df_f = df_f[df_f["volume"] >= vol_threshold]
        # Secteur
        if secteur_filtre:
            df_f = df_f[df_f["sector"].isin(secteur_filtre)]

        # ── Résultats ──
        st.markdown("---")
        st.markdown(f"### 📊 RÉSULTATS — {len(df_f)} action(s) sur {len(df)} analysées")

        if df_f.empty:
            st.warning("Aucune action ne correspond à ces filtres.")
            return

        # KPIs résumé
        k1, k2, k3, k4, k5 = st.columns(5)
        valid_pe  = df_f["pe"].dropna()
        valid_rsi = df_f["rsi"].dropna()
        hausse    = len(df_f[df_f["chg_1d"] > 0])
        k1.metric("Actions trouvées",  len(df_f))
        k2.metric("P/E moyen",         f"{valid_pe.mean():.1f}x"   if not valid_pe.empty  else "N/A")
        k3.metric("RSI moyen",         f"{valid_rsi.mean():.0f}"   if not valid_rsi.empty else "N/A")
        k4.metric("En hausse aujourd'hui", f"{hausse} / {len(df_f)}")
        k5.metric("Perf moy. 1 mois",  f"{df_f['chg_1m'].mean():+.1f}%" if df_f["chg_1m"].notna().any() else "N/A")

        st.markdown("---")

        # ── Tri ──
        col_sort1, col_sort2, _ = st.columns([1,1,2])
        with col_sort1:
            sort_by = st.selectbox("Trier par", [
                "Market Cap", "Performance 1j", "Performance 1 mois",
                "RSI", "P/E", "P/B", "Dividende", "Volume"
            ], key="sc_sort")
        with col_sort2:
            sort_asc = st.checkbox("Ordre croissant", value=False, key="sc_asc")

        sort_map = {
            "Market Cap": "mktcap", "Performance 1j": "chg_1d",
            "Performance 1 mois": "chg_1m", "RSI": "rsi",
            "P/E": "pe", "P/B": "pb", "Dividende": "div_yield", "Volume": "volume"
        }
        df_sorted = df_f.sort_values(sort_map[sort_by], ascending=sort_asc, na_position="last")

        # ── Tableau + mini charts ──
        for i, (_, row) in enumerate(df_sorted.iterrows()):
            chg1d = row["chg_1d"] if pd.notna(row["chg_1d"]) else 0
            chg1m = row["chg_1m"] if pd.notna(row["chg_1m"]) else 0
            c_1d  = "#00ff88" if chg1d >= 0 else "#ff4444"
            c_1m  = "#00ff88" if chg1m >= 0 else "#ff4444"

            # RSI couleur
            rsi = row["rsi"]
            if pd.isna(rsi):
                rsi_color, rsi_label = "#aaa", "N/A"
            elif rsi < 30:
                rsi_color, rsi_label = "#00ff88", f"{rsi:.0f} 🟢"
            elif rsi > 70:
                rsi_color, rsi_label = "#ff4444", f"{rsi:.0f} 🔴"
            else:
                rsi_color, rsi_label = "#ff9800", f"{rsi:.0f}"

            mc_str = "N/A"
            if pd.notna(row["mktcap"]):
                mc = row["mktcap"]
                mc_str = f"{mc/1e9:.1f} Md" if mc >= 1e9 else f"{mc/1e6:.0f} M"

            col_info, col_chart, col_metrics = st.columns([3, 2, 4])

            with col_info:
                st.markdown(f"""
                    <div style='padding:14px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
                                border-radius:10px;border:1.5px solid #333;height:90px;'>
                        <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <span style='color:#ff9800;font-weight:bold;font-size:16px;'>{row['symbol']}</span>
                            <span style='color:#fff;font-size:15px;font-weight:bold;'>{row['price']:.2f} <span style='font-size:11px;color:#aaa;'>{row['currency']}</span></span>
                        </div>
                        <p style='color:#aaa;margin:4px 0;font-size:11px;'>{row['name']}</p>
                        <span style='background:#222;color:#aaa;padding:2px 7px;border-radius:4px;font-size:10px;'>{row['sector']}</span>
                    </div>
                """, unsafe_allow_html=True)

            with col_chart:
                if row.get("hist") and len(row["hist"]) > 5:
                    try:
                        fig = _mini_chart(pd.Series(row["hist"]), row["symbol"], chg1d)
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False},
                                       key=f"mc_{row['symbol']}_{i}")
                    except Exception:
                        st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)

            with col_metrics:
                st.markdown(f"""
                    <div style='padding:10px 14px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
                                border-radius:10px;border:1.5px solid #333;height:90px;'>
                        <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:11px;'>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>1J</p>
                                <b style='color:{c_1d};'>{f"{chg1d:+.1f}%" if pd.notna(row["chg_1d"]) else "N/A"}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>1M</p>
                                <b style='color:{c_1m};'>{f"{chg1m:+.1f}%" if pd.notna(row["chg_1m"]) else "N/A"}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>RSI</p>
                                <b style='color:{rsi_color};'>{rsi_label}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>MKT CAP</p>
                                <b style='color:#fff;'>{mc_str}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>P/E</p>
                                <b style='color:#fff;'>{f"{row['pe']:.1f}x" if pd.notna(row["pe"]) else "N/A"}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>P/B</p>
                                <b style='color:#fff;'>{f"{row['pb']:.1f}x" if pd.notna(row["pb"]) else "N/A"}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>EPS</p>
                                <b style='color:#fff;'>{f"{row['eps']:.2f}" if pd.notna(row["eps"]) else "N/A"}</b>
                            </div>
                            <div>
                                <p style='color:#555;margin:0;font-size:9px;'>DIV</p>
                                <b style='color:#ffb84d;'>{f"{row['div_yield']:.1f}%" if row["div_yield"] else "—"}</b>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='margin:4px 0;'></div>", unsafe_allow_html=True)

        # ── Export CSV ──
        st.markdown("---")
        df_export = df_sorted.drop(columns=["_hist"], errors="ignore")
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Exporter les résultats en CSV",
            data=csv,
            file_name=f"screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="sc_csv"
        )
