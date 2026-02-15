import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# ==========================================
# 1. RENDU GRAPHIQUE TRADINGVIEW
# ==========================================

def render_tradingview_chart(symbol, interval="D", height=300, key_suffix="1"):
    """Affiche le widget TradingView"""
    # Nettoyage du symbole
    tv_symbol = f"BINANCE:{symbol}USDT" if len(symbol) < 6 else symbol
    
    html_code = f"""
    <div style="border: 1px solid #333;">
      <div id="tv_{key_suffix}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width": "100%", "height": {height}, "symbol": "{tv_symbol}",
        "interval": "{interval}", "timezone": "Etc/UTC", "theme": "dark",
        "style": "1", "locale": "fr", "enable_publishing": false,
        "hide_top_toolbar": false, "container_id": "tv_{key_suffix}",
        "overrides": {{
            "paneProperties.background": "#000000",
            "paneProperties.vertGridProperties.color": "#111",
            "paneProperties.horzGridProperties.color": "#111"
        }}
      }});
      </script>
    </div>
    """
    components.html(html_code, height=height+10)

# ==========================================
# 2. MINI-MODULES (WIDGETS DE DROITE)
# ==========================================

def mini_screener():
    st.markdown("<h6 style='color:#ff9800; margin-bottom:5px;'>🔍 TOP SCORES</h6>", unsafe_allow_html=True)
    df = pd.DataFrame({
        "Ticker": ["BTC", "ETH", "SOL", "DOT"],
        "Score": [18, 15, 12, 9]
    })
    st.dataframe(df, hide_index=True, use_container_width=True, height=150)

def mini_news():
    st.markdown("<h6 style='color:#ff9800; margin-bottom:5px;'>📰 FLASH NEWS</h6>", unsafe_allow_html=True)
    st.caption("• BTC frôle les 100k$")
    st.caption("• L'inflation US stable")
    st.caption("• NVIDIA annonce ses résultats")

def mini_vide():
    st.write("Module en attente...")

# Dictionnaire pour la sélection dynamique
MODULES_MAP = {
    "Screener": mini_screener,
    "News": mini_news,
    "Vide": mini_vide
}

# ==========================================
# 3. INTERFACE PRINCIPALE
# ==========================================

def show_interface_pro():
    # --- CSS POUR LE ZOOM 80% ET LE LOOK PRO ---
    st.markdown("""
        <style>
        /* Zoom 80% sur tout le contenu */
        [data-testid="stAppViewBlockContainer"] {
            zoom: 0.8;
            transform: scale(0.8);
            transform-origin: top left;
            width: 125% !important; /* Compense la réduction de largeur due au scale */
        }
        
        .stApp { background-color: #000000; }
        
        /* Boîtiers des modules de droite */
        .module-card {
            background-color: #0a0a0a;
            border: 1px solid #333;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 15px;
        }
        
        /* Cacher les labels des selectbox pour gagner de la place */
        label[data-testid="stWidgetLabel"] { display: none; }
        </style>
    """, unsafe_allow_html=True)


    # 2. COLONNES (Gauches: Charts / Droite: Widgets)
    col_left, col_right = st.columns([78, 22], gap="small")

    with col_left:
        # Premier Graphique
        row1_c1, row1_c2 = st.columns([1, 4])
        with row1_c1:
            s1 = st.text_input("Symbole 1", value="BTC", key="sym1")
        render_tradingview_chart(s1, height=320, key_suffix="top")
        
        # Deuxième Graphique
        row2_c1, row2_c2 = st.columns([1, 4])
        with row2_c1:
            s2 = st.text_input("Symbole 2", value="ETH", key="sym2")
        render_tradingview_chart(s2, height=320, key_suffix="bot")

    with col_right:
        # Case du haut
        st.markdown('<div class="module-card">', unsafe_allow_html=True)
        choice_top = st.selectbox("M1", list(MODULES_MAP.keys()), index=0, key="m1")
        MODULES_MAP[choice_top]()
        st.markdown('</div>', unsafe_allow_html=True)

        # Case du bas
        st.markdown('<div class="module-card">', unsafe_allow_html=True)
        choice_bot = st.selectbox("M2", list(MODULES_MAP.keys()), index=1, key="m2")
        MODULES_MAP[choice_bot]()
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.info("Interface Pro v2.0")
