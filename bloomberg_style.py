"""
bloomberg_style.py
Style Bloomberg Terminal complet pour AM-Trading Terminal
À importer dans App.py : from bloomberg_style import apply_bloomberg_style, bloomberg_header
"""

import streamlit as st
import streamlit.components.v1 as components


def apply_bloomberg_style():
    """Applique le CSS Bloomberg Terminal complet."""
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">

    <style>
    /* ═══════════════════════════════════════════
       ROOT — VARIABLES BLOOMBERG
    ═══════════════════════════════════════════ */
    :root {
        --bb-black:      #000000;
        --bb-dark:       #0a0a0a;
        --bb-panel:      #111111;
        --bb-border:     #1e1e1e;
        --bb-orange:     #ff6600;
        --bb-orange-dim: #cc4400;
        --bb-orange-glow:#ff8833;
        --bb-yellow:     #ffcc00;
        --bb-green:      #00ff41;
        --bb-red:        #ff2222;
        --bb-blue:       #0088ff;
        --bb-white:      #e8e8e8;
        --bb-gray:       #666666;
        --bb-gray-light: #999999;
        --bb-font:       'Share Tech Mono', 'Courier New', monospace;
        --bb-font-head:  'Rajdhani', monospace;
    }

    /* ═══════════════════════════════════════════
       RESET GLOBAL
    ═══════════════════════════════════════════ */
    * { box-sizing: border-box; }

    html, body, .stApp {
        background-color: var(--bb-black) !important;
        color: var(--bb-white) !important;
        font-family: var(--bb-font) !important;
    }

    /* Cache le header Streamlit par défaut */
    header[data-testid="stHeader"],
    .stApp [data-testid="stDecoration"],
    #MainMenu, footer { display: none !important; }

    /* ═══════════════════════════════════════════
       SIDEBAR — BLOOMBERG LEFT PANEL
    ═══════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background-color: #080808 !important;
        border-right: 2px solid var(--bb-orange) !important;
        min-width: 240px !important;
        padding-top: 0 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
    }

    /* Logo sidebar */
    [data-testid="stSidebar"]::before {
        content: "AM TERMINAL";
        display: block;
        background: var(--bb-orange);
        color: #000;
        font-family: var(--bb-font-head);
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 3px;
        padding: 10px 16px;
        text-align: center;
        border-bottom: 1px solid #cc4400;
    }

    /* Textes sidebar */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] span {
        color: var(--bb-orange) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }

    /* Selectbox sidebar */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #111 !important;
        border: 1px solid var(--bb-orange) !important;
        color: var(--bb-orange) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
        border-radius: 0 !important;
    }

    /* Radio sidebar */
    [data-testid="stSidebar"] .stRadio label {
        color: var(--bb-gray-light) !important;
        font-size: 11px !important;
        padding: 4px 8px !important;
        border-left: 2px solid transparent !important;
        transition: all 0.1s !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        color: var(--bb-orange) !important;
        border-left: 2px solid var(--bb-orange) !important;
        background: #1a0a00 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"] ~ span {
        color: var(--bb-orange) !important;
    }

    /* Séparateur sidebar */
    [data-testid="stSidebar"] hr {
        border-color: var(--bb-orange-dim) !important;
        margin: 6px 0 !important;
    }

    /* ═══════════════════════════════════════════
       CONTENU PRINCIPAL
    ═══════════════════════════════════════════ */
    .main .block-container {
        padding: 8px 12px 12px 12px !important;
        max-width: 100% !important;
        background: var(--bb-black) !important;
    }

    /* Titres */
    h1 {
        font-family: var(--bb-font-head) !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        color: var(--bb-orange) !important;
        text-transform: uppercase !important;
        letter-spacing: 4px !important;
        border-bottom: 1px solid var(--bb-orange) !important;
        padding-bottom: 6px !important;
        margin-bottom: 10px !important;
        text-shadow: 0 0 8px rgba(255,102,0,0.4) !important;
    }
    h2 {
        font-family: var(--bb-font-head) !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        color: var(--bb-orange) !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        border-left: 3px solid var(--bb-orange) !important;
        padding-left: 8px !important;
        margin: 12px 0 6px 0 !important;
    }
    h3 {
        font-family: var(--bb-font) !important;
        font-size: 12px !important;
        font-weight: 400 !important;
        color: var(--bb-yellow) !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        margin: 8px 0 4px 0 !important;
    }
    p, span, div, label {
        font-family: var(--bb-font) !important;
        color: var(--bb-white) !important;
    }

    /* ═══════════════════════════════════════════
       MÉTRIQUES — BLOOMBERG STYLE
    ═══════════════════════════════════════════ */
    [data-testid="metric-container"] {
        background: var(--bb-panel) !important;
        border: 1px solid var(--bb-border) !important;
        border-top: 2px solid var(--bb-orange) !important;
        border-radius: 0 !important;
        padding: 8px 12px !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 9px !important;
        color: var(--bb-gray) !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-family: var(--bb-font) !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 18px !important;
        color: var(--bb-white) !important;
        font-family: var(--bb-font) !important;
        font-weight: 400 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 11px !important;
        font-family: var(--bb-font) !important;
    }

    /* ═══════════════════════════════════════════
       BOUTONS — BLOOMBERG KEYS
    ═══════════════════════════════════════════ */
    .stButton > button {
        background-color: #1a0a00 !important;
        color: var(--bb-orange) !important;
        border: 1px solid var(--bb-orange) !important;
        border-radius: 0 !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
        font-weight: 400 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        padding: 6px 16px !important;
        transition: all 0.1s !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background-color: var(--bb-orange) !important;
        color: #000 !important;
        box-shadow: 0 0 12px rgba(255,102,0,0.5) !important;
    }
    .stButton > button:active {
        background-color: var(--bb-orange-dim) !important;
        transform: scale(0.98) !important;
    }

    /* ═══════════════════════════════════════════
       INPUTS — TERMINAL STYLE
    ═══════════════════════════════════════════ */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #0d0d0d !important;
        border: 1px solid #333 !important;
        border-bottom: 1px solid var(--bb-orange) !important;
        border-radius: 0 !important;
        color: var(--bb-white) !important;
        font-family: var(--bb-font) !important;
        font-size: 12px !important;
        padding: 6px 10px !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--bb-orange) !important;
        box-shadow: 0 0 0 1px var(--bb-orange) !important;
        outline: none !important;
    }
    .stTextInput label, .stNumberInput label,
    .stTextArea label, .stSelectbox label {
        color: var(--bb-gray) !important;
        font-size: 9px !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-family: var(--bb-font) !important;
    }

    /* ═══════════════════════════════════════════
       SELECTBOX — TERMINAL DROPDOWN
    ═══════════════════════════════════════════ */
    .stSelectbox > div > div {
        background-color: #0d0d0d !important;
        border: 1px solid #333 !important;
        border-bottom: 1px solid var(--bb-orange) !important;
        border-radius: 0 !important;
        color: var(--bb-white) !important;
        font-family: var(--bb-font) !important;
        font-size: 12px !important;
    }

    /* ═══════════════════════════════════════════
       TABS — BLOOMBERG FUNCTION KEYS
    ═══════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        background: #000 !important;
        border-bottom: 1px solid var(--bb-orange) !important;
        gap: 0 !important;
        padding: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: #0a0a0a !important;
        border: 1px solid #222 !important;
        border-bottom: none !important;
        border-radius: 0 !important;
        color: var(--bb-gray) !important;
        font-family: var(--bb-font) !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 6px 16px !important;
        margin-right: 2px !important;
        transition: all 0.1s !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--bb-orange) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border-color: var(--bb-orange) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: #1a0a00 !important;
        color: var(--bb-orange) !important;
    }

    /* ═══════════════════════════════════════════
       DATAFRAME / TABLE
    ═══════════════════════════════════════════ */
    .stDataFrame, [data-testid="stDataFrame"] {
        border: 1px solid var(--bb-border) !important;
        border-radius: 0 !important;
    }
    .stDataFrame thead tr th {
        background: #1a0a00 !important;
        color: var(--bb-orange) !important;
        font-family: var(--bb-font) !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        border-bottom: 1px solid var(--bb-orange) !important;
        padding: 6px 10px !important;
    }
    .stDataFrame tbody tr td {
        background: var(--bb-dark) !important;
        color: var(--bb-white) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
        border-bottom: 1px solid #1a1a1a !important;
        padding: 5px 10px !important;
    }
    .stDataFrame tbody tr:hover td {
        background: #1a0a00 !important;
        color: var(--bb-orange) !important;
    }

    /* ═══════════════════════════════════════════
       EXPANDER — BLOOMBERG PANEL
    ═══════════════════════════════════════════ */
    .streamlit-expanderHeader {
        background: #0d0d0d !important;
        border: 1px solid #222 !important;
        border-left: 3px solid var(--bb-orange) !important;
        border-radius: 0 !important;
        color: var(--bb-orange) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 8px 12px !important;
    }
    .streamlit-expanderHeader:hover {
        background: #1a0a00 !important;
    }
    .streamlit-expanderContent {
        background: #080808 !important;
        border: 1px solid #1a1a1a !important;
        border-top: none !important;
        border-radius: 0 !important;
        padding: 12px !important;
    }

    /* ═══════════════════════════════════════════
       ALERTS / MESSAGES
    ═══════════════════════════════════════════ */
    .stSuccess {
        background: #001a00 !important;
        border: 1px solid var(--bb-green) !important;
        border-left: 4px solid var(--bb-green) !important;
        border-radius: 0 !important;
        color: var(--bb-green) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
    }
    .stError {
        background: #1a0000 !important;
        border: 1px solid var(--bb-red) !important;
        border-left: 4px solid var(--bb-red) !important;
        border-radius: 0 !important;
        color: var(--bb-red) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
    }
    .stWarning {
        background: #1a1000 !important;
        border: 1px solid var(--bb-yellow) !important;
        border-left: 4px solid var(--bb-yellow) !important;
        border-radius: 0 !important;
        color: var(--bb-yellow) !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
    }
    .stInfo {
        background: #001020 !important;
        border: 1px solid var(--bb-blue) !important;
        border-left: 4px solid var(--bb-blue) !important;
        border-radius: 0 !important;
        color: #66aaff !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
    }

    /* ═══════════════════════════════════════════
       SLIDER
    ═══════════════════════════════════════════ */
    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background: var(--bb-orange) !important;
        border: 2px solid var(--bb-orange) !important;
        border-radius: 0 !important;
    }
    .stSlider [data-baseweb="slider"] div[data-testid="stSlider"] {
        background: #222 !important;
    }

    /* ═══════════════════════════════════════════
       CHECKBOX
    ═══════════════════════════════════════════ */
    .stCheckbox label span {
        color: var(--bb-white) !important;
        font-size: 11px !important;
    }
    .stCheckbox [data-baseweb="checkbox"] [data-checked] {
        background: var(--bb-orange) !important;
        border-color: var(--bb-orange) !important;
    }

    /* ═══════════════════════════════════════════
       PROGRESS BAR
    ═══════════════════════════════════════════ */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--bb-orange-dim), var(--bb-orange)) !important;
        border-radius: 0 !important;
    }
    .stProgress > div > div {
        background: #1a1a1a !important;
        border-radius: 0 !important;
    }

    /* ═══════════════════════════════════════════
       DIVIDER
    ═══════════════════════════════════════════ */
    hr {
        border: none !important;
        border-top: 1px solid #1e1e1e !important;
        margin: 10px 0 !important;
    }

    /* ═══════════════════════════════════════════
       SCROLLBAR — BLOOMBERG DARK
    ═══════════════════════════════════════════ */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #080808; }
    ::-webkit-scrollbar-thumb { background: var(--bb-orange-dim); border-radius: 0; }
    ::-webkit-scrollbar-thumb:hover { background: var(--bb-orange); }

    /* ═══════════════════════════════════════════
       MULTISELECT
    ═══════════════════════════════════════════ */
    .stMultiSelect [data-baseweb="tag"] {
        background: #1a0a00 !important;
        border: 1px solid var(--bb-orange) !important;
        border-radius: 0 !important;
        color: var(--bb-orange) !important;
        font-family: var(--bb-font) !important;
        font-size: 10px !important;
    }

    /* ═══════════════════════════════════════════
       SPINNER
    ═══════════════════════════════════════════ */
    .stSpinner > div {
        border-color: var(--bb-orange) transparent transparent transparent !important;
    }

    /* ═══════════════════════════════════════════
       SIDEBAR INFO BOX
    ═══════════════════════════════════════════ */
    [data-testid="stSidebar"] .stInfo {
        background: #050505 !important;
        border-color: #333 !important;
        font-size: 10px !important;
        padding: 6px !important;
    }

    /* ═══════════════════════════════════════════
       DOWNLOAD BUTTON
    ═══════════════════════════════════════════ */
    .stDownloadButton > button {
        background: #001a00 !important;
        color: var(--bb-green) !important;
        border: 1px solid var(--bb-green) !important;
        border-radius: 0 !important;
        font-family: var(--bb-font) !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }
    .stDownloadButton > button:hover {
        background: var(--bb-green) !important;
        color: #000 !important;
    }

    /* ═══════════════════════════════════════════
       SCAN LINES EFFECT (Bloomberg CRT feel)
    ═══════════════════════════════════════════ */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 0, 0, 0.03) 2px,
            rgba(0, 0, 0, 0.03) 4px
        );
        pointer-events: none;
        z-index: 9999;
    }

    /* ═══════════════════════════════════════════
       COLUMN BORDERS
    ═══════════════════════════════════════════ */
    [data-testid="column"] {
        border-right: 1px solid #111;
        padding: 0 8px !important;
    }
    [data-testid="column"]:last-child {
        border-right: none !important;
    }

    /* Caption / footnotes */
    .stCaption, small {
        color: var(--bb-gray) !important;
        font-size: 9px !important;
        font-family: var(--bb-font) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }

    </style>
    """, unsafe_allow_html=True)


def bloomberg_header(watchlist_string=""):
    """
    Affiche le header Bloomberg Terminal en haut de l'app.
    watchlist_string : string HTML avec les tickers déjà formatés
    """
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    header_html = f"""
    <div style="
        background: #000;
        border-bottom: 2px solid #ff6600;
        padding: 0;
        margin-bottom: 8px;
        font-family: 'Share Tech Mono', 'Courier New', monospace;
    ">
        <!-- TOP BAR -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 14px;
            background: #0a0a0a;
            border-bottom: 1px solid #1a1a1a;
        ">
            <!-- LOGO -->
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="
                    background: #ff6600;
                    color: #000;
                    font-family: 'Rajdhani', monospace;
                    font-weight: 700;
                    font-size: 18px;
                    letter-spacing: 3px;
                    padding: 3px 12px;
                    clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 100%, 0 100%);
                ">AM</div>
                <div>
                    <span style="color:#ff6600; font-size:13px; font-weight:700; letter-spacing:2px;">TRADING TERMINAL</span>
                    <span style="color:#444; font-size:9px; margin-left:8px;">v2.0 PRO</span>
                </div>
            </div>

            <!-- STATUS INDICATORS -->
            <div style="display:flex; gap:20px; align-items:center;">
                <div style="text-align:center;">
                    <div style="color:#666; font-size:8px; letter-spacing:1px;">SYSTEM</div>
                    <div style="color:#00ff41; font-size:10px;">● ONLINE</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#666; font-size:8px; letter-spacing:1px;">DATA</div>
                    <div style="color:#00ff41; font-size:10px;">● LIVE</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#666; font-size:8px; letter-spacing:1px;">TIME (REU)</div>
                    <div style="color:#ff6600; font-size:10px;">{now}</div>
                </div>
                <div style="
                    background: #ff6600;
                    color: #000;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 4px 10px;
                    letter-spacing: 1px;
                ">LA RÉUNION UTC+4</div>
            </div>
        </div>

        <!-- TICKER MARQUEE -->
        <div style="
            background: #000;
            overflow: hidden;
            padding: 5px 0;
            border-top: 1px solid #1a1a1a;
            position: relative;
        ">
            <div style="
                display: inline-block;
                white-space: nowrap;
                animation: bbmarquee 35s linear infinite;
                font-size: 11px;
                letter-spacing: 1px;
            ">
                {watchlist_string if watchlist_string else '<span style="color:#444;">— CHARGEMENT DES DONNÉES MARCHÉ —</span>'}
            </div>
        </div>

        <!-- FUNCTION KEY BAR -->
        <div style="
            display: flex;
            background: #050505;
            border-top: 1px solid #1a1a1a;
            padding: 4px 8px;
            gap: 4px;
            flex-wrap: wrap;
        ">
            {''.join([f'<div style="background:#111; border:1px solid #1e1e1e; color:#666; font-size:9px; padding:2px 8px; letter-spacing:1px; cursor:default;">{k}</div>'
                for k in ["F1 HELP","F2 EQUITY","F3 FIXED","F4 FX","F5 CMDTY","F6 INDEX","F7 NEWS","F8 CRYPTO","F9 ECON","ESC BACK","GO <GO>"]])}
        </div>
    </div>

    <style>
    @keyframes bbmarquee {{
        0%   {{ transform: translateX(100vw); }}
        100% {{ transform: translateX(-100%); }}
    }}
    </style>
    """
    components.html(header_html, height=120, scrolling=False)


def bloomberg_panel(title, content_html, color="#ff6600", height=None):
    """Crée un panel style Bloomberg avec titre et contenu."""
    height_style = f"height:{height}px; overflow:auto;" if height else ""
    st.markdown(f"""
        <div style="
            border: 1px solid #1e1e1e;
            border-top: 2px solid {color};
            background: #0a0a0a;
            margin-bottom: 8px;
            {height_style}
        ">
            <div style="
                background: #111;
                border-bottom: 1px solid #1e1e1e;
                padding: 5px 10px;
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <div style="width:6px; height:6px; background:{color}; clip-path:polygon(50% 0%, 100% 100%, 0% 100%);"></div>
                <span style="
                    color: {color};
                    font-family: 'Share Tech Mono', monospace;
                    font-size: 10px;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                ">{title}</span>
            </div>
            <div style="padding: 10px;">
                {content_html}
            </div>
        </div>
    """, unsafe_allow_html=True)


def bloomberg_kpi(label, value, change=None, change_positive=True):
    """Affiche un KPI style Bloomberg."""
    change_html = ""
    if change is not None:
        color = "#00ff41" if change_positive else "#ff2222"
        arrow = "▲" if change_positive else "▼"
        change_html = f'<div style="color:{color}; font-size:11px;">{arrow} {change}</div>'

    st.markdown(f"""
        <div style="
            background: #0a0a0a;
            border: 1px solid #1e1e1e;
            border-top: 2px solid #ff6600;
            padding: 8px 12px;
            min-width: 120px;
        ">
            <div style="color:#555; font-size:8px; text-transform:uppercase; letter-spacing:1.5px; font-family:'Share Tech Mono',monospace;">{label}</div>
            <div style="color:#e8e8e8; font-size:20px; font-family:'Share Tech Mono',monospace; margin: 3px 0;">{value}</div>
            {change_html}
        </div>
    """, unsafe_allow_html=True)
