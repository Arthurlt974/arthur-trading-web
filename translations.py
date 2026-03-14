# ============================================================
#  translations.py — AM.TERMINAL
#  Fichier central de traductions FR / EN
# ============================================================

import streamlit as st

def get_lang():
    """Retourne la langue active depuis session_state."""
    return st.session_state.get("lang", "FR")

def t(key):
    """Retourne la traduction selon la langue active."""
    lang = get_lang()
    return TRANSLATIONS.get(key, {}).get(lang, key)

def render_lang_toggle():
    """Toggle FR / EN affiché en haut de page."""
    st.markdown("""
    <style>
    .lang-toggle {
        display: flex; align-items: center; gap: 8px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px; color: #555;
        margin-bottom: 12px;
    }
    .lang-btn {
        padding: 3px 10px;
        border-radius: 3px;
        border: 1px solid #1a1a1a;
        background: transparent;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px; cursor: pointer;
        color: #555;
    }
    .lang-btn.active { color: #ff6600; border-color: #ff6600; background: #0d0800; }
    </style>
    """, unsafe_allow_html=True)

    lang = get_lang()
    col1, col2, col3 = st.columns([1, 1, 10])
    with col1:
        if st.button("🇫🇷 FR", key="btn_fr",
                     type="primary" if lang == "FR" else "secondary"):
            st.session_state.lang = "FR"
            st.rerun()
    with col2:
        if st.button("🇬🇧 EN", key="btn_en",
                     type="primary" if lang == "EN" else "secondary"):
            st.session_state.lang = "EN"
            st.rerun()


# ============================================================
#  DICTIONNAIRE DE TRADUCTIONS
# ============================================================

TRANSLATIONS = {

    # ── NAVIGATION SIDEBAR ──
    "nav_markets":          {"FR": "📊 MARCHÉS",           "EN": "📊 MARKETS"},
    "nav_home":             {"FR": "🏠 ACCUEIL",           "EN": "🏠 HOME"},
    "nav_actions":          {"FR": "📈 ACTIONS & BOURSE",  "EN": "📈 STOCKS & MARKETS"},
    "nav_crypto":           {"FR": "🪙 MARCHÉ CRYPTO",     "EN": "🪙 CRYPTO MARKET"},
    "nav_forex":            {"FR": "💱 FOREX",             "EN": "💱 FOREX"},
    "nav_matieres":         {"FR": "🛢 MATIÈRES PREMIÈRES","EN": "🛢 COMMODITIES"},
    "nav_economie":         {"FR": "🌍 ÉCONOMIE",          "EN": "🌍 ECONOMY"},
    "nav_analyse":          {"FR": "⚙️ ANALYSE",           "EN": "⚙️ ANALYSIS"},
    "nav_finance":          {"FR": "🔬 FINANCE DE MARCHÉ", "EN": "🔬 MARKET FINANCE"},
    "nav_pro":              {"FR": "🧠 INTERFACE PRO",     "EN": "🧠 PRO INTERFACE"},
    "nav_crypto_pro":       {"FR": "🤖 INTERFACE CRYPTO PRO","EN": "🤖 CRYPTO PRO"},
    "nav_espace":           {"FR": "📐 MON ESPACE ANALYSE","EN": "📐 MY ANALYSIS"},
    "nav_intelligence":     {"FR": "💡 AM INTELLIGENCE",   "EN": "💡 AM INTELLIGENCE"},
    "nav_outils":           {"FR": "🛠 OUTILS",            "EN": "🛠 TOOLS"},
    "nav_portfolio":        {"FR": "💼 PORTFOLIO",         "EN": "💼 PORTFOLIO"},
    "nav_screener":         {"FR": "🔭 SCREENER",          "EN": "🔭 SCREENER"},
    "nav_alertes":          {"FR": "🔔 ALERTES",           "EN": "🔔 ALERTS"},
    "nav_boite":            {"FR": "🧰 BOITE À OUTILS",    "EN": "🧰 TOOLBOX"},
    "nav_terminal":         {"FR": "🖥 TERMINAL",          "EN": "🖥 TERMINAL"},
    "nav_connected":        {"FR": "CONNECTÉ",             "EN": "CONNECTED"},

    # ── PAGE ACCUEIL ──
    "home_title":           {"FR": "MARKET DASHBOARD",     "EN": "MARKET DASHBOARD"},
    "home_crypto":          {"FR": "CRYPTO",               "EN": "CRYPTO"},
    "home_indices":         {"FR": "INDICES BOURSIERS",    "EN": "STOCK INDICES"},
    "home_movers":          {"FR": "TOP MOVERS DU JOUR",   "EN": "TOP MOVERS TODAY"},
    "home_gainers":         {"FR": "▲ TOP GAINERS",        "EN": "▲ TOP GAINERS"},
    "home_losers":          {"FR": "▼ TOP LOSERS",         "EN": "▼ TOP LOSERS"},
    "home_news":            {"FR": "ACTUALITÉS MARCHÉ",    "EN": "MARKET NEWS"},
    "home_loading":         {"FR": "Chargement des données marché...", "EN": "Loading market data..."},
    "home_no_news":         {"FR": "Actualités indisponibles", "EN": "News unavailable"},

    # ── MODULES ACTIONS ──
    "mod_analyseur":        {"FR": "ANALYSEUR PRO",        "EN": "PRO ANALYZER"},
    "mod_technique":        {"FR": "ANALYSE TECHNIQUE PRO","EN": "PRO TECHNICAL ANALYSIS"},
    "mod_fibonacci":        {"FR": "FIBONACCI CALCULATOR", "EN": "FIBONACCI CALCULATOR"},
    "mod_backtest":         {"FR": "BACKTESTING ENGINE",   "EN": "BACKTESTING ENGINE"},
    "mod_valorisation":     {"FR": "VALORISATION FONDAMENTALE","EN": "FUNDAMENTAL VALUATION"},
    "mod_multicharts":      {"FR": "MULTI-CHARTS",         "EN": "MULTI-CHARTS"},
    "mod_expert":           {"FR": "EXPERT SYSTEM",        "EN": "EXPERT SYSTEM"},
    "mod_council":          {"FR": "THE GRAND COUNCIL",    "EN": "THE GRAND COUNCIL"},
    "mod_duel":             {"FR": "MODE DUEL",            "EN": "DUEL MODE"},
    "mod_monitor":          {"FR": "MARKET MONITOR",       "EN": "MARKET MONITOR"},
    "mod_screener_cac":     {"FR": "SCREENER CAC 40",      "EN": "CAC 40 SCREENER"},
    "mod_dividend":         {"FR": "DIVIDEND CALENDAR",    "EN": "DIVIDEND CALENDAR"},

    # ── MODULES CRYPTO ──
    "mod_graphique_crypto": {"FR": "GRAPHIQUE CRYPTO",     "EN": "CRYPTO CHART"},
    "mod_btc_dom":          {"FR": "BITCOIN DOMINANCE",    "EN": "BITCOIN DOMINANCE"},
    "mod_wallet":           {"FR": "CRYPTO WALLET",        "EN": "CRYPTO WALLET"},
    "mod_heatmap_liq":      {"FR": "HEATMAP LIQUIDATIONS", "EN": "LIQUIDATIONS HEATMAP"},
    "mod_orderbook":        {"FR": "ORDER BOOK LIVE",      "EN": "LIVE ORDER BOOK"},
    "mod_whale":            {"FR": "WHALE WATCHER",        "EN": "WHALE WATCHER"},
    "mod_onchain":          {"FR": "ON-CHAIN ANALYTICS",   "EN": "ON-CHAIN ANALYTICS"},
    "mod_liq_funding":      {"FR": "LIQUIDATIONS & FUNDING","EN": "LIQUIDATIONS & FUNDING"},
    "mod_staking":          {"FR": "STAKING & YIELD",      "EN": "STAKING & YIELD"},

    # ── MODULES BOITE À OUTILS ──
    "mod_daily":            {"FR": "DAILY BRIEF",          "EN": "DAILY BRIEF"},
    "mod_calendrier":       {"FR": "CALENDRIER ÉCO",       "EN": "ECO CALENDAR"},
    "mod_fear":             {"FR": "Fear and Greed Index",  "EN": "Fear and Greed Index"},
    "mod_correlation":      {"FR": "CORRÉLATION DASH",     "EN": "CORRELATION DASH"},
    "mod_interets":         {"FR": "INTÉRÊTS COMPOSÉS",    "EN": "COMPOUND INTEREST"},
    "mod_heatmap":          {"FR": "HEATMAP MARCHÉ",       "EN": "MARKET HEATMAP"},
    "mod_alerts":           {"FR": "ALERTS MANAGER",       "EN": "ALERTS MANAGER"},

    # ── MODULES FINANCE DE MARCHÉ ──
    "mod_options":          {"FR": "⚙️ Pricing Options (BS + Greeks)", "EN": "⚙️ Options Pricing (BS + Greeks)"},
    "mod_vol_surface":      {"FR": "📊 Surface de Volatilité",         "EN": "📊 Volatility Surface"},
    "mod_yield_curve":      {"FR": "📈 Courbe des Taux & Obligations", "EN": "📈 Yield Curve & Bonds"},
    "mod_var":              {"FR": "🎯 VaR & Stress Tests",            "EN": "🎯 VaR & Stress Tests"},
    "mod_markowitz":        {"FR": "🏆 Optimisation Markowitz",        "EN": "🏆 Markowitz Optimization"},
    "mod_backtest_quant":   {"FR": "🔁 Backtest Quantitatif",          "EN": "🔁 Quantitative Backtest"},
    "mod_monte_carlo":      {"FR": "🎲 Monte Carlo (GBM)",             "EN": "🎲 Monte Carlo (GBM)"},
    "mod_capm":             {"FR": "📐 CAPM & Analyse Factorielle",    "EN": "📐 CAPM & Factor Analysis"},

    # ── WIDGETS COMMUNS ──
    "ticker":               {"FR": "TICKER",               "EN": "TICKER"},
    "periode":              {"FR": "PÉRIODE",              "EN": "PERIOD"},
    "valider":              {"FR": "VALIDER",              "EN": "VALIDATE"},
    "charger":              {"FR": "CHARGER",              "EN": "LOAD"},
    "calculer":             {"FR": "CALCULER",             "EN": "CALCULATE"},
    "analyser":             {"FR": "ANALYSER",             "EN": "ANALYZE"},
    "rechercher":           {"FR": "RECHERCHER",           "EN": "SEARCH"},
    "exporter":             {"FR": "EXPORTER",             "EN": "EXPORT"},
    "ajouter":              {"FR": "AJOUTER",              "EN": "ADD"},
    "supprimer":            {"FR": "SUPPRIMER",            "EN": "DELETE"},
    "sauvegarder":          {"FR": "SAUVEGARDER",          "EN": "SAVE"},
    "rafraichir":           {"FR": "RAFRAÎCHIR",           "EN": "REFRESH"},
    "prix":                 {"FR": "PRIX",                 "EN": "PRICE"},
    "variation":            {"FR": "VARIATION",            "EN": "CHANGE"},
    "volume":               {"FR": "VOLUME",               "EN": "VOLUME"},
    "rendement":            {"FR": "RENDEMENT",            "EN": "RETURN"},
    "volatilite":           {"FR": "VOLATILITÉ",           "EN": "VOLATILITY"},
    "capitalisation":       {"FR": "CAPITALISATION",       "EN": "MARKET CAP"},
    "secteur":              {"FR": "SECTEUR",              "EN": "SECTOR"},
    "devise":               {"FR": "DEVISE",               "EN": "CURRENCY"},
    "date_debut":           {"FR": "DATE DÉBUT",           "EN": "START DATE"},
    "date_fin":             {"FR": "DATE FIN",             "EN": "END DATE"},
    "capital":              {"FR": "CAPITAL",              "EN": "CAPITAL"},
    "frais":                {"FR": "FRAIS",                "EN": "FEES"},
    "signal":               {"FR": "SIGNAL",               "EN": "SIGNAL"},
    "achat":                {"FR": "ACHAT",                "EN": "BUY"},
    "vente":                {"FR": "VENTE",                "EN": "SELL"},
    "erreur":               {"FR": "Erreur",               "EN": "Error"},
    "chargement":           {"FR": "Chargement...",        "EN": "Loading..."},
    "donnees_indispo":      {"FR": "Données indisponibles","EN": "Data unavailable"},
    "aucun_resultat":       {"FR": "Aucun résultat",       "EN": "No results"},
    "connexion_requise":    {"FR": "Connexion requise",    "EN": "Login required"},

    # ── INTERFACE PRO ──
    "pro_title":            {"FR": "ANALYSEUR ACTIONS PRO","EN": "PRO STOCK ANALYZER"},
    "pro_ticker_label":     {"FR": "Entrez un ticker (ex: AAPL, MC.PA, NVDA)", "EN": "Enter a ticker (e.g. AAPL, MC.PA, NVDA)"},
    "pro_analyser_btn":     {"FR": "🔍 ANALYSER",          "EN": "🔍 ANALYZE"},
    "pro_prix_actuel":      {"FR": "PRIX ACTUEL",          "EN": "CURRENT PRICE"},
    "pro_variation_jour":   {"FR": "VARIATION JOUR",       "EN": "DAY CHANGE"},
    "pro_volume":           {"FR": "VOLUME",               "EN": "VOLUME"},
    "pro_52w_high":         {"FR": "52W HIGH",             "EN": "52W HIGH"},
    "pro_52w_low":          {"FR": "52W LOW",              "EN": "52W LOW"},
    "pro_per":              {"FR": "P/E RATIO",            "EN": "P/E RATIO"},
    "pro_eps":              {"FR": "EPS",                  "EN": "EPS"},
    "pro_dividende":        {"FR": "DIVIDENDE",            "EN": "DIVIDEND"},
    "pro_beta":             {"FR": "BETA",                 "EN": "BETA"},
    "pro_valorisation":     {"FR": "VALORISATION",         "EN": "VALUATION"},
    "pro_fondamentaux":     {"FR": "FONDAMENTAUX",         "EN": "FUNDAMENTALS"},
    "pro_technique":        {"FR": "TECHNIQUE",            "EN": "TECHNICAL"},
    "pro_historique":       {"FR": "HISTORIQUE",           "EN": "HISTORY"},
    "pro_evolution_prix":   {"FR": "ÉVOLUTION DU PRIX",    "EN": "PRICE EVOLUTION"},

    # ── PORTFOLIO ──
    "port_title":           {"FR": "MON PORTFOLIO",        "EN": "MY PORTFOLIO"},
    "port_ajouter":         {"FR": "Ajouter une position", "EN": "Add a position"},
    "port_ticker":          {"FR": "Ticker",               "EN": "Ticker"},
    "port_quantite":        {"FR": "Quantité",             "EN": "Quantity"},
    "port_prix_achat":      {"FR": "Prix d'achat",         "EN": "Purchase price"},
    "port_valeur":          {"FR": "Valeur actuelle",      "EN": "Current value"},
    "port_pnl":             {"FR": "P&L",                  "EN": "P&L"},
    "port_allocation":      {"FR": "Allocation",           "EN": "Allocation"},
    "port_performance":     {"FR": "Performance",          "EN": "Performance"},
    "port_total":           {"FR": "Valeur totale",        "EN": "Total value"},
    "port_vide":            {"FR": "Aucune position dans le portfolio", "EN": "No positions in portfolio"},

    # ── ALERTES ──
    "alert_title":          {"FR": "GESTIONNAIRE D'ALERTES","EN": "ALERTS MANAGER"},
    "alert_ajouter":        {"FR": "Nouvelle alerte",      "EN": "New alert"},
    "alert_ticker":         {"FR": "Ticker",               "EN": "Ticker"},
    "alert_condition":      {"FR": "Condition",            "EN": "Condition"},
    "alert_seuil":          {"FR": "Seuil",                "EN": "Threshold"},
    "alert_active":         {"FR": "Active",               "EN": "Active"},
    "alert_declenche":      {"FR": "Déclenchée",           "EN": "Triggered"},
    "alert_vide":           {"FR": "Aucune alerte configurée", "EN": "No alerts configured"},
    "alert_sup":            {"FR": "Supérieur à",          "EN": "Greater than"},
    "alert_inf":            {"FR": "Inférieur à",          "EN": "Less than"},
    "alert_croise":         {"FR": "Croise",               "EN": "Crosses"},

    # ── SCREENER ──
    "scr_title":            {"FR": "SCREENER",             "EN": "SCREENER"},
    "scr_filtres":          {"FR": "FILTRES",              "EN": "FILTERS"},
    "scr_marche":           {"FR": "Marché",               "EN": "Market"},
    "scr_secteur":          {"FR": "Secteur",              "EN": "Sector"},
    "scr_per_min":          {"FR": "P/E minimum",          "EN": "Min P/E"},
    "scr_per_max":          {"FR": "P/E maximum",          "EN": "Max P/E"},
    "scr_capitalisation":   {"FR": "Capitalisation min",   "EN": "Min market cap"},
    "scr_appliquer":        {"FR": "Appliquer les filtres","EN": "Apply filters"},
    "scr_resultats":        {"FR": "RÉSULTATS",            "EN": "RESULTS"},

    # ── ÉCONOMIE ──
    "eco_title":            {"FR": "ÉCONOMIE MONDIALE",    "EN": "WORLD ECONOMY"},
    "eco_taux":             {"FR": "Taux directeurs",      "EN": "Key rates"},
    "eco_inflation":        {"FR": "Inflation",            "EN": "Inflation"},
    "eco_pib":              {"FR": "Croissance PIB",       "EN": "GDP Growth"},
    "eco_emploi":           {"FR": "Emploi",               "EN": "Employment"},
    "eco_calendrier":       {"FR": "Calendrier économique","EN": "Economic calendar"},
    "eco_indicateurs":      {"FR": "Indicateurs macro",    "EN": "Macro indicators"},

    # ── FOREX ──
    "forex_title":          {"FR": "MARCHÉ DES CHANGES",   "EN": "FOREX MARKET"},
    "forex_paire":          {"FR": "Paire de devises",     "EN": "Currency pair"},
    "forex_taux":           {"FR": "Taux de change",       "EN": "Exchange rate"},
    "forex_volatilite":     {"FR": "Volatilité",           "EN": "Volatility"},

    # ── MATIÈRES PREMIÈRES ──
    "mat_title":            {"FR": "MATIÈRES PREMIÈRES",   "EN": "COMMODITIES"},
    "mat_energie":          {"FR": "Énergie",              "EN": "Energy"},
    "mat_metaux":           {"FR": "Métaux précieux",      "EN": "Precious metals"},
    "mat_agricole":         {"FR": "Agricole",             "EN": "Agricultural"},

    # ── FINANCE DE MARCHÉ ──
    "fm_title":             {"FR": "FINANCE DE MARCHÉ — OUTILS QUANT", "EN": "MARKET FINANCE — QUANT TOOLS"},
    "fm_spot":              {"FR": "SPOT (S)",             "EN": "SPOT (S)"},
    "fm_strike":            {"FR": "STRIKE (K)",           "FR2": "STRIKE (K)", "EN": "STRIKE (K)"},
    "fm_maturite":          {"FR": "MATURITÉ (ANNÉES)",    "EN": "MATURITY (YEARS)"},
    "fm_taux_rf":           {"FR": "TAUX SANS RISQUE (%)", "EN": "RISK-FREE RATE (%)"},
    "fm_vol_impl":          {"FR": "VOLATILITÉ IMPLICITE (%)","EN": "IMPLIED VOLATILITY (%)"},
    "fm_dividende":         {"FR": "DIVIDENDE CONTINU (%)", "EN": "CONTINUOUS DIVIDEND (%)"},
    "fm_type":              {"FR": "TYPE",                 "EN": "TYPE"},
    "fm_style":             {"FR": "STYLE",                "EN": "STYLE"},
    "fm_europeen":          {"FR": "EUROPÉEN",             "EN": "EUROPEAN"},
    "fm_americain":         {"FR": "AMÉRICAIN",            "EN": "AMERICAN"},
    "fm_resultat":          {"FR": "RÉSULTAT DU PRICING",  "EN": "PRICING RESULT"},
    "fm_prix_option":       {"FR": "PRIX OPTION",          "EN": "OPTION PRICE"},
    "fm_valeur_temps":      {"FR": "VALEUR TEMPS",         "EN": "TIME VALUE"},
    "fm_greeks":            {"FR": "GREEKS — SENSIBILITÉS","EN": "GREEKS — SENSITIVITIES"},
    "fm_payoff":            {"FR": "PROFIL DE PAYOFF",     "EN": "PAYOFF PROFILE"},
    "fm_var_title":         {"FR": "VALUE AT RISK & STRESS TESTS","EN": "VALUE AT RISK & STRESS TESTS"},
    "fm_confiance":         {"FR": "NIVEAU DE CONFIANCE (%)","EN": "CONFIDENCE LEVEL (%)"},
    "fm_horizon":           {"FR": "HORIZON (JOURS)",      "EN": "HORIZON (DAYS)"},
    "fm_var_param":         {"FR": "VaR PARAMÉTRIQUE",     "EN": "PARAMETRIC VaR"},
    "fm_var_hist":          {"FR": "VaR HISTORIQUE",       "EN": "HISTORICAL VaR"},
    "fm_var_mc":            {"FR": "VaR MONTE CARLO",      "EN": "MONTE CARLO VaR"},
    "fm_shortfall":         {"FR": "EXPECTED SHORTFALL",   "EN": "EXPECTED SHORTFALL"},
    "fm_stress":            {"FR": "STRESS TESTS",         "EN": "STRESS TESTS"},
    "fm_markowitz_title":   {"FR": "OPTIMISATION MARKOWITZ — FRONTIÈRE EFFICIENTE","EN": "MARKOWITZ OPTIMIZATION — EFFICIENT FRONTIER"},
    "fm_sharpe":            {"FR": "MAX SHARPE RATIO",     "EN": "MAX SHARPE RATIO"},
    "fm_min_variance":      {"FR": "MINIMUM VARIANCE",     "EN": "MINIMUM VARIANCE"},
    "fm_allocation":        {"FR": "ALLOCATION OPTIMALE",  "EN": "OPTIMAL ALLOCATION"},
    "fm_mc_title":          {"FR": "SIMULATION MONTE CARLO","EN": "MONTE CARLO SIMULATION"},
    "fm_simulations":       {"FR": "NOMBRE DE SIMULATIONS","EN": "NUMBER OF SIMULATIONS"},
    "fm_capm_title":        {"FR": "ANALYSE FACTORIELLE — CAPM & FAMA-FRENCH","EN": "FACTOR ANALYSIS — CAPM & FAMA-FRENCH"},
    "fm_benchmark":         {"FR": "BENCHMARK",            "EN": "BENCHMARK"},
    "fm_alpha":             {"FR": "ALPHA (A) ANN.",       "EN": "ALPHA (A) ANN."},
    "fm_beta":              {"FR": "BÊTA (B)",             "EN": "BETA (B)"},
    "fm_tracking":          {"FR": "TRACKING ERROR",       "EN": "TRACKING ERROR"},
    "fm_info_ratio":        {"FR": "INFO RATIO",           "EN": "INFO RATIO"},

    # ── ANALYSE PERSO ──
    "ap_title":             {"FR": "MON ESPACE ANALYSE",   "EN": "MY ANALYSIS SPACE"},
    "ap_notes":             {"FR": "Mes notes",            "EN": "My notes"},
    "ap_idees":             {"FR": "Mes idées de trades",  "EN": "My trade ideas"},
    "ap_watchlist":         {"FR": "Ma watchlist",         "EN": "My watchlist"},
    "ap_journal":           {"FR": "Journal de trading",   "EN": "Trading journal"},

    # ── AM INTELLIGENCE ──
    "ai_title":             {"FR": "AM INTELLIGENCE",      "EN": "AM INTELLIGENCE"},
    "ai_question":          {"FR": "Posez votre question financière...", "EN": "Ask your financial question..."},
    "ai_analyser":          {"FR": "Analyser avec l'IA",  "EN": "Analyze with AI"},
    "ai_resume":            {"FR": "Résumé du marché",     "EN": "Market summary"},
    "ai_signal":            {"FR": "Signaux détectés",     "EN": "Detected signals"},

    # ── MESSAGES GÉNÉRAUX ──
    "msg_bienvenue":        {"FR": "Bienvenue sur AM.TERMINAL", "EN": "Welcome to AM.TERMINAL"},
    "msg_connexion":        {"FR": "Connectez-vous pour accéder à toutes les fonctionnalités", "EN": "Log in to access all features"},
    "msg_gratuit":          {"FR": "100% Gratuit",         "EN": "100% Free"},
    "msg_erreur_data":      {"FR": "Impossible de charger les données", "EN": "Unable to load data"},
    "msg_succes":           {"FR": "Succès",               "EN": "Success"},
    "msg_confirmation":     {"FR": "Confirmer",            "EN": "Confirm"},
    "msg_annuler":          {"FR": "Annuler",              "EN": "Cancel"},
    "msg_fermer":           {"FR": "Fermer",               "EN": "Close"},
    "btn_voir_plus":        {"FR": "Voir plus",            "EN": "See more"},
    "btn_voir_moins":       {"FR": "Voir moins",           "EN": "See less"},
    "lbl_oui":              {"FR": "Oui",                  "EN": "Yes"},
    "lbl_non":              {"FR": "Non",                  "EN": "No"},
    "lbl_all":              {"FR": "Tous",                 "EN": "All"},
    "lbl_none":             {"FR": "Aucun",                "EN": "None"},
}
