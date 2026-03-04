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
    show_header: bool = True,
    show_volume: bool = True,
    show_bottom: bool = True,
    pair_label: str   = None,
    exchange: str     = "CoinGecko · Spot",
    live_sim: bool    = True,   # simulation temps réel si pas d'API live
) -> str:

    try:
        candles, is_live = fetch_ohlcv(symbol=symbol, interval=interval, limit=limit)
    except Exception as e:
        print(f"[chart_module] {e}")
        candles, is_live = [], False

    pair_disp  = pair_label or (
        symbol.upper() + "/USD" if symbol.lower() in ["bitcoin","ethereum","solana","dogecoin","cardano","ripple","polkadot","avalanche-2","chainlink","litecoin","cosmos","near","uniswap","binancecoin","matic-network"]
        else symbol.replace("USDT","/USDT").replace("-USD","/USD")
    )
    c          = COLORS
    cd         = json.dumps(candles)
    status_txt = "● LIVE" if is_live else "◎ SIM"
    status_cls = "live"   if is_live else "sim"
    run_sim    = "true"   if not is_live else "false"  # simulation seulement si pas live

    # Diagnostic affiché dans la console du navigateur
    data_info  = f"CoinGecko · {len(candles)} bougies · is_live={is_live}" if is_live else f"MOCK DATA · {len(candles)} bougies (CoinGecko indisponible)"

    # Interval en secondes pour la simulation
    iv_sec = {
        "1m":60,"5m":300,"15m":900,"30m":1800,
        "1h":3600,"4h":14400,"1d":86400,"1w":604800
    }.get(interval.lower(), 14400)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
:root{{
  --bg:{c['bg']};--surface:{c['surface']};--surface2:{c['surface2']};
  --border:{c['border']};--border2:{c['border2']};--border3:#333;
  --text:{c['text']};--text2:{c['text2']};--muted:{c['muted']};
  --faint:{c['faint']};--fainter:{c['fainter']};
  --orange:{c['orange']};--yellow:{c['yellow']};
  --green:{c['green']};--green2:{c['green2']};
  --red:{c['red']};--red2:{c['red2']};
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{background:var(--bg);color:var(--text);
  font-family:'IBM Plex Mono',monospace;font-size:12px;
  width:100%;overflow:hidden;}}

/* ── HEADER 1 ── */
.hdr1{{display:flex;align-items:stretch;background:var(--surface);
  border-bottom:1px solid var(--border2);height:52px;overflow:hidden;}}
.logo{{font-weight:700;font-size:13px;letter-spacing:2px;padding:0 18px;
  border-right:1px solid var(--border2);text-transform:uppercase;
  display:flex;align-items:center;white-space:nowrap;}}
.logo span{{color:var(--orange);}}
.hdr-pair{{display:flex;flex-direction:column;justify-content:center;
  padding:0 18px;border-right:1px solid var(--border2);}}
.pair-name{{font-size:14px;font-weight:700;letter-spacing:1px;}}
.pair-exch{{font-size:9px;color:var(--faint);letter-spacing:1px;margin-top:2px;}}
.hdr-price{{display:flex;flex-direction:column;justify-content:center;
  padding:0 18px;border-right:1px solid var(--border2);min-width:170px;}}
.price-val{{font-size:20px;font-weight:700;letter-spacing:-0.5px;transition:color .2s;}}
.price-chg{{font-size:10px;margin-top:2px;}}
.hdr-ohlc{{display:flex;gap:22px;padding:0 18px;align-items:center;
  border-right:1px solid var(--border2);}}
.ohlc-item{{display:flex;flex-direction:column;gap:1px;}}
.ohlc-lbl{{font-size:8px;color:var(--faint);letter-spacing:1.5px;text-transform:uppercase;}}
.ohlc-val{{font-size:11px;font-weight:600;}}

/* ── HEADER 2 ── */
.hdr2{{display:flex;align-items:stretch;background:var(--surface);
  border-bottom:1px solid var(--border2);height:36px;}}
.tf-group{{display:flex;padding:0 8px;border-right:1px solid var(--border2);
  align-items:center;gap:1px;}}
.tf-btn{{padding:3px 8px;border:none;background:transparent;color:var(--faint);
  font-family:'IBM Plex Mono',monospace;font-size:10px;cursor:pointer;
  text-transform:uppercase;border-bottom:2px solid transparent;transition:all .12s;height:100%;}}
.tf-btn:hover{{color:var(--text);background:rgba(255,255,255,0.04);}}
.tf-btn.active{{color:var(--orange);border-bottom-color:var(--orange);}}
.hdr2-right{{margin-left:auto;display:flex;align-items:stretch;}}
.stat-pill{{padding:0 14px;border-left:1px solid var(--border2);
  display:flex;flex-direction:column;justify-content:center;gap:1px;}}
.stat-pill .lbl{{font-size:8px;color:var(--faint);letter-spacing:1.5px;text-transform:uppercase;}}
.stat-pill .val{{font-size:11px;font-weight:600;color:var(--yellow);}}

/* ── MODE DROPDOWN ── */
.mode-wrap{{position:relative;border-left:1px solid var(--border2);}}
.mode-btn{{display:flex;align-items:center;gap:8px;padding:0 14px;height:100%;
  cursor:pointer;background:transparent;border:none;border-bottom:2px solid var(--text2);
  font-family:'IBM Plex Mono',monospace;min-width:110px;transition:background .12s;}}
.mode-btn:hover{{background:var(--surface2);}}
.mode-info{{display:flex;flex-direction:column;gap:1px;text-align:left;}}
.mode-lbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--text2);}}
.mode-sub{{font-size:8px;color:var(--faint);}}
.mode-caret{{margin-left:auto;font-size:8px;color:var(--faint);transition:transform .15s;}}
.mode-caret.open{{transform:rotate(180deg);}}
.mode-btn[data-mode="pro"]  .mode-lbl{{color:var(--orange);}}
.mode-btn[data-mode="quant"].mode-lbl{{color:var(--yellow);}}
.mode-btn[data-mode="pro"]  {{border-bottom-color:var(--orange);}}
.mode-btn[data-mode="quant"]{{border-bottom-color:var(--yellow);}}
.mode-dd{{display:none;position:absolute;top:100%;right:0;
  background:var(--surface);border:1px solid var(--border2);
  min-width:155px;z-index:9999;box-shadow:0 8px 20px rgba(0,0,0,0.8);}}
.mode-dd.open{{display:block;}}
.mode-opt{{display:flex;align-items:center;gap:10px;padding:9px 14px;cursor:pointer;
  border-bottom:1px solid var(--border);transition:background .1s;}}
.mode-opt:last-child{{border-bottom:none;}}
.mode-opt:hover{{background:var(--surface2);}}
.mode-opt.active{{background:rgba(255,149,0,0.06);}}
.mo-lbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;flex:1;}}
.mo-desc{{font-size:9px;color:var(--faint);}}
.mo-check{{font-size:10px;color:var(--orange);opacity:0;}}
.mode-opt.active .mo-check{{opacity:1;}}

/* ── LABEL BAR ── */
.lbar{{display:flex;align-items:center;gap:14px;padding:0 14px;
  background:var(--surface);border-bottom:1px solid var(--border);
  font-size:10px;color:var(--faint);height:28px;flex-shrink:0;}}
.lbar b{{color:var(--text2);font-weight:600;}}
.lbar .tag{{margin-left:auto;color:var(--orange);font-size:9px;
  letter-spacing:1px;text-transform:uppercase;}}
.api-badge{{font-size:8px;padding:1px 7px;border-radius:2px;letter-spacing:1px;}}
.api-badge.sim{{color:var(--orange);background:rgba(255,149,0,0.08);border:1px solid rgba(255,149,0,0.3);}}
.api-badge.live{{color:var(--green2);background:rgba(0,255,173,0.07);border:1px solid var(--green2);}}
.pulse{{animation:pulse 1.5s infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:0.4;}}}}

/* ── CANVAS ── */
#cvMain{{display:block;background:var(--bg);cursor:crosshair;}}
#cvVol {{display:block;background:var(--bg);}}

/* ── BOTTOM BAR ── */
.bbar{{display:flex;border-top:1px solid var(--border2);background:var(--surface);height:52px;}}
.bstat{{flex:1;padding:0 14px;border-right:1px solid var(--border);
  display:flex;flex-direction:column;justify-content:center;gap:2px;}}
.bstat:last-child{{border-right:none;}}
.bstat .lbl{{font-size:8px;color:var(--faint);letter-spacing:1.5px;text-transform:uppercase;}}
.bstat .val{{font-size:13px;font-weight:700;}}
.bstat .sub{{font-size:9px;color:var(--fainter);}}
::-webkit-scrollbar{{width:4px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--border3);border-radius:2px;}}
</style>
</head>
<body>

<!-- HEADER 1 -->
<div class="hdr1">
  <div class="logo">AM<span>.</span>Terminal</div>
  <div class="hdr-pair">
    <div class="pair-name">{pair_disp}</div>
    <div class="pair-exch">{exchange}</div>
  </div>
  <div class="hdr-price">
    <div class="price-val" id="curPrice" style="color:var(--green2)">—</div>
    <div class="price-chg" id="curChg"   style="color:var(--green2)">—</div>
  </div>
  <div class="hdr-ohlc">
    <div class="ohlc-item"><div class="ohlc-lbl">Open</div> <div class="ohlc-val" id="ho" style="color:var(--text2)">—</div></div>
    <div class="ohlc-item"><div class="ohlc-lbl">High</div> <div class="ohlc-val" id="hh" style="color:var(--green2)">—</div></div>
    <div class="ohlc-item"><div class="ohlc-lbl">Low</div>  <div class="ohlc-val" id="hl" style="color:var(--red2)">—</div></div>
    <div class="ohlc-item"><div class="ohlc-lbl">Close</div><div class="ohlc-val" id="hc" style="color:var(--text2)">—</div></div>
  </div>
</div>

<!-- HEADER 2 -->
<div class="hdr2">
  <div class="tf-group">
    <button class="tf-btn" onclick="setTF(this,'1m')">1M</button>
    <button class="tf-btn" onclick="setTF(this,'5m')">5M</button>
    <button class="tf-btn" onclick="setTF(this,'15m')">15M</button>
    <button class="tf-btn" onclick="setTF(this,'1h')">1H</button>
    <button class="tf-btn active" onclick="setTF(this,'4h')">4H</button>
    <button class="tf-btn" onclick="setTF(this,'1d')">1D</button>
    <button class="tf-btn" onclick="setTF(this,'1w')">1W</button>
  </div>
  <div class="hdr2-right">
    <div class="stat-pill"><div class="lbl">24H Vol</div><div class="val" id="statVol">—</div></div>
    <div class="stat-pill"><div class="lbl">24H High</div><div class="val" id="stat24h" style="color:var(--green2)">—</div></div>
    <div class="stat-pill"><div class="lbl">24H Low</div> <div class="val" id="stat24l" style="color:var(--red2)">—</div></div>
    <div class="mode-wrap">
      <button class="mode-btn" id="modeBtn" data-mode="normal" onclick="toggleDD()">
        <div class="mode-info">
          <div class="mode-lbl" id="modeLbl">Normal</div>
          <div class="mode-sub" id="modeSub">Standard</div>
        </div>
        <span class="mode-caret" id="modeCaret">&#9660;</span>
      </button>
      <div class="mode-dd" id="modeDD">
        <div class="mode-opt active" onclick="pickMode('normal','Normal','Standard')">
          <div><div class="mo-lbl" style="color:var(--text2)">Normal</div><div class="mo-desc">Vue standard</div></div>
          <span class="mo-check">&#10003;</span>
        </div>
        <div class="mode-opt" onclick="pickMode('pro','Pro','Avancée')">
          <div><div class="mo-lbl" style="color:var(--orange)">Pro</div><div class="mo-desc">Vue avancée</div></div>
          <span class="mo-check">&#10003;</span>
        </div>
        <div class="mode-opt" onclick="pickMode('quant','Quant','Algorithmique')">
          <div><div class="mo-lbl" style="color:var(--yellow)">Quant</div><div class="mo-desc">Algorithmique</div></div>
          <span class="mo-check">&#10003;</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- LABEL BAR -->
<div class="lbar">
  <span>O <b id="co">—</b></span>
  <span>H <b id="ch">—</b></span>
  <span>L <b id="cl">—</b></span>
  <span>C <b id="cc">—</b></span>
  <span class="api-badge {status_cls} pulse" id="apiBadge">{status_txt}</span>
  <span class="tag">Canvas · {pair_disp} · {interval.upper()}</span>
</div>

<!-- CANVAS PRINCIPAL -->
<canvas id="cvMain"></canvas>

<!-- VOLUME -->
<canvas id="cvVol"></canvas>

<!-- BOTTOM BAR -->
<div class="bbar">
  <div class="bstat"><div class="lbl">24H High</div><div class="val" id="b_hi" style="color:var(--green2)">—</div></div>
  <div class="bstat"><div class="lbl">24H Low</div> <div class="val" id="b_lo" style="color:var(--red2)">—</div></div>
  <div class="bstat"><div class="lbl">Variation</div><div class="val" id="b_chg">—</div></div>
  <div class="bstat"><div class="lbl">Volume total</div><div class="val" id="b_vol">—</div></div>
</div>

<script>
// ════════════════════════════════════════════════════════
//  DONNÉES HISTORIQUES (injectées depuis Python)
// ════════════════════════════════════════════════════════
const HISTORICAL = {cd};
const IV_SEC     = {iv_sec};   // durée d'une bougie en secondes

// Copie mutable des données
const D = {{
  t: HISTORICAL.map(r=>r.t),
  o: HISTORICAL.map(r=>r.o),
  h: HISTORICAL.map(r=>r.h),
  l: HISTORICAL.map(r=>r.l),
  c: HISTORICAL.map(r=>r.c),
  v: HISTORICAL.map(r=>r.v),
}};

// ════════════════════════════════════════════════════════
//  SIMULATION TEMPS RÉEL
//  Met à jour la dernière bougie en continu ET
//  crée une nouvelle bougie à chaque fin d'intervalle
// ════════════════════════════════════════════════════════
const SIM_SPEED  = 400;       // ms entre chaque tick (0.4s ≈ fluide)
const VOLATILITY = 0.0008;    // volatilité par tick (~0.08%)

let simPrice  = D.c[D.c.length-1];   // prix courant
let candleStart = D.t[D.t.length-1]; // timestamp début bougie courante
let prevPrice = simPrice;

function simTick() {{
  const now = Math.floor(Date.now()/1000);

  // ── Calcul du nouveau prix (mouvement brownien) ──
  const drift     = (Math.random() - 0.499) * VOLATILITY;
  const momentum  = (simPrice - prevPrice) * 0.15;  // légère inertie
  const noise     = (Math.random() - 0.5) * simPrice * VOLATILITY * 0.5;
  prevPrice       = simPrice;
  simPrice        = Math.max(simPrice * (1 + drift) + momentum + noise, 1);

  const last = D.t.length - 1;

  // ── Nouvelle bougie si l'intervalle est écoulé ──
  const nextCandleTime = candleStart + IV_SEC;
  if(now >= nextCandleTime) {{
    candleStart = now;
    D.t.push(now);
    D.o.push(simPrice);
    D.h.push(simPrice);
    D.l.push(simPrice);
    D.c.push(simPrice);
    D.v.push(0);
    // Fenêtre glissante : garder max 300 bougies
    if(D.t.length > 300) {{
      D.t.shift(); D.o.shift(); D.h.shift();
      D.l.shift(); D.c.shift(); D.v.shift();
      if(VIEW_START > 0) VIEW_START--;
    }}
    // Avancer la vue si on était sur la dernière bougie
    if(VIEW_END >= D.t.length-1) VIEW_END = D.t.length;
  }} else {{
    // ── Mise à jour de la bougie courante ──
    const i = D.t.length - 1;
    D.c[i] = simPrice;
    if(simPrice > D.h[i]) D.h[i] = simPrice;
    if(simPrice < D.l[i]) D.l[i] = simPrice;
    D.v[i] += Math.random() * 0.5;  // volume qui monte
  }}

  // ── Mise à jour header prix ──
  const priceEl = document.getElementById('curPrice');
  const chgEl   = document.getElementById('curChg');
  const open0   = D.o[0];
  const pct     = ((simPrice - open0) / open0 * 100).toFixed(2);
  const bull     = simPrice >= open0;

  if(priceEl) {{
    priceEl.textContent = fmt(simPrice);
    priceEl.style.color = bull ? 'var(--green2)' : 'var(--red2)';
    // Flash sur changement de direction
    priceEl.style.textShadow = simPrice > prevPrice
      ? '0 0 8px rgba(0,200,83,0.6)'
      : '0 0 8px rgba(255,59,48,0.6)';
    setTimeout(()=>{{ if(priceEl) priceEl.style.textShadow='none'; }}, 300);
  }}
  if(chgEl) {{
    chgEl.textContent = (pct>=0?'▲ +':'▼ ')+pct+'%';
    chgEl.style.color = bull ? 'var(--green2)' : 'var(--red2)';
  }}

  updateStats();
  render();
}}

// ════════════════════════════════════════════════════════
//  RENDU CANVAS
// ════════════════════════════════════════════════════════
const cvMain = document.getElementById('cvMain');
const cvVol  = document.getElementById('cvVol');
const ctxM   = cvMain.getContext('2d');
const ctxV   = cvVol.getContext('2d');

const PAD = {{l:10, r:74, t:10, b:26}};
let VIEW_START = 0;
let VIEW_END   = 0;
let HOVER_IDX  = -1;
let isDragging = false, dragStartX = 0, dragStartView = 0;

const $   = id => document.getElementById(id);
const fmt = v => {{
  if(v==null||isNaN(v)) return '—';
  return v>=1000
    ? v.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}})
    : v.toFixed(v<1?4:2);
}};
const fmtV = v => v>=1e9?(v/1e9).toFixed(2)+'B':v>=1e6?(v/1e6).toFixed(1)+'M':v.toFixed(0);
const setTxt = (id,v) => {{ const e=$(id); if(e) e.textContent=v; }};
const setCol = (id,c) => {{ const e=$(id); if(e) e.style.color=c; }};

function setupCanvas() {{
  const W = window.innerWidth || document.documentElement.clientWidth || 900;
  const totalH  = window.innerHeight || {height};
  const usedH   = 52+36+28+52+70;
  const mainH   = Math.max(totalH - usedH, 180);
  cvMain.width  = W; cvMain.height = mainH;
  cvVol.width   = W; cvVol.height  = 70;
  cvMain.style.width=W+'px'; cvMain.style.height=mainH+'px';
  cvVol.style.width =W+'px'; cvVol.style.height ='70px';
}}

function drawMain() {{
  const W=cvMain.width, H=cvMain.height;
  const ctx=ctxM;
  ctx.clearRect(0,0,W,H);

  const N = VIEW_END - VIEW_START;
  if(N<1) return;

  const ts=D.t.slice(VIEW_START,VIEW_END);
  const os=D.o.slice(VIEW_START,VIEW_END);
  const hs=D.h.slice(VIEW_START,VIEW_END);
  const ls=D.l.slice(VIEW_START,VIEW_END);
  const cs=D.c.slice(VIEW_START,VIEW_END);

  const minP = Math.min(...ls)*0.9995;
  const maxP = Math.max(...hs)*1.0005;
  const rng  = maxP-minP || 1;

  const cw  = (W-PAD.l-PAD.r)/N;
  const gap = Math.max(0.08, Math.min(0.3, 2/N));
  const bw  = Math.max(1.5, cw*(1-gap));

  const toX = i => PAD.l + i*cw + cw/2;
  const toY = p => PAD.t + (maxP-p)/rng*(H-PAD.t-PAD.b);

  // ── Grille ──────────────────────────────────────────
  const steps=6;
  for(let s=0;s<=steps;s++) {{
    const y = PAD.t + s*(H-PAD.t-PAD.b)/steps;
    ctx.strokeStyle='#1a1a1a'; ctx.lineWidth=1;
    ctx.beginPath(); ctx.moveTo(PAD.l,y); ctx.lineTo(W-PAD.r,y); ctx.stroke();
    const price = maxP - s*rng/steps;
    ctx.fillStyle='#555'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='left';
    ctx.fillText(fmt(price), W-PAD.r+4, y+3);
  }}

  // ── Axe temps ───────────────────────────────────────
  const ticks=Math.min(8,Math.floor(N/10));
  ctx.fillStyle='#555'; ctx.font='9px IBM Plex Mono,monospace'; ctx.textAlign='center';
  for(let t=0;t<=ticks;t++) {{
    const i=Math.floor(t*(N-1)/Math.max(ticks,1));
    const d=new Date(ts[i]*1000);
    const lbl=`${{d.getMonth()+1}}/${{d.getDate()}} ${{String(d.getHours()).padStart(2,'0')}}h`;
    ctx.fillText(lbl, toX(i), H-4);
  }}

  // ── Ligne de prix courant (last price) ─────────────
  const lastClose = cs[N-1];
  const py = toY(lastClose);
  const bull_last = cs[N-1] >= os[N-1];
  ctx.strokeStyle = bull_last ? 'rgba(0,200,83,0.4)' : 'rgba(255,59,48,0.4)';
  ctx.lineWidth=1; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(PAD.l,py); ctx.lineTo(W-PAD.r,py); ctx.stroke();
  ctx.setLineDash([]);
  // Label prix à droite
  const lblCol = bull_last ? '#00C853' : '#FF3B30';
  ctx.fillStyle=lblCol;
  ctx.fillRect(W-PAD.r+2, py-8, PAD.r-4, 16);
  ctx.fillStyle='#000'; ctx.font='bold 9px IBM Plex Mono,monospace'; ctx.textAlign='left';
  ctx.fillText(fmt(lastClose), W-PAD.r+4, py+3);

  // ── Bougies ─────────────────────────────────────────
  for(let i=0;i<N;i++) {{
    const x  = toX(i);
    const oy = toY(os[i]), hy=toY(hs[i]), ly=toY(ls[i]), cy=toY(cs[i]);
    const bull = cs[i]>=os[i];

    // Mèche
    ctx.strokeStyle = bull ? '#00C853' : '#FF3B30';
    ctx.lineWidth   = Math.max(1, bw*0.08);
    ctx.beginPath(); ctx.moveTo(x,hy); ctx.lineTo(x,ly); ctx.stroke();

    // Corps
    const bTop=Math.min(oy,cy), bH=Math.max(1.5,Math.abs(cy-oy));
    if(bull) {{
      ctx.strokeStyle='#00C853'; ctx.lineWidth=1;
      ctx.strokeRect(x-bw/2,bTop,bw,bH);
      ctx.fillStyle='rgba(0,200,83,0.18)';
      ctx.fillRect(x-bw/2,bTop,bw,bH);
    }} else {{
      ctx.fillStyle='#FF3B30';
      ctx.fillRect(x-bw/2,bTop,bw,bH);
    }}

    // Dernière bougie — halo animé
    if(i===N-1) {{
      ctx.strokeStyle=bull?'rgba(0,200,83,0.5)':'rgba(255,59,48,0.5)';
      ctx.lineWidth=1.5;
      const glow=2+Math.sin(Date.now()/200)*1;
      ctx.strokeRect(x-bw/2-glow, bTop-glow, bw+glow*2, bH+glow*2);
    }}
  }}

  // ── Crosshair hover ─────────────────────────────────
  if(HOVER_IDX>=0 && HOVER_IDX<N) {{
    const x=toX(HOVER_IDX);
    const ri=VIEW_START+HOVER_IDX;
    ctx.strokeStyle='rgba(255,149,0,0.6)'; ctx.lineWidth=1; ctx.setLineDash([3,3]);
    ctx.beginPath(); ctx.moveTo(x,PAD.t); ctx.lineTo(x,H-PAD.b); ctx.stroke();
    ctx.setLineDash([]);
    // Tooltip
    const tp={{
      o:fmt(D.o[ri]), h:fmt(D.h[ri]),
      l:fmt(D.l[ri]), c:fmt(D.c[ri]),
    }};
    setTxt('co',tp.o); setTxt('ch',tp.h);
    setTxt('cl',tp.l); setTxt('cc',tp.c);
    setTxt('ho',tp.o); setTxt('hh',tp.h);
    setTxt('hl',tp.l); setTxt('hc',tp.c);
  }}
}}

function drawVol() {{
  const W=cvVol.width, H=cvVol.height;
  const ctx=ctxV;
  ctx.clearRect(0,0,W,H);
  const N=VIEW_END-VIEW_START;
  if(!N) return;
  const vs=D.v.slice(VIEW_START,VIEW_END);
  const maxV=Math.max(...vs)||1;
  const cw=(W-PAD.l-PAD.r)/N;
  ctx.fillStyle='#333'; ctx.font='8px IBM Plex Mono,monospace'; ctx.textAlign='left';
  ctx.fillText('VOLUME',4,10);
  for(let i=0;i<N;i++) {{
    const bh=(vs[i]/maxV)*(H-14);
    ctx.fillStyle=D.c[VIEW_START+i]>=D.o[VIEW_START+i]
      ?'rgba(0,200,83,0.5)':'rgba(255,59,48,0.5)';
    ctx.fillRect(PAD.l+i*cw+1, H-bh, Math.max(1,cw-2), bh);
  }}
}}

function render() {{ drawMain(); drawVol(); }}

function updateStats() {{
  const N=D.c.length; if(!N) return;
  const last  = D.c[N-1];
  const h24   = Math.max(...D.h), l24=Math.min(...D.l);
  const vol   = D.v.reduce((a,b)=>a+b,0);
  const chg   = ((last-D.o[0])/D.o[0]*100).toFixed(2);
  const bull   = parseFloat(chg)>=0;
  const clr    = bull?'var(--green2)':'var(--red2)';

  // Prix courant — depuis la dernière bougie (sera remplacé par fetchLivePrice)
  setTxt('curPrice', fmt(last));
  setTxt('curChg',   (bull?'▲ +':'▼ ')+chg+'%');
  setCol('curPrice', clr);
  setCol('curChg',   clr);

  setTxt('statVol',  fmtV(vol));
  setTxt('stat24h',  fmt(h24));
  setTxt('stat24l',  fmt(l24));
  setTxt('b_hi',     fmt(h24));
  setTxt('b_lo',     fmt(l24));
  setTxt('b_chg',    (bull?'+':'')+chg+'%');
  setTxt('b_vol',    fmtV(vol));
  setCol('b_chg',    clr);
}}

// ════════════════════════════════════════════════════════
//  INTERACTIONS SOURIS
// ════════════════════════════════════════════════════════
cvMain.addEventListener('mousemove',e=>{{
  if(isDragging) {{
    const dx=e.clientX-dragStartX;
    const N=VIEW_END-VIEW_START;
    const cw=(cvMain.width-PAD.l-PAD.r)/N;
    const shift=Math.round(-dx/cw);
    const totalN=D.t.length;
    let s=Math.max(0,Math.min(totalN-N, dragStartView+shift));
    VIEW_START=s; VIEW_END=s+N;
    render(); return;
  }}
  const rect=cvMain.getBoundingClientRect();
  const x=e.clientX-rect.left;
  const N=VIEW_END-VIEW_START;
  const cw=(cvMain.width-PAD.l-PAD.r)/N;
  HOVER_IDX=Math.max(0,Math.min(N-1,Math.floor((x-PAD.l)/cw)));
  drawMain();
}});

cvMain.addEventListener('mousedown',e=>{{
  isDragging=true; dragStartX=e.clientX; dragStartView=VIEW_START;
  cvMain.style.cursor='grabbing';
}});
window.addEventListener('mouseup',()=>{{
  isDragging=false; cvMain.style.cursor='crosshair';
}});
cvMain.addEventListener('mouseleave',()=>{{
  HOVER_IDX=-1; drawMain();
}});

// Scroll zoom
cvMain.addEventListener('wheel',e=>{{
  e.preventDefault();
  const N=VIEW_END-VIEW_START;
  const factor=e.deltaY>0?1.12:0.88;
  const newN=Math.max(20,Math.min(D.t.length,Math.round(N*factor)));
  const center=HOVER_IDX>=0?VIEW_START+HOVER_IDX:Math.floor((VIEW_START+VIEW_END)/2);
  let s=Math.max(0,center-Math.floor(newN/2));
  let en=s+newN;
  if(en>D.t.length){{en=D.t.length;s=Math.max(0,en-newN);}}
  VIEW_START=s; VIEW_END=en;
  render();
}},{{passive:false}});

// ════════════════════════════════════════════════════════
//  TIMEFRAME
// ════════════════════════════════════════════════════════
function setTF(btn,tf) {{
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  // Avec une vraie API : recharger les données ici
  console.log('TF →',tf);
}}

// ════════════════════════════════════════════════════════
//  MODE DROPDOWN
// ════════════════════════════════════════════════════════
function toggleDD(){{
  $('modeDD').classList.toggle('open');
  $('modeCaret').classList.toggle('open');
}}
function pickMode(key,lbl,sub){{
  const btn=$('modeBtn'); btn.setAttribute('data-mode',key);
  $('modeLbl').textContent=lbl; $('modeSub').textContent=sub;
  document.querySelectorAll('.mode-opt').forEach((el,i)=>{{
    el.classList.toggle('active',['normal','pro','quant'][i]===key);
  }});
  $('modeDD').classList.remove('open');
  $('modeCaret').classList.remove('open');
}}
document.addEventListener('click',e=>{{
  const w=document.querySelector('.mode-wrap');
  if(w&&!w.contains(e.target)){{
    $('modeDD').classList.remove('open');
    $('modeCaret').classList.remove('open');
  }}
}});

// ════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════
const IS_LIVE  = {run_sim} === false;   // true = vraies données CoinGecko
const RUN_SIM  = {run_sim};             // false = on ne simule pas si données réelles
console.log('[Arthur Trading]', '{data_info}');
console.log('[Arthur Trading] IS_LIVE =', IS_LIVE, '| Bougies =', D.t.length);

function init() {{
  setupCanvas();
  VIEW_START = Math.max(0, D.t.length-120);
  VIEW_END   = D.t.length;
  render();
  updateStats();

  // Toujours tenter le prix live au démarrage
  fetchLivePrice();

  if(RUN_SIM) {{
    console.log('[AM.Terminal] Mode simulation actif (CoinGecko non dispo)');
    setInterval(simTick, 400);
    setInterval(()=>{{ if(HOVER_IDX<0) drawMain(); }}, 100);
  }} else {{
    console.log('[AM.Terminal] Mode LIVE — rafraîchissement prix toutes les 15s');
    setInterval(()=>{{ if(HOVER_IDX<0) drawMain(); }}, 150);
    setInterval(fetchLivePrice, 15000);
  }}
}}

// ── FETCH PRIX EN TEMPS RÉEL ─────────────────────────────
async function fetchLivePrice() {{
  try {{
    const coinId = '{symbol}';
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${{coinId}}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_24h_high=true&include_24h_low=true`;
    const res  = await fetch(url);
    const json = await res.json();
    const data = json[coinId];
    if(!data) return;

    const price   = data.usd;
    const chg24   = data.usd_24h_change?.toFixed(2);
    const vol24   = data.usd_24h_vol;
    const high24  = data.usd_24h_high;
    const low24   = data.usd_24h_low;
    const bull     = chg24 >= 0;
    const clr      = bull ? 'var(--green2)' : 'var(--red2)';

    // Mettre à jour le close de la dernière bougie avec le vrai prix
    const last = D.t.length - 1;
    if(last >= 0) {{
      D.c[last] = price;
      if(price > D.h[last]) D.h[last] = price;
      if(price < D.l[last]) D.l[last] = price;
    }}

    // Header prix
    const pe = document.getElementById('curPrice');
    const ce = document.getElementById('curChg');
    if(pe) {{
      pe.textContent = fmt(price);
      pe.style.color = clr;
      pe.style.textShadow = bull
        ? '0 0 10px rgba(0,200,83,0.5)'
        : '0 0 10px rgba(255,59,48,0.5)';
      setTimeout(()=>{{ if(pe) pe.style.textShadow='none'; }}, 500);
    }}
    if(ce) {{
      ce.textContent = (bull?'▲ +':'▼ ')+chg24+'%';
      ce.style.color = clr;
    }}

    // Stats header
    const fmtV = v => v>=1e9?(v/1e9).toFixed(2)+'B':v>=1e6?(v/1e6).toFixed(1)+'M':v?.toFixed(0)??'—';
    setTxt('statVol',  fmtV(vol24));
    setTxt('stat24h',  fmt(high24));
    setTxt('stat24l',  fmt(low24));
    setTxt('b_hi',     fmt(high24));
    setTxt('b_lo',     fmt(low24));
    setTxt('b_chg',    (bull?'+':'')+chg24+'%');
    setTxt('b_vol',    fmtV(vol24));
    setCol('b_chg',    clr);

    // Badge LIVE
    const badge = document.getElementById('apiBadge');
    if(badge) {{ badge.textContent = '● LIVE'; badge.className='api-badge live pulse'; }}

    render();
    console.log(`[Arthur Trading] Prix live: ${{fmt(price)}} (${{chg24}}%)`);
  }} catch(e) {{
    console.warn('[Arthur Trading] Prix live indisponible:', e.message);
  }}
}}

window.addEventListener('load', init);
window.addEventListener('resize',()=>{{ setupCanvas(); render(); }});
</script>
</body>
</html>"""
