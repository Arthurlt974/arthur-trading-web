"""
interface_barometres.py — AM Trading
Baromètre Achat · Baromètre Indicateurs Techniques · Baromètre Moyennes Mobiles
Écart Journalier · Écart 52 Semaines · Historique Variations
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ══════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════

def _fetch(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()

def _rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs    = gain / loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def _score_color(score: float) -> str:
    if score >= 70:  return "#00C853"
    if score >= 55:  return "#8BC34A"
    if score >= 45:  return "#FF9800"
    if score >= 30:  return "#FF5722"
    return "#FF3B30"

def _gauge(score: float, title: str, max_val: float = 100) -> go.Figure:
    color = _score_color(score / max_val * 100)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 12, "color": "#666", "family": "IBM Plex Mono"}},
        number={"font": {"size": 36, "color": color, "family": "IBM Plex Mono"}, "suffix": "%"},
        gauge={
            "axis": {"range": [0, max_val], "tickfont": {"size": 8, "color": "#333"},
                     "tickwidth": 1, "tickcolor": "#222",
                     "nticks": 6},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#0a0a0a",
            "borderwidth": 1,
            "bordercolor": "#1a1a1a",
            "steps": [
                {"range": [0, max_val*0.3],           "color": "#150000"},
                {"range": [max_val*0.3,  max_val*0.45],"color": "#151000"},
                {"range": [max_val*0.45, max_val*0.55],"color": "#151500"},
                {"range": [max_val*0.55, max_val*0.7], "color": "#001500"},
                {"range": [max_val*0.7,  max_val],     "color": "#001f00"},
            ],
            "threshold": {"line": {"color": color, "width": 4}, "thickness": 0.85, "value": score},
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10), height=220,
        font=dict(family="IBM Plex Mono", color="#aaa")
    )
    return fig

def _signal_badge(text: str, signal: str) -> str:
    colors = {"bullish": ("#002b00","#00C853"), "bearish": ("#2b0000","#FF3B30"), "neutral": ("#1a1a00","#FF9800")}
    bg, fg = colors.get(signal, ("#111","#aaa"))
    return f'<div style="background:{bg};color:{fg};border-left:3px solid {fg};padding:7px 12px;border-radius:4px;margin:3px 0;font-family:IBM Plex Mono,monospace;font-size:11px;">{text}</div>'

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
.bar-header { font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:700; color:#ff6600; letter-spacing:3px; margin-bottom:4px; }
.bar-sub { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#444; letter-spacing:2px; margin-bottom:20px; }
.bar-section { font-family:'IBM Plex Mono',monospace; font-size:9px; color:#555; letter-spacing:3px; border-left:2px solid #ff6600; padding-left:10px; margin:20px 0 12px; }
.bar-card { background:#0a0a0a; border:1px solid #1a1a1a; border-radius:10px; padding:16px 18px; font-family:'IBM Plex Mono',monospace; transition:border-color .2s; }
.bar-card:hover { border-color:#ff6600; }
.verdict { font-family:'IBM Plex Mono',monospace; font-size:14px; font-weight:700; letter-spacing:2px; padding:12px 20px; border-radius:8px; text-align:center; margin:12px 0; }
.ecart-item { background:#0a0a0a; border:1px solid #1a1a1a; border-radius:8px; padding:14px 16px; margin-bottom:6px; font-family:'IBM Plex Mono',monospace; }
.ecart-label { font-size:9px; color:#4d9fff; letter-spacing:2px; margin-bottom:4px; }
.ecart-val { font-size:18px; font-weight:700; }
.hist-bar-pos { background:linear-gradient(90deg,#00C853,transparent); height:16px; border-radius:3px; }
.hist-bar-neg { background:linear-gradient(90deg,#FF3B30,transparent); height:16px; border-radius:3px; }
</style>
"""

# ══════════════════════════════════════════
#  1. BAROMÈTRE ACHAT GLOBAL
# ══════════════════════════════════════════
def _barometre_achat(ticker: str):
    st.markdown('<div class="bar-section">BAROMÈTRE ACHAT GLOBAL</div>', unsafe_allow_html=True)

    df = _fetch(ticker, "6mo")
    if df.empty:
        st.error("Données indisponibles.")
        return

    close = df["Close"].squeeze()
    vol   = df["Volume"].squeeze() if "Volume" in df.columns else pd.Series([0]*len(close))

    # Calcul des indicateurs
    rsi_series = _rsi(close)
    rsi = float(rsi_series.iloc[-1])

    macd_line   = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd        = float(macd_line.iloc[-1])
    signal      = float(signal_line.iloc[-1])

    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma200= float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    price = float(close.iloc[-1])

    bb_std   = float(close.rolling(20).std().iloc[-1])
    bb_upper = sma20 + 2 * bb_std
    bb_lower = sma20 - 2 * bb_std
    bb_pos   = (price - bb_lower) / (bb_upper - bb_lower) * 100 if (bb_upper - bb_lower) > 0 else 50

    vol_ma  = float(vol.rolling(20).mean().iloc[-1]) if vol.sum() > 0 else 0
    vol_cur = float(vol.iloc[-1]) if vol.sum() > 0 else 0

    # Score global /100
    score = 50.0
    signals = []

    # RSI (±15 pts)
    if rsi < 30:   score += 15; signals.append(("RSI", f"SURVENTE ({rsi:.1f}) — ACHAT FORT", "bullish"))
    elif rsi < 40: score += 8;  signals.append(("RSI", f"Zone basse ({rsi:.1f}) — Opportunité", "bullish"))
    elif rsi > 70: score -= 15; signals.append(("RSI", f"SURACHAT ({rsi:.1f}) — VENTE FORT", "bearish"))
    elif rsi > 60: score -= 8;  signals.append(("RSI", f"Zone haute ({rsi:.1f}) — Prudence", "bearish"))
    else:          signals.append(("RSI", f"Neutre ({rsi:.1f})", "neutral"))

    # MACD (±10 pts)
    if macd > signal:  score += 10; signals.append(("MACD", "Haussier — au-dessus de la signal", "bullish"))
    else:              score -= 10; signals.append(("MACD", "Baissier — en-dessous de la signal", "bearish"))

    # Prix vs MAs (±15 pts)
    above_sma20 = price > sma20
    above_sma50 = (price > sma50) if sma50 else None
    above_sma200= (price > sma200) if sma200 else None

    if above_sma20: score += 5;  signals.append(("SMA20", f"Prix au-dessus ({sma20:.2f})", "bullish"))
    else:           score -= 5;  signals.append(("SMA20", f"Prix en-dessous ({sma20:.2f})", "bearish"))
    if above_sma50 is not None:
        if above_sma50: score += 5;  signals.append(("SMA50", f"Prix au-dessus ({sma50:.2f})", "bullish"))
        else:           score -= 5;  signals.append(("SMA50", f"Prix en-dessous ({sma50:.2f})", "bearish"))
    if above_sma200 is not None:
        if above_sma200: score += 5;  signals.append(("SMA200", f"Prix au-dessus ({sma200:.2f})", "bullish"))
        else:            score -= 5;  signals.append(("SMA200", f"Prix en-dessous ({sma200:.2f})", "bearish"))

    # Bollinger (±5 pts)
    if bb_pos < 20:   score += 5;  signals.append(("BB", f"Bas des bandes ({bb_pos:.0f}%) — Rebond possible", "bullish"))
    elif bb_pos > 80: score -= 5;  signals.append(("BB", f"Haut des bandes ({bb_pos:.0f}%) — Résistance", "bearish"))
    else:             signals.append(("BB", f"Zone médiane ({bb_pos:.0f}%)", "neutral"))

    # Volume (±5 pts)
    if vol_ma > 0 and vol_cur > vol_ma * 1.5: score += 5; signals.append(("VOLUME", "Volume fort — Confirmation", "bullish"))
    elif vol_ma > 0 and vol_cur < vol_ma * 0.5: score -= 3; signals.append(("VOLUME", "Volume faible — Signal peu fiable", "neutral"))

    score = max(0, min(100, score))

    # Verdict
    if score >= 70:   verdict, v_color, v_bg = "🚀 SIGNAL ACHAT FORT",   "#00C853", "#002b00"
    elif score >= 58: verdict, v_color, v_bg = "📈 SIGNAL ACHAT",         "#8BC34A", "#1a2b00"
    elif score >= 42: verdict, v_color, v_bg = "⚖️ NEUTRE",               "#FF9800", "#2b1a00"
    elif score >= 30: verdict, v_color, v_bg = "📉 SIGNAL VENTE",          "#FF5722", "#2b0a00"
    else:             verdict, v_color, v_bg = "⚠️ SIGNAL VENTE FORT",    "#FF3B30", "#2b0000"

    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(_gauge(score, "SCORE ACHAT", 100), use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<div class="verdict" style="background:{v_bg};color:{v_color};border:1px solid {v_color};">{verdict}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("**Détail des signaux :**")
        for ind, msg, sig in signals:
            st.markdown(f'<b style="color:#ff6600;font-size:9px;">{ind}</b> {_signal_badge(msg, sig)}', unsafe_allow_html=True)

# ══════════════════════════════════════════
#  2. BAROMÈTRE INDICATEURS TECHNIQUES
# ══════════════════════════════════════════
def _barometre_indicateurs(ticker: str):
    st.markdown('<div class="bar-section">BAROMÈTRE INDICATEURS TECHNIQUES</div>', unsafe_allow_html=True)

    df = _fetch(ticker, "1y")
    if df.empty:
        st.error("Données indisponibles.")
        return

    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze() if "Volume" in df.columns else pd.Series([0]*len(close))
    price = float(close.iloc[-1])

    # ── Calculs ──
    rsi14  = float(_rsi(close, 14).iloc[-1])
    rsi9   = float(_rsi(close, 9).iloc[-1])

    macd_l = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    sig_l  = macd_l.ewm(span=9, adjust=False).mean()
    macd_v = float(macd_l.iloc[-1])
    sig_v  = float(sig_l.iloc[-1])
    hist_v = macd_v - sig_v

    # Stochastic
    low14  = low.rolling(14).min()
    high14 = high.rolling(14).max()
    stoch_k = ((close - low14) / (high14 - low14).replace(0, 1e-10)) * 100
    stoch_d = stoch_k.rolling(3).mean()
    k = float(stoch_k.iloc[-1])
    d = float(stoch_d.iloc[-1])

    # Williams %R
    willr = ((high.rolling(14).max() - close) / (high.rolling(14).max() - low.rolling(14).min()).replace(0,1e-10)) * -100
    wr = float(willr.iloc[-1])

    # CCI
    tp = (high + low + close) / 3
    cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
    cci_v = float(cci.iloc[-1])

    # MFI
    try:
        raw_money = tp * vol
        pos_flow = raw_money.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg_flow = raw_money.where(tp < tp.shift(1), 0).rolling(14).sum()
        mfi = 100 - (100 / (1 + pos_flow / neg_flow.replace(0, 1e-10)))
        mfi_v = float(mfi.iloc[-1])
    except Exception:
        mfi_v = 50.0

    # ATR
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    atr_pct = (atr / price) * 100

    # Tableau résumé
    indicateurs = [
        ("RSI 14",     rsi14,  "< 30 ACHAT | > 70 VENTE",
         "bullish" if rsi14 < 30 else "bearish" if rsi14 > 70 else "neutral",
         f"{rsi14:.1f}"),
        ("RSI 9",      rsi9,   "< 30 ACHAT | > 70 VENTE",
         "bullish" if rsi9 < 30 else "bearish" if rsi9 > 70 else "neutral",
         f"{rsi9:.1f}"),
        ("MACD",       None,   "MACD > Signal = ACHAT",
         "bullish" if macd_v > sig_v else "bearish",
         f"{'▲' if macd_v > sig_v else '▼'} {abs(hist_v):.3f}"),
        ("Stoch K",    k,      "< 20 ACHAT | > 80 VENTE",
         "bullish" if k < 20 else "bearish" if k > 80 else "neutral",
         f"{k:.1f}"),
        ("Williams %R",None,   "< -80 ACHAT | > -20 VENTE",
         "bullish" if wr < -80 else "bearish" if wr > -20 else "neutral",
         f"{wr:.1f}"),
        ("CCI",        None,   "< -100 ACHAT | > 100 VENTE",
         "bullish" if cci_v < -100 else "bearish" if cci_v > 100 else "neutral",
         f"{cci_v:.1f}"),
        ("MFI",        mfi_v,  "< 20 ACHAT | > 80 VENTE",
         "bullish" if mfi_v < 20 else "bearish" if mfi_v > 80 else "neutral",
         f"{mfi_v:.1f}"),
        ("ATR 14",     None,   "Volatilité journalière",
         "neutral",
         f"{atr:.2f} ({atr_pct:.1f}%)"),
    ]

    # Compter les signaux
    bull = sum(1 for _, _, _, s, _ in indicateurs if s == "bullish")
    bear = sum(1 for _, _, _, s, _ in indicateurs if s == "bearish")
    neut = sum(1 for _, _, _, s, _ in indicateurs if s == "neutral")
    total = bull + bear + neut

    score_tech = round(bull / total * 100) if total > 0 else 50

    # Gauges
    col1, col2, col3 = st.columns(3)
    with col1:
        bull_pct = round(bull / total * 100) if total > 0 else 0
        st.plotly_chart(_gauge(bull_pct, f"ACHATS {bull}/{total}", 100), use_container_width=True, config={"displayModeBar": False})
    with col2:
        st.plotly_chart(_gauge(score_tech, "SCORE TECHNIQUE", 100), use_container_width=True, config={"displayModeBar": False})
    with col3:
        bear_pct = round(bear / total * 100) if total > 0 else 0
        st.plotly_chart(_gauge(bear_pct, f"VENTES {bear}/{total}", 100), use_container_width=True, config={"displayModeBar": False})

    # Tableau des indicateurs
    st.markdown("**Détail des indicateurs :**")
    c_ind, c_val, c_sig, c_int = st.columns([2,1,1,3])
    c_ind.markdown("**INDICATEUR**")
    c_val.markdown("**VALEUR**")
    c_sig.markdown("**SIGNAL**")
    c_int.markdown("**INTERPRÉTATION**")
    st.markdown("<hr style='margin:4px 0;border-color:#1a1a1a;'>", unsafe_allow_html=True)

    sig_labels = {"bullish": "🟢 ACHAT", "bearish": "🔴 VENTE", "neutral": "🟡 NEUTRE"}
    for nom, val, interp, sig, val_str in indicateurs:
        c1, c2, c3, c4 = st.columns([2,1,1,3])
        c1.markdown(f'<span style="font-family:IBM Plex Mono;font-size:12px;color:#aaa;">{nom}</span>', unsafe_allow_html=True)
        c2.markdown(f'<span style="font-family:IBM Plex Mono;font-size:12px;color:#ff6600;font-weight:700;">{val_str}</span>', unsafe_allow_html=True)
        color = "#00C853" if sig=="bullish" else "#FF3B30" if sig=="bearish" else "#FF9800"
        c3.markdown(f'<span style="font-family:IBM Plex Mono;font-size:11px;color:{color};">{sig_labels[sig]}</span>', unsafe_allow_html=True)
        c4.markdown(f'<span style="font-family:IBM Plex Mono;font-size:10px;color:#555;">{interp}</span>', unsafe_allow_html=True)

# ══════════════════════════════════════════
#  3. BAROMÈTRE MOYENNES MOBILES
# ══════════════════════════════════════════
def _barometre_mm(ticker: str):
    st.markdown('<div class="bar-section">BAROMÈTRE MOYENNES MOBILES</div>', unsafe_allow_html=True)

    df = _fetch(ticker, "1y")
    if df.empty:
        st.error("Données indisponibles.")
        return

    close = df["Close"].squeeze()
    price = float(close.iloc[-1])

    mas = [
        ("SMA 5",    5,  "simple"),
        ("SMA 10",   10, "simple"),
        ("SMA 20",   20, "simple"),
        ("SMA 50",   50, "simple"),
        ("SMA 100",  100,"simple"),
        ("SMA 200",  200,"simple"),
        ("EMA 5",    5,  "ema"),
        ("EMA 10",   10, "ema"),
        ("EMA 20",   20, "ema"),
        ("EMA 50",   50, "ema"),
        ("EMA 100",  100,"ema"),
        ("EMA 200",  200,"ema"),
    ]

    results = []
    for nom, period, typ in mas:
        if len(close) < period:
            continue
        val = float(close.ewm(span=period, adjust=False).mean().iloc[-1]) if typ == "ema" \
              else float(close.rolling(period).mean().iloc[-1])
        if pd.isna(val):
            continue
        diff_pct = (price - val) / val * 100
        sig = "bullish" if price > val else "bearish"
        results.append((nom, val, diff_pct, sig))

    bull = sum(1 for _, _, _, s in results if s == "bullish")
    bear = sum(1 for _, _, _, s in results if s == "bearish")
    total = bull + bear
    score = round(bull / total * 100) if total > 0 else 50

    # Gauge
    col_g, col_r = st.columns([1, 2])
    with col_g:
        st.plotly_chart(_gauge(score, f"MM HAUSSIÈRES {bull}/{total}", 100), use_container_width=True, config={"displayModeBar": False})
        if score >= 70:   verdict, vc = "🚀 TENDANCE HAUSSIÈRE FORTE", "#00C853"
        elif score >= 55: verdict, vc = "📈 LÉGÈREMENT HAUSSIER",       "#8BC34A"
        elif score >= 45: verdict, vc = "⚖️ INDÉCIS",                   "#FF9800"
        elif score >= 30: verdict, vc = "📉 LÉGÈREMENT BAISSIER",        "#FF5722"
        else:             verdict, vc = "⚠️ TENDANCE BAISSIÈRE FORTE",  "#FF3B30"
        st.markdown(f'<div style="background:#0a0a0a;border:1px solid {vc};border-radius:8px;padding:10px;text-align:center;font-family:IBM Plex Mono;font-size:12px;font-weight:700;color:{vc};">{verdict}</div>', unsafe_allow_html=True)

    with col_r:
        # Tableau des MAs
        sma_res = [(n,v,d,s) for n,v,d,s in results if "SMA" in n]
        ema_res = [(n,v,d,s) for n,v,d,s in results if "EMA" in n]

        col_s, col_e = st.columns(2)
        for col, data, label in [(col_s, sma_res, "SMA"), (col_e, ema_res, "EMA")]:
            with col:
                st.markdown(f'<div style="font-family:IBM Plex Mono;font-size:9px;color:#4d9fff;letter-spacing:2px;margin-bottom:8px;">{label}</div>', unsafe_allow_html=True)
                for nom, val, diff_pct, sig in data:
                    color = "#00C853" if sig == "bullish" else "#FF3B30"
                    arrow = "▲" if sig == "bullish" else "▼"
                    st.markdown(f"""
                    <div style='background:#0a0a0a;border:1px solid #1a1a1a;border-radius:6px;
                                padding:8px 12px;margin-bottom:4px;display:flex;
                                justify-content:space-between;align-items:center;'>
                        <span style='font-family:IBM Plex Mono;font-size:11px;color:#aaa;'>{nom}</span>
                        <span style='font-family:IBM Plex Mono;font-size:11px;color:#666;'>{val:.2f}</span>
                        <span style='font-family:IBM Plex Mono;font-size:12px;font-weight:700;color:{color};'>{arrow} {diff_pct:+.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)

# ══════════════════════════════════════════
#  4. ÉCART JOURNALIER
# ══════════════════════════════════════════
def _ecart_journalier(ticker: str):
    st.markdown('<div class="bar-section">ÉCART JOURNALIER</div>', unsafe_allow_html=True)

    df = _fetch(ticker, "3mo")
    if df.empty:
        st.error("Données indisponibles.")
        return

    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    open_ = df["Open"].squeeze()

    price     = float(close.iloc[-1])
    prev_close= float(close.iloc[-2]) if len(close) > 1 else price
    day_open  = float(open_.iloc[-1])
    day_high  = float(high.iloc[-1])
    day_low   = float(low.iloc[-1])

    chg_abs   = price - prev_close
    chg_pct   = (chg_abs / prev_close) * 100 if prev_close else 0
    day_range = day_high - day_low
    pos_in_range = ((price - day_low) / day_range * 100) if day_range > 0 else 50

    # ATR moyen
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr14 = float(tr.rolling(14).mean().iloc[-1])
    atr_pct = (atr14 / price) * 100

    # Volatilité historique 20j
    log_ret = np.log(close / close.shift(1)).dropna()
    vol20 = float(log_ret.rolling(20).std().iloc[-1] * np.sqrt(252) * 100)

    # Cards
    c1, c2, c3, c4 = st.columns(4)
    color_chg = "#00C853" if chg_abs >= 0 else "#FF3B30"
    arrow = "▲" if chg_abs >= 0 else "▼"

    def _card(col, label, value, color="#ff6600", sub=None):
        with col:
            sub_html = f'<div style="font-size:10px;color:#555;margin-top:4px;">{sub}</div>' if sub else ""
            st.markdown(f"""
            <div class="ecart-item">
                <div class="ecart-label">{label}</div>
                <div class="ecart-val" style="color:{color};">{value}</div>
                {sub_html}
            </div>""", unsafe_allow_html=True)

    _card(c1, "VARIATION JOUR",    f"{arrow} {chg_abs:+.2f}", color_chg, f"{chg_pct:+.2f}%")
    _card(c2, "RANGE JOURNALIER",  f"{day_range:.2f}", "#ff6600", f"H:{day_high:.2f} | B:{day_low:.2f}")
    _card(c3, "ATR 14 JOURS",      f"{atr14:.2f}", "#4d9fff", f"{atr_pct:.1f}% du prix")
    _card(c4, "VOLATILITÉ 20J",    f"{vol20:.1f}%", "#FF9800", "Annualisée")

    # Barre position dans le range
    st.markdown(f"""
    <div style='background:#0a0a0a;border:1px solid #1a1a1a;border-radius:8px;padding:16px;margin-top:8px;'>
        <div style='font-family:IBM Plex Mono;font-size:9px;color:#4d9fff;letter-spacing:2px;margin-bottom:10px;'>POSITION DANS LE RANGE JOURNALIER</div>
        <div style='display:flex;justify-content:space-between;font-family:IBM Plex Mono;font-size:10px;color:#555;margin-bottom:6px;'>
            <span>BAS {day_low:.2f}</span><span>HAUT {day_high:.2f}</span>
        </div>
        <div style='background:#1a1a1a;border-radius:4px;height:10px;position:relative;'>
            <div style='background:#ff6600;width:{pos_in_range:.1f}%;height:100%;border-radius:4px;'></div>
        </div>
        <div style='font-family:IBM Plex Mono;font-size:10px;color:#ff6600;text-align:center;margin-top:6px;'>
            {price:.2f} — {pos_in_range:.0f}% du range
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Graphique range 30j
    df30 = df.tail(30).copy()
    fig = go.Figure()
    colors_bar = ["#00C853" if c >= o else "#FF3B30" for c, o in zip(df30["Close"].squeeze(), df30["Open"].squeeze())]
    fig.add_trace(go.Candlestick(
        x=df30.index, open=df30["Open"].squeeze(), high=df30["High"].squeeze(),
        low=df30["Low"].squeeze(), close=df30["Close"].squeeze(),
        increasing_line_color="#00C853", decreasing_line_color="#FF3B30",
        name="Prix"
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#050505",
        margin=dict(l=10,r=10,t=30,b=10), height=200,
        xaxis=dict(showgrid=False, color="#444"), yaxis=dict(showgrid=True, gridcolor="#111", color="#444"),
        showlegend=False, title=dict(text="RANGE 30 DERNIERS JOURS", font=dict(size=10,color="#555",family="IBM Plex Mono")),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════
#  5. ÉCART 52 SEMAINES
# ══════════════════════════════════════════
def _ecart_52sem(ticker: str):
    st.markdown('<div class="bar-section">ÉCART 52 SEMAINES</div>', unsafe_allow_html=True)

    df = _fetch(ticker, "1y")
    if df.empty:
        st.error("Données indisponibles.")
        return

    close = df["Close"].squeeze()
    price = float(close.iloc[-1])

    high52 = float(close.max())
    low52  = float(close.min())
    mean52 = float(close.mean())
    med52  = float(close.median())

    ecart_high = (price - high52) / high52 * 100
    ecart_low  = (price - low52)  / low52  * 100
    ecart_mean = (price - mean52) / mean52 * 100
    pos_52 = (price - low52) / (high52 - low52) * 100 if (high52 - low52) > 0 else 50

    # Performance 52 semaines
    perf_52 = (price / float(close.iloc[0]) - 1) * 100 if len(close) > 1 else 0
    perf_6m  = (price / float(close.iloc[len(close)//2] if len(close) > 2 else close.iloc[0]) - 1) * 100
    perf_1m  = (price / float(close.iloc[-22]) - 1) * 100 if len(close) >= 22 else 0
    perf_1w  = (price / float(close.iloc[-5])  - 1) * 100 if len(close) >= 5  else 0

    c1, c2, c3, c4 = st.columns(4)
    def _card52(col, label, val, color, sub=None):
        with col:
            sub_html = f'<div style="font-size:10px;color:#555;margin-top:4px;">{sub}</div>' if sub else ""
            st.markdown(f'<div class="ecart-item"><div class="ecart-label">{label}</div><div class="ecart-val" style="color:{color};">{val}</div>{sub_html}</div>', unsafe_allow_html=True)

    _card52(c1, "PLUS HAUT 52 SEM", f"{high52:.2f}", "#FF3B30", f"{ecart_high:+.1f}% vs actuel")
    _card52(c2, "PLUS BAS 52 SEM",  f"{low52:.2f}",  "#00C853", f"{ecart_low:+.1f}% vs actuel")
    _card52(c3, "MOYENNE 52 SEM",   f"{mean52:.2f}", "#FF9800", f"{ecart_mean:+.1f}% vs actuel")
    _card52(c4, "POSITION 52 SEM",  f"{pos_52:.0f}%","#4d9fff", "du range annuel")

    # Barre de position 52 semaines
    st.markdown(f"""
    <div style='background:#0a0a0a;border:1px solid #1a1a1a;border-radius:8px;padding:16px;margin:8px 0;'>
        <div style='font-family:IBM Plex Mono;font-size:9px;color:#4d9fff;letter-spacing:2px;margin-bottom:10px;'>POSITION DANS LE RANGE 52 SEMAINES</div>
        <div style='display:flex;justify-content:space-between;font-family:IBM Plex Mono;font-size:10px;color:#555;margin-bottom:6px;'>
            <span>🟢 BAS {low52:.2f}</span>
            <span style='color:#FF9800;'>MOY {mean52:.2f}</span>
            <span>🔴 HAUT {high52:.2f}</span>
        </div>
        <div style='background:#1a1a1a;border-radius:4px;height:12px;position:relative;'>
            <div style='background:linear-gradient(90deg,#00C853,#FF9800,#FF3B30);width:100%;height:100%;border-radius:4px;opacity:0.3;position:absolute;'></div>
            <div style='background:#ff6600;width:3px;height:100%;border-radius:4px;position:absolute;left:{pos_52:.1f}%;'></div>
        </div>
        <div style='font-family:IBM Plex Mono;font-size:11px;color:#ff6600;text-align:center;margin-top:8px;font-weight:700;'>
            {price:.2f} — {pos_52:.0f}% du range annuel
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Performances
    st.markdown("**Performances sur différentes périodes :**")
    perfs = [("1 SEMAINE", perf_1w), ("1 MOIS", perf_1m), ("6 MOIS", perf_6m), ("52 SEMAINES", perf_52)]
    cols = st.columns(4)
    for col, (label, perf) in zip(cols, perfs):
        with col:
            color = "#00C853" if perf >= 0 else "#FF3B30"
            arrow = "▲" if perf >= 0 else "▼"
            st.markdown(f"""
            <div class="ecart-item" style="text-align:center;">
                <div class="ecart-label">{label}</div>
                <div style="font-size:20px;font-weight:700;color:{color};">{arrow} {perf:+.1f}%</div>
            </div>""", unsafe_allow_html=True)

    # Graphique 52 semaines avec high/low
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=close, mode="lines",
        line=dict(color="#ff6600", width=1.5), name="Prix", fill="tozeroy",
        fillcolor="rgba(255,102,0,0.05)"
    ))
    fig.add_hline(y=high52, line=dict(color="#FF3B30", width=1, dash="dot"), annotation_text=f"52W HIGH {high52:.2f}", annotation_font_color="#FF3B30")
    fig.add_hline(y=low52,  line=dict(color="#00C853", width=1, dash="dot"), annotation_text=f"52W LOW {low52:.2f}",  annotation_font_color="#00C853")
    fig.add_hline(y=mean52, line=dict(color="#FF9800", width=1, dash="dot"), annotation_text=f"MEAN {mean52:.2f}",    annotation_font_color="#FF9800")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#050505",
        margin=dict(l=10,r=80,t=10,b=10), height=250,
        xaxis=dict(showgrid=False, color="#444"), yaxis=dict(showgrid=True, gridcolor="#111", color="#444"),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ══════════════════════════════════════════
#  6. HISTORIQUE VARIATIONS
# ══════════════════════════════════════════
def _historique_variations(ticker: str):
    st.markdown('<div class="bar-section">HISTORIQUE DES VARIATIONS</div>', unsafe_allow_html=True)

    df = _fetch(ticker, "1y")
    if df.empty:
        st.error("Données indisponibles.")
        return

    close = df["Close"].squeeze()
    returns = close.pct_change().dropna() * 100

    # Stats
    mean_ret = float(returns.mean())
    std_ret  = float(returns.std())
    max_gain = float(returns.max())
    max_loss = float(returns.min())
    pos_days = int((returns > 0).sum())
    neg_days = int((returns < 0).sum())
    win_rate = pos_days / len(returns) * 100

    c1, c2, c3, c4 = st.columns(4)
    def _card_hist(col, label, val, color, sub=None):
        with col:
            sub_html = f'<div style="font-size:10px;color:#555;margin-top:4px;">{sub}</div>' if sub else ""
            st.markdown(f'<div class="ecart-item"><div class="ecart-label">{label}</div><div class="ecart-val" style="color:{color};">{val}</div>{sub_html}</div>', unsafe_allow_html=True)

    _card_hist(c1, "TAUX DE JOURS HAUSSIERS", f"{win_rate:.0f}%", "#00C853", f"{pos_days}j↑ vs {neg_days}j↓")
    _card_hist(c2, "VARIATION MOY. JOURNALIÈRE", f"{mean_ret:+.2f}%", "#FF9800", f"σ = {std_ret:.2f}%")
    _card_hist(c3, "MEILLEURE SÉANCE",          f"+{max_gain:.2f}%", "#00C853", "52 semaines")
    _card_hist(c4, "PIRE SÉANCE",               f"{max_loss:.2f}%",  "#FF3B30", "52 semaines")

    # Distribution des variations
    fig_dist = go.Figure()
    colors_hist = ["#00C853" if x >= 0 else "#FF3B30" for x in returns]
    fig_dist.add_trace(go.Histogram(
        x=returns, nbinsx=50,
        marker_color=["#00C853" if x >= 0 else "#FF3B30" for x in returns],
        opacity=0.8, name="Distribution"
    ))
    fig_dist.add_vline(x=0, line=dict(color="#fff", width=1, dash="dot"))
    fig_dist.add_vline(x=mean_ret, line=dict(color="#FF9800", width=1.5, dash="dash"), annotation_text=f"Moy {mean_ret:+.2f}%", annotation_font_color="#FF9800")
    fig_dist.update_layout(
        title=dict(text="DISTRIBUTION DES VARIATIONS JOURNALIÈRES", font=dict(size=10,color="#555",family="IBM Plex Mono")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#050505",
        margin=dict(l=10,r=10,t=40,b=10), height=200,
        xaxis=dict(showgrid=False, color="#444", title="Variation %"),
        yaxis=dict(showgrid=True, gridcolor="#111", color="#444", title="Fréquence"),
        showlegend=False, bargap=0.05
    )
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    # Calendrier des variations — 30 derniers jours
    st.markdown("**Variations journalières — 30 derniers jours :**")
    ret30 = returns.tail(30)
    dates = [d.strftime("%d/%m") for d in ret30.index]
    vals  = ret30.values
    colors_30 = ["#00C853" if v >= 0 else "#FF3B30" for v in vals]

    fig_bar = go.Figure(go.Bar(
        x=dates, y=vals,
        marker_color=colors_30,
        text=[f"{v:+.1f}%" for v in vals], textposition="outside",
        textfont=dict(size=8, color="#aaa", family="IBM Plex Mono")
    ))
    fig_bar.add_hline(y=0, line=dict(color="#333", width=1))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#050505",
        margin=dict(l=10,r=10,t=10,b=40), height=220,
        xaxis=dict(showgrid=False, color="#444", tickfont=dict(size=8)),
        yaxis=dict(showgrid=True, gridcolor="#111", color="#444"),
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # Meilleures/pires séances
    col_best, col_worst = st.columns(2)
    with col_best:
        st.markdown('<div style="font-family:IBM Plex Mono;font-size:9px;color:#00C853;letter-spacing:2px;margin-bottom:8px;">▲ TOP 5 MEILLEURES SÉANCES</div>', unsafe_allow_html=True)
        for date, val in returns.nlargest(5).items():
            st.markdown(f'<div style="background:#002b00;border:1px solid #00C853;border-radius:6px;padding:8px 12px;margin-bottom:4px;font-family:IBM Plex Mono;font-size:11px;display:flex;justify-content:space-between;"><span style="color:#aaa;">{date.strftime("%d/%m/%Y")}</span><span style="color:#00C853;font-weight:700;">+{val:.2f}%</span></div>', unsafe_allow_html=True)

    with col_worst:
        st.markdown('<div style="font-family:IBM Plex Mono;font-size:9px;color:#FF3B30;letter-spacing:2px;margin-bottom:8px;">▼ TOP 5 PIRES SÉANCES</div>', unsafe_allow_html=True)
        for date, val in returns.nsmallest(5).items():
            st.markdown(f'<div style="background:#2b0000;border:1px solid #FF3B30;border-radius:6px;padding:8px 12px;margin-bottom:4px;font-family:IBM Plex Mono;font-size:11px;display:flex;justify-content:space-between;"><span style="color:#aaa;">{date.strftime("%d/%m/%Y")}</span><span style="color:#FF3B30;font-weight:700;">{val:.2f}%</span></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════
#  INTERFACE PRINCIPALE
# ══════════════════════════════════════════
def show_barometres():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<div class="bar-header">📊 BAROMÈTRES & ANALYSES</div>', unsafe_allow_html=True)
    st.markdown('<div class="bar-sub">SIGNAUX TECHNIQUES · MOYENNES MOBILES · VARIATIONS · STATISTIQUES</div>', unsafe_allow_html=True)

    # ── Ticker input ──
    col_t, col_b, _ = st.columns([2, 1, 3])
    with col_t:
        ticker = st.text_input("TICKER", value="NVDA", placeholder="NVDA, AAPL, BTC-USD...", key="bar_ticker").upper().strip()
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("🔍 ANALYSER", type="primary", use_container_width=True, key="bar_run")

    if not ticker:
        return

    if run or "bar_last_ticker" in st.session_state:
        if run:
            st.session_state.bar_last_ticker = ticker
        ticker = st.session_state.get("bar_last_ticker", ticker)

        st.markdown("---")

        # ── Tabs pour chaque outil ──
        tabs = st.tabs([
            "🎯 Baromètre Achat",
            "📐 Indicateurs Techniques",
            "📉 Moyennes Mobiles",
            "📊 Écart Journalier",
            "📅 Écart 52 Sem.",
            "📈 Historique Variations",
        ])

        with tabs[0]:
            _barometre_achat(ticker)
        with tabs[1]:
            _barometre_indicateurs(ticker)
        with tabs[2]:
            _barometre_mm(ticker)
        with tabs[3]:
            _ecart_journalier(ticker)
        with tabs[4]:
            _ecart_52sem(ticker)
        with tabs[5]:
            _historique_variations(ticker)
