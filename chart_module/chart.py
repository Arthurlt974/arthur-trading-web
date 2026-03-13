import json
from .data import fetch_ohlcv
from .config import (
    DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_LIMIT,
    CHART_HEIGHT, VOLUME_HEIGHT, BOTTOM_BAR_H, COLORS
)


def render_chart(
    symbol: str       = DEFAULT_SYMBOL,
    interval: str     = DEFAULT_INTERVAL,
    limit: int        = DEFAULT_LIMIT,
    height: int       = 700,
    show_header: bool = True,   # afficher le header avec prix/OHLC
    show_volume: bool = True,   # afficher le panneau volume
    show_bottom: bool = True,   # afficher la barre du bas (24H stats)
    pair_label: str   = None,   # label affiché (ex: "BTC/USDT")
    exchange: str     = "Binance · Spot",  # source affichée
    live_sim: bool    = True,   # simulation si pas de données live
    show_ma: bool     = True,   # afficher MA20/50/200
    show_bb: bool     = False,  # afficher Bollinger Bands
    default_tf: str   = None,   # timeframe actif par défaut (ex: "4h")
) -> str:

    from .config import COINGECKO_IDS, DATA_SOURCE

    try:
        candles, is_live = fetch_ohlcv(symbol=symbol, interval=interval, limit=limit)
    except Exception as e:
        print(f"[chart_module] Erreur fetch ({symbol} {interval}): {e}")
        candles, is_live = [], False

    # ── Quant : calibration Merton depuis l'historique ──────
    try:
        from .quant.monte_carlo import estimate_params
        closes_list: list = []
        for c in (candles or []):
            if isinstance(c, dict):
                closes_list.append(float(c.get('close', c.get('c', 0)) or 0))
            elif isinstance(c, (list, tuple)) and len(c) >= 5:
                closes_list.append(float(c[4] or 0))
        mp       = estimate_params(closes_list, freq=interval.lower())
        mc_mu    = round(mp['mu']    * 100, 2)   # dérive annualisée en %
        mc_sigma = round(mp['sigma'] * 100, 2)   # vol annualisée en %
    except Exception:
        mc_mu, mc_sigma = 50.0, 80.0

    # ── Quant : Kelly Criterion depuis l'historique ──────────
    try:
        from kelly import kelly_full_analysis
        kp = kelly_full_analysis(
            closes   = closes_list,
            capital  = 10_000.0,
            freq     = interval.lower(),
            fraction = 0.5,
        )
    except Exception:
        kp = {
            "kelly_win_rate":      50.0,
            "kelly_ratio_wl":      1.50,
            "kelly_n_candles":     0,
            "kelly_reliable":      "0",
            "kelly_edge_pct":      0.0,
            "kelly_ruin_risk_pct": 100.0,
            "kelly_mu_pct":        50.0,
            "kelly_sigma_pct":     80.0,
            "kelly_sharpe":        0.0,
            "kelly_f_full":        0.0,
            "kelly_f_half":        0.0,
            "kelly_f_quarter":     0.0,
            "kelly_f_pct":         0.0,
            "kelly_pos_size":      0.0,
            "kelly_capital":       10000.0,
        }

    # ── Affichage du nom de la paire ──
    pair_disp = pair_label or (
        symbol.upper() + "/USD"
        if symbol.lower() in ["bitcoin","ethereum","solana","dogecoin","cardano",
                               "ripple","polkadot","avalanche-2","chainlink",
                               "litecoin","cosmos","near","uniswap","binancecoin","matic-network"]
        else symbol.replace("USDT","/USDT").replace("-USD","/USD")
    )

    # ── ID CoinGecko (pour fallback prix live) ──
    _s = symbol.upper().replace("USDT","").replace("USD","").replace("-","")
    coingecko_id = COINGECKO_IDS.get(_s, symbol.lower())

    # ── Symbol Binance (pour WebSocket) ──
    _sym_up = symbol.upper().replace("-","").replace("/","")
    binance_symbol = _sym_up if _sym_up.endswith("USDT") or _sym_up.endswith("BUSD") else _sym_up + "USDT"

    # ── Exchange affiché selon source ──
    src_labels = {
        "binance":   "Binance · Spot",
        "bybit":     "Bybit · Spot",
        "coingecko": "CoinGecko · Spot",
        "yfinance":  "Yahoo Finance",
        "kraken":    "Kraken · Spot",
        "mock":      "Simulation",
    }
    if exchange == "Binance · Spot":  # valeur par défaut → auto-detect
        exchange = src_labels.get(DATA_SOURCE.lower(), DATA_SOURCE)

    # ── Timeframe actif par défaut ──
    active_tf = default_tf or interval.lower()

    c          = COLORS
    cd         = json.dumps(candles)
    n_candles  = len(candles)
    status_txt = "● LIVE" if is_live else "◎ SIM"
    status_cls = "live"   if is_live else "sim"
    run_sim    = "true"   if (not is_live and live_sim) else "false"

    # ── Visibilité des sections ──
    hdr_display  = "flex"   if show_header else "none"
    bbar_display = "flex"   if show_bottom else "none"
    vol_init_js  = "true"   if show_volume else "false"
    ma_init_js   = "true"   if show_ma     else "false"
    bb_init_js   = "true"   if show_bb     else "false"

    data_info = (
        f"{DATA_SOURCE.upper()} · {n_candles} bougies · LIVE"
        if is_live else
        f"MOCK · {n_candles} bougies ({DATA_SOURCE} indisponible)"
    )

    iv_sec = {
        "1m":60,"5m":300,"15m":900,"30m":1800,
        "1h":3600,"4h":14400,"1d":86400,"1w":604800
    }.get(interval.lower(), 14400)

    # ── Classes CSS pré-calculées (évite les f-strings imbriquées) ──
    def _tf(tf):
        return "tf-btn active" if active_tf == tf else "tf-btn"

    cls_1m  = _tf("1m");  cls_5m  = _tf("5m");  cls_15m = _tf("15m")
    cls_1h  = _tf("1h");  cls_4h  = _tf("4h");  cls_1d  = _tf("1d");  cls_1w  = _tf("1w")
    cls_ma  = "indicator-btn on" if show_ma     else "indicator-btn"
    cls_vol = "indicator-btn on" if show_volume else "indicator-btn"
    cls_bb  = "indicator-btn on" if show_bb     else "indicator-btn"
    cls_gc  = "indicator-btn"
    cls_ob  = "indicator-btn"

    # ── Dépaquetage Kelly pour le f-string (évite NameError sur kp[key]) ──
    kelly_win_rate      = kp["kelly_win_rate"]
    kelly_ratio_wl      = kp["kelly_ratio_wl"]
    kelly_n_candles     = kp["kelly_n_candles"]
    kelly_mu_pct        = kp["kelly_mu_pct"]
    kelly_sigma_pct     = kp["kelly_sigma_pct"]
    kelly_capital       = kp["kelly_capital"]
    kelly_f_full        = kp["kelly_f_full"]
    kelly_f_half        = kp["kelly_f_half"]
    kelly_f_quarter     = kp["kelly_f_quarter"]
    kelly_f_pct         = kp["kelly_f_pct"]
    kelly_pos_size      = kp["kelly_pos_size"]
    kelly_edge_pct      = kp["kelly_edge_pct"]
    kelly_ruin_risk_pct = kp["kelly_ruin_risk_pct"]
    kelly_sharpe        = kp["kelly_sharpe"]

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@700&display=swap');
:root{{
  --bg:#000000;--surface:#0a0a0a;--surface2:#111111;
  --border:#1a1a1a;--border2:#1e1e1e;
  --text:#e8e8e8;--text2:#4d9fff;--muted:#4d9fff;
  --faint:#4d9fff;--fainter:#1e1e1e;
  --orange:#ff6600;--yellow:#ffcc00;
  --green:#00ff41;--green2:#00cc33;
  --red:#ff2222;--red2:#cc0000;
  --bull:#00ff41;--bear:#ff2222;
  --bull-bg:rgba(0,255,65,0.08);--bear-bg:rgba(255,34,34,0.08);
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{
  background:var(--bg);color:var(--text);
  font-family:'Share Tech Mono',monospace;font-size:12px;
  width:100%;height:100vh;overflow:hidden;display:flex;flex-direction:column;
}}

/* ── HEADER ── */
.hdr{{display:flex;align-items:center;background:var(--surface);
  border-bottom:1px solid var(--border2);height:46px;padding:0 12px;gap:0;flex-shrink:0;}}
.logo{{font-weight:700;font-size:12px;letter-spacing:2px;color:var(--orange);
  padding-right:14px;border-right:1px solid var(--border2);margin-right:14px;white-space:nowrap;}}
.pair{{font-size:15px;font-weight:700;color:var(--text);letter-spacing:0.5px;margin-right:8px;}}
.exch{{font-size:9px;color:var(--faint);letter-spacing:1px;margin-right:16px;}}
.price-big{{font-size:20px;font-weight:700;letter-spacing:-0.5px;transition:color .15s;margin-right:6px;}}
.price-chg{{font-size:11px;padding:2px 7px;border-radius:3px;font-weight:600;margin-right:16px;}}
.price-chg.up{{background:rgba(38,166,154,0.15);color:var(--bull);}}
.price-chg.dn{{background:rgba(239,83,80,0.15);color:var(--bear);}}
.ohlc-row{{display:flex;gap:16px;align-items:center;}}
.ohlc-item{{display:flex;flex-direction:column;gap:1px;}}
.ohlc-lbl{{font-size:8px;color:var(--faint);letter-spacing:1px;text-transform:uppercase;}}
.ohlc-val{{font-size:11px;font-weight:600;}}
.hdr-right{{margin-left:auto;display:flex;align-items:center;gap:12px;}}
.live-badge{{font-size:9px;padding:2px 8px;border-radius:2px;letter-spacing:1px;font-weight:700;}}
.live-badge.live{{color:#00e676;background:rgba(0,230,118,0.08);border:1px solid rgba(0,230,118,0.3);animation:pulse 1.5s infinite;}}
.live-badge.sim{{color:var(--orange);background:rgba(255,152,0,0.08);border:1px solid rgba(255,152,0,0.3);}}
@keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:0.4;}}}}

/* ── TOOLBAR (timeframes) ── */
.toolbar{{display:flex;align-items:center;background:var(--surface);
  border-bottom:1px solid var(--border2);height:34px;padding:0 8px;gap:2px;flex-shrink:0;}}
.tf-btn{{padding:3px 9px;border:none;background:transparent;color:var(--muted);
  font-family:'Share Tech Mono',monospace;font-size:11px;font-weight:600;cursor:pointer;
  border-radius:3px;transition:all .1s;text-transform:uppercase;letter-spacing:0.5px;}}
.tf-btn:hover{{background:var(--surface2);color:var(--text);}}
.tf-btn.active{{background:rgba(255,152,0,0.12);color:var(--orange);}}
.tb-sep{{width:1px;height:18px;background:var(--border2);margin:0 4px;}}
.indicator-btn{{padding:3px 9px;border:1px solid var(--border2);background:transparent;
  color:var(--muted);font-family:'Share Tech Mono',monospace;font-size:10px;cursor:pointer;
  border-radius:3px;transition:all .1s;}}
.indicator-btn:hover{{background:var(--surface2);color:var(--text);}}
.indicator-btn.on{{color:var(--orange);border-color:rgba(255,152,0,0.4);}}


/* ── DRAWING TOOLBAR ── */
.draw-toolbar{{
  width:36px;flex-shrink:0;background:var(--surface);
  border-right:1px solid var(--border2);
  display:flex;flex-direction:column;align-items:center;
  padding:6px 0;gap:2px;z-index:10;
}}
.draw-btn{{
  width:26px;height:26px;background:transparent;border:none;
  color:var(--muted);font-size:13px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  border-radius:3px;transition:all .1s;
}}
.draw-btn:hover{{background:var(--surface2);color:var(--text);}}
.draw-btn.active{{background:rgba(255,152,0,0.15);color:var(--orange);}}
.draw-sep{{width:20px;height:1px;background:var(--border2);margin:2px 0;}}


/* ── FULLSCREEN BUTTON ── */
.fs-btn{{
  width:28px;height:28px;border:1px solid #1e1e1e;
  background:transparent;color:#4d9fff;
  font-size:13px;cursor:pointer;border-radius:4px;
  display:flex;align-items:center;justify-content:center;
  transition:all .15s;flex-shrink:0;
}}
.fs-btn:hover{{background:rgba(77,159,255,0.1);border-color:#4d9fff;}}
body.is-fullscreen .fs-btn{{color:#ff6600;border-color:rgba(255,102,0,0.4);}}
/* En fullscreen : on prend tout l'écran */
body.is-fullscreen{{
  position:fixed;top:0;left:0;width:100vw;height:100vh;
  z-index:99999;background:#000;
}}

/* ── CHART ZONE ── */
.chart-zone{{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden;}}
#cvMain{{display:block;cursor:crosshair;}}
.vol-sep{{height:1px;background:var(--border);flex-shrink:0;}}
#cvVol{{display:block;background:var(--bg);flex-shrink:0;}}


/* ════ MONTE CARLO PANEL ════ */
.mc-panel {{
  flex-shrink: 0;
  display: none;
  flex-direction: column;
  background: #000;
  position: relative;
}}
.mc-panel.open {{ display: flex; }}

/* Resize handle */
.mc-resize-bar {{
  height: 5px;
  background: #0D0D0D;
  border-top: 1px solid #1A1A1A;
  cursor: ns-resize;
  flex-shrink: 0;
  transition: background .15s;
  display: flex; align-items: center; justify-content: center;
}}
.mc-resize-bar:hover {{ background: rgba(250,190,44,0.15); }}
.mc-resize-bar::after {{
  content: '⋯'; color: #333; font-size: 10px; pointer-events: none;
}}

/* Top bar */
.mc-bar {{
  height: 30px;
  background: #050505;
  border-top: 1px solid #1E1E1E;
  border-bottom: 1px solid #161616;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 0;
}}
.mc-bar-title {{
  font-family: 'Rajdhani', sans-serif;
  font-weight: 700; font-size: 10px; letter-spacing: 2px;
  color: #FABE2C;
  padding: 0 12px;
  border-right: 1px solid #1E1E1E;
  height: 100%; display: flex; align-items: center; gap: 5px;
}}
.mc-tab {{
  padding: 0 13px; height: 100%;
  background: transparent; border: none;
  border-right: 1px solid #161616;
  font-family: 'Share Tech Mono', monospace;
  font-size: 9px; letter-spacing: 1px;
  color: #555; cursor: pointer;
  transition: all .15s; text-transform: uppercase;
  display: flex; align-items: center; gap: 5px;
}}
.mc-tab:hover {{ color: #999; background: #0A0A0A; }}
.mc-tab.active {{ color: #FABE2C; background: rgba(250,190,44,0.05); }}
.mc-tab-dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; opacity: 0.8;
}}
.mc-params {{
  display: flex; align-items: center;
  margin-left: auto; height: 100%;
  border-left: 1px solid #161616;
}}
.mc-param-group {{
  display: flex; align-items: center; gap: 4px;
  padding: 0 9px; height: 100%;
  border-right: 1px solid #161616;
}}
.mc-param-lbl {{
  font-size: 8px; color: #444;
  letter-spacing: .5px; text-transform: uppercase;
  white-space: nowrap;
}}
.mc-param-inp {{
  width: 36px; padding: 2px 4px;
  background: #111; border: 1px solid #222;
  color: #bbb; font-family: 'Share Tech Mono', monospace;
  font-size: 9px; text-align: center;
  outline: none;
}}
.mc-param-inp:focus {{ border-color: rgba(250,190,44,0.4); }}
.mc-run {{
  padding: 0 13px; height: 100%;
  background: rgba(250,190,44,0.07);
  border: none; border-right: 1px solid rgba(250,190,44,0.2);
  color: #FABE2C; font-family: 'Share Tech Mono', monospace;
  font-size: 9px; letter-spacing: 1px;
  cursor: pointer; transition: all .15s; white-space: nowrap;
}}
.mc-run:hover {{ background: rgba(250,190,44,0.15); }}
.mc-close {{
  padding: 0 11px; height: 100%;
  background: transparent; border: none;
  color: #333; cursor: pointer; font-size: 13px;
  transition: color .12s;
}}
.mc-close:hover {{ color: #888; }}

/* Canvas wrap */
.mc-canvas-wrap {{
  flex: 1; overflow: hidden; position: relative;
  background: #000;
}}

/* Stats footer */
.mc-stats {{
  height: 22px; flex-shrink: 0;
  background: #030303;
  border-top: 1px solid #141414;
  display: flex; align-items: center;
}}
.mc-stat {{
  display: flex; align-items: center; gap: 5px;
  padding: 0 11px; height: 100%;
  border-right: 1px solid #111;
}}
.mc-stat-k {{
  font-size: 7px; letter-spacing: .5px;
  color: #3A3A3A; text-transform: uppercase;
}}
.mc-stat-v {{
  font-family: 'Share Tech Mono', monospace;
  font-size: 9px; font-weight: 700;
}}
/* ── TOOLTIP FLOTTANT ── */
#tooltip{{
  position:fixed;pointer-events:none;z-index:9999;
  background:var(--surface);border:1px solid var(--border2);
  padding:8px 12px;border-radius:4px;font-size:10px;
  box-shadow:0 4px 16px rgba(0,0,0,0.6);display:none;
  min-width:160px;
}}
#tooltip .tt-date{{color:var(--muted);font-size:9px;margin-bottom:6px;letter-spacing:1px;}}
#tooltip .tt-row{{display:flex;justify-content:space-between;gap:16px;margin:2px 0;}}
#tooltip .tt-lbl{{color:var(--faint);font-size:9px;}}
#tooltip .tt-val{{font-weight:600;font-size:10px;}}

/* ── BOTTOM BAR ── */
.bbar{{display:flex;background:var(--surface);border-top:1px solid var(--border2);
  height:36px;flex-shrink:0;}}
.bstat{{flex:1;padding:0 14px;border-right:1px solid var(--border);
  display:flex;align-items:center;gap:8px;}}
.bstat:last-child{{border-right:none;}}
.bstat .lbl{{font-size:8px;color:var(--faint);letter-spacing:1px;text-transform:uppercase;}}
.bstat .val{{font-size:12px;font-weight:700;}}

::-webkit-scrollbar{{width:4px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:2px;}}

/* ── MAIN LAYOUT ── */
.main{{display:flex;flex:1;overflow:hidden;}}
.chart-zone{{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden;}}
/* Zones invisibles pour curseur sur axes */
.axis-y-zone{{position:absolute;right:0;top:0;bottom:24px;width:72px;cursor:ns-resize;z-index:10;}}
.axis-x-zone{{position:absolute;left:0;right:72px;bottom:0;height:24px;cursor:ew-resize;z-index:10;}}
.axis-reset-btn{{position:absolute;right:74px;bottom:26px;width:14px;height:14px;
  background:#1a1a1a;border:1px solid #2a2a2a;color:#4d9fff;font-size:8px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  border-radius:2px;z-index:20;opacity:0.7;}}
.axis-reset-btn:hover{{opacity:1;color:#ff6600;border-color:#ff6600;}}

/* ── QUANT TOGGLE BUTTON (toolbar) ── */
.qp-toggle-btn{{
  display:none;align-items:center;gap:6px;
  padding:3px 12px;border:1px solid rgba(250,190,44,0.35);
  background:rgba(250,190,44,0.07);color:#FABE2C;
  font-family:'Share Tech Mono',monospace;font-size:10px;
  font-weight:700;letter-spacing:1.5px;cursor:pointer;
  border-radius:3px;transition:all .15s;white-space:nowrap;
}}
.qp-toggle-btn:hover{{background:rgba(250,190,44,0.14);border-color:rgba(250,190,44,0.6);}}
.qp-toggle-btn.qmode{{display:flex;}}

/* ── QUANT PANEL ── */
.quant-panel{{
  width:320px;flex-shrink:0;
  background:var(--surface);
  display:flex;flex-direction:column;
  overflow:hidden;
  border-left:1px solid #2A2A2A;
  height:100%;          /* force bound so qp-tools can scroll */
  min-height:0;
}}
.qp-header{{
  display:flex;align-items:center;
  height:36px;padding:0 12px;
  background:var(--surface2);
  border-bottom:1px solid #2A2A2A;
  gap:8px;flex-shrink:0;
}}
.qp-title{{
  font-family:'Rajdhani',sans-serif;
  font-weight:700;font-size:12px;
  letter-spacing:2px;color:#FABE2C;
}}
.qp-sub{{font-size:8px;color:var(--muted);margin-left:auto;}}
.qp-tabs{{
  display:flex;background:var(--bg);
  border-bottom:1px solid #2A2A2A;flex-shrink:0;
}}
.qp-tab{{
  flex:1;padding:7px 4px;text-align:center;
  font-size:8px;letter-spacing:1px;color:var(--muted);
  cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;
}}
.qp-tab:hover{{color:var(--text2);}}
.qp-tab.active{{color:#FABE2C;border-bottom-color:#FABE2C;background:rgba(250,190,44,0.04);}}
.qp-tools{{
  flex:1;overflow-y:auto;overflow-x:hidden;padding:8px;
  display:flex;flex-direction:column;gap:6px;
  min-height:0;          /* critical: allow flex child to shrink & scroll */
}}
.qp-tools::-webkit-scrollbar{{width:4px;}}
.qp-tools::-webkit-scrollbar-track{{background:#0A0A0A;}}
.qp-tools::-webkit-scrollbar-thumb{{background:#2A2A2A;border-radius:2px;}}
.qp-tools::-webkit-scrollbar-thumb:hover{{background:#3A3A3A;}}
.tool-card{{
  background:var(--surface2);border:1px solid #1A1A1A;
  border-radius:4px;cursor:pointer;transition:all .15s;overflow:hidden;
}}
.tool-card:hover{{border-color:#2A2A2A;background:var(--surface);}}
.tool-card.tc-active{{border-color:rgba(250,190,44,0.4);background:rgba(250,190,44,0.04);}}
.tool-card.tc-running{{border-color:rgba(255,102,0,0.5);}}
.tool-header-q{{
  display:flex;align-items:center;padding:7px 10px;gap:8px;
}}
.tool-icon{{font-size:14px;min-width:20px;text-align:center;}}
.tool-name{{
  font-family:'Rajdhani',sans-serif;font-weight:700;
  font-size:12px;letter-spacing:1px;color:var(--text);flex:1;
}}
.tool-card.tc-active .tool-name{{color:#FABE2C;}}
.tool-card.tc-running .tool-name{{color:var(--orange);}}
.tool-tag{{font-size:7px;padding:1px 5px;border-radius:2px;letter-spacing:0.5px;}}
.tag-risk{{background:rgba(255,34,34,0.12);color:#FF6B6B;border:1px solid rgba(255,34,34,0.2);}}
.tag-sim {{background:rgba(255,102,0,0.12);color:#FF9944;border:1px solid rgba(255,102,0,0.2);}}
.tag-opt {{background:rgba(0,200,83,0.10);color:#00E676;border:1px solid rgba(0,200,83,0.2);}}
.tag-stat{{background:rgba(100,180,255,0.10);color:#64B5F6;border:1px solid rgba(100,180,255,0.2);}}
.tool-body-q{{
  padding:0 10px 10px;display:none;
  flex-direction:column;gap:6px;border-top:1px solid #1A1A1A;
}}
.tool-card.tc-active .tool-body-q{{display:flex;}}
.field-row{{display:flex;gap:6px;align-items:center;}}
.field-lbl{{font-size:8px;color:var(--muted);letter-spacing:0.5px;min-width:72px;}}
.field-inp{{
  flex:1;background:var(--bg);border:1px solid #2A2A2A;
  color:#FF9944;font-family:'Share Tech Mono',monospace;
  font-size:10px;padding:3px 7px;border-radius:2px;outline:none;
}}
.field-inp:focus{{border-color:rgba(255,102,0,0.5);}}
.field-unit{{font-size:8px;color:var(--muted);min-width:28px;}}
.run-btn{{
  margin-top:4px;padding:6px;
  background:rgba(255,102,0,0.12);border:1px solid rgba(255,102,0,0.3);
  color:var(--orange);font-family:'Rajdhani',sans-serif;font-weight:700;
  font-size:11px;letter-spacing:2px;cursor:pointer;border-radius:3px;
  transition:all .15s;text-align:center;
}}
.run-btn:hover{{background:rgba(255,102,0,0.22);border-color:var(--orange);}}
.result-box{{
  background:var(--bg);border:1px solid #2A2A2A;
  border-radius:3px;padding:8px;
  display:flex;flex-direction:column;gap:4px;
}}
.result-row{{display:flex;justify-content:space-between;align-items:center;}}
.result-lbl{{font-size:8px;color:var(--muted);}}
.result-val{{font-size:10px;font-weight:600;}}
.val-green{{color:var(--green);}} .val-red{{color:var(--red);}}
.val-orange{{color:#FF9944;}} .val-yellow{{color:#FABE2C;}}
.result-bar{{height:3px;background:#1A1A1A;border-radius:2px;margin-top:4px;overflow:hidden;}}
.result-bar-fill{{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--orange),#FABE2C);}}

/* ── MODE DROPDOWN ── */
.mode-wrap{{position:relative;margin-left:auto;}}
.mode-btn{{
  display:flex;align-items:center;gap:8px;padding:0 12px;height:34px;
  cursor:pointer;background:transparent;border:none;
  border-left:1px solid var(--border2);
  font-family:'Share Tech Mono',monospace;
  transition:background .12s;
}}
.mode-btn:hover{{background:var(--surface2);}}
.mode-icon{{font-size:13px;color:#ffffff;}}
.mode-info{{display:flex;flex-direction:column;gap:1px;text-align:left;}}
.mode-lbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--text2);}}
.mode-sub{{font-size:8px;color:var(--faint);}}
.mode-caret{{font-size:8px;color:var(--faint);transition:transform .15s;margin-left:4px;}}
.mode-caret.open{{transform:rotate(180deg);}}

/* Couleur selon mode */
.mode-btn[data-mode="normal"] .mode-lbl{{color:var(--text2);}}
.mode-btn[data-mode="pro"]    .mode-lbl{{color:var(--orange);}}
.mode-btn[data-mode="quant"]  .mode-lbl{{color:var(--yellow);}}
.mode-btn[data-mode="normal"] {{border-bottom:none;}}
.mode-btn[data-mode="pro"]    {{border-bottom:none;}}
.mode-btn[data-mode="quant"]  {{border-bottom:none;}}

.mode-dd{{
  display:none;position:absolute;top:100%;right:0;
  background:var(--surface);border:1px solid var(--border2);
  min-width:190px;z-index:9999;
  box-shadow:0 8px 24px rgba(0,0,0,0.7);
}}
.mode-dd.open{{display:block;}}
.mode-opt{{
  display:flex;align-items:center;gap:12px;
  padding:10px 14px;cursor:pointer;
  border-bottom:1px solid var(--border);
  transition:background .1s;
}}
.mode-opt:last-child{{border-bottom:none;}}
.mode-opt:hover{{background:var(--surface2);}}
.mode-opt.active{{background:rgba(255,152,0,0.05);}}
.mo-icon{{font-size:16px;min-width:20px;color:#555;transition:color .15s;}}
.mode-opt.active .mo-icon{{color:#ffffff;}}
.mo-text{{flex:1;}}
.mo-lbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;}}
.mo-desc{{font-size:9px;color:var(--faint);margin-top:2px;}}
.mo-check{{font-size:11px;color:var(--orange);opacity:0;}}
.mode-opt.active .mo-check{{opacity:1;}}
.mo-badge{{font-size:8px;padding:1px 5px;border-radius:2px;letter-spacing:0.5px;
  background:rgba(255,152,0,0.1);color:var(--orange);border:1px solid rgba(255,152,0,0.2);}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr" style="display:{hdr_display}">
  <div class="logo">AM<span style="color:#fff">.</span>TERMINAL</div>
  <div class="pair">{pair_disp}</div>
  <div class="exch">{exchange}</div>
  <div class="live-badge" style="background:rgba(255,152,0,0.08);color:var(--orange);border:1px solid rgba(255,152,0,0.2);font-size:8px;padding:2px 7px;border-radius:2px;letter-spacing:1px;">{DATA_SOURCE.upper()}</div>
  <div class="price-big" id="curPrice">—</div>
  <div class="price-chg up" id="curChg">—</div>
  <div class="ohlc-row">
    <div class="ohlc-item"><div class="ohlc-lbl">O</div><div class="ohlc-val" id="ho">—</div></div>
    <div class="ohlc-item"><div class="ohlc-lbl">H</div><div class="ohlc-val" id="hh" style="color:var(--bull)">—</div></div>
    <div class="ohlc-item"><div class="ohlc-lbl">L</div><div class="ohlc-val" id="hl" style="color:var(--bear)">—</div></div>
    <div class="ohlc-item"><div class="ohlc-lbl">C</div><div class="ohlc-val" id="hc">—</div></div>
  </div>
  <div class="hdr-right">
    <span class="live-badge {status_cls}" id="apiBadge">{status_txt}</span>
  </div>
</div>

<!-- TOOLBAR -->
<div class="toolbar">
  <button class="{cls_1m}" onclick="setTF(this,'1m')">1m</button>
  <button class="{cls_5m}" onclick="setTF(this,'5m')">5m</button>
  <button class="{cls_15m}" onclick="setTF(this,'15m')">15m</button>
  <button class="{cls_1h}" onclick="setTF(this,'1h')">1h</button>
  <button class="{cls_4h}" onclick="setTF(this,'4h')">4h</button>
  <button class="{cls_1d}" onclick="setTF(this,'1d')">1D</button>
  <button class="{cls_1w}" onclick="setTF(this,'1w')">1W</button>
  <div class="tb-sep"></div>
  <button class="{cls_ma}" id="btnMA" onclick="toggleMA()">MA</button>
  <button class="{cls_vol}" id="btnVol" onclick="toggleVol()">Vol</button>
  <button class="{cls_bb}" id="btnBB" onclick="toggleBB()">BB</button>
  <button class="indicator-btn" id="btnRSI" onclick="toggleRSI()">RSI</button>
  <button class="indicator-btn" id="btnMACD" onclick="toggleMACD()">MACD</button>
  <button class="{cls_gc}" id="btnGC" onclick="toggleGC()" title="Gaussian Channel">GC</button>
  <button class="{cls_ob}" id="btnOB" onclick="toggleOB()" title="Order Blocks">OB</button>

  <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
    <button class="fs-btn" id="fsBtn" onclick="toggleFullscreen()" title="Plein écran (F11)" style="height:26px;width:26px;font-size:14px;">⛶</button>
  </div>
  <!-- QUANT TOOLS TOGGLE (visible only in quant mode) -->
  <button class="qp-toggle-btn" id="qpToggleBtn" onclick="toggleQuantPanel()">⚙ QUANT TOOLS ▶</button>

  <!-- MODE DROPDOWN -->
  <div class="mode-wrap">
    <button class="mode-btn" id="modeBtn" data-mode="normal" onclick="toggleModeDD()">
      <span class="mode-icon" id="modeIcon">▣</span>
      <div class="mode-info">
        <div class="mode-lbl" id="modeLbl">Normal</div>
        <div class="mode-sub" id="modeSub">Vue standard</div>
      </div>
      <span class="mode-caret" id="modeCaret">&#9660;</span>
    </button>
    <div class="mode-dd" id="modeDD">
      <div class="mode-opt active" onclick="pickMode('normal','Normal','Vue standard','▣')">
        <span class="mo-icon">▣</span>
        <div class="mo-text">
          <div class="mo-lbl" style="color:var(--text2)">Normal</div>
          <div class="mo-desc">Bougies · MA · Volume</div>
        </div>
        <span class="mo-check">✓</span>
      </div>
      <div class="mode-opt" onclick="pickMode('pro','Pro','Vue avancée','◈')">
        <span class="mo-icon">◈</span>
        <div class="mo-text">
          <div class="mo-lbl" style="color:var(--orange)">Pro</div>
          <div class="mo-desc">Indicateurs avancés · RSI · MACD</div>
        </div>
        <span class="mo-badge">Bientôt</span>
        <span class="mo-check">✓</span>
      </div>
      <div class="mode-opt" onclick="pickMode('quant','Quant','Algorithmique','⬡')">
        <span class="mo-icon">⬡</span>
        <div class="mo-text">
          <div class="mo-lbl" style="color:var(--yellow)">Quant</div>
          <div class="mo-desc">Signaux algo · Patterns · AI</div>
        </div>
        <span class="mo-badge">Bientôt</span>
        <span class="mo-check">✓</span>
      </div>
    </div>
  </div>
</div>

<!-- MAIN = CHART + QUANT PANEL -->
<div class="main" id="mainArea">

<!-- DRAWING TOOLBAR -->
<div class="draw-toolbar" id="drawToolbar">
  <button class="draw-btn active" id="dBtn_cursor" onclick="setDrawTool('cursor')" title="Curseur">&#9654;</button>
  <div class="draw-sep"></div>
  <button class="draw-btn" id="dBtn_line"  onclick="setDrawTool('line')"  title="Ligne de tendance">&#9135;</button>
  <button class="draw-btn" id="dBtn_hline" onclick="setDrawTool('hline')" title="Ligne horizontale">&#8212;</button>
  <button class="draw-btn" id="dBtn_vline" onclick="setDrawTool('vline')" title="Ligne verticale">&#124;</button>
  <button class="draw-btn" id="dBtn_ray"   onclick="setDrawTool('ray')"   title="Rayon">&#8599;</button>
  <div class="draw-sep"></div>
  <button class="draw-btn" id="dBtn_fibo"  onclick="setDrawTool('fibo')"  title="Fibonacci">&#966;</button>
  <button class="draw-btn" id="dBtn_rect"  onclick="setDrawTool('rect')"  title="Rectangle">&#9645;</button>
  <button class="draw-btn" id="dBtn_range" onclick="setDrawTool('range')" title="Intervalle de prix">&#8597;</button>
  <div class="draw-sep"></div>
  <button class="draw-btn" id="dBtn_text"  onclick="setDrawTool('text')"  title="Texte">T</button>
  <div class="draw-sep"></div>
  <button class="draw-btn" id="dBtn_clear" onclick="clearDrawings()"       title="Effacer" style="color:#ff4444;font-size:11px">&#10006;</button>
</div>

<!-- ZONE CHART -->
<div class="chart-zone">
  <canvas id="cvMain"></canvas>
  <!-- Zones de drag axes -->
  <div class="axis-y-zone"  id="axisY"></div>
  <div class="axis-x-zone"  id="axisX"></div>
  <div class="axis-reset-btn" id="axisReset" onclick="resetAxisScale()" title="Réinitialiser le zoom des axes">⊙</div>
  <div class="vol-sep"></div>
  <canvas id="cvVol"></canvas>
  <div class="vol-sep" id="rsiSep" style="display:none"></div>
  <canvas id="cvRSI" style="display:none"></canvas>
  <div class="vol-sep" id="macdSep" style="display:none"></div>
  <canvas id="cvMACD" style="display:none"></canvas>

  <!-- ══ MONTE CARLO PANEL ══ -->
  <div class="mc-panel" id="mcPanel">
    <div class="mc-resize-bar" id="mcResizeBar"></div>
    <div class="mc-bar">
      <div class="mc-bar-title">◈ MONTE CARLO</div>
      <button class="mc-tab active" id="mcTabFan" onclick="mcSetVis('fan')">
        <span class="mc-tab-dot"></span>Fan Chart
      </button>
      <button class="mc-tab" id="mcTabHist" onclick="mcSetVis('histogram')">
        <span class="mc-tab-dot"></span>Distribution
      </button>
      <span id="mcBarInfo" style="margin-left:auto;font-size:8px;color:#444;font-family:'Share Tech Mono',monospace;padding:0 10px;">—</span>
    </div>
    <div class="mc-canvas-wrap" id="mcCanvasWrap">
      <canvas id="cvMC"></canvas>
    </div>
    <div class="mc-stats">
      <div class="mc-stat"><span class="mc-stat-k">Médiane</span><span class="mc-stat-v" id="mcStatMed" style="color:#FABE2C">—</span></div>
      <div class="mc-stat"><span class="mc-stat-k">P95 Haussier</span><span class="mc-stat-v" id="mcStatP95" style="color:#00C853">—</span></div>
      <div class="mc-stat"><span class="mc-stat-k">P5 Baissier</span><span class="mc-stat-v" id="mcStatP5" style="color:#FF3B30">—</span></div>
      <div class="mc-stat"><span class="mc-stat-k">Prob. profit</span><span class="mc-stat-v" id="mcStatProb" style="color:#00C853">—</span></div>
      <div class="mc-stat"><span class="mc-stat-k">VaR 95%</span><span class="mc-stat-v" id="mcStatVar" style="color:#FF3B30">—</span></div>
    </div>
  </div>
</div>

<!-- QUANT PANEL (hidden by default, shown in quant mode) -->
<div class="quant-panel" id="quantPanel" style="display:none">
  <div class="qp-header">
    <span style="color:#FABE2C;font-size:14px">⬡</span>
    <span class="qp-title">QUANT TOOLS</span>
    <span class="qp-sub" id="qpSub">— · —</span>
  </div>
  <div class="qp-tabs">
    <div class="qp-tab active" onclick="switchQTab(this,'risk')">RISK</div>
    <div class="qp-tab" onclick="switchQTab(this,'simul')">SIMUL</div>
    <div class="qp-tab" onclick="switchQTab(this,'optim')">OPTIM</div>
    <div class="qp-tab" onclick="switchQTab(this,'stats')">STATS</div>
  </div>
  <div class="qp-tools">

    <!-- Monte Carlo Merton Jump-Diffusion -->
    <div class="tool-card tc-active" id="tc-montecarlo" data-tab="simul">
      <div class="tool-header-q" onclick="toggleToolCard('tc-montecarlo')">
        <span class="tool-icon">◈</span>
        <span class="tool-name">Monte Carlo · Merton JD</span>
        <span class="tool-tag tag-sim">JUMP DIFF</span>
      </div>
      <div class="tool-body-q">

        <!-- Séparateur paramètres GBM -->
        <div style="font-size:7px;letter-spacing:1.5px;color:#4d9fff;margin:4px 0 2px;border-bottom:1px solid #1a1a1a;padding-bottom:3px;">
          GBM — AUTO-CALIBRÉ <span style="color:#333;font-size:8px;">(modifiable)</span>
        </div>
        <div class="field-row">
          <span class="field-lbl">DÉRIVE μ/AN</span>
          <input class="field-inp" id="mc_mu" value="{mc_mu}" style="max-width:55px">
          <span class="field-unit">%</span>
        </div>
        <div class="field-row">
          <span class="field-lbl">VOL σ/AN</span>
          <input class="field-inp" id="mc_sigma" value="{mc_sigma}" style="max-width:55px">
          <span class="field-unit">%</span>
        </div>

        <!-- Séparateur Merton -->
        <div style="font-size:7px;letter-spacing:1.5px;color:#FABE2C;margin:6px 0 2px;border-bottom:1px solid #1a1a1a;padding-bottom:3px;">MERTON — SAUTS</div>
        <div class="field-row">
          <span class="field-lbl">λ SAUTS/AN</span>
          <input class="field-inp" id="mc_lam" value="3" style="max-width:45px"
            title="Intensité Poisson : nombre moyen de sauts par an">
        </div>
        <div class="field-row">
          <span class="field-lbl">μ_J MOY SAUT</span>
          <input class="field-inp" id="mc_muj" value="-5" style="max-width:45px"
            title="Taille log-moyenne d'un saut (négatif = crash)">
          <span class="field-unit">%</span>
        </div>
        <div class="field-row">
          <span class="field-lbl">σ_J VOL SAUT</span>
          <input class="field-inp" id="mc_sigmaj" value="10" style="max-width:45px"
            title="Dispersion log des sauts">
          <span class="field-unit">%</span>
        </div>

        <!-- Séparateur simulation -->
        <div style="font-size:7px;letter-spacing:1.5px;color:#FF9944;margin:6px 0 2px;border-bottom:1px solid #1a1a1a;padding-bottom:3px;">SIMULATION</div>
        <div class="field-row">
          <span class="field-lbl">HORIZON</span>
          <input class="field-inp" id="mc_horizon" value="90" style="max-width:50px">
          <span class="field-unit">jours</span>
        </div>
        <div class="field-row">
          <span class="field-lbl">SIMULATIONS</span>
          <input class="field-inp" id="mc_nsim" value="5000" style="max-width:60px">
        </div>

        <!-- Sélecteur visualisation -->
        <div style="font-size:7px;letter-spacing:1.5px;color:#FABE2C;margin:8px 0 4px;border-bottom:1px solid #1a1a1a;padding-bottom:3px;">VISUALISATION</div>
        <div style="display:flex;gap:4px;margin-bottom:8px;">
          <div id="mc_vis_fan" onclick="mcSetVis('fan')" style="flex:1;padding:5px 0;text-align:center;font-size:8px;letter-spacing:1px;cursor:pointer;border:1px solid rgba(250,190,44,0.5);background:rgba(250,190,44,0.10);color:#FABE2C;transition:all .15s;">≋ FAN CHART</div>
          <div id="mc_vis_hist" onclick="mcSetVis('histogram')" style="flex:1;padding:5px 0;text-align:center;font-size:8px;letter-spacing:1px;cursor:pointer;border:1px solid #2a2a2a;background:transparent;color:#555;transition:all .15s;">▨ DISTRIBUTION</div>
        </div>

        <!-- Boutons -->
        <div style="display:flex;gap:6px;margin-top:2px;">
          <div class="run-btn" style="flex:1;" id="mc_calc_btn" onclick="runMonteCarlo()">▶ CALCULER</div>
          <div class="run-btn" id="mc_graph_btn" style="flex:1;background:rgba(77,159,255,0.10);border-color:rgba(77,159,255,0.35);color:#4d9fff;" onclick="toggleMCPanel()">↗ GRAPHIQUE</div>
        </div>

        <!-- Résultats -->
        <div class="result-box" id="mc-result-box" style="margin-top:6px;">
          <div style="font-size:7px;color:#666;letter-spacing:1px;margin-bottom:4px;">— RÉSULTATS SIMULATION —</div>
          <div class="result-row"><span class="result-lbl">PRIX ACTUEL S₀</span><span class="result-val" id="mc_r_s0" style="color:#4d9fff;">—</span></div>
          <div class="result-row"><span class="result-lbl">PRIX MOYEN</span><span class="result-val val-orange" id="mc_r_mean">—</span></div>
          <div class="result-row"><span class="result-lbl">MÉDIANE P50</span><span class="result-val val-yellow" id="mc_r_p50">—</span></div>
          <div class="result-row"><span class="result-lbl">P95 HAUSSIER</span><span class="result-val val-green" id="mc_r_p95">—</span></div>
          <div class="result-row"><span class="result-lbl">P5 BAISSIER</span><span class="result-val val-red" id="mc_r_p5">—</span></div>
          <div class="result-row"><span class="result-lbl">PROB. PROFIT</span><span class="result-val" id="mc_r_prob">—</span></div>
          <div class="result-row"><span class="result-lbl">VaR 95% (1J)</span><span class="result-val val-red" id="mc_r_var">—</span></div>
          <div class="result-row"><span class="result-lbl">CVaR 95%</span><span class="result-val val-red" id="mc_r_cvar">—</span></div>
          <div style="font-size:7px;color:#333;margin-top:3px;text-align:right;" id="mc_r_info">cliquer ▶ CALCULER</div>
          <div class="result-bar" style="margin-top:4px;"><div class="result-bar-fill" id="mc_r_bar" style="width:0%"></div></div>
        </div>

      </div>
    </div>

    <!-- VaR / CVaR -->
    <div class="tool-card tc-running" id="tc-var"        data-tab="risk">
      <div class="tool-header-q" onclick="toggleToolCard('tc-var')">
        <span class="tool-icon">▽</span>
        <span class="tool-name">Value at Risk · CVaR</span>
        <span class="tool-tag tag-risk">AVEC LEVIER</span>
      </div>
      <div class="tool-body-q">
        <div class="field-row">
          <span class="field-lbl">CAPITAL</span>
          <input class="field-inp" value="10000" style="max-width:70px">
          <span class="field-unit">USDT</span>
        </div>
        <div class="field-row">
          <span class="field-lbl">LEVIER</span>
          <input class="field-inp" value="3" style="max-width:40px">
          <span class="field-unit">x</span>
        </div>
        <div class="field-row">
          <span class="field-lbl">CONFIANCE</span>
          <input class="field-inp" value="95" style="max-width:40px">
          <span class="field-unit">%</span>
        </div>
        <div class="run-btn" style="background:rgba(255,34,34,0.1);border-color:rgba(255,34,34,0.3);color:#FF6B6B">▶ CALCULER</div>
        <div class="result-box">
          <div class="result-row"><span class="result-lbl">VaR 95% (1J)</span><span class="result-val val-red">-$1,240</span></div>
          <div class="result-row"><span class="result-lbl">CVaR 95%</span><span class="result-val val-red">-$1,890</span></div>
          <div class="result-row"><span class="result-lbl">LIQUIDATION</span><span class="result-val val-red">$0.062 (-33%)</span></div>
        </div>
      </div>
    </div>

    <!-- Kelly Criterion -->
    <div class="tool-card" id="tc-kelly" data-tab="risk">
      <div class="tool-header-q" onclick="toggleToolCard('tc-kelly')">
        <span class="tool-icon">⊛</span>
        <span class="tool-name">Kelly Criterion</span>
        <span class="tool-tag tag-opt">POSITION</span>
      </div>
      <div class="tool-body-q">

        <div style="font-size:7px;letter-spacing:1.5px;color:#4d9fff;margin:4px 0 2px;border-bottom:1px solid #1a1a1a;padding-bottom:3px;">
          AUTO-CALIBRÉ <span style="color:#555;font-size:8px;">{kelly_n_candles} bougies</span>
        </div>

        <!-- Mode tabs -->
        <div style="display:flex;gap:4px;margin-bottom:6px;">
          <div id="kelly_tab_trade" onclick="kellySetMode('trade')"
            style="flex:1;padding:5px 0;text-align:center;font-size:8px;letter-spacing:1px;cursor:pointer;
                   border:1px solid rgba(0,255,65,0.4);background:rgba(0,255,65,0.08);color:#00FF41;transition:all .15s;">
            ◆ TRADE
          </div>
          <div id="kelly_tab_ret" onclick="kellySetMode('rendement')"
            style="flex:1;padding:5px 0;text-align:center;font-size:8px;letter-spacing:1px;cursor:pointer;
                   border:1px solid #2a2a2a;background:transparent;color:#555;transition:all .15s;">
            ∫ RENDEMENT
          </div>
        </div>

        <!-- Inputs Trade -->
        <div id="kelly_inputs_trade">
          <div class="field-row">
            <span class="field-lbl">WIN RATE</span>
            <input class="field-inp" id="kelly_p" value="{kelly_win_rate}" style="max-width:55px" oninput="calcKelly()">
            <span class="field-unit">%</span>
          </div>
          <div class="field-row">
            <span class="field-lbl">RATIO W/L</span>
            <input class="field-inp" id="kelly_b" value="{kelly_ratio_wl}" style="max-width:55px" oninput="calcKelly()">
          </div>
        </div>

        <!-- Inputs Rendement -->
        <div id="kelly_inputs_ret" style="display:none">
          <div class="field-row">
            <span class="field-lbl">DÉRIVE μ/AN</span>
            <input class="field-inp" id="kelly_mu" value="{kelly_mu_pct}" style="max-width:55px" oninput="calcKelly()">
            <span class="field-unit">%</span>
          </div>
          <div class="field-row">
            <span class="field-lbl">VOL σ/AN</span>
            <input class="field-inp" id="kelly_sigma" value="{kelly_sigma_pct}" style="max-width:55px" oninput="calcKelly()">
            <span class="field-unit">%</span>
          </div>
        </div>

        <!-- Capital -->
        <div class="field-row" style="margin-top:4px">
          <span class="field-lbl">CAPITAL</span>
          <input class="field-inp" id="kelly_capital" value="{kelly_capital}" style="max-width:70px" oninput="calcKelly()">
          <span class="field-unit">USDT</span>
        </div>

        <!-- Résultats -->
        <div class="result-box" id="kelly-result-box" style="margin-top:6px;">
          <div style="font-size:7px;color:#666;letter-spacing:1px;margin-bottom:4px;">— FRACTIONS KELLY —</div>
          <div class="result-row">
            <span class="result-lbl">FULL KELLY</span>
            <span class="result-val val-green" id="kelly_r_full">{kelly_f_full}</span>
          </div>
          <div class="result-row">
            <span class="result-lbl">½ KELLY</span>
            <span class="result-val val-orange" id="kelly_r_half">{kelly_f_half}</span>
          </div>
          <div class="result-row">
            <span class="result-lbl">¼ KELLY</span>
            <span class="result-val val-yellow" id="kelly_r_quarter">{kelly_f_quarter}</span>
          </div>
          <div style="font-size:7px;color:#666;letter-spacing:1px;margin:6px 0 4px;">— SIZING (½ KELLY) —</div>
          <div class="result-row">
            <span class="result-lbl">% DU CAPITAL</span>
            <span class="result-val val-green" id="kelly_r_pct">{kelly_f_pct}%</span>
          </div>
          <div class="result-row">
            <span class="result-lbl">TAILLE POSITION</span>
            <span class="result-val val-green" id="kelly_r_size">${{kelly_pos_size}}</span>
          </div>
          <div style="font-size:7px;color:#666;letter-spacing:1px;margin:6px 0 4px;">— RISQUE —</div>
          <div class="result-row">
            <span class="result-lbl">EDGE</span>
            <span class="result-val" id="kelly_r_edge">{kelly_edge_pct}%</span>
          </div>
          <div class="result-row">
            <span class="result-lbl">RISQUE RUINE</span>
            <span class="result-val val-red" id="kelly_r_ruin">{kelly_ruin_risk_pct}%</span>
          </div>
          <div class="result-row">
            <span class="result-lbl">SHARPE</span>
            <span class="result-val" id="kelly_r_sharpe">{kelly_sharpe}</span>
          </div>
        </div>

      </div>
    </div>

    <!-- Sharpe / Sortino -->
    <div class="tool-card" id="tc-sharpe"     data-tab="stats">
      <div class="tool-header-q" onclick="toggleToolCard('tc-sharpe')">
        <span class="tool-icon">∑</span>
        <span class="tool-name">Sharpe · Sortino</span>
        <span class="tool-tag tag-stat">PERF</span>
      </div>
      <div class="tool-body-q">
        <div class="field-row"><span class="field-lbl">PÉRIODE</span><input class="field-inp" value="30" style="max-width:50px"><span class="field-unit">jours</span></div>
        <div class="run-btn" style="background:rgba(100,180,255,0.08);border-color:rgba(100,180,255,0.3);color:#64B5F6">▶ CALCULER</div>
      </div>
    </div>

    <!-- GARCH -->
    <div class="tool-card" id="tc-garch"      data-tab="stats">
      <div class="tool-header-q" onclick="toggleToolCard('tc-garch')">
        <span class="tool-icon">σ</span>
        <span class="tool-name">GARCH Volatility</span>
        <span class="tool-tag tag-stat">VOL MODEL</span>
      </div>
      <div class="tool-body-q">
        <div class="field-row"><span class="field-lbl">FENÊTRE</span><input class="field-inp" value="50" style="max-width:50px"><span class="field-unit">jours</span></div>
        <div class="run-btn" style="background:rgba(100,180,255,0.08);border-color:rgba(100,180,255,0.3);color:#64B5F6">▶ CALCULER</div>
      </div>
    </div>

    <!-- Correlation Matrix -->
    <div class="tool-card" id="tc-corr"       data-tab="stats">
      <div class="tool-header-q" onclick="toggleToolCard('tc-corr')">
        <span class="tool-icon">⊞</span>
        <span class="tool-name">Correlation Matrix</span>
        <span class="tool-tag tag-stat">MULTI-ASSET</span>
      </div>
      <div class="tool-body-q">
        <div class="field-row"><span class="field-lbl">ACTIFS</span><input class="field-inp" value="BTC,ETH,SOL"></div>
        <div class="run-btn" style="background:rgba(100,180,255,0.08);border-color:rgba(100,180,255,0.3);color:#64B5F6">▶ CALCULER</div>
      </div>
    </div>

    <!-- Portfolio Optim -->
    <div class="tool-card" id="tc-portfolio"  data-tab="optim">
      <div class="tool-header-q" onclick="toggleToolCard('tc-portfolio')">
        <span class="tool-icon">◎</span>
        <span class="tool-name">Portfolio Optim.</span>
        <span class="tool-tag tag-opt">MARKOWITZ</span>
      </div>
      <div class="tool-body-q">
        <div class="field-row"><span class="field-lbl">ACTIFS</span><input class="field-inp" value="BTC,ETH,SOL,DOGE"></div>
        <div class="run-btn" style="background:rgba(0,200,83,0.08);border-color:rgba(0,200,83,0.3);color:#00E676">▶ OPTIMISER</div>
      </div>
    </div>

    <!-- ML Predictions -->
    <div class="tool-card" id="tc-ml"         data-tab="simul">
      <div class="tool-header-q" onclick="toggleToolCard('tc-ml')">
        <span class="tool-icon">⬡</span>
        <span class="tool-name">ML Predictions</span>
        <span class="tool-tag tag-sim">BETA</span>
      </div>
      <div class="tool-body-q">
        <div class="field-row"><span class="field-lbl">MODÈLE</span><input class="field-inp" value="LSTM" style="max-width:70px"></div>
        <div class="field-row"><span class="field-lbl">HORIZON</span><input class="field-inp" value="7" style="max-width:50px"><span class="field-unit">jours</span></div>
        <div class="run-btn">▶ PRÉDIRE</div>
      </div>
    </div>

  </div>
</div>

</div><!-- end .main -->

<!-- TOOLTIP -->
<div id="tooltip">
  <div class="tt-date" id="ttDate">—</div>
  <div class="tt-row"><span class="tt-lbl">Open</span><span class="tt-val" id="ttO">—</span></div>
  <div class="tt-row"><span class="tt-lbl">High</span><span class="tt-val" id="ttH" style="color:var(--bull)">—</span></div>
  <div class="tt-row"><span class="tt-lbl">Low</span> <span class="tt-val" id="ttL" style="color:var(--bear)">—</span></div>
  <div class="tt-row"><span class="tt-lbl">Close</span><span class="tt-val" id="ttC">—</span></div>
  <div class="tt-row"><span class="tt-lbl">Vol</span><span class="tt-val" id="ttV" style="color:var(--muted)">—</span></div>
</div>

<!-- BOTTOM BAR -->
<div class="bbar" style="display:{bbar_display}">
  <div class="bstat"><span class="lbl">24H HIGH</span><span class="val" id="b_hi" style="color:var(--bull)">—</span></div>
  <div class="bstat"><span class="lbl">24H LOW</span> <span class="val" id="b_lo" style="color:var(--bear)">—</span></div>
  <div class="bstat"><span class="lbl">CHANGE</span>  <span class="val" id="b_chg">—</span></div>
  <div class="bstat"><span class="lbl">VOLUME</span>  <span class="val" id="b_vol" style="color:var(--muted)">—</span></div>
</div>

<script>
// ════════════════════════════════════════════════════════
//  DONNÉES — chargées 100% depuis Binance en JS
//  (aucune donnée Python injectée pour éviter conflit au reload)
// ════════════════════════════════════════════════════════
const SYMBOL_INIT = '{binance_symbol}';
const IV_INIT     = '{active_tf}';
const IV_SEC      = {iv_sec};

// D démarre VIDE — rempli par fetchInit()
const D = {{ t:[], o:[], h:[], l:[], c:[], v:[] }};

// ════════════════════════════════════════════════════════
//  CONFIG RENDU
// ════════════════════════════════════════════════════════
const PAD  = {{l:0, r:72, t:8, b:24}};

// ── Axis scaling (TradingView style) ──
let PRICE_SCALE  = 1.0;   // multiplicateur zoom vertical (>1 = zoomé)
let PRICE_OFFSET = 0.0;   // décalage vertical en % du range
let TIME_SCALE   = 1.0;   // multiplicateur zoom horizontal (>1 = plus de bougies)

// État drag axes
let axisDrag = null;  // {{type:'y'|'x', startY, startX, startScale, startOffset, startN, startStart}}
const VPAH = 80;   // hauteur volume
let showMA  = {ma_init_js};
let showVol = {vol_init_js};
let showBB   = {bb_init_js};
let showRSI  = false;
let showMACD = false;
const RSI_H  = 80;
const MACD_H = 80;
let showGC  = false;   // Gaussian Channel
let showOB  = false;   // Order Blocks

let VIEW_START = 0, VIEW_END = 0;
let HOVER_IDX  = -1, HOVER_Y = -1;
let isDragging = false, dragStartX = 0, dragStartView = 0;

// ════════════════════════════════════════════════════════
//  SIMULATION
// ════════════════════════════════════════════════════════
let simActive   = false;
let wsConnected = false;
let simPrice    = 100;
let candleStart = Math.floor(Date.now()/1000);
let prevPrice   = 100;
const VOLATILITY = 0.0006;

function simTick() {{
  if(!simActive) return;
  const now = Math.floor(Date.now()/1000);
  const drift    = (Math.random()-0.499)*VOLATILITY;
  const momentum = (simPrice-prevPrice)*0.12;
  const noise    = (Math.random()-0.5)*simPrice*VOLATILITY*0.4;
  prevPrice = simPrice;
  simPrice  = Math.max(simPrice*(1+drift)+momentum+noise, 0.01);

  if(now >= candleStart+IV_SEC) {{
    candleStart = now;
    D.t.push(now); D.o.push(simPrice); D.h.push(simPrice);
    D.l.push(simPrice); D.c.push(simPrice); D.v.push(0);
    if(D.t.length>350){{D.t.shift();D.o.shift();D.h.shift();D.l.shift();D.c.shift();D.v.shift();if(VIEW_START>0)VIEW_START--;}}
    if(VIEW_END>=D.t.length-1) VIEW_END=D.t.length;
  }} else {{
    const i=D.t.length-1;
    D.c[i]=simPrice;
    if(simPrice>D.h[i])D.h[i]=simPrice;
    if(simPrice<D.l[i])D.l[i]=simPrice;
    D.v[i]+=Math.random()*0.3;
  }}
  applyHeaderPrice(simPrice, ((simPrice-D.o[0])/D.o[0]*100));
  render();
}}

// ════════════════════════════════════════════════════════
//  CANVAS
// ════════════════════════════════════════════════════════
const cvMain = document.getElementById('cvMain');
const cvVol  = document.getElementById('cvVol');
const ctxM   = cvMain.getContext('2d');
const ctxV   = cvVol.getContext('2d');
const $      = id => document.getElementById(id);
const setTxt = (id,v) => {{ const e=$(id); if(e) e.textContent=v; }};
const setCol = (id,c) => {{ const e=$(id); if(e) e.style.color=c; }};

const fmt = v => {{
  if(v==null||isNaN(v)) return '—';
  if(v>=10000) return v.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
  if(v>=100)   return v.toFixed(2);
  if(v>=1)     return v.toFixed(4);
  return v.toFixed(6);
}};
const fmtV = v => v>=1e9?(v/1e9).toFixed(2)+'B':v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v.toFixed(0);
const fmtDate = ts => {{
  const d=new Date(ts*1000);
  return d.toLocaleDateString('fr-FR',{{day:'2-digit',month:'short'}})
    +' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
}};

function setupCanvas() {{
  const panelW = (CHART_MODE === 'quant' && quantPanelOpen) ? 320 : 0;
  const W  = (window.innerWidth  || 900) - panelW - 36;
  const fullH = window.innerHeight || 600;
  const hdrH  = 46, tbH = 34, bbarH = 36, sepH = 1;
  const volH  = showVol  ? VPAH   : 0;
  const rsiH  = showRSI  ? RSI_H  : 0;
  const macdH = showMACD ? MACD_H : 0;
  const mcH   = MC_OPEN  ? (MC_HEIGHT + 5) : 0;  // +5 = resize bar
  const extras = volH + rsiH + macdH + (showVol?1:0) + (showRSI?1:0) + (showMACD?1:0);
  const mainH = Math.max(fullH - hdrH - tbH - bbarH - extras - mcH - sepH, 100);

  cvMain.width=W; cvMain.height=mainH;
  cvVol.width=W;  cvVol.height=volH;
  cvMain.style.width=W+'px'; cvMain.style.height=mainH+'px';
  cvVol.style.width=W+'px';  cvVol.style.height=volH+'px';
  cvVol.style.display=showVol?'block':'none';
  document.querySelector('.vol-sep').style.display=showVol?'block':'none';

  const cvR=$('cvRSI'), sepR=$('rsiSep');
  if(cvR){{ cvR.width=W; cvR.height=rsiH; cvR.style.width=W+'px'; cvR.style.height=rsiH+'px'; cvR.style.display=showRSI?'block':'none'; }}
  if(sepR) sepR.style.display=showRSI?'block':'none';

  const cvMC=$('cvMACD'), sepMC=$('macdSep');
  if(cvMC){{ cvMC.width=W; cvMC.height=macdH; cvMC.style.width=W+'px'; cvMC.style.height=macdH+'px'; cvMC.style.display=showMACD?'block':'none'; }}
  if(sepMC) sepMC.style.display=showMACD?'block':'none';
}}

// ── Calcul MA ──
function calcMA(data, period) {{
  const out=[];
  for(let i=0;i<data.length;i++) {{
    if(i<period-1){{out.push(null);continue;}}
    let s=0;for(let j=i-period+1;j<=i;j++) s+=data[j];
    out.push(s/period);
  }}
  return out;
}}

// ── Calcul Bollinger Bands ──
function calcBB(data, period=20, mult=2) {{
  const ma=calcMA(data,period);
  const upper=[],lower=[];
  for(let i=0;i<data.length;i++) {{
    if(ma[i]===null){{upper.push(null);lower.push(null);continue;}}
    let v=0;for(let j=i-period+1;j<=i;j++) v+=Math.pow(data[j]-ma[i],2);
    const sd=Math.sqrt(v/period);
    upper.push(ma[i]+mult*sd);lower.push(ma[i]-mult*sd);
  }}
  return {{ma,upper,lower}};
}}


// ════════════════════════════════════════════════════════
//  GAUSSIAN CHANNEL [DW] — traduit de Pine Script v4
// ════════════════════════════════════════════════════════
function calcGaussianChannel(closes, highs, lows, N=4, per=144, mult=1.414) {{
  const n = closes.length;
  if(n < per) return null;

  // Beta & alpha
  const beta  = (1 - Math.cos(4*Math.asin(1)/per)) / (Math.pow(1.414, 2/N) - 1);
  const alpha = -beta + Math.sqrt(beta*beta + 2*beta);
  const x     = 1 - alpha;
  const lag   = Math.floor((per - 1) / (2 * N));

  // Calcul filtre gaussien (N poles) sur hlc3
  const src  = closes.map((c,i) => (highs[i] + lows[i] + c) / 3);
  const trs  = closes.map((c,i) => {{
    const prev = i > 0 ? closes[i-1] : c;
    return Math.max(highs[i] - lows[i], Math.abs(highs[i] - prev), Math.abs(lows[i] - prev));
  }});

  function applyFilter(data, a) {{
    const f = new Array(data.length).fill(0);
    const xv = 1 - a;
    for(let i = 0; i < data.length; i++) {{
      let val = Math.pow(a, N) * (data[i] || 0);
      if(i >= 1) val += N * xv * f[i-1];
      if(N >= 2 && i >= 2) val -= (N*(N-1)/2) * xv*xv * f[i-2];
      if(N >= 3 && i >= 3) val += (N*(N-1)*(N-2)/6) * Math.pow(xv,3) * f[i-3];
      if(N >= 4 && i >= 4) val -= (N*(N-1)*(N-2)*(N-3)/24) * Math.pow(xv,4) * f[i-4];
      f[i] = val;
    }}
    return f;
  }}

  const filt   = applyFilter(src, alpha);
  const filttr = applyFilter(trs, alpha);

  const upper = filt.map((v,i) => v + filttr[i] * mult);
  const lower = filt.map((v,i) => v - filttr[i] * mult);

  return {{ filt, upper, lower }};
}}

// ════════════════════════════════════════════════════════
//  ORDER BLOCKS [LuxAlgo / Flux] — traduit de Pine Script
// ════════════════════════════════════════════════════════
function calcOrderBlocks(opens, highs, lows, closes, volumes, swingLen=10, maxOBs=3) {{
  const n = closes.length;
  if(n < swingLen * 2 + 5) return {{ bull: [], bear: [] }};

  // ATR (10)
  function calcATR(period=10) {{
    const atrs = [];
    for(let i=0; i<n; i++) {{
      if(i < period) {{ atrs.push(null); continue; }}
      let sum = 0;
      for(let j=i-period+1; j<=i; j++) {{
        const prev = closes[j-1] || closes[j];
        sum += Math.max(highs[j]-lows[j], Math.abs(highs[j]-prev), Math.abs(lows[j]-prev));
      }}
      atrs.push(sum/period);
    }}
    return atrs;
  }}
  const atr = calcATR(10);

  // Swing detection
  const swingType = new Array(n).fill(0);
  for(let i=swingLen; i<n; i++) {{
    const upper = Math.max(...highs.slice(i-swingLen, i));
    const lower = Math.min(...lows.slice(i-swingLen, i));
    if(highs[i-swingLen] > upper) swingType[i] = 0;
    else if(lows[i-swingLen] < lower) swingType[i] = 1;
    else swingType[i] = swingType[i-1] || 0;
  }}

  const bullOBs = [];
  const bearOBs = [];

  // Pivot volume highs
  for(let i=swingLen; i<n-swingLen; i++) {{
    const vol = volumes[i];
    let isVolPivot = true;
    for(let j=i-swingLen; j<=i+swingLen; j++) {{
      if(j!==i && volumes[j] > vol) {{ isVolPivot=false; break; }}
    }}
    if(!isVolPivot) continue;

    const st = swingType[i];

    // Bullish OB : pivot volume en downtrend (os==1)
    if(st === 1 && bullOBs.length < maxOBs) {{
      const top = (highs[i] + lows[i]) / 2;
      const btm = lows[i];
      const atv = atr[i] || (highs[i]-lows[i]);
      if(Math.abs(top-btm) <= atv * 3.5) {{
        bullOBs.unshift({{ top, btm, idx: i, mitigated: false }});
        if(bullOBs.length > maxOBs) bullOBs.pop();
      }}
    }}
    // Bearish OB : pivot volume en uptrend (os==0)
    if(st === 0 && bearOBs.length < maxOBs) {{
      const top = highs[i];
      const btm = (highs[i] + lows[i]) / 2;
      const atv = atr[i] || (highs[i]-lows[i]);
      if(Math.abs(top-btm) <= atv * 3.5) {{
        bearOBs.unshift({{ top, btm, idx: i, mitigated: false }});
        if(bearOBs.length > maxOBs) bearOBs.pop();
      }}
    }}
  }}

  // Mitigation : check si le prix a traversé l'OB
  bullOBs.forEach(ob => {{
    for(let i=ob.idx+1; i<n; i++) {{
      if(lows[i] < ob.btm) {{ ob.mitigated=true; break; }}
    }}
  }});
  bearOBs.forEach(ob => {{
    for(let i=ob.idx+1; i<n; i++) {{
      if(highs[i] > ob.top) {{ ob.mitigated=true; break; }}
    }}
  }});

  return {{ bull: bullOBs, bear: bearOBs }};
}}

// ════════════════════════════════════════════════════════
//  DRAW — GAUSSIAN CHANNEL
// ════════════════════════════════════════════════════════
function drawGaussianChannel(ctx, W, H, toX, toY, VIEW_START, VIEW_END) {{
  const gc = calcGaussianChannel(D.c, D.h, D.l, 4, 144, 1.414);
  if(!gc) return;

  const N = VIEW_END - VIEW_START;
  const filt  = gc.filt.slice(VIEW_START, VIEW_END);
  const upper = gc.upper.slice(VIEW_START, VIEW_END);
  const lower = gc.lower.slice(VIEW_START, VIEW_END);

  // Fill canal
  ctx.beginPath();
  let started = false;
  for(let i=0; i<N; i++) {{
    if(upper[i]==null) continue;
    started ? ctx.lineTo(toX(i), toY(upper[i])) : ctx.moveTo(toX(i), toY(upper[i]));
    started = true;
  }}
  for(let i=N-1; i>=0; i--) {{
    if(lower[i]==null) continue;
    ctx.lineTo(toX(i), toY(lower[i]));
  }}
  ctx.closePath();
  ctx.fillStyle = 'rgba(0,200,100,0.06)';
  ctx.fill();

  // Upper band
  ctx.beginPath(); started=false;
  for(let i=0;i<N;i++) {{
    if(upper[i]==null) continue;
    started?ctx.lineTo(toX(i),toY(upper[i])):ctx.moveTo(toX(i),toY(upper[i]));
    started=true;
  }}
  ctx.strokeStyle='rgba(0,255,136,0.45)'; ctx.lineWidth=1.2; ctx.setLineDash([4,3]); ctx.stroke(); ctx.setLineDash([]);

  // Lower band
  ctx.beginPath(); started=false;
  for(let i=0;i<N;i++) {{
    if(lower[i]==null) continue;
    started?ctx.lineTo(toX(i),toY(lower[i])):ctx.moveTo(toX(i),toY(lower[i]));
    started=true;
  }}
  ctx.strokeStyle='rgba(255,75,75,0.45)'; ctx.lineWidth=1.2; ctx.setLineDash([4,3]); ctx.stroke(); ctx.setLineDash([]);

  // Filtre central (coloré selon direction)
  for(let i=1;i<N;i++) {{
    if(filt[i]==null||filt[i-1]==null) continue;
    const rising = filt[i] > filt[i-1];
    ctx.beginPath();
    ctx.moveTo(toX(i-1), toY(filt[i-1]));
    ctx.lineTo(toX(i),   toY(filt[i]));
    ctx.strokeStyle = rising ? 'rgba(0,255,136,0.85)' : 'rgba(255,75,75,0.85)';
    ctx.lineWidth = 2.2; ctx.stroke();
  }}

  // Légende
  ctx.font = '9px Share Tech Mono,monospace'; ctx.textAlign='left';
  ctx.fillStyle='rgba(0,255,136,0.7)';
  ctx.fillText('GC', 8, 30);
}}

// ════════════════════════════════════════════════════════
//  DRAW — ORDER BLOCKS
// ════════════════════════════════════════════════════════
function drawOrderBlocks(ctx, W, H, toX, toY, VIEW_START, VIEW_END) {{
  const obs = calcOrderBlocks(D.o, D.h, D.l, D.c, D.v, 10, 3);
  const N   = VIEW_END - VIEW_START;
  const CW  = (W - 72) / N;   // PAD.r = 72

  function drawOB(ob, isBull) {{
    // Convertir idx global en idx vue
    const viewIdx = ob.idx - VIEW_START;
    if(viewIdx < -10 || viewIdx > N + 10) return; // hors vue

    const xStart = Math.max(0, toX(viewIdx) - CW/2);
    const xEnd   = W - 72; // étendre jusqu'au bord droit (prix actuel)

    const yTop = toY(ob.top);
    const yBtm = toY(ob.btm);
    const boxH  = Math.abs(yBtm - yTop);

    if(boxH < 1) return;

    const alpha    = ob.mitigated ? 0.12 : 0.22;
    const border   = ob.mitigated ? 0.25 : 0.55;
    const fillCol  = isBull
      ? `rgba(8,153,129,${{alpha}})`
      : `rgba(242,54,70,${{alpha}})`;
    const lineCol  = isBull
      ? `rgba(8,200,150,${{border}})`
      : `rgba(242,54,70,${{border}})`;

    // Rectangle zone
    ctx.fillStyle   = fillCol;
    ctx.strokeStyle = lineCol;
    ctx.lineWidth   = 1;
    ctx.beginPath();
    ctx.rect(xStart, Math.min(yTop,yBtm), xEnd-xStart, boxH);
    ctx.fill();
    ctx.stroke();

    // Ligne médiane (average)
    const yMid = (yTop + yBtm) / 2;
    ctx.beginPath();
    ctx.moveTo(xStart, yMid); ctx.lineTo(xEnd, yMid);
    ctx.strokeStyle = isBull ? 'rgba(8,200,150,0.45)' : 'rgba(242,54,70,0.45)';
    ctx.lineWidth = 1; ctx.setLineDash([3,3]); ctx.stroke(); ctx.setLineDash([]);

    // Label
    const label = (isBull ? 'Bull OB' : 'Bear OB') + (ob.mitigated ? ' ✗' : '');
    ctx.font = 'bold 8px Share Tech Mono,monospace';
    ctx.fillStyle = isBull ? 'rgba(0,255,180,0.75)' : 'rgba(255,100,100,0.75)';
    ctx.textAlign = 'left';
    ctx.fillText(label, xStart + 4, Math.min(yTop,yBtm) + 10);
  }}

  obs.bull.forEach(ob => drawOB(ob, true));
  obs.bear.forEach(ob => drawOB(ob, false));

  // Légende
  ctx.font='9px Share Tech Mono,monospace'; ctx.textAlign='left';
  ctx.fillStyle='rgba(8,200,150,0.7)';
  ctx.fillText('OB', 8+25, 30);
}}

function drawMain() {{
  const W=cvMain.width, H=cvMain.height;
  const ctx=ctxM;
  ctx.clearRect(0,0,W,H);

  const N=VIEW_END-VIEW_START;
  if(N<1) return;

  const slice=(arr)=>arr.slice(VIEW_START,VIEW_END);
  const ts=slice(D.t), os=slice(D.o), hs=slice(D.h), ls=slice(D.l), cs=slice(D.c);

  const minP=Math.min(...ls);
  const maxP=Math.max(...hs);
  const pad =Math.max((maxP-minP)*0.05, maxP*0.001);
  const lo=minP-pad, hi=maxP+pad, rng=hi-lo||1;

  const CW=(W-PAD.l-PAD.r)/N;
  const BW=Math.max(1, CW*0.75);
  const toX=i=>PAD.l+i*CW+CW/2;
  // Axis scale : zoom Y via PRICE_SCALE, pan Y via PRICE_OFFSET
  const midP   = (hi+lo)/2 + PRICE_OFFSET*rng;
  const scaledRng = rng / PRICE_SCALE;
  const sHi    = midP + scaledRng/2;
  const sLo    = midP - scaledRng/2;
  const toY=p=>PAD.t+(sHi-p)/scaledRng*(H-PAD.t-PAD.b);

  // ── FOND ──
  ctx.fillStyle='#000000';
  ctx.fillRect(0,0,W,H);

  // ── GRILLE HORIZONTALE ──
  const gridSteps=6;
  for(let s=0;s<=gridSteps;s++) {{
    const y=PAD.t+s*(H-PAD.t-PAD.b)/gridSteps;
    const price=hi-s*rng/gridSteps;
    ctx.strokeStyle='#111111'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    // Prix axe droit
    ctx.fillStyle='#4d9fff'; ctx.font='10px Share Tech Mono,monospace';
    ctx.textAlign='left'; ctx.fillText(fmt(price), W-PAD.r+6, y+4);
  }}

  // ── GRILLE VERTICALE + AXE TEMPS ──
  ctx.fillStyle='#4d9fff'; ctx.font='9px Share Tech Mono,monospace'; ctx.textAlign='center';
  const nTicks=Math.min(10,Math.max(3,Math.floor(N/15)));
  const prevMonth={{val:-1}};
  for(let t=0;t<=nTicks;t++) {{
    const i=Math.floor(t*(N-1)/Math.max(nTicks,1));
    const x=toX(i);
    const d=new Date(ts[i]*1000);
    ctx.strokeStyle='#111111'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(x,PAD.t); ctx.lineTo(x,H-PAD.b); ctx.stroke();
    // Label : heure si intraday, date si daily+
    let lbl;
    if(IV_SEC<86400) {{
      lbl=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
      if(d.getDate()!==prevMonth.val) {{
        lbl=d.toLocaleDateString('fr-FR',{{day:'2-digit',month:'short'}});
        prevMonth.val=d.getDate();
      }}
    }} else {{
      lbl=d.toLocaleDateString('fr-FR',{{day:'2-digit',month:'short'}});
    }}
    ctx.fillText(lbl, x, H-6);
  }}

  // ── BOLLINGER BANDS ──
  if(showBB) {{
    const bbAll=calcBB(D.c,20,2);
    const bbU=bbAll.upper.slice(VIEW_START,VIEW_END);
    const bbL=bbAll.lower.slice(VIEW_START,VIEW_END);
    const bbM=bbAll.ma.slice(VIEW_START,VIEW_END);

    // Fill entre upper et lower
    ctx.beginPath();
    for(let i=0;i<N;i++) {{ if(bbU[i]!==null){{ const x=toX(i);i===0?ctx.moveTo(x,toY(bbU[i])):ctx.lineTo(x,toY(bbU[i])); }} }}
    for(let i=N-1;i>=0;i--) {{ if(bbL[i]!==null){{ ctx.lineTo(toX(i),toY(bbL[i])); }} }}
    ctx.closePath();
    ctx.fillStyle='rgba(255,152,0,0.04)'; ctx.fill();

    // Lignes upper/lower/middle
    [bbU,bbL].forEach((band,bi)=>{{
      ctx.beginPath(); let started=false;
      for(let i=0;i<N;i++) {{
        if(band[i]===null) continue;
        started?ctx.lineTo(toX(i),toY(band[i])):ctx.moveTo(toX(i),toY(band[i]));
        started=true;
      }}
      ctx.strokeStyle='rgba(255,102,0,0.35)'; ctx.lineWidth=1; ctx.setLineDash([3,3]); ctx.stroke(); ctx.setLineDash([]);
    }});
    ctx.beginPath(); let s2=false;
    for(let i=0;i<N;i++) {{
      if(bbM[i]===null) continue;
      s2?ctx.lineTo(toX(i),toY(bbM[i])):ctx.moveTo(toX(i),toY(bbM[i]));
      s2=true;
    }}
    ctx.strokeStyle='rgba(255,102,0,0.45)'; ctx.lineWidth=1; ctx.stroke();
  }}

  // ── GAUSSIAN CHANNEL ──
  if(showGC) drawGaussianChannel(ctx, W, H, toX, toY, VIEW_START, VIEW_END);

  // ── ORDER BLOCKS ──
  if(showOB) drawOrderBlocks(ctx, W, H, toX, toY, VIEW_START, VIEW_END);

  // ── MOVING AVERAGES ──
  if(showMA) {{
    const maConf=[
      {{p:20,  color:'rgba(255,102,0,0.90)',  w:1.3}},
      {{p:50,  color:'rgba(255,204,0,0.85)',  w:1.3}},
      {{p:200, color:'rgba(100,180,255,0.80)',w:1.6}},
    ];
    maConf.forEach(mc=>{{
      const ma=calcMA(D.c,mc.p).slice(VIEW_START,VIEW_END);
      ctx.beginPath(); let started=false;
      for(let i=0;i<N;i++) {{
        if(ma[i]===null) continue;
        const x=toX(i), y=toY(ma[i]);
        started?ctx.lineTo(x,y):ctx.moveTo(x,y);
        started=true;
      }}
      ctx.strokeStyle=mc.color; ctx.lineWidth=mc.w; ctx.stroke();
    }});
    // Légende MA
    ctx.font='9px Share Tech Mono,monospace'; ctx.textAlign='left';
    [{{'p':20,'c':'rgba(255,102,0,0.90)'}},{{'p':50,'c':'rgba(255,204,0,0.85)'}},{{'p':200,'c':'rgba(100,180,255,0.80)'}}].forEach((m,i)=>{{
      ctx.fillStyle=m.c;
      ctx.fillText(`MA${{m.p}}`, 8+i*52, 18);
    }});
  }}

  // ── MONTE CARLO MERTON — BANDES ──
  drawMCBands(ctx, W, H, toX, toY, N, CW);

  // ── BOUGIES ──
  for(let i=0;i<N;i++) {{
    const x=toX(i);
    const oy=toY(os[i]), hy=toY(hs[i]), ly=toY(ls[i]), cy=toY(cs[i]);
    const bull=cs[i]>=os[i];
    const bullCol='#00ff41', bearCol='#ff2222';
    const col=bull?bullCol:bearCol;

    // Mèche
    const wickW=Math.max(1, BW*0.1);
    ctx.strokeStyle=col; ctx.lineWidth=wickW;
    ctx.beginPath(); ctx.moveTo(x,hy); ctx.lineTo(x,ly); ctx.stroke();

    // Corps
    const top=Math.min(oy,cy);
    const bH =Math.max(1, Math.abs(cy-oy));
    const hw =Math.max(1, BW/2);

    // Corps plein — haussier vert, baissier rouge
    ctx.fillStyle = bull ? bullCol : bearCol;
    ctx.fillRect(x-hw, top, hw*2, bH);

    // Dernière bougie — halo pulsant
    if(i===N-1) {{
      const glow=1.5+Math.sin(Date.now()/300)*1;
      ctx.strokeStyle=bull?'rgba(38,166,154,0.6)':'rgba(239,83,80,0.6)';
      ctx.lineWidth=1;
      ctx.strokeRect(x-hw-glow, top-glow, hw*2+glow*2, bH+glow*2);
    }}
  }}

  // ── LIGNE PRIX ACTUEL ──
  const lastC=cs[N-1], lastO=os[N-1];
  const lastBull=lastC>=lastO;
  const py=toY(lastC);
  // Ligne pointillée
  ctx.strokeStyle=lastBull?'rgba(0,255,65,0.4)':'rgba(255,34,34,0.4)';
  ctx.lineWidth=1; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(0,py); ctx.lineTo(W-PAD.r,py); ctx.stroke();
  ctx.setLineDash([]);
  // Tag prix
  const tagCol=lastBull?'#00ff41':'#ff2222';
  ctx.fillStyle=tagCol;
  ctx.beginPath();
  ctx.roundRect(W-PAD.r+2, py-9, PAD.r-4, 18, 2);
  ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold 9px Share Tech Mono,monospace'; ctx.textAlign='left';
  ctx.fillText(fmt(lastC), W-PAD.r+5, py+4);

  // ── DRAWINGS ──
  drawAllDrawings(ctx, W, H);

  // ── CROSSHAIR ──
  if(HOVER_IDX>=0 && HOVER_IDX<N) {{
    const x=toX(HOVER_IDX);
    // Ligne verticale
    ctx.strokeStyle='rgba(255,102,0,0.25)'; ctx.lineWidth=1; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(x,PAD.t); ctx.lineTo(x,H); ctx.stroke();
    // Ligne horizontale
    if(HOVER_Y>0) {{
      ctx.beginPath(); ctx.moveTo(0,HOVER_Y); ctx.lineTo(W-PAD.r,HOVER_Y); ctx.stroke();
      // Tag prix crosshair à droite
      const hp=sHi-(HOVER_Y-PAD.t)/((H-PAD.t-PAD.b))*scaledRng;
      ctx.fillStyle='#1a0800';
      ctx.beginPath(); ctx.roundRect(W-PAD.r+2,HOVER_Y-9,PAD.r-4,18,2); ctx.fill();
      ctx.fillStyle='#e8e8e8'; ctx.font='9px Share Tech Mono,monospace'; ctx.textAlign='left';
      ctx.fillText(fmt(hp), W-PAD.r+5, HOVER_Y+4);
    }}
    // Label date en bas
    const d=new Date(ts[HOVER_IDX]*1000);
    const dateLbl=fmtDate(ts[HOVER_IDX]);
    ctx.fillStyle='#1a0800'; ctx.textAlign='center';
    const tw=ctx.measureText(dateLbl).width+12;
    ctx.beginPath(); ctx.roundRect(x-tw/2, H-PAD.b+2, tw, 16, 2); ctx.fill();
    ctx.fillStyle='#e8e8e8'; ctx.font='9px Share Tech Mono,monospace';
    ctx.fillText(dateLbl, x, H-PAD.b+13);

    // Mise à jour OHLC header
    const ri=VIEW_START+HOVER_IDX;
    const bull2=D.c[ri]>=D.o[ri];
    setTxt('ho',fmt(D.o[ri])); setCol('ho',bull2?'var(--bull)':'var(--bear)');
    setTxt('hh',fmt(D.h[ri])); setCol('hh','var(--bull)');
    setTxt('hl',fmt(D.l[ri])); setCol('hl','var(--bear)');
    setTxt('hc',fmt(D.c[ri])); setCol('hc',bull2?'var(--bull)':'var(--bear)');
  }}
}}


// ════════════════════════════════════════════════════════
//  RSI — Relative Strength Index (14)
// ════════════════════════════════════════════════════════
function calcRSI(closes, period=14) {{
  const rsi = new Array(closes.length).fill(null);
  if(closes.length < period+1) return rsi;
  let avgGain=0, avgLoss=0;
  for(let i=1;i<=period;i++) {{
    const d=closes[i]-closes[i-1];
    if(d>=0) avgGain+=d; else avgLoss+=Math.abs(d);
  }}
  avgGain/=period; avgLoss/=period;
  rsi[period] = 100 - 100/(1+(avgLoss===0?Infinity:avgGain/avgLoss));
  for(let i=period+1;i<closes.length;i++) {{
    const d=closes[i]-closes[i-1];
    avgGain=(avgGain*(period-1)+(d>0?d:0))/period;
    avgLoss=(avgLoss*(period-1)+(d<0?Math.abs(d):0))/period;
    rsi[i]=100-100/(1+(avgLoss===0?100:avgGain/avgLoss));
  }}
  return rsi;
}}

function drawRSI() {{
  const cv=$('cvRSI');
  if(!cv||!showRSI) return;
  const W=cv.width, H=cv.height;
  const ctx=cv.getContext('2d');
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#000000'; ctx.fillRect(0,0,W,H);
  const N=VIEW_END-VIEW_START;
  if(N<2||H<10) return;

  const rsiAll=calcRSI(D.c,14);
  const rsi=rsiAll.slice(VIEW_START,VIEW_END);
  const CW=(W-PAD.l-PAD.r)/N;
  const toX=i=>PAD.l+i*CW+CW/2;
  const toY=v=>H-4-(v/100)*(H-8);

  // Zones 70/30
  ctx.fillStyle='rgba(255,34,34,0.06)';
  ctx.fillRect(0,4,W-PAD.r,toY(70)-4);
  ctx.fillStyle='rgba(0,255,65,0.06)';
  ctx.fillRect(0,toY(30),W-PAD.r,H-toY(30)-4);

  // Lignes 70/50/30
  [[70,'rgba(255,34,34,0.5)'],[50,'rgba(100,100,100,0.4)'],[30,'rgba(0,255,65,0.5)']].forEach(([v,col])=>{{
    const y=toY(v);
    ctx.strokeStyle=col; ctx.lineWidth=1; ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=col; ctx.font='8px Share Tech Mono,monospace';
    ctx.textAlign='left'; ctx.fillText(v,W-PAD.r+4,y+3);
  }});

  // Courbe RSI
  for(let i=1;i<N;i++) {{
    if(rsi[i]===null||rsi[i-1]===null) continue;
    const avg=(rsi[i]+rsi[i-1])/2;
    ctx.beginPath(); ctx.moveTo(toX(i-1),toY(rsi[i-1])); ctx.lineTo(toX(i),toY(rsi[i]));
    ctx.strokeStyle=avg>=70?'#ff4444':avg<=30?'#00ff65':'#e8a838';
    ctx.lineWidth=1.5; ctx.stroke();
  }}

  // Tag valeur actuelle
  const last=rsi.filter(v=>v!==null).pop();
  if(last!=null) {{
    const col=last>=70?'#ff4444':last<=30?'#00ff65':'#e8a838';
    ctx.fillStyle=col;
    ctx.beginPath(); ctx.roundRect(W-PAD.r+2,toY(last)-8,PAD.r-4,16,2); ctx.fill();
    ctx.fillStyle='#000'; ctx.font='bold 8px Share Tech Mono,monospace'; ctx.textAlign='left';
    ctx.fillText(last.toFixed(1),W-PAD.r+5,toY(last)+3);
  }}

  ctx.fillStyle='#4d9fff'; ctx.font='8px Share Tech Mono,monospace';
  ctx.textAlign='left'; ctx.fillText('RSI(14)',4,10);
}}

// ════════════════════════════════════════════════════════
//  MACD — Moving Average Convergence Divergence (12/26/9)
// ════════════════════════════════════════════════════════
function calcEMA(data, period) {{
  const ema=new Array(data.length).fill(null);
  const k=2/(period+1);
  let prev=null;
  for(let i=0;i<data.length;i++) {{
    if(data[i]===null) continue;
    if(prev===null){{ prev=data[i]; ema[i]=prev; continue; }}
    prev=data[i]*k+prev*(1-k); ema[i]=prev;
  }}
  return ema;
}}

function calcMACD(closes,fast=12,slow=26,signal=9) {{
  const ema12=calcEMA(closes,fast);
  const ema26=calcEMA(closes,slow);
  const macd=closes.map((_,i)=>(ema12[i]!==null&&ema26[i]!==null)?ema12[i]-ema26[i]:null);
  const sig=calcEMA(macd,signal);
  const hist=macd.map((v,i)=>(v!==null&&sig[i]!==null)?v-sig[i]:null);
  return {{macd,signal:sig,hist}};
}}

function drawMACD() {{
  const cv=$('cvMACD');
  if(!cv||!showMACD) return;
  const W=cv.width, H=cv.height;
  const ctx=cv.getContext('2d');
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#000000'; ctx.fillRect(0,0,W,H);
  const N=VIEW_END-VIEW_START;
  if(N<2||H<10) return;

  const md=calcMACD(D.c,12,26,9);
  const macd=md.macd.slice(VIEW_START,VIEW_END);
  const sig=md.signal.slice(VIEW_START,VIEW_END);
  const hist=md.hist.slice(VIEW_START,VIEW_END);

  const vals=[...macd,...sig,...hist].filter(v=>v!==null);
  if(!vals.length) return;
  const rng=Math.max(Math.abs(Math.max(...vals)),Math.abs(Math.min(...vals)))*1.1||1;

  const CW=(W-PAD.l-PAD.r)/N;
  const toX=i=>PAD.l+i*CW+CW/2;
  const toY=v=>(H/2)-(v/rng)*(H/2-4);

  // Ligne zéro
  ctx.strokeStyle='rgba(100,100,100,0.4)'; ctx.lineWidth=1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(0,H/2); ctx.lineTo(W-PAD.r,H/2); ctx.stroke();
  ctx.setLineDash([]);

  // Histogramme
  for(let i=0;i<N;i++) {{
    if(hist[i]===null) continue;
    const x=PAD.l+i*CW+1, bw=Math.max(1,CW-2);
    const y0=H/2, y1=toY(hist[i]);
    const bull=hist[i]>=0;
    const prev=hist[i-1]||0;
    ctx.fillStyle=bull?(hist[i]>prev?'#00cc44':'#007722'):(hist[i]<prev?'#cc0000':'#882200');
    ctx.fillRect(x,Math.min(y0,y1),bw,Math.abs(y1-y0));
  }}

  // Ligne MACD
  ctx.beginPath(); let s1=false;
  for(let i=0;i<N;i++) {{
    if(macd[i]===null) continue;
    s1?ctx.lineTo(toX(i),toY(macd[i])):ctx.moveTo(toX(i),toY(macd[i])); s1=true;
  }}
  ctx.strokeStyle='rgba(100,180,255,0.9)'; ctx.lineWidth=1.5; ctx.stroke();

  // Ligne Signal
  ctx.beginPath(); let s2=false;
  for(let i=0;i<N;i++) {{
    if(sig[i]===null) continue;
    s2?ctx.lineTo(toX(i),toY(sig[i])):ctx.moveTo(toX(i),toY(sig[i])); s2=true;
  }}
  ctx.strokeStyle='rgba(255,165,0,0.9)'; ctx.lineWidth=1.2; ctx.stroke();

  // Valeurs
  const lm=macd.filter(v=>v!==null).pop();
  const ls=sig.filter(v=>v!==null).pop();
  ctx.font='8px Share Tech Mono,monospace';
  if(lm!=null){{ ctx.fillStyle='rgba(100,180,255,0.8)'; ctx.textAlign='right'; ctx.fillText('M:'+lm.toFixed(4),W-PAD.r-2,10); }}
  if(ls!=null){{ ctx.fillStyle='rgba(255,165,0,0.8)'; ctx.textAlign='right'; ctx.fillText('S:'+ls.toFixed(4),W-PAD.r-2,20); }}
  ctx.fillStyle='#4d9fff'; ctx.textAlign='left'; ctx.fillText('MACD(12,26,9)',4,10);
}}

function drawVol() {{
  if(!showVol) return;
  const W=cvVol.width, H=cvVol.height;
  const ctx=ctxV;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#000000'; ctx.fillRect(0,0,W,H);

  const N=VIEW_END-VIEW_START;
  if(!N||H<4) return;
  const vs=D.v.slice(VIEW_START,VIEW_END);
  const maxV=Math.max(...vs)||1;
  const CW=(W-PAD.l-PAD.r)/N;

  // MA volume (20)
  const maV=calcMA(D.v,20).slice(VIEW_START,VIEW_END);

  for(let i=0;i<N;i++) {{
    const bh=Math.max(1,(vs[i]/maxV)*(H-4));
    const bull=D.c[VIEW_START+i]>=D.o[VIEW_START+i];
    ctx.fillStyle=bull?'rgba(38,166,154,0.5)':'rgba(239,83,80,0.5)';
    ctx.fillRect(PAD.l+i*CW+1, H-bh, Math.max(1,CW-2), bh);
  }}

  // MA volume line
  ctx.beginPath(); let s=false;
  for(let i=0;i<N;i++) {{
    if(maV[i]===null) continue;
    const x=PAD.l+i*CW+CW/2;
    const y=H-(maV[i]/maxV)*(H-4);
    s?ctx.lineTo(x,y):ctx.moveTo(x,y); s=true;
  }}
  ctx.strokeStyle='rgba(255,102,0,0.70)'; ctx.lineWidth=1; ctx.stroke();

  // Label
  ctx.fillStyle='#333333'; ctx.font='8px Share Tech Mono,monospace';
  ctx.textAlign='left'; ctx.fillText('VOLUME', 4, 10);
}}

function render() {{ drawMain(); drawVol(); drawRSI(); drawMACD(); }}

function applyHeaderPrice(price, pct) {{
  const bull=parseFloat(pct)>=0;
  const clr=bull?'var(--bull)':'var(--bear)';
  const pe=$('curPrice'), ce=$('curChg');
  if(pe) {{ pe.textContent=fmt(price); pe.style.color=clr; }}
  if(ce) {{
    ce.textContent=(bull?'▲ +':'▼ ')+Math.abs(parseFloat(pct)).toFixed(2)+'%';
    ce.className='price-chg '+(bull?'up':'dn');
  }}
}}

function updateStats() {{
  const N=D.c.length; if(!N) return;
  const last=D.c[N-1];
  const h24=Math.max(...D.h.slice(-96)), l24=Math.min(...D.l.slice(-96));
  const vol=D.v.slice(-96).reduce((a,b)=>a+b,0);
  const chg=((last-D.o[Math.max(0,N-96)])/D.o[Math.max(0,N-96)]*100);
  const bull=chg>=0;
  applyHeaderPrice(last,chg);
  setTxt('statVol',fmtV(vol));
  setTxt('b_hi',fmt(h24)); setTxt('b_lo',fmt(l24));
  setTxt('b_chg',(bull?'+':'')+chg.toFixed(2)+'%'); setCol('b_chg',bull?'var(--bull)':'var(--bear)');
  setTxt('b_vol',fmtV(vol));
  // OHLC header = dernière bougie
  setTxt('ho',fmt(D.o[N-1])); setTxt('hh',fmt(D.h[N-1]));
  setTxt('hl',fmt(D.l[N-1])); setTxt('hc',fmt(D.c[N-1]));
}}


// ════════════════════════════════════════════════════════
//  OUTILS DE DESSIN
// ════════════════════════════════════════════════════════
let DRAW_TOOL = 'cursor';
let drawings  = [];
let drawPending = null;  // dessin en cours (1er point posé)

function setDrawTool(tool) {{
  DRAW_TOOL = tool;
  document.querySelectorAll('.draw-btn').forEach(b => b.classList.remove('active'));
  const btn = $('dBtn_'+tool);
  if(btn) btn.classList.add('active');
  cvMain.style.cursor = tool === 'cursor' ? 'crosshair' : tool === 'text' ? 'text' : 'crosshair';
  drawPending = null;
}}

function clearDrawings() {{
  drawings = []; drawPending = null; render();
}}

// Convertir pixel → prix/index
function pxToPrice(y) {{
  const H = cvMain.height;
  const N = VIEW_END - VIEW_START;
  const slice = arr => arr.slice(VIEW_START, VIEW_END);
  const hi = Math.max(...slice(D.h));
  const lo = Math.min(...slice(D.l));
  const rng = (hi - lo) || 1;
  return hi - ((y - PAD.t) / (H - PAD.t - PAD.b)) * rng;
}}
function pxToIdx(x) {{
  const W = cvMain.width;
  const N = VIEW_END - VIEW_START;
  const CW = (W - PAD.l - PAD.r) / N;
  return VIEW_START + Math.max(0, Math.min(N-1, Math.floor((x - PAD.l) / CW)));
}}
// Convertir prix/index → pixel
function priceToY(price) {{
  const H = cvMain.height;
  const N = VIEW_END - VIEW_START;
  const slice = arr => arr.slice(VIEW_START, VIEW_END);
  const hi = Math.max(...slice(D.h));
  const lo = Math.min(...slice(D.l));
  const rng = (hi - lo) || 1;
  return PAD.t + ((hi - price) / rng) * (H - PAD.t - PAD.b);
}}
function idxToX(idx) {{
  const W = cvMain.width;
  const N = VIEW_END - VIEW_START;
  const CW = (W - PAD.l - PAD.r) / N;
  return PAD.l + (idx - VIEW_START) * CW + CW / 2;
}}

// Dessiner tous les drawings sur le canvas principal
function drawAllDrawings(ctx, W, H) {{
  drawings.forEach(d => drawSingle(ctx, d, W, H));
  if(drawPending) drawSingle(ctx, drawPending, W, H);
}}

function drawSingle(ctx, d, W, H) {{
  ctx.save();
  ctx.strokeStyle = d.color || '#FABE2C';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([]);

  const x1 = idxToX(d.i1), y1 = priceToY(d.p1);
  const x2 = d.i2 != null ? idxToX(d.i2) : x1;
  const y2 = d.p2 != null ? priceToY(d.p2) : y1;

  if(d.type === 'line') {{
    ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
    // Petits cercles aux extrémités
    ctx.fillStyle = d.color||'#FABE2C';
    ctx.beginPath(); ctx.arc(x1,y1,3,0,Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(x2,y2,3,0,Math.PI*2); ctx.fill();

  }} else if(d.type === 'hline') {{
    ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(0,y1); ctx.lineTo(W-PAD.r,y1); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=d.color||'#FABE2C'; ctx.font='8px Share Tech Mono,monospace';
    ctx.textAlign='right'; ctx.fillText(fmt(d.p1), W-PAD.r-4, y1-3);

  }} else if(d.type === 'vline') {{
    ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(x1,PAD.t); ctx.lineTo(x1,H-PAD.b); ctx.stroke();
    ctx.setLineDash([]);

  }} else if(d.type === 'ray') {{
    // Étendre jusqu'au bord droit
    const dx = x2 - x1, dy = y2 - y1;
    const t = dx !== 0 ? (W - PAD.r - x1) / dx : 999;
    ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x1+dx*t, y1+dy*t); ctx.stroke();
    ctx.fillStyle=d.color||'#FABE2C';
    ctx.beginPath(); ctx.arc(x1,y1,3,0,Math.PI*2); ctx.fill();

  }} else if(d.type === 'rect') {{
    if(d.i2==null) {{ ctx.beginPath(); ctx.arc(x1,y1,3,0,Math.PI*2); ctx.fill(); }}
    else {{
      ctx.strokeRect(Math.min(x1,x2), Math.min(y1,y2), Math.abs(x2-x1), Math.abs(y2-y1));
      ctx.fillStyle = 'rgba(250,190,44,0.06)';
      ctx.fillRect(Math.min(x1,x2), Math.min(y1,y2), Math.abs(x2-x1), Math.abs(y2-y1));
    }}

  }} else if(d.type === 'fibo') {{
    if(d.i2==null) {{ ctx.beginPath(); ctx.arc(x1,y1,3,0,Math.PI*2); ctx.fill(); }}
    else {{
      const levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0];
      const cols   = ['#888','#26a69a','#66bb6a','#FABE2C','#ff9800','#ef5350','#888'];
      levels.forEach((lv, li) => {{
        const p = d.p1 + (d.p2 - d.p1) * lv;
        const y = priceToY(p);
        ctx.strokeStyle = cols[li]; ctx.lineWidth=1; ctx.setLineDash([3,3]);
        ctx.beginPath(); ctx.moveTo(Math.min(x1,x2), y); ctx.lineTo(Math.max(x1,x2), y); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle=cols[li]; ctx.font='8px Share Tech Mono,monospace';
        ctx.textAlign='left';
        ctx.fillText((lv*100).toFixed(1)+'%  '+fmt(p), Math.min(x1,x2)+4, y-2);
      }});
    }}

  }} else if(d.type === 'range') {{
    if(d.i2==null) {{ ctx.beginPath(); ctx.arc(x1,y1,3,0,Math.PI*2); ctx.fill(); }}
    else {{
      const yTop=Math.min(y1,y2), yBot=Math.max(y1,y2);
      const pTop=d.p1>d.p2?d.p1:d.p2, pBot=d.p1<d.p2?d.p1:d.p2;
      const bull=pTop>pBot;
      ctx.strokeStyle=bull?'rgba(38,166,154,0.9)':'rgba(239,83,80,0.9)';
      ctx.fillStyle=bull?'rgba(38,166,154,0.08)':'rgba(239,83,80,0.08)';
      ctx.fillRect(Math.min(x1,x2), yTop, Math.abs(x2-x1), yBot-yTop);
      ctx.strokeRect(Math.min(x1,x2), yTop, Math.abs(x2-x1), yBot-yTop);
      const pct=((pTop-pBot)/pBot*100).toFixed(2);
      ctx.fillStyle=bull?'rgba(38,166,154,0.9)':'rgba(239,83,80,0.9)';
      ctx.font='bold 10px Share Tech Mono,monospace'; ctx.textAlign='center';
      ctx.fillText((bull?'▲ +':'▼ ')+pct+'%', (Math.min(x1,x2)+Math.max(x1,x2))/2, (yTop+yBot)/2+4);
      ctx.font='8px Share Tech Mono,monospace'; ctx.textAlign='right';
      ctx.fillText(fmt(pTop), Math.max(x1,x2)-4, yTop-3);
      ctx.fillText(fmt(pBot), Math.max(x1,x2)-4, yBot+10);
    }}

  }} else if(d.type === 'text') {{
    ctx.fillStyle=d.color||'#FABE2C';
    ctx.font='bold 12px Share Tech Mono,monospace'; ctx.textAlign='left';
    ctx.fillText(d.label||'', x1+2, y1);
  }}
  ctx.restore();
}}

// ════════════════════════════════════════════════════════
//  INTERACTIONS SOURIS
// ════════════════════════════════════════════════════════
cvMain.addEventListener('mousemove', e => {{
  const rect=cvMain.getBoundingClientRect();
  const mx=e.clientX-rect.left;
  const my=e.clientY-rect.top;
  HOVER_Y=my;

  if(isDragging) {{
    const N=VIEW_END-VIEW_START;
    const CW=(cvMain.width-PAD.l-PAD.r)/N;
    const shift=Math.round(-(e.clientX-dragStartX)/CW);
    const totalN=D.t.length;
    let s=Math.max(0,Math.min(totalN-N,dragStartView+shift));
    VIEW_START=s; VIEW_END=s+N;
    render(); return;
  }}

  const N=VIEW_END-VIEW_START;
  const CW=(cvMain.width-PAD.l-PAD.r)/N;
  HOVER_IDX=Math.max(0,Math.min(N-1,Math.floor((mx-PAD.l)/CW)));

  // Tooltip flottant
  const ri=VIEW_START+HOVER_IDX;
  const tt=$('tooltip');
  if(tt && ri>=0 && ri<D.t.length) {{
    const bull2=D.c[ri]>=D.o[ri];
    tt.style.display='block';
    // Position : éviter bords
    let tx=e.clientX+16, ty=e.clientY-80;
    if(tx+180>window.innerWidth) tx=e.clientX-196;
    if(ty<0) ty=e.clientY+10;
    tt.style.left=tx+'px'; tt.style.top=ty+'px';
    setTxt('ttDate', fmtDate(D.t[ri]));
    setTxt('ttO', fmt(D.o[ri])); setCol('ttO', bull2?'var(--bull)':'var(--bear)');
    setTxt('ttH', fmt(D.h[ri]));
    setTxt('ttL', fmt(D.l[ri]));
    setTxt('ttC', fmt(D.c[ri])); setCol('ttC', bull2?'var(--bull)':'var(--bear)');
    setTxt('ttV', fmtV(D.v[ri]));
  }}
  // Mise à jour dessin en cours
  if(drawPending) {{
    const rect2=cvMain.getBoundingClientRect();
    drawPending.i2=pxToIdx(e.clientX-rect2.left);
    drawPending.p2=pxToPrice(e.clientY-rect2.top);
  }}
  drawMain();
}});

cvMain.addEventListener('mousedown', e => {{
  if(DRAW_TOOL !== 'cursor') {{
    const rect=cvMain.getBoundingClientRect();
    const mx=e.clientX-rect.left, my=e.clientY-rect.top;
    const price=pxToPrice(my), idx=pxToIdx(mx);

    if(DRAW_TOOL==='hline') {{
      drawings.push({{type:'hline',i1:idx,p1:price,i2:null,p2:null}});
      drawPending=null; render(); return;
    }}
    if(DRAW_TOOL==='vline') {{
      drawings.push({{type:'vline',i1:idx,p1:price,i2:null,p2:null}});
      drawPending=null; render(); return;
    }}
    if(DRAW_TOOL==='text') {{
      const lbl=prompt('Texte :'); if(!lbl) return;
      drawings.push({{type:'text',i1:idx,p1:price,i2:null,p2:null,label:lbl}});
      drawPending=null; render(); return;
    }}
    // Outils 2 points : line, ray, fibo, rect, range
    if(!drawPending) {{
      drawPending={{type:DRAW_TOOL,i1:idx,p1:price,i2:idx,p2:price}};
    }} else {{
      drawPending.i2=idx; drawPending.p2=price;
      drawings.push({{...drawPending}});
      drawPending=null;
      setDrawTool('cursor');
      render();
    }}
    return;
  }}
  isDragging=true; dragStartX=e.clientX; dragStartView=VIEW_START;
  cvMain.style.cursor='grabbing';
}});
window.addEventListener('mouseup', () => {{
  isDragging=false;
  if(DRAW_TOOL==='cursor') cvMain.style.cursor='crosshair';
}});
cvMain.addEventListener('mouseleave', () => {{
  HOVER_IDX=-1; HOVER_Y=-1;
  const tt=$('tooltip'); if(tt) tt.style.display='none';
  // Remettre OHLC de la dernière bougie
  const N=D.c.length;
  if(N) {{ setTxt('ho',fmt(D.o[N-1])); setTxt('hh',fmt(D.h[N-1])); setTxt('hl',fmt(D.l[N-1])); setTxt('hc',fmt(D.c[N-1])); }}
  drawMain();
}});

// Scroll = zoom
cvMain.addEventListener('wheel', e => {{
  e.preventDefault();
  const N=VIEW_END-VIEW_START;
  const factor=e.deltaY>0?1.1:0.9;
  const newN=Math.max(20,Math.min(D.t.length,Math.round(N*factor)));
  const center=HOVER_IDX>=0?VIEW_START+HOVER_IDX:Math.floor((VIEW_START+VIEW_END)/2);
  let s=Math.max(0,center-Math.floor(newN/2));
  let en=s+newN;
  if(en>D.t.length){{en=D.t.length;s=Math.max(0,en-newN);}}
  VIEW_START=s; VIEW_END=en;
  render();
}},{{passive:false}});


// Raccourcis clavier
document.addEventListener('keydown', e => {{
  if(e.key==='Escape') {{ drawPending=null; setDrawTool('cursor'); render(); }}
  if((e.ctrlKey||e.metaKey) && e.key==='z') {{
    drawings.pop(); drawPending=null; render();
  }}
}});


// ════════════════════════════════════════════════════════
//  AXIS SCALE (TradingView style)
// ════════════════════════════════════════════════════════
const axisY = document.getElementById('axisY');
const axisX = document.getElementById('axisX');

function resetAxisScale() {{
  PRICE_SCALE  = 1.0;
  PRICE_OFFSET = 0.0;
  render();
}}

// ── Drag axe Y (droite) : zoom vertical ──
axisY.addEventListener('mousedown', e => {{
  e.preventDefault();
  const N = VIEW_END - VIEW_START;
  const slice_h = D.h.slice(VIEW_START, VIEW_END);
  const slice_l = D.l.slice(VIEW_START, VIEW_END);
  const hi = Math.max(...slice_h);
  const lo = Math.min(...slice_l);
  const rng = (hi - lo) || 1;
  axisDrag = {{
    type: 'y',
    startY: e.clientY,
    startScale: PRICE_SCALE,
    startOffset: PRICE_OFFSET,
  }};
}});

// ── Drag axe X (bas) : zoom horizontal ──
axisX.addEventListener('mousedown', e => {{
  e.preventDefault();
  axisDrag = {{
    type: 'x',
    startX: e.clientX,
    startN: VIEW_END - VIEW_START,
    startStart: VIEW_START,
    startEnd: VIEW_END,
  }};
}});

window.addEventListener('mousemove', e => {{
  if(!axisDrag) return;

  if(axisDrag.type === 'y') {{
    // Drag vers le haut = zoom in (PRICE_SCALE augmente)
    // Drag vers le bas  = zoom out
    const dy = axisDrag.startY - e.clientY;
    const factor = 1 + dy * 0.005;
    PRICE_SCALE = Math.max(0.1, Math.min(20, axisDrag.startScale * factor));

    // Shift+drag = pan vertical
    if(e.shiftKey) {{
      const panDy = e.clientY - axisDrag.startY;
      PRICE_OFFSET = axisDrag.startOffset + (panDy / cvMain.height) * 0.5;
    }}
    render();
  }}

  if(axisDrag.type === 'x') {{
    // Drag vers la droite = zoom out (plus de bougies visibles)
    // Drag vers la gauche = zoom in  (moins de bougies)
    const dx = e.clientX - axisDrag.startX;
    const totalN = D.t.length;
    const currentN = axisDrag.startN;
    const factor = 1 + dx * 0.008;
    const newN = Math.max(20, Math.min(totalN, Math.round(currentN * factor)));

    // Centrer sur la position de départ
    const center = Math.floor((axisDrag.startStart + axisDrag.startEnd) / 2);
    let s = Math.max(0, center - Math.floor(newN / 2));
    let en = s + newN;
    if(en > totalN) {{ en = totalN; s = Math.max(0, en - newN); }}
    VIEW_START = s; VIEW_END = en;
    render();
  }}
}});

window.addEventListener('mouseup', () => {{
  axisDrag = null;
}});

// Double-clic axe Y = reset zoom vertical
axisY.addEventListener('dblclick', () => {{
  PRICE_SCALE  = 1.0;
  PRICE_OFFSET = 0.0;
  render();
}});

// Double-clic axe X = fit all
axisX.addEventListener('dblclick', () => {{
  VIEW_START = 0;
  VIEW_END   = D.t.length;
  render();
}});

// ════════════════════════════════════════════════════════
//  TIMEFRAME & INDICATEURS
// ════════════════════════════════════════════════════════
// ── Variable globale mode ──
let CHART_MODE = 'normal';  // 'normal' | 'pro' | 'quant'
let MC_OPEN   = false;
let MC_HEIGHT = 260;

// ── Mapping TF → intervalle Binance + secondes ──
const TF_MAP = {{
  '1m':  {{iv:'1m',  sec:60}},
  '5m':  {{iv:'5m',  sec:300}},
  '15m': {{iv:'15m', sec:900}},
  '1h':  {{iv:'1h',  sec:3600}},
  '4h':  {{iv:'4h',  sec:14400}},
  '1d':  {{iv:'1d',  sec:86400}},
  '1w':  {{iv:'1w',  sec:604800}},
}};

let CURRENT_TF = '{active_tf}';

async function setTF(btn, tf) {{
  tf = tf.toLowerCase();
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  CURRENT_TF = tf;

  // Fermer WS actuel
  if(ws && ws.readyState===WebSocket.OPEN) ws.close();

  // Loader visuel
  const badge = $('apiBadge');
  if(badge) {{ badge.textContent='⟳ CHARGEMENT'; badge.className='live-badge sim'; }}

  // Recharger les données OHLCV
  await reloadOHLCV(tf);

  // Redémarrer le WS avec la même paire
  startBinanceWS();
}}

async function reloadOHLCV(tf) {{
  const sym   = '{binance_symbol}'.toUpperCase();
  const cfg   = TF_MAP[tf] || TF_MAP['4h'];
  const limit = 200;

  // Mettre à jour IV_SEC globalement
  window.IV_SEC_CURRENT = cfg.sec;

  try {{
    const url = `https://api.binance.com/api/v3/klines?symbol=${{sym}}&interval=${{cfg.iv}}&limit=${{limit}}`;
    const res  = await fetch(url);
    if(!res.ok) throw new Error('Binance ' + res.status);
    const raw = await res.json();

    // Remplacer les données
    D.t.length=0; D.o.length=0; D.h.length=0;
    D.l.length=0; D.c.length=0; D.v.length=0;
    raw.forEach(c=>{{
      D.t.push(Math.floor(c[0]/1000));
      D.o.push(parseFloat(c[1]));
      D.h.push(parseFloat(c[2]));
      D.l.push(parseFloat(c[3]));
      D.c.push(parseFloat(c[4]));
      D.v.push(parseFloat(c[5]));
    }});

    // Reset vue
    VIEW_START = Math.max(0, D.t.length-120);
    VIEW_END   = D.t.length;
    candleStart = D.t[D.t.length-1] || Math.floor(Date.now()/1000);
    simPrice    = D.c[D.c.length-1] || simPrice;

    render();
    updateStats();
    console.log(`[AM.Terminal] TF ${{tf}} → ${{D.t.length}} bougies chargées`);

  }} catch(e) {{
    console.warn('[AM.Terminal] reloadOHLCV erreur:', e.message);
    // Fallback CoinGecko si Binance bloqué
    await reloadOHLCVCoinGecko(tf);
  }}
}}

async function reloadOHLCVCoinGecko(tf) {{
  const coinId = '{coingecko_id}';
  const daysMap = {{'1m':1,'5m':1,'15m':1,'1h':7,'4h':30,'1d':365,'1w':1825}};
  const days = daysMap[tf] || 30;
  try {{
    const url = `https://api.coingecko.com/api/v3/coins/${{coinId}}/ohlc?vs_currency=usd&days=${{days}}`;
    const res  = await fetch(url, {{signal: AbortSignal.timeout(10000)}});
    const raw  = await res.json();
    if(!Array.isArray(raw)||!raw.length) throw new Error('vide');

    D.t.length=0; D.o.length=0; D.h.length=0;
    D.l.length=0; D.c.length=0; D.v.length=0;
    raw.forEach(c=>{{
      D.t.push(Math.floor(c[0]/1000));
      D.o.push(parseFloat(c[1]));
      D.h.push(parseFloat(c[2]));
      D.l.push(parseFloat(c[3]));
      D.c.push(parseFloat(c[4]));
      D.v.push(0);
    }});

    VIEW_START=Math.max(0,D.t.length-120);
    VIEW_END=D.t.length;
    render(); updateStats();
    console.log(`[AM.Terminal] CoinGecko fallback TF ${{tf}} → ${{D.t.length}} bougies`);
  }} catch(e) {{
    console.warn('[AM.Terminal] CoinGecko fallback échoué:', e.message);
  }}
}}

// ════════════════════════════════════════════════════════
//  QUANT PANEL
// ════════════════════════════════════════════════════════
let quantPanelOpen = false;

function toggleQuantPanel() {{
  quantPanelOpen = !quantPanelOpen;
  const qPanel = $('quantPanel');
  const btn    = $('qpToggleBtn');
  if(qPanel) qPanel.style.display = quantPanelOpen ? 'flex' : 'none';
  if(btn)    btn.textContent = quantPanelOpen ? '⚙ QUANT TOOLS ◀' : '⚙ QUANT TOOLS ▶';
  // Initialise le filtre d'onglet à la première ouverture
  if(quantPanelOpen) {{
    const activeTab = document.querySelector('.qp-tab.active');
    const tabName   = activeTab ? activeTab.textContent.trim().toLowerCase() : 'risk';
    document.querySelectorAll('.tool-card').forEach(card => {{
      card.style.display = (!card.dataset.tab || card.dataset.tab === tabName) ? '' : 'none';
    }});
  }}
  setupCanvas(); render();
}}

function switchQTab(el, tab) {{
  document.querySelectorAll('.qp-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.tool-card').forEach(card => {{
    card.style.display = (!card.dataset.tab || card.dataset.tab === tab) ? '' : 'none';
  }});
}}

function toggleToolCard(id) {{
  const card = $(id);
  if(!card) return;
  const wasActive = card.classList.contains('tc-active');
  // Close all
  document.querySelectorAll('.tool-card').forEach(c => {{
    c.classList.remove('tc-active');
    c.classList.remove('tc-running');
  }});
  if(!wasActive) card.classList.add('tc-active');
}}

function toggleModeDD() {{
  $('modeDD').classList.toggle('open');
  $('modeCaret').classList.toggle('open');
}}

function pickMode(key, lbl, sub, icon) {{
  CHART_MODE = key;
  // Mettre à jour le bouton
  const btn = $('modeBtn');
  btn.setAttribute('data-mode', key);
  $('modeLbl').textContent = lbl;
  $('modeSub').textContent = sub;
  $('modeIcon').textContent = icon;
  // Coches
  document.querySelectorAll('.mode-opt').forEach(el => {{
    el.classList.remove('active');
    el.querySelector('.mo-check').style.opacity = '0';
  }});
  const opts = document.querySelectorAll('.mode-opt');
  const idx = ['normal','pro','quant'].indexOf(key);
  if(idx>=0) {{
    opts[idx].classList.add('active');
    opts[idx].querySelector('.mo-check').style.opacity = '1';
  }}
  // Fermer le dropdown
  $('modeDD').classList.remove('open');
  $('modeCaret').classList.remove('open');

  // ── Gestion du panneau QUANT ──
  const isQuant = key === 'quant';
  const qpBtn   = $('qpToggleBtn');
  const qPanel  = $('quantPanel');
  if(qpBtn) qpBtn.classList.toggle('qmode', isQuant);
  if(qPanel) {{
    if(isQuant) {{
      quantPanelOpen = false;  // reset — bouton toggle ouvre
      qPanel.style.display = 'none';
      if(qpBtn) qpBtn.textContent = '⚙ QUANT TOOLS ▶';
    }} else {{
      quantPanelOpen = false;
      qPanel.style.display = 'none';
      if(qpBtn) qpBtn.textContent = '⚙ QUANT TOOLS ▶';
    }}
  }}
  // Fermer le panel MC si on quitte le mode quant
  if(key !== 'quant' && MC_OPEN) mcClose();

  setupCanvas(); render();
}}

// Fermer dropdown si clic extérieur
document.addEventListener('click', e => {{
  const w = document.querySelector('.mode-wrap');
  if(w && !w.contains(e.target)) {{
    $('modeDD').classList.remove('open');
    $('modeCaret').classList.remove('open');
  }}
}});
// ════════════════════════════════════════════════════════
//  MERTON JUMP-DIFFUSION  — moteur JS (TypedArray)
//  Miroir fidèle de quant/monte_carlo.py
// ════════════════════════════════════════════════════════
let MC_SHOW  = false;
let MC_BANDS = null;   // trajectoires percentiles pour drawMCBands

/* Box-Muller → N(0,1) */
function _randn() {{
  let u, v, s;
  do {{ u = Math.random()*2-1; v = Math.random()*2-1; s = u*u+v*v; }} while(s>=1||s===0);
  return u * Math.sqrt(-2*Math.log(s)/s);
}}

/* Poisson(λ) — Knuth pour λ<30, approx normale sinon */
function _poisson(lam) {{
  if(lam <= 0) return 0;
  if(lam < 30) {{
    const L = Math.exp(-lam); let k=0, p=1;
    do {{ k++; p *= Math.random(); }} while(p > L);
    return k-1;
  }}
  return Math.max(0, Math.round(lam + Math.sqrt(lam)*_randn()));
}}

function mertonJDSim(S0, mu, sigma, lam, mu_j, sigma_j, horizon, nSim) {{
  const dt     = 1/252;                              // pas journalier
  const sqDt   = Math.sqrt(dt);
  const k      = Math.exp(mu_j + 0.5*sigma_j*sigma_j) - 1; // saut moyen
  const mu_c   = mu - lam * k;                      // dérive corrigée Merton
  const steps  = horizon + 1;

  // ── Stockage de toutes les trajectoires (Float64Array) ──
  const allPaths = new Float64Array(nSim * steps);

  for(let s=0; s<nSim; s++) {{
    let price = S0;
    allPaths[s*steps] = price;
    for(let t=1; t<steps; t++) {{
      // Brownien
      const Z = _randn();
      // Sauts de Poisson
      const nj = _poisson(lam * dt);
      let J = 0;
      for(let jj=0; jj<nj; jj++) J += _randn()*sigma_j + mu_j;
      // Log-return Merton
      price *= Math.exp((mu_c - 0.5*sigma*sigma)*dt + sigma*sqDt*Z + J);
      if(price < 1e-12) price = 1e-12;
      allPaths[s*steps + t] = price;
    }}
  }}

  // ── Calcul des percentiles par pas de temps ──
  const PCTS = [5, 10, 25, 50, 75, 90, 95];
  const pPaths = {{}};
  for(const p of PCTS) pPaths[`p${{p}}`] = new Float64Array(steps);

  const col = new Float64Array(nSim);
  for(let t=0; t<steps; t++) {{
    for(let s=0; s<nSim; s++) col[s] = allPaths[s*steps + t];
    const sorted = col.slice().sort();
    for(const p of PCTS) {{
      const idx = Math.min(nSim-1, Math.floor(p/100*(nSim-1)));
      pPaths[`p${{p}}`][t] = sorted[idx];
    }}
  }}

  // ── Stats terminales ──
  const finals = new Float64Array(nSim);
  for(let s=0; s<nSim; s++) finals[s] = allPaths[s*steps + horizon];
  const sortedF   = finals.slice().sort();
  const sumF      = finals.reduce((a,b)=>a+b,0);
  const mean      = sumF / nSim;
  const p5v       = sortedF[Math.floor(0.05*(nSim-1))];
  const p25v      = sortedF[Math.floor(0.25*(nSim-1))];
  const p50v      = sortedF[Math.floor(0.50*(nSim-1))];
  const p75v      = sortedF[Math.floor(0.75*(nSim-1))];
  const p95v      = sortedF[Math.floor(0.95*(nSim-1))];
  let probProfit=0, tailSum=0, tailN=0;
  for(let s=0;s<nSim;s++) {{
    if(finals[s] > S0) probProfit++;
    if(finals[s] <= p5v) {{ tailSum+=finals[s]; tailN++; }}
  }}
  const cvar95 = tailN>0 ? tailSum/tailN - S0 : p5v - S0;

  return {{
    paths: pPaths,                // percentile paths (Float64Array per pct)
    finals,                       // Float64Array des prix finaux (histogramme)
    mean, p5:p5v, p25:p25v, p50:p50v, p75:p75v, p95:p95v,
    probProfit: probProfit/nSim*100,
    var95: p5v - S0,
    cvar95,
    S0, horizon,
  }};
}}

// ════════════════════════════════════════════════════════
//  AUTO-CALIBRATION μ et σ depuis D.c
// ════════════════════════════════════════════════════════
function autoCalibrateMC() {{
  if(D.c.length < 10) return;
  const ANN = {{'1m':525600,'5m':105120,'15m':35040,'30m':17520,
                '1h':8760,'4h':2190,'1d':252,'1w':52}};
  const factor = ANN[window.CURRENT_TF||'4h'] || 2190;
  let sumLR=0, n=D.c.length;
  const lrs = [];
  for(let i=1;i<n;i++) {{
    if(D.c[i-1]>0) {{
      const lr = Math.log(D.c[i]/D.c[i-1]);
      lrs.push(lr); sumLR+=lr;
    }}
  }}
  if(lrs.length < 5) return;
  const muP  = sumLR / lrs.length;
  let varSum  = 0;
  for(const r of lrs) varSum += (r-muP)*(r-muP);
  const sigP = Math.sqrt(varSum / (lrs.length-1));
  const muAnn  = (muP  * factor * 100).toFixed(2);
  const sigAnn = (sigP * Math.sqrt(factor) * 100).toFixed(2);
  const muEl  = $('mc_mu');   if (muEl && !muEl.dataset.userChanged) muEl.value = muAnn.toFixed(2);
  const sigEl = $('mc_sigma');if (sigEl && !sigEl.dataset.userChanged) sigEl.value = sigAnn.toFixed(2);
}}

// ════════════════════════════════════════════════════════
//  BOUTON ▶ CALCULER
// ════════════════════════════════════════════════════════
function runMonteCarlo() {{
  // Prix courant du graphique (live)
  const S0 = D.c[D.c.length-1] || 100;

  // Re-calibration automatique avant calcul
  //autoCalibrateMC();

  // Lecture des paramètres
  const mu      = (parseFloat($('mc_mu'   )?.value) || 50)  / 100;
  const sigma   = (parseFloat($('mc_sigma')?.value) || 80)  / 100;
  const lam     = parseFloat($('mc_lam'   )?.value) || 3;
  const mu_j    = (parseFloat($('mc_muj'  )?.value) || -5)  / 100;
  const sigma_j = (parseFloat($('mc_sigmaj')?.value)|| 10)  / 100;
  const horizon = parseInt  ($('mc_horizon')?.value) || 90;
  const nSim    = Math.min(10000, parseInt($('mc_nsim')?.value) || 5000);

  // Info calcul en cours
  const infoEl = $('mc_r_info');
  if(infoEl) infoEl.textContent = `⏳ Calcul ${{nSim}} trajectoires…`;

  // Calcul asynchrone (évite de bloquer l'UI)
  setTimeout(() => {{
    const t0  = performance.now();
    const res = mertonJDSim(S0, mu, sigma, lam, mu_j, sigma_j, horizon, nSim);
    const ms  = (performance.now() - t0).toFixed(0);

    // Formatage résultats
    const fmtR = (v, ref) => {{
      const pct = ((v-ref)/ref*100);
      return fmt(v) + ' (' + (pct>=0?'+':'') + pct.toFixed(1) + '%)';
    }};
    const setR = (id, txt, cls) => {{
      const el=$(id);
      if(!el) return;
      el.textContent = txt;
      if(cls) el.className = 'result-val ' + cls;
    }};

    setR('mc_r_s0',   fmt(S0),                     '');
    setR('mc_r_mean', fmtR(res.mean, S0),           'val-orange');
    setR('mc_r_p50',  fmtR(res.p50,  S0),           'val-yellow');
    setR('mc_r_p95',  fmtR(res.p95,  S0),           'val-green');
    setR('mc_r_p5',   fmtR(res.p5,   S0),           'val-red');
    const pp = res.probProfit;
    setR('mc_r_prob', pp.toFixed(1)+'%',             pp>=50?'val-green':'val-red');
    setR('mc_r_var',  (res.var95>=0?'+':'')+fmt(res.var95)+ ' ('+((res.var95/S0)*100).toFixed(1)+'%)', 'val-red');
    setR('mc_r_cvar', (res.cvar95>=0?'+':'')+fmt(res.cvar95)+'  CVaR','val-red');

    const bar = $('mc_r_bar');
    if(bar) bar.style.width = pp.toFixed(0)+'%';
    if(infoEl) infoEl.textContent =
      `${{nSim}} sim · ${{horizon}}j · Merton JD · ${{ms}}ms`;

    // Sauvegarde (ancien système canvas)
    MC_BANDS = res;

    // ── Alimenter le panel MC avec les mêmes résultats ──────
    // Convertir format mertonJDSim → format panel mcDraw
    MC_RESULT = {{
      percs:       res.paths,
      allPaths:    null,
      finals:      res.finals,
      S0:          res.S0,
      horizon:     res.horizon,
      mean:        res.mean,
      p5:          res.p5,
      p25:         res.p25,
      p50:         res.p50,
      p75:         res.p75,
      p95:         res.p95,
      prob_profit: res.probProfit,
      var_95:      res.var95,
    }};

    // Si panel ouvert → redessiner immédiatement
    if(MC_OPEN) {{
      mcResizeCanvas();
      mcDraw();
    }}
    const barInfo = $('mcBarInfo');
    if(barInfo) barInfo.textContent = nSim + ' sim · ' + horizon + 'j · Merton JD';
  }}, 10);
}}

// ════════════════════════════════════════════════════════
//  BOUTON 📈 GRAPHIQUE  — toggle direct du panel MC
// ════════════════════════════════════════════════════════
function toggleMCPanel() {{
  if(MC_OPEN) {{ mcClose(); }}
  else        {{ mcOpen(); }}
}}

function _mcUpdateGraphBtn(open) {{
  const btn = $('mc_graph_btn');
  if(!btn) return;
  btn.style.background  = open ? 'rgba(77,159,255,0.22)' : 'rgba(77,159,255,0.10)';
  btn.style.borderColor = open ? '#4d9fff' : 'rgba(77,159,255,0.35)';
  btn.textContent       = open ? '📈 MASQUER' : '📈 GRAPHIQUE';
}}

// ════════════════════════════════════════════════════════
//  DESSIN DES BANDES MC SUR LE CANVAS
// ════════════════════════════════════════════════════════
function drawMCBands(ctx, W, H, toX, toY, N, CW) {{
  if(!MC_SHOW || !MC_BANDS) return;
  const {{ paths, horizon, S0 }} = MC_BANDS;
  const steps = horizon + 1;

  // Point de départ : fin de la vue actuelle
  const lastX = toX(N - 1);
  const toMCX = step => lastX + step * CW;
  const clipX  = W - PAD.r;   // ne pas déborder sur l'axe prix

  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, clipX, H);
  ctx.clip();

  // ── Fonction dessiner une bande remplie entre deux courbes ──
  function drawBand(pHigh, pLow, fillStyle) {{
    ctx.beginPath();
    let started = false;
    for(let t=0; t<steps; t++) {{
      const x = toMCX(t);
      if(x > clipX) break;
      const y = toY(pHigh[t]);
      if(!started) {{ ctx.moveTo(x, y); started=true; }}
      else           ctx.lineTo(x, y);
    }}
    for(let t=steps-1; t>=0; t--) {{
      const x = toMCX(t);
      if(x > clipX) continue;
      ctx.lineTo(x, toY(pLow[t]));
    }}
    ctx.closePath();
    ctx.fillStyle = fillStyle;
    ctx.fill();
  }}

  // ── Bande P5–P95  (très transparente) ──
  drawBand(paths.p95, paths.p5,  'rgba(77,159,255,0.07)');
  // ── Bande P10–P90 ──
  drawBand(paths.p90, paths.p10, 'rgba(77,159,255,0.10)');
  // ── Bande P25–P75  (cœur de distribution) ──
  drawBand(paths.p75, paths.p25, 'rgba(77,159,255,0.18)');

  // ── Lignes P5 / P95 ──
  [[paths.p5,'rgba(255,80,80,0.55)'],[paths.p95,'rgba(0,230,118,0.55)']].forEach(([arr,col]) => {{
    ctx.beginPath(); let s2=false;
    for(let t=0; t<steps; t++) {{
      const x=toMCX(t); if(x>clipX) break;
      const y=toY(arr[t]);
      s2 ? ctx.lineTo(x,y) : (ctx.moveTo(x,y), s2=true);
    }}
    ctx.strokeStyle=col; ctx.lineWidth=1.2; ctx.setLineDash([4,3]); ctx.stroke();
    ctx.setLineDash([]);
  }});

  // ── Médiane P50 (ligne principale) ──
  ctx.beginPath(); let sm=false;
  for(let t=0; t<steps; t++) {{
    const x=toMCX(t); if(x>clipX) break;
    const y=toY(paths.p50[t]);
    sm ? ctx.lineTo(x,y) : (ctx.moveTo(x,y), sm=true);
  }}
  ctx.strokeStyle='rgba(77,159,255,0.85)';
  ctx.lineWidth=1.8; ctx.setLineDash([]); ctx.stroke();

  // ── Ligne de départ (S0) ──
  const x0 = toMCX(0);
  const yS0 = toY(S0);
  ctx.beginPath(); ctx.moveTo(x0, yS0); ctx.lineTo(x0, H-PAD.b);
  ctx.strokeStyle='rgba(77,159,255,0.25)'; ctx.lineWidth=1;
  ctx.setLineDash([2,4]); ctx.stroke(); ctx.setLineDash([]);

  // ── Label ──
  ctx.font='bold 9px Share Tech Mono,monospace';
  ctx.fillStyle='rgba(77,159,255,0.75)';
  ctx.textAlign='left';
  ctx.fillText('MERTON MC', x0+4, 20);

  ctx.restore();
}}

function toggleMA() {{
  showMA=!showMA; $('btnMA').classList.toggle('on',showMA); render();
}}
function toggleVol() {{
  showVol=!showVol; $('btnVol').classList.toggle('on',showVol);
  setupCanvas(); render();
}}
function toggleBB() {{
  showBB=!showBB; $('btnBB').classList.toggle('on',showBB); render();
}}
function toggleRSI() {{
  showRSI=!showRSI; $('btnRSI').classList.toggle('on',showRSI);
  setupCanvas(); render();
}}
function toggleMACD() {{
  showMACD=!showMACD; $('btnMACD').classList.toggle('on',showMACD);
  setupCanvas(); render();
}}
function toggleGC() {{
  showGC=!showGC; $('btnGC').classList.toggle('on',showGC); render();
}}
function toggleOB() {{
  showOB=!showOB; $('btnOB').classList.toggle('on',showOB); render();
}}


// ════════════════════════════════════════════════════════
//  FULLSCREEN
// ════════════════════════════════════════════════════════
function toggleFullscreen() {{
  const isFS = document.body.classList.toggle('is-fullscreen');
  const btn  = $('fsBtn');
  if(btn) btn.title = isFS ? 'Quitter le plein écran' : 'Plein écran';
  if(btn) btn.textContent = isFS ? '✕' : '⛶';

  // Tenter l'API Fullscreen native si dans un iframe / navigateur
  try {{
    if(isFS) {{
      const el = document.documentElement;
      if(el.requestFullscreen)            el.requestFullscreen();
      else if(el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    }} else {{
      if(document.exitFullscreen)            document.exitFullscreen();
      else if(document.webkitExitFullscreen) document.webkitExitFullscreen();
    }}
  }} catch(e) {{}}

  // Redessiner après resize
  setTimeout(() => {{ setupCanvas(); render(); }}, 100);
}}

// Quitter avec Échap
document.addEventListener('fullscreenchange', () => {{
  if(!document.fullscreenElement) {{
    document.body.classList.remove('is-fullscreen');
    const btn = $('fsBtn');
    if(btn) {{ btn.title = 'Plein écran'; btn.textContent = '⛶'; }}
    setTimeout(() => {{ setupCanvas(); render(); }}, 100);
  }}
}});

// ════════════════════════════════════════════════════════
//  PRIX TEMPS RÉEL
// ════════════════════════════════════════════════════════
let ws=null;

function applyPriceUpdate(price, chg24, vol24, high24, low24) {{
  const bull=parseFloat(chg24)>=0;
  const last=D.t.length-1;
  if(last>=0){{ D.c[last]=price; if(price>D.h[last])D.h[last]=price; if(price<D.l[last])D.l[last]=price; }}
  applyHeaderPrice(price, chg24);
  const fV=v=>v>=1e9?(v/1e9).toFixed(2)+'B':v>=1e6?(v/1e6).toFixed(1)+'M':(v||0).toFixed(0);
  if(vol24){{ setTxt('b_vol',fV(vol24)); }}
  if(high24){{ setTxt('b_hi',fmt(high24)); }}
  if(low24) {{ setTxt('b_lo',fmt(low24)); }}
  setTxt('b_chg',(bull?'+':'')+parseFloat(chg24).toFixed(2)+'%');
  setCol('b_chg',bull?'var(--bull)':'var(--bear)');
  const badge=$('apiBadge');
  if(badge){{ badge.textContent='● LIVE'; badge.className='live-badge live'; }}
  render();
}}

function startBinanceWS() {{
  const sym='{binance_symbol}'.toLowerCase();
  if(!sym||sym==='undefined'){{ startFallbackPolling(); return; }}
  ws=new WebSocket(`wss://stream.binance.com:9443/stream?streams=${{sym}}@ticker`);
  ws.onopen=()=>{{ simActive=false; wsConnected=true; console.log('[AM.Terminal] WS Binance connecté'); }};
  ws.onmessage=e=>{{
    try {{
      const d=(JSON.parse(e.data).data)||JSON.parse(e.data);
      const p=parseFloat(d.c);
      if(!isNaN(p)) applyPriceUpdate(p,parseFloat(d.P),parseFloat(d.q),parseFloat(d.h),parseFloat(d.l));
    }} catch(err) {{}}
  }};
  ws.onclose=()=>{{ setTimeout(startBinanceWS,5000); }};
  ws.onerror=()=>{{ simActive=false; ws.close(); startFallbackPolling(); }};
}}

async function fetchLivePrice() {{
  try {{
    const id='{coingecko_id}';
    const res=await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${{id}}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true`,{{signal:AbortSignal.timeout(8000)}});
    const json=await res.json(); const data=json[id];
    if(data) applyPriceUpdate(data.usd,data.usd_24h_change,data.usd_24h_vol,null,null);
  }} catch(e) {{}}
}}
function startFallbackPolling(){{ fetchLivePrice(); setInterval(fetchLivePrice,15000); }}

// ════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════
const RUN_SIM = {run_sim};
console.log('[AM.Terminal] {data_info}');

async function fetchInit() {{
  // Charge les données OHLCV depuis Binance dès le départ
  const TF_MAP = {{
    '1m':{{iv:'1m',sec:60}},'5m':{{iv:'5m',sec:300}},'15m':{{iv:'15m',sec:900}},
    '1h':{{iv:'1h',sec:3600}},'4h':{{iv:'4h',sec:14400}},
    '1d':{{iv:'1d',sec:86400}},'1w':{{iv:'1w',sec:604800}},
  }};
  const cfg = TF_MAP[IV_INIT] || TF_MAP['4h'];
  window.IV_SEC_CURRENT = cfg.sec;
  window.CURRENT_TF = IV_INIT;
  window.CURRENT_SYMBOL = SYMBOL_INIT;
  try {{
    const url = `https://api.binance.com/api/v3/klines?symbol=${{SYMBOL_INIT}}&interval=${{cfg.iv}}&limit=200`;
    const res = await fetch(url);
    if(!res.ok) throw new Error('Binance ' + res.status);
    const raw = await res.json();
    raw.forEach(c=>{{
      D.t.push(Math.floor(c[0]/1000));
      D.o.push(parseFloat(c[1]));
      D.h.push(parseFloat(c[2]));
      D.l.push(parseFloat(c[3]));
      D.c.push(parseFloat(c[4]));
      D.v.push(parseFloat(c[5]));
    }});
    simPrice  = D.c[D.c.length-1] || 100;
    prevPrice = simPrice;
    candleStart = D.t[D.t.length-1] || Math.floor(Date.now()/1000);
    console.log(`[AM.Terminal] Init ${{SYMBOL_INIT}} ${{IV_INIT}} → ${{D.t.length}} bougies`);
  }} catch(e) {{
    console.warn('[AM.Terminal] fetchInit Binance échoué:', e.message);
    // Fallback CoinGecko
    try {{
      const cgId = '{coingecko_id}';
      const daysMap={{'1m':1,'5m':1,'15m':1,'1h':7,'4h':30,'1d':365,'1w':1825}};
      const days = daysMap[IV_INIT]||30;
      const r2 = await fetch(`https://api.coingecko.com/api/v3/coins/${{cgId}}/ohlc?vs_currency=usd&days=${{days}}`);
      const raw2 = await r2.json();
      if(Array.isArray(raw2)) raw2.forEach(c=>{{
        D.t.push(Math.floor(c[0]/1000));
        D.o.push(parseFloat(c[1]));
        D.h.push(parseFloat(c[2]));
        D.l.push(parseFloat(c[3]));
        D.c.push(parseFloat(c[4]));
        D.v.push(0);
      }});
      simPrice = D.c[D.c.length-1]||100;
      prevPrice = simPrice;
    }} catch(e2) {{ console.warn('[AM.Terminal] CoinGecko aussi échoué'); }}
  }}
}}

function init() {{
  setupCanvas();
  // Afficher canvas vide pendant le chargement
  VIEW_START=0; VIEW_END=0;
  render();

  // Init Kelly (valeurs Python déjà injectées dans les inputs)
  calcKelly();

  // Charger les données PUIS démarrer
  fetchInit().then(()=>{{
    VIEW_START=Math.max(0,D.t.length-120);
    VIEW_END=D.t.length;
    render();
    updateStats();
    startBinanceWS();
    // Sim seulement si WS mort après 6s
    if(RUN_SIM) {{
      setTimeout(()=>{{ if(!wsConnected) {{ simActive=true; }} }}, 6000);
      setInterval(simTick, 400);
    }}
    setInterval(()=>{{ if(HOVER_IDX<0) drawMain(); }}, 200);
  }});
}}

window.addEventListener('load', init);

// ════════════════════════════════════════════════════════════════
//  MONTE CARLO  (Merton Jump-Diffusion, vectorisé JS)
// ════════════════════════════════════════════════════════════════

let MC_MODE    = 'fan';      // 'fan' | 'spaghetti'
let MC_RESULT  = null;
const MC_MIN_H = 140;
const MC_MAX_H = 520;

// MC panel : s'ouvre via bouton GRAPHIQUE uniquement

function mcOpen() {{
  MC_OPEN = true;
  const p = document.getElementById('mcPanel');
  p.classList.add('open');
  p.style.height = MC_HEIGHT + 'px';
  _mcUpdateGraphBtn(true);
  setupCanvas(); render();
  mcResizeCanvas();
  if(MC_RESULT) mcDraw();
}}

function mcClose() {{
  MC_OPEN = false;
  document.getElementById('mcPanel').classList.remove('open');
  _mcUpdateGraphBtn(false);
  setupCanvas(); render();
}}


// ════════════════════════════════════════════════════════
//  SÉLECTEUR FAN / HISTOGRAMME
// ════════════════════════════════════════════════════════
function mcSetVis(mode) {{
  MC_MODE = mode;
  const btnFan  = $('mc_vis_fan');
  const btnHist = $('mc_vis_hist');
  if(btnFan) {{
    btnFan.style.borderColor = mode==='fan' ? 'rgba(250,190,44,0.5)' : '#2a2a2a';
    btnFan.style.background  = mode==='fan' ? 'rgba(250,190,44,0.10)' : 'transparent';
    btnFan.style.color       = mode==='fan' ? '#FABE2C' : '#555';
  }}
  if(btnHist) {{
    btnHist.style.borderColor = mode==='histogram' ? 'rgba(250,190,44,0.5)' : '#2a2a2a';
    btnHist.style.background  = mode==='histogram' ? 'rgba(250,190,44,0.10)' : 'transparent';
    btnHist.style.color       = mode==='histogram' ? '#FABE2C' : '#555';
  }}
  const tabFan  = $('mcTabFan');
  const tabHist = $('mcTabHist');
  if(tabFan)  tabFan.classList.toggle('active',  mode==='fan');
  if(tabHist) tabHist.classList.toggle('active', mode==='histogram');
  if(MC_RESULT && MC_OPEN) mcDraw();
}}

function mcSetMode(mode) {{
  MC_MODE = mode;
  document.getElementById('mcTabFan').classList.toggle('active',  mode==='fan');
  document.getElementById('mcTabHist').classList.toggle('active', mode==='histogram');
  if(MC_RESULT) mcDraw();
}}

function mcResizeCanvas() {{
  const wrap = document.getElementById('mcCanvasWrap');
  const cv   = document.getElementById('cvMC');
  if(!wrap || !cv) return;
  const W = wrap.offsetWidth;
  const H = wrap.offsetHeight;
  if(W < 10 || H < 10) return;
  cv.width  = W; cv.height = H;
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
}}

// ── Merton Jump-Diffusion ─────────────────────────────────────
function mcRandNormal() {{
  let u, v;
  do {{ u = Math.random(); }} while(u === 0);
  do {{ v = Math.random(); }} while(v === 0);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}}
function mcPoisson(lam) {{
  const L = Math.exp(-lam);
  let k = 0, p = 1;
  do {{ k++; p *= Math.random(); }} while(p > L);
  return k - 1;
}}

function mcSimulate(closes, horizon, nSim, lam) {{
  const n = closes.length;
  if(n < 10) return null;

  // Estimer µ et σ annualisés (252 jours)
  const ANN = 252;
  const lr  = [];
  for(let i = 1; i < n; i++) lr.push(Math.log(closes[i] / closes[i-1]));
  const muPer  = lr.reduce((a,b)=>a+b, 0) / lr.length;
  const sigPer = Math.sqrt(lr.reduce((a,b)=>a+(b-muPer)**2, 0) / Math.max(lr.length-1,1));
  const mu     = muPer  * ANN;
  const sigma  = sigPer * Math.sqrt(ANN);
  const dt     = 1 / ANN;

  // Params sauts Merton
  const mu_j   = -0.05;
  const sig_j  = 0.10;
  const k      = Math.exp(mu_j + 0.5 * sig_j * sig_j) - 1;
  const mu_c   = mu - lam * k;

  const S0     = closes[closes.length - 1];
  const allPaths = [];   // pour spaghetti: stocker toutes les trajectoires

  const PCTS   = [5, 10, 25, 50, 75, 90, 95];
  // Matrice: steps × nSim  (stocker juste les valeurs à chaque step pour percentile)
  const steps  = horizon + 1;
  const matrix = Array.from({{length: steps}}, () => new Float64Array(nSim));
  matrix[0].fill(S0);

  for(let s = 0; s < nSim; s++) {{
    let price = S0;
    const path = [price];
    for(let t = 0; t < horizon; t++) {{
      const Z  = mcRandNormal();
      const nj = mcPoisson(lam * dt);
      let J    = 0;
      for(let j = 0; j < nj; j++) J += mcRandNormal() * sig_j + mu_j;
      const ret = (mu_c - 0.5 * sigma * sigma) * dt
                + sigma * Math.sqrt(dt) * Z
                + J;
      price = price * Math.exp(ret);
      path.push(price);
      matrix[t+1][s] = price;
    }}
    if(nSim <= 120) allPaths.push(path);   // garder si assez peu
  }}

  // Calculer percentiles à chaque step
  const percs = {{}};
  PCTS.forEach(p => percs['p'+p] = new Array(steps));
  for(let t = 0; t < steps; t++) {{
    const sorted = Array.from(matrix[t]).sort((a,b)=>a-b);
    PCTS.forEach(p => {{
      const idx = Math.max(0, Math.floor(p / 100 * (sorted.length - 1)));
      percs['p'+p][t] = sorted[idx];
    }});
  }}

  const finals  = Array.from(matrix[steps - 1]).sort((a,b)=>a-b);
  const mean    = finals.reduce((a,b)=>a+b,0) / finals.length;
  const p5v     = finals[Math.floor(0.05 * finals.length)];
  const probP   = finals.filter(v => v > S0).length / finals.length * 100;

  return {{ percs, allPaths, finals, S0, horizon, mean,
    p5:  finals[Math.floor(0.05 * finals.length)],
    p25: finals[Math.floor(0.25 * finals.length)],
    p50: finals[Math.floor(0.50 * finals.length)],
    p75: finals[Math.floor(0.75 * finals.length)],
    p95: finals[Math.floor(0.95 * finals.length)],
    prob_profit: probP,
    var_95: p5v - S0,
  }};
}}

function mcRun() {{
  const runBtn = document.querySelector('.mc-run');
  if(runBtn) {{ runBtn.textContent = '⏳ ...'; runBtn.disabled = true; }}

  setTimeout(() => {{
    const horizon = Math.min(Math.max(parseInt(document.getElementById('mcHorizon').value)||60, 10), 365);
    const nSim    = Math.min(Math.max(parseInt(document.getElementById('mcNSim').value)||300, 30), 500);
    const lam     = Math.max(parseFloat(document.getElementById('mcLambda').value)||3, 0);

    MC_RESULT = mcSimulate(D.c.slice(), horizon, nSim, lam);

    if(runBtn) {{ runBtn.textContent = '▶ SIMULER'; runBtn.disabled = false; }}

    if(!MC_OPEN) mcOpen();
    mcResizeCanvas();
    mcDraw();
    mcUpdateStats();
  }}, 10);
}}

function mcUpdateStats() {{
  if(!MC_RESULT) return;
  const r  = MC_RESULT;
  const S0 = r.S0;
  const pct = v => (v/S0 - 1) * 100;
  const sign = v => v >= 0 ? '+' : '';
  const fmtStat = v => fmt(v) + ' (' + sign(pct(v)) + pct(v).toFixed(1) + '%)';

  const set = (id, v) => {{ const el = document.getElementById(id); if(el) el.textContent = v; }};
  set('mcStatMed',  fmtStat(r.p50));
  set('mcStatP95',  fmtStat(r.p95));
  set('mcStatP5',   fmtStat(r.p5));
  set('mcStatProb', r.prob_profit.toFixed(1) + '%');
  set('mcStatVar',  fmt(Math.abs(r.var_95)) + ' (' + (r.var_95/S0*100).toFixed(1) + '%)');
}}

// ── Rendu principal ───────────────────────────────────────────
function mcDraw() {{
  const cv  = document.getElementById('cvMC');
  if(!cv || !MC_RESULT) return;
  const ctx = cv.getContext('2d');
  const W   = cv.width, H = cv.height;
  if(W < 10 || H < 10) return;

  const r = MC_RESULT;

  // ── Données historiques à afficher (40 bougies visible max)
  const nHist    = Math.min(40, VIEW_END - VIEW_START, D.c.length);
  const histStart = D.c.length - nHist;
  const histC = D.c.slice(histStart);
  const histO = D.o.slice(histStart);
  const histH = D.h.slice(histStart);
  const histL = D.l.slice(histStart);

  // ── Range de prix : historique + toutes les bandes MC ──────
  const allPrices = [
    ...histH, ...histL,
    ...r.percs.p5, ...r.percs.p95,
  ];
  const rawMin = Math.min(...allPrices);
  const rawMax = Math.max(...allPrices);
  const pad    = (rawMax - rawMin) * 0.06 || rawMax * 0.02;
  const pMin   = rawMin - pad;
  const pMax   = rawMax + pad;
  const pRng   = pMax - pMin || 1;

  // ── Layout ─────────────────────────────────────────────────
  const PL = 4, PR = 70, PT = 8, PB = 20;
  const plotW = W - PL - PR;
  const plotH = H - PT - PB;

  // Nombre total de colonnes : historique + projection
  const totalCols = nHist + r.horizon;
  const CW        = plotW / totalCols;

  const toX = i  => PL + i * CW + CW * 0.5;
  const toY = p  => PT + (1 - (p - pMin) / pRng) * plotH;

  // ── Fond + grille ───────────────────────────────────────────
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W, H);

  ctx.strokeStyle = '#0F0F0F';
  ctx.lineWidth   = 1;
  for(let g = 0; g <= 5; g++) {{
    const y     = PT + g / 5 * plotH;
    const price = pMax - g / 5 * pRng;
    ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(W - PR, y); ctx.stroke();
    ctx.fillStyle  = '#2A2A2A';
    ctx.font       = '9px Share Tech Mono,monospace';
    ctx.textAlign  = 'left';
    ctx.fillText(fmt(price), W - PR + 6, y + 3);
  }}

  // ── Séparateur NOW ──────────────────────────────────────────
  const xNow = toX(nHist - 0.5);
  ctx.save();
  ctx.strokeStyle = 'rgba(250,190,44,0.25)';
  ctx.lineWidth   = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(xNow, PT); ctx.lineTo(xNow, H - PB); ctx.stroke();
  ctx.restore();
  ctx.fillStyle = 'rgba(250,190,44,0.45)';
  ctx.font      = '7px Share Tech Mono,monospace';
  ctx.textAlign = 'center';
  ctx.fillText('NOW', xNow, PT - 1);

  // ── Bougies historiques (Fan uniquement) ────────────────────
  if(MC_MODE !== 'histogram') {{
    for(let i = 0; i < nHist; i++) {{
      const o = histO[i], h = histH[i], l = histL[i], cl = histC[i];
      const bull = cl >= o;
      const x    = toX(i);
      const bw   = Math.max(1, CW * 0.65);
      ctx.strokeStyle = bull ? '#1A6B38' : '#7A2020';
      ctx.fillStyle   = bull ? '#00C853' : '#FF3B30';
      ctx.lineWidth   = 1;
      ctx.beginPath();
      ctx.moveTo(x, toY(h));
      ctx.lineTo(x, toY(l));
      ctx.stroke();
      const y1 = toY(Math.max(o, cl));
      const y2 = toY(Math.min(o, cl));
      ctx.fillRect(x - bw/2, y1, bw, Math.max(1, y2 - y1));
    }}
  }}

  // ── Ligne de prix courant ───────────────────────────────────
  const lastPrice = histC[histC.length - 1];
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.2)';
  ctx.lineWidth = 1; ctx.setLineDash([2,4]);
  ctx.beginPath();
  ctx.moveTo(PL, toY(lastPrice));
  ctx.lineTo(W - PR, toY(lastPrice));
  ctx.stroke();
  ctx.restore();

  // ── Branches MC ─────────────────────────────────────────────
  if(MC_MODE === 'fan') {{
    mcDrawFan(ctx, r, toX, toY, nHist, W, PR);
  }} else {{
    mcDrawHistogram(ctx, r, toX, toY, nHist, W, H, PR, PT, PB, pMin, pMax, pRng);
  }}
}}

function mcDrawFan(ctx, r, toX, toY, offset, W, PR) {{
  // Bandes de couleur : de l'extérieur vers l'intérieur
  const bands = [
    {{ lo: 'p5',  hi: 'p95', fill: 'rgba(250,190,44,0.05)' }},
    {{ lo: 'p10', hi: 'p90', fill: 'rgba(250,190,44,0.08)' }},
    {{ lo: 'p25', hi: 'p75', fill: 'rgba(250,190,44,0.12)' }},
  ];

  bands.forEach(b => {{
    ctx.beginPath();
    // Point de départ : prix courant (convergence)
    const xStart = toX(offset);
    const yStart = toY(r.S0);
    ctx.moveTo(xStart, yStart);
    // Bord haut
    for(let i = 0; i <= r.horizon; i++) {{
      ctx.lineTo(toX(offset + i), toY(r.percs[b.hi][i]));
    }}
    // Bord bas (retour)
    for(let i = r.horizon; i >= 0; i--) {{
      ctx.lineTo(toX(offset + i), toY(r.percs[b.lo][i]));
    }}
    ctx.closePath();
    ctx.fillStyle = b.fill;
    ctx.fill();
  }});

  // Lignes de percentile
  const lines = [
    {{ key: 'p95', color: 'rgba(0,200,83,0.85)',   lw: 1.5, dash: [] }},
    {{ key: 'p75', color: 'rgba(0,200,83,0.35)',   lw: 1,   dash: [3,3] }},
    {{ key: 'p50', color: 'rgba(250,190,44,0.9)',  lw: 2,   dash: [] }},
    {{ key: 'p25', color: 'rgba(255,59,48,0.35)',  lw: 1,   dash: [3,3] }},
    {{ key: 'p5',  color: 'rgba(255,59,48,0.85)',  lw: 1.5, dash: [] }},
  ];

  lines.forEach(l => {{
    ctx.save();
    ctx.strokeStyle = l.color; ctx.lineWidth = l.lw;
    ctx.setLineDash(l.dash);
    ctx.beginPath();
    for(let i = 0; i <= r.horizon; i++) {{
      const x = toX(offset + i), y = toY(r.percs[l.key][i]);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }}
    ctx.stroke();
    ctx.restore();
  }});

  // Labels à droite
  const labels = [
    {{ key: 'p95', color: '#00C853',  lbl: 'P95' }},
    {{ key: 'p50', color: '#FABE2C',  lbl: 'MED' }},
    {{ key: 'p5',  color: '#FF3B30',  lbl: 'P5'  }},
  ];
  const endX = toX(offset + r.horizon) + 4;
  ctx.font = '8px Share Tech Mono,monospace';
  ctx.textAlign = 'left';
  labels.forEach(l => {{
    ctx.fillStyle = l.color;
    ctx.fillText(l.lbl + ' ' + fmt(r.percs[l.key][r.horizon]), endX, toY(r.percs[l.key][r.horizon]) + 3);
  }});
}}

function mcDrawHistogram(ctx, r, toX, toY, offset, W, H, PR, PT, PB, pMin, pMax, pRng) {{
  const rawFinals = r.finals;
  if(!rawFinals || rawFinals.length === 0) return;

  const finals  = Array.from(rawFinals);
  const n       = finals.length;
  const S0      = r.S0;
  const plotH   = H - PT - PB;

  // ── Bornes de la zone MC (pleine largeur, collé à gauche) ───
  const xLeft  = 4;                    // bord gauche = bord du canvas
  const xRight = W - PR - 2;          // bord droit (avant labels)
  const maxBarW = xRight - xLeft;
  if(maxBarW <= 0) return;

  // ── Clip ──────────────────────────────────────────────────
  ctx.save();
  ctx.beginPath();
  ctx.rect(xLeft, PT, xRight - xLeft + PR, plotH);
  ctx.clip();

  // ── Binning ───────────────────────────────────────────────
  const N_BINS  = 48;
  const binSize = (pMax - pMin) / N_BINS;
  const counts  = new Array(N_BINS).fill(0);
  for(const v of finals) {{
    const b = Math.min(N_BINS - 1, Math.max(0, Math.floor((v - pMin) / binSize)));
    counts[b]++;
  }}
  const maxCount = Math.max(...counts) || 1;

  // ── Fond semi-transparent ─────────────────────────────────
  ctx.fillStyle = 'rgba(255,255,255,0.015)';
  ctx.fillRect(xLeft, PT, maxBarW, plotH);

  // ── Barres ───────────────────────────────────────────────
  const barH = Math.max(1, plotH / N_BINS - 0.5);
  for(let b = 0; b < N_BINS; b++) {{
    if(counts[b] === 0) continue;
    const barPrice = pMin + (b + 0.5) * binSize;
    const y        = toY(pMin + (b + 1) * binSize);
    const bw       = (counts[b] / maxCount) * maxBarW;
    const isBull   = barPrice >= S0;
    const alpha    = 0.15 + 0.65 * (counts[b] / maxCount);

    const grad = ctx.createLinearGradient(xLeft, 0, xLeft + bw, 0);
    if(isBull) {{
      grad.addColorStop(0, `rgba(0,200,83,${{(alpha * 0.3).toFixed(2)}})`);
      grad.addColorStop(1, `rgba(0,200,83,${{alpha.toFixed(2)}})`);
    }} else {{
      grad.addColorStop(0, `rgba(255,59,48,${{(alpha * 0.3).toFixed(2)}})`);
      grad.addColorStop(1, `rgba(255,59,48,${{alpha.toFixed(2)}})`);
    }}
    ctx.fillStyle = grad;
    ctx.fillRect(xLeft, y, bw, barH);

    // Tranche brillante droite
    ctx.fillStyle = isBull
      ? `rgba(0,230,100,${{(alpha * 0.5).toFixed(2)}})`
      : `rgba(255,80,60,${{(alpha * 0.5).toFixed(2)}})`;
    ctx.fillRect(xLeft + bw - 1, y, 1, barH);
  }}

  // ── Courbe de densité (KDE approximée) ────────────────────
  ctx.beginPath();
  let first = true;
  for(let b = 0; b < N_BINS; b++) {{
    const bw   = (counts[b] / maxCount) * maxBarW;
    const yMid = toY(pMin + (b + 0.5) * binSize);
    if(first) {{ ctx.moveTo(xLeft + bw, yMid); first = false; }}
    else ctx.lineTo(xLeft + bw, yMid);
  }}
  ctx.strokeStyle = 'rgba(250,190,44,0.6)';
  ctx.lineWidth   = 1.2;
  ctx.setLineDash([]);
  ctx.stroke();

  // ── Ligne S0 (prix actuel) ────────────────────────────────
  const yS0 = toY(S0);
  ctx.strokeStyle = 'rgba(255,255,255,0.2)';
  ctx.lineWidth   = 1;
  ctx.setLineDash([3, 4]);
  ctx.beginPath();
  ctx.moveTo(xLeft, yS0);
  ctx.lineTo(xRight, yS0);
  ctx.stroke();
  ctx.setLineDash([]);

  // ── Lignes de percentiles + labels ───────────────────────
  ctx.restore();   // libérer le clip pour écrire les labels à droite
  ctx.save();

  const annots = [
    {{ price: r.p5,   color: '#FF3B30', dash: [4,4], lbl: 'P5'  }},
    {{ price: r.p25,  color: '#FF7043', dash: [2,4], lbl: 'P25' }},
    {{ price: r.mean, color: '#4d9fff', dash: [3,3], lbl: 'MED' }},
    {{ price: r.p75,  color: '#66BB6A', dash: [2,4], lbl: 'P75' }},
    {{ price: r.p95,  color: '#00C853', dash: [4,4], lbl: 'P95' }},
  ];

  ctx.font = '8px Share Tech Mono,monospace';
  annots.forEach(a => {{
    const y = toY(a.price);
    if(y < PT || y > H - PB) return;

    // Ligne uniquement dans la zone MC (xLeft → xRight)
    ctx.save();
    ctx.beginPath();
    ctx.rect(xLeft, PT, xRight - xLeft, plotH);
    ctx.clip();
    ctx.strokeStyle = a.color;
    ctx.lineWidth   = 1;
    ctx.setLineDash(a.dash);
    ctx.beginPath();
    ctx.moveTo(xLeft, y);
    ctx.lineTo(xRight, y);
    ctx.stroke();
    ctx.restore();

    // Label à droite (hors clip)
    ctx.fillStyle = a.color;
    ctx.textAlign = 'left';
    ctx.setLineDash([]);
    ctx.fillText(a.lbl + ' ' + fmt(a.price), W - PR + 4, y + 3);
  }});

  // ── Encart stats ──────────────────────────────────────────
  const profitPct  = (finals.filter(v => v > S0).length / n * 100).toFixed(1);
  const lossPct    = (100 - parseFloat(profitPct)).toFixed(1);
  const isProfit   = parseFloat(profitPct) >= 50;
  const profitColor = '#00C853';
  const lossColor   = '#FF3B30';

  // Dimensions de l'encart
  const bx = xLeft + 8, by = PT + 8;
  const bw2 = 178, bh = 82;
  const pad = 10;

  // Fond avec dégradé subtil
  const bgGrad = ctx.createLinearGradient(bx, by, bx, by + bh);
  bgGrad.addColorStop(0, 'rgba(10,10,10,0.92)');
  bgGrad.addColorStop(1, 'rgba(0,0,0,0.88)');
  ctx.fillStyle = bgGrad;
  ctx.beginPath();
  ctx.roundRect(bx, by, bw2, bh, 4);
  ctx.fill();

  // Bordure colorée selon profit/perte
  ctx.strokeStyle = isProfit ? 'rgba(0,200,83,0.35)' : 'rgba(255,59,48,0.35)';
  ctx.lineWidth   = 1;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.roundRect(bx, by, bw2, bh, 4);
  ctx.stroke();

  // Barre colorée à gauche (accent)
  ctx.fillStyle = isProfit ? 'rgba(0,200,83,0.7)' : 'rgba(255,59,48,0.7)';
  ctx.beginPath();
  ctx.roundRect(bx, by, 3, bh, [4, 0, 0, 4]);
  ctx.fill();

  // Titre
  ctx.font      = '8px Share Tech Mono,monospace';
  ctx.fillStyle = '#555';
  ctx.textAlign = 'left';
  ctx.letterSpacing = '1px';
  ctx.fillText('DISTRIBUTION FINALE', bx + pad, by + 16);

  // Séparateur
  ctx.strokeStyle = '#1e1e1e';
  ctx.lineWidth   = 1;
  ctx.beginPath();
  ctx.moveTo(bx + pad, by + 22); ctx.lineTo(bx + bw2 - pad, by + 22);
  ctx.stroke();

  // Ligne PROFIT
  const pBarW = Math.round((parseFloat(profitPct) / 100) * (bw2 - pad * 2));
  ctx.fillStyle = 'rgba(0,200,83,0.12)';
  ctx.fillRect(bx + pad, by + 27, pBarW, 16);
  ctx.fillStyle = profitColor;
  ctx.font      = '10px Share Tech Mono,monospace';
  ctx.fillText('▲ PROFIT', bx + pad + 4, by + 39);
  ctx.textAlign = 'right';
  ctx.font      = '11px Share Tech Mono,monospace';
  ctx.fillText(profitPct + '%', bx + bw2 - pad, by + 39);

  // Ligne PERTE
  ctx.textAlign = 'left';
  const lBarW = Math.round((parseFloat(lossPct) / 100) * (bw2 - pad * 2));
  ctx.fillStyle = 'rgba(255,59,48,0.10)';
  ctx.fillRect(bx + pad, by + 47, lBarW, 16);
  ctx.fillStyle = lossColor;
  ctx.font      = '10px Share Tech Mono,monospace';
  ctx.fillText('▼ PERTE ', bx + pad + 4, by + 59);
  ctx.textAlign = 'right';
  ctx.font      = '11px Share Tech Mono,monospace';
  ctx.fillText(lossPct + '%', bx + bw2 - pad, by + 59);

  // Mini barre de progression globale
  ctx.textAlign = 'left';
  const trackY = by + bh - 12;
  ctx.fillStyle = 'rgba(255,59,48,0.3)';
  ctx.fillRect(bx + pad, trackY, bw2 - pad * 2, 4);
  ctx.fillStyle = 'rgba(0,200,83,0.7)';
  ctx.fillRect(bx + pad, trackY, pBarW, 4);

  ctx.restore();
}}

// ════════════════════════════════════════════════════════
//  KELLY CRITERION — Calculs JS (interactif)
//  Valeurs initiales auto-calibrées depuis Python/NumPy
// ════════════════════════════════════════════════════════

let KELLY_MODE = 'trade';

function kellySetMode(mode) {{
  KELLY_MODE = mode;
  const tradeTab = document.getElementById('kelly_tab_trade');
  const retTab   = document.getElementById('kelly_tab_ret');
  const tradeInp = document.getElementById('kelly_inputs_trade');
  const retInp   = document.getElementById('kelly_inputs_ret');
  if(!tradeTab || !retTab) return;

  const onStyle  = 'flex:1;padding:5px 0;text-align:center;font-size:8px;letter-spacing:1px;cursor:pointer;border:1px solid rgba(0,255,65,0.4);background:rgba(0,255,65,0.08);color:#00FF41;transition:all .15s;';
  const offStyle = 'flex:1;padding:5px 0;text-align:center;font-size:8px;letter-spacing:1px;cursor:pointer;border:1px solid #2a2a2a;background:transparent;color:#555;transition:all .15s;';

  if (mode === 'trade') {{
    tradeTab.style.cssText = onStyle;
    retTab.style.cssText   = offStyle;
    if(tradeInp) tradeInp.style.display = 'block';
    if(retInp)   retInp.style.display   = 'none';
  }} else {{
    retTab.style.cssText   = onStyle;
    tradeTab.style.cssText = offStyle;
    if(retInp)   retInp.style.display   = 'block';
    if(tradeInp) tradeInp.style.display = 'none';
  }}
  calcKelly();
}}

function calcKelly() {{
  const capital = parseFloat(document.getElementById('kelly_capital')?.value) || 10000;
  let f_full = 0, edge = 0, ruin = null, sharpe = null;

  if (KELLY_MODE === 'trade') {{
    const p = (parseFloat(document.getElementById('kelly_p')?.value) || 50) / 100;
    const b =  parseFloat(document.getElementById('kelly_b')?.value) || 1.5;
    const q = 1 - p;
    f_full = (p * b - q) / b;
    edge   = (p * b - q) * 100;
    ruin   = f_full > 0.001 ? Math.pow(q / p, 1 / f_full) * 100 : 100;
  }} else {{
    const mu    = (parseFloat(document.getElementById('kelly_mu')?.value)    || 50)  / 100;
    const sigma = (parseFloat(document.getElementById('kelly_sigma')?.value) || 80)  / 100;
    f_full = sigma > 0 ? mu / (sigma * sigma) : 0;
    edge   = mu * 100;
    sharpe = sigma > 0 ? (mu / sigma) : 0;
  }}

  f_full = Math.max(0, Math.min(1, f_full || 0));
  const f_half    = f_full * 0.5;
  const f_quarter = f_full * 0.25;
  const pos_size  = capital * f_half;

  const fmt4 = v => (v != null && isFinite(v)) ? v.toFixed(4) : '—';
  const fmtP = v => (v != null && isFinite(v)) ? v.toFixed(2) + '%' : '—';
  const fmtD = v => (v != null && isFinite(v))
    ? '$' + v.toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}})
    : '—';

  const setTxtK = (id, v) => {{ const e = document.getElementById(id); if(e) e.textContent = v; }};
  const setColK = (id, c) => {{ const e = document.getElementById(id); if(e) e.style.color  = c; }};

  setTxtK('kelly_r_full',    fmt4(f_full));
  setTxtK('kelly_r_half',    fmt4(f_half));
  setTxtK('kelly_r_quarter', fmt4(f_quarter));
  setTxtK('kelly_r_pct',     fmtP(f_half * 100));
  setTxtK('kelly_r_size',    fmtD(pos_size));
  setTxtK('kelly_r_edge',    fmtP(edge));
  setTxtK('kelly_r_ruin',    ruin   != null ? fmtP(Math.min(ruin, 100)) : '—');
  setTxtK('kelly_r_sharpe',  sharpe != null ? sharpe.toFixed(2) : '—');

  const col = f_full > 0.01 ? '#00FF41' : '#FF2222';
  setColK('kelly_r_full', col);
  setColK('kelly_r_pct',  col);
  setColK('kelly_r_size', col);
  setColK('kelly_r_edge', f_full > 0.01 ? '#00E676' : '#FF6B6B');
}}

// ── Resize handle ─────────────────────────────────────────────
(function() {{
  const bar = document.getElementById('mcResizeBar');
  if(!bar) return;
  let active = false, startY = 0, startH = 0;

  bar.addEventListener('mousedown', e => {{
    active = true; startY = e.clientY; startH = MC_HEIGHT;
    e.preventDefault();
    document.body.style.userSelect = 'none';
  }});

  window.addEventListener('mousemove', e => {{
    if(!active) return;
    // Tirer vers le haut = agrandir (delta négatif = on monte)
    const delta  = startY - e.clientY;
    MC_HEIGHT    = Math.min(MC_MAX_H, Math.max(MC_MIN_H, startH + delta));
    const panel  = document.getElementById('mcPanel');
    panel.style.height = MC_HEIGHT + 'px';
    mcResizeCanvas();
    if(MC_RESULT) mcDraw();
  }});

  window.addEventListener('mouseup', () => {{
    if(active) {{
      active = false;
      document.body.style.userSelect = '';
      setupCanvas(); render();
    }}
  }});
}})();

window.addEventListener('resize', ()=>{{ setupCanvas(); render(); if(MC_OPEN){{ mcResizeCanvas(); if(MC_RESULT) mcDraw(); }} }});
</script>
</body>
</html>"""
