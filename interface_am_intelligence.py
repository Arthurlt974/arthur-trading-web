"""
interface_am_intelligence.py — AM Trading
Version finale — Chat IA + 6 Experts Wall Street + PDF + Historique
"""

import streamlit as st
import requests
import json
import io
import re
from datetime import datetime
from translations import t, get_lang

GROQ_MODEL = "llama-3.3-70b-versatile"

# ══════════════════════════════════════════
#  6 EXPERTS WALL STREET
# ══════════════════════════════════════════
ANALYSTES = {
    "🏦 JPMorgan — Pré-Earnings": {
        "description": "Note d'analyse pré-résultats style JPMorgan Senior",
        "color": "#1a3a5c", "border": "#2d6abf",
        "champs": [("entreprise", "Nom de l'entreprise", "ex: Apple, NVIDIA, LVMH...")],
        "prompt": lambda d: f"""Tu es un analyste senior en recherche actions chez JPMorgan, spécialisé dans les notes de pré-publication de résultats pour investisseurs institutionnels.

Fournis un rapport factuel et data-driven dans le style d'une note JPMorgan pré-earnings :
- Résultats des 4 derniers trimestres vs consensus (historique de beat/miss sur CA et EPS)
- Consensus actuel pour le prochain trimestre (CA + EPS)
- Les key metrics que Wall Street surveille spécifiquement pour cette société
- Répartition du CA par segment + tendances récentes
- Résumé des guidances et commentaires du management lors du dernier earnings call
- Mouvement implicite anticipé du titre (via options)
- Réaction historique du cours le jour des résultats sur les 4 derniers trimestres
- Scénario haussier : estimation d'impact sur le prix
- Scénario baissier : estimation du risque downside
- Recommandation stratégique pré-résultats : acheter, vendre, attendre

Ton senior JPMorgan (factuel, précis, sans hype).
Entreprise : {d['entreprise']}"""
    },

    "🌑 BlackRock — Multi-Asset Allocation": {
        "description": "Portefeuille personnalisé style BlackRock institutionnel",
        "color": "#1a1a2e", "border": "#e63946",
        "champs": [
            ("age", "Âge", "ex: 28"),
            ("revenus", "Revenus annuels", "ex: 45 000€"),
            ("epargne", "Épargne mensuelle", "ex: 500€"),
            ("objectif", "Objectif", "RETRAITE / ACHAT IMMOBILIER / REVENU PASSIF / CROISSANCE"),
            ("risque", "Tolérance au risque", "CONSERVATEUR / MODÉRÉ / DYNAMIQUE / AGRESSIF"),
            ("compte", "Type de compte", "PEA / CTO / Assurance-vie / PER"),
            ("horizon", "Horizon d'investissement", "COURT / MOYEN / LONG TERME / 5-10 ANS / +10 ANS"),
        ],
        "prompt": lambda d: f"""Tu es un stratège senior en gestion de portefeuille chez BlackRock, responsable des allocations multi-actifs pour clients institutionnels (>500 Md$).

Construis de zéro un portefeuille personnalisé :
- Allocation d'actifs précise (actions, obligations, alternatifs, cash...) avec % exacts
- Recommandations d'ETF/fonds spécifiques (tickers) par catégorie
- Distinction claire core vs satellites
- Fourchette de rendement annuel attendu (données 2020-2026)
- Drawdown max estimé en année baissière
- Calendrier de rééquilibrage + règles de déclenchement
- Optimisation fiscale selon mon type de compte
- Plan DCA si versements mensuels
- Benchmark de référence + Investment Policy Statement

Profil : Âge {d['age']} | Revenus {d['revenus']} | Épargne {d['epargne']} | Objectif {d['objectif']} | Risque {d['risque']} | Compte {d['compte']} | Horizon {d['horizon']}

IMPORTANT : Commence IMMÉDIATEMENT par l'allocation d'actifs. Pas d'introduction."""
    },

    "⚜️ Rothschild — Legacy Portfolio": {
        "description": "Blueprint patrimonial intergénérationnel style Rothschild & Co",
        "color": "#1a1208", "border": "#d4a017",
        "champs": [
            ("age", "Âge", "ex: 45"),
            ("revenus", "Revenus annuels", "ex: 120 000€"),
            ("epargne", "Épargne mensuelle", "ex: 2000€"),
            ("objectif", "Objectif", "PRÉSERVATION / TRANSMISSION / REVENU PASSIF / CROISSANCE MODÉRÉE"),
            ("risque", "Tolérance au risque", "CONSERVATEUR / MODÉRÉ / DYNAMIQUE"),
            ("compte", "Type de compte", "PEA / Assurance-vie / PER / CTO"),
            ("horizon", "Horizon", "LONG TERME / 10-20 ANS / +20 ANS / INTERGÉNÉRATIONNEL"),
        ],
        "prompt": lambda d: f"""Tu es un stratège senior chez Rothschild & Co, expert en investissements intergénérationnels pour familles fortunées.

Construis un blueprint portefeuille patrimoine :
- Allocation d'actifs précise avec % exacts
- Recommandations ETF/fonds/actifs réels (tickers) par catégorie
- Core (préservation capital) vs satellites (croissance modérée)
- Rendement annuel attendu + drawdown max
- Stratégie de transmission patrimoniale
- Optimisation fiscale + plan de rebalancement annuel

Profil : Âge {d['age']} | Revenus {d['revenus']} | Épargne {d['epargne']} | Objectif {d['objectif']} | Risque {d['risque']} | Compte {d['compte']} | Horizon {d['horizon']}

Ton Rothschild : élégant, conservateur, long terme."""
    },

    "🏛️ Goldman Sachs — Stock Screener": {
        "description": "Sélection d'actions style Goldman Sachs Equity Research",
        "color": "#0a1628", "border": "#4169e1",
        "champs": [
            ("risque", "Tolérance au risque", "FAIBLE / MODÉRÉ / ÉLEVÉ"),
            ("montant", "Montant à investir", "ex: 10 000€"),
            ("horizon", "Horizon", "COURT TERME / MOYEN TERME / LONG TERME"),
            ("secteurs", "Secteurs préférés", "ex: Tech, Santé, Énergie, Finance, Tous"),
        ],
        "prompt": lambda d: f"""Tu es un analyste senior en recherche actions chez Goldman Sachs.

Fournis les 10 meilleures actions correspondant aux critères. Pour chaque action :
- Ratio P/E actuel vs moyenne sectorielle
- Évolution du CA sur 5 ans
- Santé du bilan : ratio dette/fonds propres
- Rendement dividende + score soutenabilité (1-10)
- Avantage concurrentiel avec justification
- Objectif cours à 12 mois (haussier/baissier)
- Note de risque (1-10) + zone d'entrée + stop-loss

Présente un tableau récapitulatif + commentaire global sur la sélection.

Profil : Risque {d['risque']} | Montant {d['montant']} | Horizon {d['horizon']} | Secteurs {d['secteurs']}

IMPORTANT : Commence IMMÉDIATEMENT par le tableau. Pas d'introduction."""
    },

    "🎯 Bridgewater — Macro Strategy": {
        "description": "Analyse macro globale style Ray Dalio / Bridgewater",
        "color": "#0d1f0d", "border": "#00c853",
        "champs": [
            ("periode", "Horizon temporel", "ex: 6 mois, 1 an, 3 ans"),
            ("region", "Région focus", "ex: USA, Europe, Asie, Global"),
            ("theme", "Thème macro", "ex: Inflation, Récession, Croissance, Géopolitique"),
        ],
        "prompt": lambda d: f"""Tu es un stratège macro senior chez Bridgewater Associates, spécialisé dans l'analyse des cycles économiques.

Fournis une analyse macro complète style Ray Dalio :
- État actuel du cycle économique global (dette, inflation, croissance, emploi)
- Analyse des grandes banques centrales (Fed, BCE, BoJ) et impact marchés
- Positionnement recommandé par classe d'actifs avec % d'allocation
- Risques systémiques à surveiller
- Scénario central + alternatifs (haussier/baissier)
- Actifs refuge recommandés + hedges contre les risques

Horizon : {d['periode']} | Région : {d['region']} | Thème : {d['theme']}

Style : analytique, global, cycles économiques, data-driven."""
    },

    "⚡ Citadel — Trading Tactique": {
        "description": "Stratégie de trading court terme style Citadel",
        "color": "#1a0a0a", "border": "#ff3b30",
        "champs": [
            ("actif", "Actif à trader", "ex: NVDA, BTC, EUR/USD, Gold"),
            ("capital", "Capital disponible", "ex: 5 000€"),
            ("style", "Style de trading", "DAY TRADING / SWING / SCALPING"),
            ("horizon", "Horizon", "1 jour / 1 semaine / 1 mois"),
        ],
        "prompt": lambda d: f"""Tu es un trader quantitatif senior chez Citadel, spécialisé dans les stratégies tactiques court terme.

Fournis une stratégie de trading complète et actionnable :
- Analyse technique (tendance, supports/résistances, momentum)
- Setup précis : point d'entrée exact, stop-loss, take profit (ratio R/R)
- Catalyseurs à surveiller (macro, earnings, news)
- Indicateurs techniques à monitorer (RSI, MACD, volumes)
- Taille de position recommandée (% risqué par trade)
- Plan de gestion du trade (trailing stop, partiel, sortie)
- Scénario alternatif si invalidation
- Backtesting rapide du setup sur 3 derniers mois

Actif : {d['actif']} | Capital : {d['capital']} | Style : {d['style']} | Horizon : {d['horizon']}

Style : précis, chiffré, actionnable, risque maîtrisé."""
    },
}

# ══════════════════════════════════════════
#  SYSTEM PROMPT CHAT
# ══════════════════════════════════════════
CHAT_SYSTEM = """Tu es AM Intelligence, un assistant financier expert de haut niveau créé par AM Trading.
Tu as les compétences combinées d'un analyste JPMorgan, d'un stratège BlackRock, d'un trader Citadel et d'un macro analyst Bridgewater.

Tu peux analyser :
- N'importe quelle action (fondamentaux, valorisation, technique, catalyseurs)
- Les marchés crypto (Bitcoin, Ethereum, altcoins)
- Les marchés forex et matières premières
- La macroéconomie globale (inflation, taux, cycles)
- Les portefeuilles et allocations d'actifs
- Les stratégies de trading et d'investissement
- L'actualité économique et financière

Règles :
- Réponds toujours en français
- Sois précis, factuel et data-driven
- Utilise des données récentes (2025-2026) quand pertinent
- Structure tes réponses clairement avec des titres et bullet points
- Inclus toujours des chiffres concrets (P/E, prix, %, etc.)
- Mentionne les risques importants
- Termine par une conclusion actionnable
- Tu es concis mais complet. Qualité > quantité."""


# ══════════════════════════════════════════
#  API GROQ
# ══════════════════════════════════════════
def _call_groq(prompt: str, system: str = None, history: list = None) -> str:
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if not key:
            return "❌ Clé API Groq manquante dans les secrets Streamlit."

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "max_tokens": 4000, "temperature": 0.3},
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Erreur API : {e}"


# ══════════════════════════════════════════
#  GÉNÉRATION PDF
# ══════════════════════════════════════════
def _generate_pdf(analyste_nom: str, donnees: dict, rapport: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER

    C_ORANGE = colors.HexColor("#ff9800")
    C_GREY   = colors.HexColor("#aaaaaa")
    C_WHITE  = colors.HexColor("#ffffff")
    C_BORDER = colors.HexColor("#333333")
    C_AMBER  = colors.HexColor("#ffb84d")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm, bottomMargin=15*mm)

    def S(name, **kw): return ParagraphStyle(name, **kw)
    s_title  = S("t",  fontName="Helvetica-Bold", fontSize=24, textColor=C_ORANGE, alignment=TA_CENTER, spaceAfter=4)
    s_sub    = S("s",  fontName="Helvetica", fontSize=10, textColor=C_GREY, alignment=TA_CENTER, spaceAfter=3)
    s_sect   = S("se", fontName="Helvetica-Bold", fontSize=12, textColor=C_ORANGE, spaceBefore=10, spaceAfter=4)
    s_h1     = S("h1", fontName="Helvetica-Bold", fontSize=11, textColor=C_ORANGE, spaceBefore=8, spaceAfter=3)
    s_h2     = S("h2", fontName="Helvetica-Bold", fontSize=10, textColor=C_AMBER, spaceBefore=6, spaceAfter=2)
    s_h3     = S("h3", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE, spaceBefore=4, spaceAfter=2)
    s_body   = S("b",  fontName="Helvetica", fontSize=8, textColor=C_GREY, spaceAfter=3, leading=13)
    s_bullet = S("bl", fontName="Helvetica", fontSize=8, textColor=C_WHITE, spaceAfter=2, leading=12, leftIndent=12)
    s_param  = S("p",  fontName="Helvetica", fontSize=8, textColor=C_AMBER, spaceAfter=2)
    s_footer = S("f",  fontName="Helvetica", fontSize=7, textColor=C_BORDER, alignment=TA_CENTER)

    story = [Spacer(1, 4*mm)]
    story.append(Paragraph("AM-TRADING", s_title))
    story.append(Paragraph("AM INTELLIGENCE — RAPPORT D'ANALYSE", s_sub))
    story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", s_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ORANGE, spaceAfter=8))
    story.append(Paragraph(f"Analyste : {analyste_nom}", s_sect))

    if donnees:
        story.append(Paragraph("Paramètres :", s_h2))
        for k, v in donnees.items():
            if v and str(v).strip():
                story.append(Paragraph(f"• {k.upper()} : {v}", s_param))
        story.append(Spacer(1, 3*mm))

    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=8))
    story.append(Paragraph("RAPPORT", s_sect))

    for line in rapport.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm)); continue
        line  = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        clean = re.sub(r"[*#`]", "", line).strip()
        if not clean: continue
        if   line.startswith("# "):   story.append(Paragraph(re.sub(r"^#+\s*","",clean), s_h1))
        elif line.startswith("## "):  story.append(Paragraph(re.sub(r"^#+\s*","",clean), s_h2))
        elif line.startswith("### "): story.append(Paragraph(re.sub(r"^#+\s*","",clean), s_h3))
        elif line.startswith(("- ","• ")): story.append(Paragraph(f"• {clean[2:]}", s_bullet))
        elif re.match(r"^\d+\.\s", line): story.append(Paragraph(clean, s_bullet))
        elif line.startswith("---"): story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=4))
        else: story.append(Paragraph(clean, s_body))

    story += [Spacer(1, 6*mm), HRFlowable(width="100%", thickness=1, color=C_BORDER), Spacer(1, 2*mm)]
    story.append(Paragraph("AM-Trading Bloomberg Terminal  •  Analyse générée par IA  •  Ne constitue pas un conseil en investissement", s_footer))
    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════
#  INTERFACE PRINCIPALE
# ══════════════════════════════════════════
def show_am_intelligence():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&display=swap');
    .ai-header { font-family:'IBM Plex Mono',monospace; font-size:26px; font-weight:700; color:#ff6600; letter-spacing:3px; margin-bottom:4px; }
    .ai-sub { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#444; letter-spacing:2px; margin-bottom:20px; }
    .chat-container { background:#050505; border:1px solid #1a1a1a; border-radius:10px; padding:16px; max-height:520px; overflow-y:auto; margin-bottom:12px; }
    .chat-msg-user { background:#0d1f0d; border:1px solid #00c853; border-radius:10px 10px 2px 10px; padding:10px 14px; margin:8px 0 8px 60px; font-family:'IBM Plex Mono',monospace; font-size:12px; color:#e0e0e0; }
    .chat-msg-ai { background:#0a0a1a; border:1px solid #2d6abf; border-radius:10px 10px 10px 2px; padding:10px 14px; margin:8px 60px 8px 0; font-family:'IBM Plex Mono',monospace; font-size:12px; color:#e0e0e0; line-height:1.7; }
    .chat-role-user { font-size:9px; color:#00c853; letter-spacing:1px; margin-bottom:4px; font-weight:700; }
    .chat-role-ai { font-size:9px; color:#4d9fff; letter-spacing:1px; margin-bottom:4px; font-weight:700; }
    .chat-time { font-size:8px; color:#333; text-align:right; margin-top:4px; }
    .stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th { font-family:'IBM Plex Mono',monospace !important; font-size:12px !important; color:#ccc !important; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { font-family:'IBM Plex Mono',monospace !important; color:#ff6600 !important; letter-spacing:1px !important; }
    .stMarkdown table { background:#080808 !important; border:1px solid #1a1a1a !important; width:100% !important; }
    .stMarkdown th { background:#0d0800 !important; color:#ff6600 !important; border:1px solid #333 !important; padding:6px 10px !important; }
    .stMarkdown td { border:1px solid #1a1a1a !important; padding:5px 10px !important; }
    .stMarkdown strong { color:#ff6600 !important; }
    .disclaimer-ai { font-family:'IBM Plex Mono',monospace; font-size:9px; color:#333; border-top:1px solid #111; padding-top:8px; margin-top:16px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ai-header">🤖 AM INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="ai-sub">CHAT IA · 6 EXPERTS WALL STREET · ANALYSES FINANCIÈRES</div>', unsafe_allow_html=True)

    # ── Sélecteur de mode ──
    if "ai_mode" not in st.session_state:
        st.session_state.ai_mode = "chat"

    col_m1, col_m2, col_m3 = st.columns([1, 1, 4])
    with col_m1:
        if st.button("💬 CHAT IA", key="mode_chat",
                     type="primary" if st.session_state.ai_mode == "chat" else "secondary",
                     use_container_width=True):
            st.session_state.ai_mode = "chat"
            st.rerun()
    with col_m2:
        if st.button("🏛️ EXPERTS", key="mode_experts",
                     type="primary" if st.session_state.ai_mode == "experts" else "secondary",
                     use_container_width=True):
            st.session_state.ai_mode = "experts"
            st.rerun()

    st.markdown("---")

    # ════════════════════════════════════
    #  MODE CHAT
    # ════════════════════════════════════
    if st.session_state.ai_mode == "chat":

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "chat_pending" not in st.session_state:
            st.session_state.chat_pending = None

        # Suggestions si chat vide
        if not st.session_state.chat_history:
            st.markdown("""
            <div style='text-align:center;padding:20px 0 12px;'>
                <div style='font-family:IBM Plex Mono;font-size:14px;color:#ff6600;margin-bottom:6px;'>💬 Pose-moi n'importe quelle question financière</div>
                <div style='font-family:IBM Plex Mono;font-size:10px;color:#444;'>Actions · Crypto · Forex · Macro · Portefeuille · Trading</div>
            </div>
            """, unsafe_allow_html=True)

            suggestions = [
                "📈 Analyse NVIDIA", "₿ Bitcoin va-t-il remonter ?",
                "🏆 Meilleurs ETF 2025", "💹 Impact inflation marchés",
                "🌍 Analyse macro USA", "💰 Top dividendes France",
                "🥇 Stratégie sur l'or", "💱 EUR/USD analyse",
            ]
            cols = st.columns(4)
            for i, sug in enumerate(suggestions):
                with cols[i % 4]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state.chat_pending = sug.split(" ", 1)[1] if " " in sug else sug
                        st.rerun()

        # Affichage historique
        if st.session_state.chat_history:
            chat_html = '<div class="chat-container">'
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    chat_html += f'<div class="chat-msg-user"><div class="chat-role-user">▶ VOUS</div>{msg["content"].replace(chr(10),"<br>")}<div class="chat-time">{msg.get("time","")}</div></div>'
                else:
                    content = msg["content"]
                    content = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#ff6600">\1</strong>', content)
                    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
                    content = content.replace("\n", "<br>")
                    chat_html += f'<div class="chat-msg-ai"><div class="chat-role-ai">🤖 AM INTELLIGENCE</div>{content}<div class="chat-time">{msg.get("time","")}</div></div>'
            chat_html += '</div>'
            st.markdown(chat_html, unsafe_allow_html=True)

            col_cl1, col_cl2, col_cl3 = st.columns([3, 1, 1])
            with col_cl2:
                if st.button("📄 PDF CHAT", key="chat_pdf_btn", use_container_width=True):
                    rapport_chat = "\n\n".join([
                        f"{'VOUS' if m['role']=='user' else 'AM INTELLIGENCE'} — {m.get('time','')}\n{m['content']}"
                        for m in st.session_state.chat_history
                    ])
                    try:
                        pdf_bytes = _generate_pdf(
                            analyste_nom="AM Intelligence — Session Chat",
                            donnees={"Session": datetime.now().strftime("%d/%m/%Y %H:%M"), "Messages": str(len(st.session_state.chat_history))},
                            rapport=rapport_chat
                        )
                        st.download_button("⬇️ Télécharger", data=pdf_bytes,
                            file_name=f"AM_Chat_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf", key="dl_chat_pdf", use_container_width=True)
                    except Exception as e:
                        st.error(f"Erreur PDF : {e}")
            with col_cl3:
                if st.button("🗑 Effacer", key="clear_chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.session_state.chat_pending = None
                    st.rerun()

        # Input
        with st.form("chat_form", clear_on_submit=True):
            col_inp, col_send = st.columns([5, 1])
            with col_inp:
                user_input = st.text_input("Message", placeholder="Ex: Analyse NVIDIA, Que penses-tu du BTC ?, Meilleurs ETF Europe...", label_visibility="collapsed", key="chat_input_field")
            with col_send:
                send = st.form_submit_button("📤 ENVOYER", use_container_width=True, type="primary")

        # Traitement
        message_to_send = None
        if send and user_input.strip():
            message_to_send = user_input.strip()
        elif st.session_state.chat_pending:
            message_to_send = st.session_state.chat_pending
            st.session_state.chat_pending = None

        if message_to_send:
            st.session_state.chat_history.append({"role": "user", "content": message_to_send, "time": datetime.now().strftime("%H:%M")})
            api_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history[:-1]]
            with st.spinner("🤖 AM Intelligence analyse..."):
                response = _call_groq(prompt=message_to_send, system=CHAT_SYSTEM, history=api_history)
            st.session_state.chat_history.append({"role": "assistant", "content": response, "time": datetime.now().strftime("%H:%M")})
            st.rerun()

    # ════════════════════════════════════
    #  MODE EXPERTS
    # ════════════════════════════════════
    else:
        noms = list(ANALYSTES.keys())
        if "ai_analyste" not in st.session_state:
            st.session_state["ai_analyste"] = noms[0]

        choix = st.radio("Expert", options=noms,
                         index=noms.index(st.session_state["ai_analyste"]),
                         label_visibility="collapsed", key="ai_analyste_radio")
        if choix != st.session_state["ai_analyste"]:
            st.session_state["ai_analyste"] = choix
            st.session_state.pop("ai_result", None)
            st.rerun()

        analyste = ANALYSTES[st.session_state["ai_analyste"]]
        st.markdown(f"""
        <div style='background:{analyste["color"]};border:1.5px solid {analyste["border"]};
        border-radius:10px;padding:14px 18px;margin:12px 0;font-family:IBM Plex Mono,monospace;'>
        <div style='font-size:13px;color:{analyste["border"]};letter-spacing:1px;font-weight:700;'>{st.session_state["ai_analyste"]}</div>
        <div style='font-size:10px;color:#888;margin-top:4px;'>{analyste["description"]}</div>
        </div>""", unsafe_allow_html=True)

        # Formulaire en 2 colonnes
        st.markdown("##### 📋 Paramètres")
        donnees = {}
        champs = analyste["champs"]
        if len(champs) <= 2:
            for key, label, placeholder in champs:
                donnees[key] = st.text_input(label, placeholder=placeholder, key=f"ai_{key}_{st.session_state['ai_analyste']}")
        else:
            col_a, col_b = st.columns(2)
            for i, (key, label, placeholder) in enumerate(champs):
                with (col_a if i % 2 == 0 else col_b):
                    donnees[key] = st.text_input(label, placeholder=placeholder, key=f"ai_{key}_{st.session_state['ai_analyste']}")

        col1, col2 = st.columns([3, 1])
        with col1:
            generer = st.button("🚀 GÉNÉRER L'ANALYSE", use_container_width=True, type="primary")
        with col2:
            if st.button("🗑 Effacer", use_container_width=True):
                st.session_state.pop("ai_result", None)
                st.rerun()

        if generer:
            champs_vides = [label for key, label, _ in analyste["champs"] if not donnees.get(key, "").strip()]
            if champs_vides:
                st.warning(f"⚠️ Remplis : {', '.join(champs_vides[:2])}")
            else:
                with st.spinner("⏳ Analyse en cours... (30-60 secondes)"):
                    result = _call_groq(analyste["prompt"](donnees))
                    st.session_state["ai_result"]  = result
                    st.session_state["ai_donnees"] = donnees

        if "ai_result" in st.session_state and st.session_state["ai_result"]:
            st.markdown("---")
            st.markdown(st.session_state["ai_result"])

            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                if st.button("📄 EXPORTER PDF", key="btn_pdf_intel", use_container_width=True, type="primary"):
                    with st.spinner("Génération du PDF..."):
                        try:
                            pdf_bytes = _generate_pdf(
                                analyste_nom=st.session_state.get("ai_analyste",""),
                                donnees=st.session_state.get("ai_donnees",{}),
                                rapport=st.session_state["ai_result"]
                            )
                            fname = f"AM_Intel_{st.session_state.get('ai_analyste','rapport').replace(' ','_').replace('/','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                            st.download_button("⬇️ Télécharger PDF", data=pdf_bytes, file_name=fname,
                                               mime="application/pdf", key="dl_pdf_intel", use_container_width=True)
                        except Exception as e:
                            st.error(f"Erreur PDF : {e}")

            with col_a2:
                if st.button("💬 CONTINUER EN CHAT", key="to_chat", use_container_width=True):
                    if "chat_history" not in st.session_state:
                        st.session_state.chat_history = []
                    st.session_state.chat_history.append({"role": "user", "content": f"Voici le rapport {st.session_state.get('ai_analyste','')} :", "time": datetime.now().strftime("%H:%M")})
                    st.session_state.chat_history.append({"role": "assistant", "content": st.session_state["ai_result"], "time": datetime.now().strftime("%H:%M")})
                    st.session_state.ai_mode = "chat"
                    st.rerun()

            with col_a3:
                if st.button("🔄 NOUVELLE ANALYSE", key="reset_expert", use_container_width=True):
                    st.session_state.pop("ai_result", None)
                    st.rerun()

            st.markdown("""
            <div class="disclaimer-ai">
            ⚠️ AVERTISSEMENT : Les analyses générées par AM Intelligence sont produites par une IA à des fins éducatives et informatives uniquement.
            Elles ne constituent pas un conseil en investissement. Tout investissement comporte un risque de perte en capital.
            </div>""", unsafe_allow_html=True)
