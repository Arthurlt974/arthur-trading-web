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

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
:root{{
  --bg:#131722;--surface:#1e222d;--surface2:#2a2e39;
  --border:#2a2e39;--border2:#363a45;
  --text:#d1d4dc;--text2:#b2b5be;--muted:#787b86;
  --faint:#50535e;--fainter:#363a45;
  --orange:#ff9800;--yellow:#f0b429;
  --green:#26a69a;--green2:#00e676;
  --red:#ef5350;--red2:#ff5252;
  --bull:#26a69a;--bear:#ef5350;
  --bull-bg:rgba(38,166,154,0.15);--bear-bg:rgba(239,83,80,0.15);
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{
  background:var(--bg);color:var(--text);
  font-family:'IBM Plex Mono',monospace;font-size:12px;
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
  font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;cursor:pointer;
  border-radius:3px;transition:all .1s;text-transform:uppercase;letter-spacing:0.5px;}}
.tf-btn:hover{{background:var(--surface2);color:var(--text);}}
.tf-btn.active{{background:rgba(255,152,0,0.12);color:var(--orange);}}
.tb-sep{{width:1px;height:18px;background:var(--border2);margin:0 4px;}}
.indicator-btn{{padding:3px 9px;border:1px solid var(--border2);background:transparent;
  color:var(--muted);font-family:'IBM Plex Mono',monospace;font-size:10px;cursor:pointer;
  border-radius:3px;transition:all .1s;}}
.indicator-btn:hover{{background:var(--surface2);color:var(--text);}}
.indicator-btn.on{{color:var(--orange);border-color:rgba(255,152,0,0.4);}}

/* ── CHART ZONE ── */
.chart-zone{{flex:1;display:flex;flex-direction:column;position:relative;overflow:hidden;}}
#cvMain{{display:block;cursor:crosshair;}}
.vol-sep{{height:1px;background:var(--border);flex-shrink:0;}}
#cvVol{{display:block;background:var(--bg);flex-shrink:0;}}

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
  <button class="tf-btn {'active' if active_tf=='1m' else ''}" onclick="setTF(this,'1m')">1m</button>
  <button class="tf-btn {'active' if active_tf=='5m' else ''}" onclick="setTF(this,'5m')">5m</button>
  <button class="tf-btn {'active' if active_tf=='15m' else ''}" onclick="setTF(this,'15m')">15m</button>
  <button class="tf-btn {'active' if active_tf=='1h' else ''}" onclick="setTF(this,'1h')">1h</button>
  <button class="tf-btn {'active' if active_tf=='4h' else ''}" onclick="setTF(this,'4h')">4h</button>
  <button class="tf-btn {'active' if active_tf=='1d' else ''}" onclick="setTF(this,'1D')">1D</button>
  <button class="tf-btn {'active' if active_tf=='1w' else ''}" onclick="setTF(this,'1W')">1W</button>
  <div class="tb-sep"></div>
  <button class="indicator-btn {'on' if show_ma else ''}" id="btnMA" onclick="toggleMA()">MA</button>
  <button class="indicator-btn {'on' if show_volume else ''}" id="btnVol" onclick="toggleVol()">Vol</button>
  <button class="indicator-btn {'on' if show_bb else ''}" id="btnBB" onclick="toggleBB()">BB</button>
</div>

<!-- ZONE CHART -->
<div class="chart-zone">
  <canvas id="cvMain"></canvas>
  <div class="vol-sep"></div>
  <canvas id="cvVol"></canvas>
</div>

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
//  DONNÉES
// ════════════════════════════════════════════════════════
const HISTORICAL = {cd};
const IV_SEC     = {iv_sec};

const D = {{
  t: HISTORICAL.map(r=>r.t),
  o: HISTORICAL.map(r=>r.o),
  h: HISTORICAL.map(r=>r.h),
  l: HISTORICAL.map(r=>r.l),
  c: HISTORICAL.map(r=>r.c),
  v: HISTORICAL.map(r=>r.v),
}};

// ════════════════════════════════════════════════════════
//  CONFIG RENDU
// ════════════════════════════════════════════════════════
const PAD  = {{l:0, r:72, t:8, b:24}};
const VPAH = 80;   // hauteur volume
let showMA  = {ma_init_js};
let showVol = {vol_init_js};
let showBB  = {bb_init_js};

let VIEW_START = 0, VIEW_END = 0;
let HOVER_IDX  = -1, HOVER_Y = -1;
let isDragging = false, dragStartX = 0, dragStartView = 0;

// ════════════════════════════════════════════════════════
//  SIMULATION
// ════════════════════════════════════════════════════════
let simActive   = true;
let simPrice    = D.c[D.c.length-1] || 100;
let candleStart = D.t[D.t.length-1] || Math.floor(Date.now()/1000);
let prevPrice   = simPrice;
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
  const W  = window.innerWidth  || 900;
  const fullH = window.innerHeight || 600;
  // Hauteurs fixes des zones UI
  const hdrH  = 46, tbH = 34, bbarH = 36, sepH = 1;
  const volH  = showVol ? VPAH : 0;
  const mainH = Math.max(fullH - hdrH - tbH - bbarH - volH - sepH, 150);

  cvMain.width=W; cvMain.height=mainH;
  cvVol.width=W;  cvVol.height=volH;
  cvMain.style.width=W+'px'; cvMain.style.height=mainH+'px';
  cvVol.style.width=W+'px';  cvVol.style.height=volH+'px';
  cvVol.style.display=showVol?'block':'none';
  document.querySelector('.vol-sep').style.display=showVol?'block':'none';
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
  const toY=p=>PAD.t+(hi-p)/rng*(H-PAD.t-PAD.b);

  // ── FOND ──
  ctx.fillStyle='#131722';
  ctx.fillRect(0,0,W,H);

  // ── GRILLE HORIZONTALE ──
  const gridSteps=6;
  for(let s=0;s<=gridSteps;s++) {{
    const y=PAD.t+s*(H-PAD.t-PAD.b)/gridSteps;
    const price=hi-s*rng/gridSteps;
    ctx.strokeStyle='#1e222d'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    // Prix axe droit
    ctx.fillStyle='#787b86'; ctx.font='10px IBM Plex Mono,monospace';
    ctx.textAlign='left'; ctx.fillText(fmt(price), W-PAD.r+6, y+4);
  }}

  // ── GRILLE VERTICALE + AXE TEMPS ──
  ctx.fillStyle='#787b86'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  const nTicks=Math.min(10,Math.max(3,Math.floor(N/15)));
  const prevMonth={{val:-1}};
  for(let t=0;t<=nTicks;t++) {{
    const i=Math.floor(t*(N-1)/Math.max(nTicks,1));
    const x=toX(i);
    const d=new Date(ts[i]*1000);
    ctx.strokeStyle='#1e222d'; ctx.lineWidth=1;
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
      ctx.strokeStyle='rgba(255,152,0,0.4)'; ctx.lineWidth=1; ctx.setLineDash([3,3]); ctx.stroke(); ctx.setLineDash([]);
    }});
    ctx.beginPath(); let s2=false;
    for(let i=0;i<N;i++) {{
      if(bbM[i]===null) continue;
      s2?ctx.lineTo(toX(i),toY(bbM[i])):ctx.moveTo(toX(i),toY(bbM[i]));
      s2=true;
    }}
    ctx.strokeStyle='rgba(255,152,0,0.5)'; ctx.lineWidth=1; ctx.stroke();
  }}

  // ── MOVING AVERAGES ──
  if(showMA) {{
    const maConf=[
      {{p:20,  color:'rgba(255,200,50,0.85)',  w:1.2}},
      {{p:50,  color:'rgba(33,150,243,0.85)',  w:1.2}},
      {{p:200, color:'rgba(255,82,82,0.85)',   w:1.5}},
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
    ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='left';
    [{{'p':20,'c':'rgba(255,200,50,0.85)'}},{{'p':50,'c':'rgba(33,150,243,0.85)'}},{{'p':200,'c':'rgba(255,82,82,0.85)'}}].forEach((m,i)=>{{
      ctx.fillStyle=m.c;
      ctx.fillText(`MA${{m.p}}`, 8+i*52, 18);
    }});
  }}

  // ── BOUGIES ──
  for(let i=0;i<N;i++) {{
    const x=toX(i);
    const oy=toY(os[i]), hy=toY(hs[i]), ly=toY(ls[i]), cy=toY(cs[i]);
    const bull=cs[i]>=os[i];
    const bullCol='#26a69a', bearCol='#ef5350';
    const col=bull?bullCol:bearCol;

    // Mèche
    const wickW=Math.max(1, BW*0.1);
    ctx.strokeStyle=col; ctx.lineWidth=wickW;
    ctx.beginPath(); ctx.moveTo(x,hy); ctx.lineTo(x,ly); ctx.stroke();

    // Corps
    const top=Math.min(oy,cy);
    const bH =Math.max(1, Math.abs(cy-oy));
    const hw =Math.max(1, BW/2);

    if(bull) {{
      // Haussier : contour + fill semi-transparent (style TradingView)
      ctx.fillStyle='rgba(38,166,154,0.15)';
      ctx.fillRect(x-hw, top, hw*2, bH);
      ctx.strokeStyle=bullCol; ctx.lineWidth=1.5;
      ctx.strokeRect(x-hw, top, hw*2, bH);
    }} else {{
      // Baissier : plein
      ctx.fillStyle=bearCol;
      ctx.fillRect(x-hw, top, hw*2, bH);
    }}

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
  ctx.strokeStyle=lastBull?'rgba(38,166,154,0.5)':'rgba(239,83,80,0.5)';
  ctx.lineWidth=1; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(0,py); ctx.lineTo(W-PAD.r,py); ctx.stroke();
  ctx.setLineDash([]);
  // Tag prix
  const tagCol=lastBull?'#26a69a':'#ef5350';
  ctx.fillStyle=tagCol;
  ctx.beginPath();
  ctx.roundRect(W-PAD.r+2, py-9, PAD.r-4, 18, 2);
  ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold 9px IBM Plex Mono,monospace'; ctx.textAlign='left';
  ctx.fillText(fmt(lastC), W-PAD.r+5, py+4);

  // ── CROSSHAIR ──
  if(HOVER_IDX>=0 && HOVER_IDX<N) {{
    const x=toX(HOVER_IDX);
    // Ligne verticale
    ctx.strokeStyle='rgba(132,142,156,0.4)'; ctx.lineWidth=1; ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(x,PAD.t); ctx.lineTo(x,H); ctx.stroke();
    // Ligne horizontale
    if(HOVER_Y>0) {{
      ctx.beginPath(); ctx.moveTo(0,HOVER_Y); ctx.lineTo(W-PAD.r,HOVER_Y); ctx.stroke();
      // Tag prix crosshair à droite
      const hp=hi-(HOVER_Y-PAD.t)/((H-PAD.t-PAD.b))*rng;
      ctx.fillStyle='#363a45';
      ctx.beginPath(); ctx.roundRect(W-PAD.r+2,HOVER_Y-9,PAD.r-4,18,2); ctx.fill();
      ctx.fillStyle='#d1d4dc'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='left';
      ctx.fillText(fmt(hp), W-PAD.r+5, HOVER_Y+4);
    }}
    // Label date en bas
    const d=new Date(ts[HOVER_IDX]*1000);
    const dateLbl=fmtDate(ts[HOVER_IDX]);
    ctx.fillStyle='#363a45'; ctx.textAlign='center';
    const tw=ctx.measureText(dateLbl).width+12;
    ctx.beginPath(); ctx.roundRect(x-tw/2, H-PAD.b+2, tw, 16, 2); ctx.fill();
    ctx.fillStyle='#d1d4dc'; ctx.font='9px IBM Plex Mono,monospace';
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

function drawVol() {{
  if(!showVol) return;
  const W=cvVol.width, H=cvVol.height;
  const ctx=ctxV;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#131722'; ctx.fillRect(0,0,W,H);

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
  ctx.strokeStyle='rgba(255,152,0,0.7)'; ctx.lineWidth=1; ctx.stroke();

  // Label
  ctx.fillStyle='#50535e'; ctx.font='8px IBM Plex Mono,monospace';
  ctx.textAlign='left'; ctx.fillText('VOLUME', 4, 10);
}}

function render() {{ drawMain(); drawVol(); }}

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
  drawMain();
}});

cvMain.addEventListener('mousedown', e => {{
  isDragging=true; dragStartX=e.clientX; dragStartView=VIEW_START;
  cvMain.style.cursor='grabbing';
}});
window.addEventListener('mouseup', () => {{
  isDragging=false; cvMain.style.cursor='crosshair';
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

// ════════════════════════════════════════════════════════
//  TIMEFRAME & INDICATEURS
// ════════════════════════════════════════════════════════
function setTF(btn,tf) {{
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  console.log('[AM.Terminal] TF →', tf);
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
  ws.onopen=()=>{{ simActive=false; console.log('[AM.Terminal] WS Binance connecté'); }};
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

function init() {{
  setupCanvas();
  VIEW_START=Math.max(0,D.t.length-120);
  VIEW_END=D.t.length;
  render();
  updateStats();
  startBinanceWS();
  if(RUN_SIM) {{
    setInterval(simTick, 400);
    setInterval(()=>{{ if(HOVER_IDX<0) drawMain(); }}, 100);
  }} else {{
    setInterval(()=>{{ if(HOVER_IDX<0) drawMain(); }}, 200);
  }}
}}

window.addEventListener('load', init);
window.addEventListener('resize', ()=>{{ setupCanvas(); render(); }});
</script>
</body>
</html>"""
