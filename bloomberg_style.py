"""
bloomberg_style.py — VERSION FINALE PRO
Corrige : espaces blancs, dropdown blanc, espace vide haut, radio mal alignés,
tab bar Streamlit visible, inputs blancs page login, boutons F-keys décoratifs
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime


def apply_bloomberg_style():
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    <style>

    /* ════════════════════════════════════════════════
       1. RESET GLOBAL — SUPPRIME TOUT FOND BLANC
    ════════════════════════════════════════════════ */
    *, *::before, *::after { box-sizing: border-box; }

    html, body {
        background: #000000 !important;
        color: #e8e8e8 !important;
        font-family: 'Share Tech Mono', 'Courier New', monospace !important;
    }

    .stApp,
    .main,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    section[data-testid="stMain"],
    section.main,
    div.block-container,
    .element-container,
    [data-testid="stMarkdownContainer"] {
        background-color: #000000 !important;
        color: #e8e8e8 !important;
    }

    /* ════════════════════════════════════════════════
       2. SUPPRIME HEADER + ESPACE VIDE EN HAUT
    ════════════════════════════════════════════════ */
    header[data-testid="stHeader"] {
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
        display: none !important;
    }
    [data-testid="stDecoration"],
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    #MainMenu,
    footer,
    .stDeployButton,
    button[kind="header"],
    [data-testid="stHeaderActionElements"] {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    /* Supprime le padding-top causant l'espace blanc */
    .main .block-container,
    div.block-container {
        padding-top: 0px !important;
        padding-bottom: 16px !important;
        padding-left: 10px !important;
        padding-right: 10px !important;
        max-width: 100% !important;
        margin-top: 0 !important;
    }
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    section[data-testid="stMain"] > div:first-child {
        padding-top: 0 !important;
    }

    /* ════════════════════════════════════════════════
       3. SIDEBAR
    ════════════════════════════════════════════════ */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div > div,
    [data-testid="stSidebar"] section {
        background-color: #050505 !important;
        border-right: 2px solid #ff6600 !important;
    }
    [data-testid="stSidebar"] {
        min-width: 210px !important;
        max-width: 210px !important;
        padding: 0 !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ff6600 !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-family: 'Share Tech Mono', monospace !important;
        padding: 6px 10px 4px !important;
        border-bottom: 1px solid #1a0800 !important;
        margin: 0 !important;
        background: transparent !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }

    /* DROPDOWN SIDEBAR — fond noir */
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div > div > div {
        background-color: #111 !important;
        background: #111 !important;
        border: 1px solid #ff6600 !important;
        border-radius: 0 !important;
        color: #ff6600 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 11px !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] span { color: #ff6600 !important; background: transparent !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] svg path { fill: #ff6600 !important; }

    /* RADIO SIDEBAR */
    [data-testid="stSidebar"] [data-baseweb="radio"] > div { padding: 1px 0 !important; }
    [data-testid="stSidebar"] [data-baseweb="radio"] label {
        display: flex !important;
        align-items: flex-start !important;
        gap: 6px !important;
        padding: 5px 10px !important;
        margin: 0 !important;
        cursor: pointer !important;
        border-left: 2px solid transparent !important;
        transition: all 0.1s !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] label:hover {
        background: #110500 !important;
        border-left: 2px solid #ff6600 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] label > div:first-child {
        width: 10px !important;
        height: 10px !important;
        min-width: 10px !important;
        border: 1px solid #333 !important;
        background: transparent !important;
        border-radius: 0 !important;
        margin-top: 1px !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] label[aria-checked="true"] {
        border-left: 2px solid #ff6600 !important;
        background: #0d0400 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] label[aria-checked="true"] > div:first-child {
        border-color: #ff6600 !important;
        background: #ff6600 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] div[data-testid="stMarkdownContainer"] p {
        color: #777 !important;
        font-size: 10px !important;
        line-height: 1.3 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    [data-testid="stSidebar"] [data-baseweb="radio"] label[aria-checked="true"] div[data-testid="stMarkdownContainer"] p {
        color: #ff6600 !important;
    }

    [data-testid="stSidebar"] hr {
        border: none !important;
        border-top: 1px solid #1a0800 !important;
        margin: 6px 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background: #0a0500 !important;
        border: 1px solid #2a1400 !important;
        border-left: 3px solid #ff6600 !important;
        border-radius: 0 !important;
        padding: 5px 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlert"] p { color: #555 !important; font-size: 9px !important; }
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        background: #0d0d0d !important;
        border: 1px solid #ff6600 !important;
        border-radius: 0 !important;
        color: #ff6600 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 8px !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover { background: #ff6600 !important; color: #000 !important; }

    /* ════════════════════════════════════════════════
       4. DROPDOWN GLOBAL — CORRIGE LE BLANC
    ════════════════════════════════════════════════ */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    ul[data-baseweb="menu"],
    [data-baseweb="menu"],
    [data-baseweb="menu"] ul,
    [role="listbox"] {
        background-color: #111 !important;
        background: #111 !important;
        border: 1px solid #ff6600 !important;
        border-radius: 0 !important;
    }
    [role="option"],
    [data-baseweb="menu"] li {
        background-color: #111 !important;
        color: #bb7733 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 11px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        padding: 8px 12px !important;
        border-bottom: 1px solid #1a1a1a !important;
    }
    [role="option"]:hover, [data-baseweb="menu"] li:hover { background: #1a0800 !important; color: #ff6600 !important; }
    [aria-selected="true"][role="option"] { background: #1a0800 !important; color: #ff6600 !important; }

    /* ════════════════════════════════════════════════
       5. INPUTS — CORRIGE LE FOND BLANC LOGIN
    ════════════════════════════════════════════════ */
    input[type="text"], input[type="password"], input[type="email"],
    input[type="number"], textarea,
    [data-baseweb="input"] input,
    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    [data-testid="stTextInputRootElement"] input {
        background-color: #0d0d0d !important;
        background: #0d0d0d !important;
        border: 1px solid #1e1e1e !important;
        border-bottom: 1px solid #ff6600 !important;
        border-radius: 0 !important;
        color: #e8e8e8 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 13px !important;
        padding: 8px 12px !important;
        caret-color: #ff6600 !important;
        outline: none !important;
    }
    input::placeholder, textarea::placeholder { color: #2a2a2a !important; }
    input:focus, textarea:focus {
        border-bottom-color: #ff8833 !important;
        box-shadow: 0 2px 0 0 rgba(255,102,0,0.25) !important;
    }
    [data-baseweb="input"], [data-baseweb="base-input"],
    [data-testid="stTextInputRootElement"],
    [data-testid="stTextInput"] > div, .stTextInput > div > div {
        background: #0d0d0d !important;
        border-radius: 0 !important;
    }
    .stTextInput label, .stNumberInput label, .stTextArea label,
    .stSelectbox label, .stMultiSelect label, .stSlider label {
        color: #444 !important;
        font-size: 9px !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    [data-testid="stTextInputRootElement"] button, .stTextInput button {
        background: transparent !important;
        border: none !important;
        color: #ff6600 !important;
    }

    /* ════════════════════════════════════════════════
       6. SELECTBOX PRINCIPAL
    ════════════════════════════════════════════════ */
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] > div > div {
        background-color: #0d0d0d !important;
        border: 1px solid #1e1e1e !important;
        border-bottom: 1px solid #ff6600 !important;
        border-radius: 0 !important;
        color: #e8e8e8 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 11px !important;
    }
    .stSelectbox svg path { fill: #ff6600 !important; }

    /* ════════════════════════════════════════════════
       7. TYPOGRAPHIE
    ════════════════════════════════════════════════ */
    h1 {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #ff6600 !important;
        text-transform: uppercase !important;
        letter-spacing: 4px !important;
        border-left: 4px solid #ff6600 !important;
        padding: 6px 0 6px 12px !important;
        background: #080808 !important;
        margin-bottom: 10px !important;
    }
    h2 {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 12px !important;
        color: #ff6600 !important;
        text-transform: uppercase !important;
        letter-spacing: 3px !important;
        border-left: 3px solid #ff6600 !important;
        padding-left: 8px !important;
        margin: 12px 0 6px 0 !important;
        background: transparent !important;
    }
    h3 {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 11px !important;
        color: #ffcc00 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        margin: 8px 0 4px 0 !important;
        background: transparent !important;
    }
    p { font-family: 'Share Tech Mono', monospace !important; font-size: 12px !important; color: #aaa !important; background: transparent !important; }

    /* ════════════════════════════════════════════════
       8. BOUTONS
    ════════════════════════════════════════════════ */
    .stButton > button {
        background: #0d0d0d !important;
        color: #ff6600 !important;
        border: 1px solid #ff6600 !important;
        border-radius: 0 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        padding: 7px 16px !important;
        transition: background 0.1s, color 0.1s !important;
        box-shadow: none !important;
    }
    .stButton > button:hover { background: #ff6600 !important; color: #000 !important; box-shadow: 0 0 10px rgba(255,102,0,0.3) !important; }
    .stButton > button:active { background: #cc4400 !important; color: #000 !important; }
    .stButton > button:focus:not(:active) { box-shadow: 0 0 0 2px rgba(255,102,0,0.35) !important; }

    /* ════════════════════════════════════════════════
       9. MÉTRIQUES
    ════════════════════════════════════════════════ */
    [data-testid="metric-container"] {
        background: #080808 !important;
        border: 1px solid #1a1a1a !important;
        border-top: 2px solid #ff6600 !important;
        border-radius: 0 !important;
        padding: 8px 12px !important;
    }
    [data-testid="stMetricLabel"] div { font-family: 'Share Tech Mono', monospace !important; font-size: 9px !important; color: #444 !important; text-transform: uppercase !important; letter-spacing: 1.5px !important; }
    [data-testid="stMetricValue"] div { font-family: 'Share Tech Mono', monospace !important; font-size: 20px !important; color: #e8e8e8 !important; }
    [data-testid="stMetricDelta"] div { font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; }

    /* ════════════════════════════════════════════════
       10. TABS
    ════════════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] { background: #000 !important; border-bottom: 1px solid #ff6600 !important; gap: 0 !important; padding: 0 !important; }
    .stTabs [data-baseweb="tab"] {
        background: #080808 !important;
        border: 1px solid #1a1a1a !important;
        border-bottom: none !important;
        border-radius: 0 !important;
        color: #555 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 6px 14px !important;
        margin-right: 2px !important;
    }
    .stTabs [aria-selected="true"] { background: #ff6600 !important; color: #000 !important; font-weight: 700 !important; border-color: #ff6600 !important; }
    .stTabs [data-baseweb="tab"]:hover { background: #1a0800 !important; color: #ff6600 !important; }
    .stTabs [data-baseweb="tab-panel"] { background: #000 !important; padding: 10px 0 !important; }

    /* ════════════════════════════════════════════════
       11. DATAFRAME
    ════════════════════════════════════════════════ */
    [data-testid="stDataFrame"] { background: #000 !important; border: 1px solid #1a1a1a !important; border-radius: 0 !important; }
    [data-testid="stDataFrame"] th { background: #0d0d0d !important; color: #ff6600 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 9px !important; text-transform: uppercase !important; border-bottom: 1px solid #ff6600 !important; padding: 5px 8px !important; }
    [data-testid="stDataFrame"] td { background: #040404 !important; color: #ccc !important; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; border-bottom: 1px solid #0d0d0d !important; padding: 4px 8px !important; }
    [data-testid="stDataFrame"] tr:hover td { background: #0d0500 !important; }

    /* ════════════════════════════════════════════════
       12. EXPANDER
    ════════════════════════════════════════════════ */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {
        background: #080808 !important;
        border: 1px solid #1a1a1a !important;
        border-left: 3px solid #ff6600 !important;
        border-radius: 0 !important;
        color: #ff6600 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        padding: 8px 12px !important;
    }
    [data-testid="stExpander"] > div:last-child { background: #060606 !important; border: 1px solid #1a1a1a !important; border-top: none !important; border-radius: 0 !important; }

    /* ════════════════════════════════════════════════
       13. ALERTS
    ════════════════════════════════════════════════ */
    [data-testid="stAlert"] { border-radius: 0 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 11px !important; }
    div.stSuccess { background: #001500 !important; border: 1px solid #00ff41 !important; border-left: 4px solid #00ff41 !important; color: #00ff41 !important; }
    div.stError { background: #150000 !important; border: 1px solid #ff2222 !important; border-left: 4px solid #ff2222 !important; color: #ff2222 !important; }
    div.stWarning { background: #151000 !important; border: 1px solid #ffcc00 !important; border-left: 4px solid #ffcc00 !important; color: #ffcc00 !important; }
    div.stInfo { background: #00061a !important; border: 1px solid #0055bb !important; border-left: 4px solid #0088ff !important; color: #66aaff !important; }

    /* ════════════════════════════════════════════════
       14. DIVERS
    ════════════════════════════════════════════════ */
    [data-testid="stProgressBar"] > div { background: #111 !important; border-radius: 0 !important; }
    [data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #cc4400, #ff6600) !important; border-radius: 0 !important; }
    .stMultiSelect [data-baseweb="tag"] { background: #1a0800 !important; border: 1px solid #ff6600 !important; border-radius: 0 !important; color: #ff6600 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 10px !important; }
    .stDownloadButton > button { background: #001200 !important; color: #00ff41 !important; border: 1px solid #00ff41 !important; border-radius: 0 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 10px !important; text-transform: uppercase !important; }
    .stDownloadButton > button:hover { background: #00ff41 !important; color: #000 !important; }
    [role="slider"] { background: #ff6600 !important; border: 2px solid #ff6600 !important; border-radius: 0 !important; }
    [data-baseweb="checkbox"] [data-checked="true"] { background: #ff6600 !important; border-color: #ff6600 !important; }
    .stNumberInput button { background: #111 !important; border: 1px solid #1e1e1e !important; color: #ff6600 !important; border-radius: 0 !important; }
    .stNumberInput button:hover { background: #1a0800 !important; }
    .stCaption, [data-testid="stCaptionContainer"] p { color: #333 !important; font-size: 9px !important; font-family: 'Share Tech Mono', monospace !important; text-transform: uppercase !important; }
    hr { border: none !important; border-top: 1px solid #111 !important; margin: 8px 0 !important; }
    iframe { border: 1px solid #1a1a1a !important; border-radius: 0 !important; display: block !important; }

    /* ════════════════════════════════════════════════
       15. SCROLLBAR
    ════════════════════════════════════════════════ */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: #050505; }
    ::-webkit-scrollbar-thumb { background: #2a1000; }
    ::-webkit-scrollbar-thumb:hover { background: #ff6600; }

    /* ════════════════════════════════════════════════
       16. SCAN LINES CRT
    ════════════════════════════════════════════════ */
    body::after {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(0deg, transparent 0px, transparent 3px, rgba(0,0,0,0.03) 3px, rgba(0,0,0,0.03) 4px);
        pointer-events: none;
        z-index: 999999;
    }

    </style>
    """, unsafe_allow_html=True)


def bloomberg_header(watchlist_string=""):
    """Header Bloomberg Terminal avec ticker bar animée et function keys."""
    now_str = datetime.now().strftime("%Y-%m-%d  %H:%M")

    fkeys = [
        ("F1", "HELP"), ("F2", "EQUITY"), ("F3", "FIXED"), ("F4", "FX"),
        ("F5", "CMDTY"), ("F6", "INDEX"), ("F7", "NEWS"), ("F8", "CRYPTO"),
        ("F9", "ECON"), ("ESC", "BACK"), ("⏎", "GO")
    ]
    fkeys_html = "".join([
        f'<span style="display:inline-flex;align-items:center;gap:3px;'
        f'background:#0a0a0a;border:1px solid #1a1a1a;padding:2px 8px;margin-right:2px;">'
        f'<span style="color:#ff6600;font-size:9px;font-family:\'Share Tech Mono\',monospace;">{k}</span>'
        f'<span style="color:#2a2a2a;font-size:9px;font-family:\'Share Tech Mono\',monospace;">{v}</span>'
        f'</span>'
        for k, v in fkeys
    ])

    ticker_content = watchlist_string if watchlist_string else \
        '<span style="color:#2a2a2a;font-family:\'Share Tech Mono\',monospace;font-size:11px;letter-spacing:1px;">— CHARGEMENT DONNÉES MARCHÉ —</span>'

    html = f"""
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@700&display=swap" rel="stylesheet">
    <div style="
        background:#000;border-bottom:2px solid #ff6600;
        margin:0 0 6px 0;font-family:'Share Tech Mono',monospace;
        width:100%;box-sizing:border-box;
    ">
        <!-- LIGNE 1 : LOGO + STATUS -->
        <div style="display:flex;justify-content:space-between;align-items:center;padding:5px 14px;background:#040404;border-bottom:1px solid #0d0d0d;">
            <div style="display:flex;align-items:center;gap:12px;">
                <div style="background:#ff6600;color:#000;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:17px;letter-spacing:4px;padding:3px 16px 3px 12px;clip-path:polygon(0 0,calc(100% - 8px) 0,100% 100%,0 100%);">AM</div>
                <div>
                    <div style="color:#ff6600;font-size:13px;letter-spacing:3px;font-family:'Rajdhani',sans-serif;font-weight:700;">TRADING TERMINAL</div>
                    <div style="color:#1e1e1e;font-size:8px;letter-spacing:2px;font-family:'Share Tech Mono',monospace;">PRO EDITION — LA RÉUNION 974</div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="text-align:right;">
                    <div style="color:#333;font-size:8px;letter-spacing:1px;margin-bottom:2px;font-family:'Share Tech Mono',monospace;">SYSTEM</div>
                    <div style="color:#00ff41;font-size:10px;letter-spacing:1px;font-family:'Share Tech Mono',monospace;">● ONLINE &nbsp;● LIVE</div>
                </div>
                <div style="background:#0a0a0a;border:1px solid #1a1a1a;padding:4px 12px;text-align:center;">
                    <div style="color:#333;font-size:8px;letter-spacing:1px;font-family:'Share Tech Mono',monospace;">HEURE REU</div>
                    <div style="color:#ff6600;font-size:12px;letter-spacing:1px;font-family:'Share Tech Mono',monospace;">{now_str}</div>
                </div>
                <div style="background:#ff6600;color:#000;font-family:'Rajdhani',sans-serif;font-weight:700;font-size:11px;letter-spacing:2px;padding:5px 12px;">UTC +4</div>
            </div>
        </div>

        <!-- LIGNE 2 : TICKER BAR -->
        <div style="background:#000;overflow:hidden;height:24px;border-bottom:1px solid #080808;position:relative;">
            <div style="position:absolute;top:0;left:0;display:inline-block;white-space:nowrap;animation:bbscroll 45s linear infinite;line-height:24px;padding-left:100%;">
                {ticker_content}
                &nbsp;&nbsp;<span style="color:#1a1a1a;font-family:'Share Tech Mono',monospace;">|||</span>&nbsp;&nbsp;
                {ticker_content}
            </div>
        </div>

        <!-- LIGNE 3 : FUNCTION KEYS -->
        <div style="display:flex;align-items:center;background:#020202;padding:3px 8px;gap:2px;overflow:hidden;border-top:1px solid #080808;">
            {fkeys_html}
        </div>
    </div>
    <style>
    @keyframes bbscroll {{
        0%   {{ transform: translateX(0); }}
        100% {{ transform: translateX(-50%); }}
    }}
    </style>
    """
    components.html(html, height=102, scrolling=False)
