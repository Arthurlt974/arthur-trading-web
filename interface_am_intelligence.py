import streamlit as st
import requests
import json
import io
from datetime import datetime
from translations import t, get_lang

# ── Modèle Groq ──
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── 6 Prompts ──
ANALYSTES = {
    "🏦 JPMorgan — Pré-Earnings": {
        "description": "Note d'analyse pré-résultats style JPMorgan Senior",
        "color": "#1a3a5c",
        "border": "#2d6abf",
        "champs": [
            ("entreprise", "Nom de l'entreprise", "ex: Apple, NVIDIA, LVMH..."),
        ],
        "prompt": lambda d: f"""Tu es un analyste senior en recherche actions chez JPMorgan, spécialisé dans les notes de pré-publication de résultats pour investisseurs institutionnels.

J'ai besoin d'une analyse complète, structurée et professionnelle des résultats d'une entreprise avant sa publication. Fournis-moi un rapport factuel et data-driven dans le style d'une note JPMorgan pré-earnings :
- Résultats des 4 derniers trimestres vs consensus (historique de beat/miss sur CA et EPS)
- Consensus actuel pour le prochain trimestre (CA + EPS)
- Les key metrics que Wall Street surveille spécifiquement pour cette société
- Répartition du CA par segment + tendances récentes
- Résumé des guidances et commentaires du management lors du dernier earnings call
- Mouvement implicite anticipé du titre (via options)
- Réaction historique du cours le jour des résultats sur les 4 derniers trimestres
- Scénario haussier : estimation d'impact sur le prix
- Scénario baissier : estimation du risque downside
- Recommandation stratégique pré-résultats : acheter, vendre, attendre (avec justification courte)

Présente le tout sous forme de note d'analyse pré-résultats professionnelle et concise, avec un ton senior JPMorgan (factuel, précis, sans hype).

Entreprise : {d['entreprise']}
"""
    },

    "🌑 BlackRock — Multi-Asset Allocation": {
        "description": "Portefeuille personnalisé style BlackRock institutionnel",
        "color": "#1a1a2e",
        "border": "#e63946",
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

Construis de zéro un portefeuille personnalisé, équilibré et adapté à ma situation :
- Allocation d'actifs précise (actions, obligations, alternatifs, cash...) avec % exacts
- Recommandations d'ETF/fonds spécifiques (tickers) par catégorie
- Distinction claire core (noyau stable) vs satellites (opportunistes)
- Fourchette de rendement annuel attendu (données 2020-2026)
- Drawdown max estimé en année baissière
- Calendrier de rééquilibrage + règles de déclenchement
- Optimisation fiscale selon mon type de compte
- Plan DCA si versements mensuels
- Benchmark de référence
- Investment Policy Statement (IPS) d'une page

Style : factuel, prudent, data-driven, comme une note interne BlackRock (données 2025-2026).

Ma situation :
- Âge : {d['age']}
- Revenus annuels : {d['revenus']}
- Épargne mensuelle : {d['epargne']}
- Objectif : {d['objectif']}
- Tolérance au risque : {d['risque']}
- Type de compte : {d['compte']}
- Horizon : {d['horizon']}

IMPORTANT : Commence IMMÉDIATEMENT par l'allocation d'actifs. Pas d'introduction. Structure directe et professionnelle."""
    },

    "⚜️ Rothschild — Legacy Portfolio": {
        "description": "Blueprint patrimonial intergénérationnel style Rothschild & Co",
        "color": "#1a1208",
        "border": "#d4a017",
        "champs": [
            ("age", "Âge", "ex: 45"),
            ("revenus", "Revenus annuels", "ex: 120 000€"),
            ("epargne", "Épargne mensuelle", "ex: 2000€"),
            ("objectif", "Objectif", "PRÉSERVATION / TRANSMISSION / REVENU PASSIF / CROISSANCE MODÉRÉE"),
            ("risque", "Tolérance au risque", "CONSERVATEUR / MODÉRÉ / DYNAMIQUE"),
            ("compte", "Type de compte", "PEA / Assurance-vie / PER / CTO / Fiducie"),
            ("horizon", "Horizon", "LONG TERME / 10-20 ANS / +20 ANS / INTERGÉNÉRATIONNEL"),
        ],
        "prompt": lambda d: f"""Tu es un stratège senior en analyse financière chez Rothschild & Co, expert en investissements intergénérationnels pour familles fortunées, avec un focus sur la préservation du capital et la diversification value.

Je souhaite construire un portefeuille inspiré de la stratégie Rothschild : actifs réels durables, value investing conservateur, buy & hold pour transmission patrimoniale et croissance composée. Construis et présente un blueprint portefeuille patrimoine adapté à mon profil :
- Allocation d'actifs précise (actions value, obligations, immobilier/or/alternatifs, cash...) avec % exacts
- Recommandations spécifiques d'ETF/fonds/actifs réels (tickers) par catégorie
- Distinction claire core (préservation capital) vs opportunistes (croissance modérée)
- Fourchette de rendement annuel attendu (données historiques 2020-2026)
- Estimation du drawdown max en année baissière
- Calendrier de rééquilibrage + règles de déclenchement
- Optimisation fiscale/transmission pour héritage (selon type de compte)
- Plan de versements progressifs (DCA) si applicable
- Benchmark de référence
- Investment Policy Statement (IPS) d'une page

Style : prudent, value-oriented, factuel comme un conseiller Rothschild — données récentes (2025-2026), sans spéculation.

Ma situation :
- Âge : {d['age']}
- Revenus annuels : {d['revenus']}
- Épargne mensuelle : {d['epargne']}
- Objectif : {d['objectif']}
- Tolérance au risque : {d['risque']}
- Type de compte : {d['compte']}
- Horizon : {d['horizon']}

IMPORTANT : Commence IMMÉDIATEMENT par l'allocation. Pas d'introduction ni d'espace vide."""
    },

    "🎩 Buffett — Value Portfolio": {
        "description": "Portefeuille value long terme style Berkshire Hathaway",
        "color": "#0a1a08",
        "border": "#4caf50",
        "champs": [
            ("risque", "Tolérance au risque", "CONSERVATEUR / MODÉRÉ / DYNAMIQUE / AGRESSIF"),
            ("montant", "Montant total investi", "ex: 10 000€"),
            ("horizon", "Horizon d'investissement", "LONG TERME / 10-20 ANS / +20 ANS"),
            ("secteurs", "Secteurs préférés", "ex: TECH, SANTÉ, FINANCE, CONSOMMATION..."),
        ],
        "prompt": lambda d: f"""Tu es Warren Buffett, CEO de Berkshire Hathaway, maître du value investing long terme et des intérêts composés. Je souhaite construire un portefeuille inspiré de ta stratégie : achat d'entreprises exceptionnelles à prix raisonnable, buy & hold pour maximiser les intérêts composés.

Construis et présente un blueprint portefeuille value long terme adapté à mon profil :
- Sélection de 10-15 actions value avec fort moat (tickers + valorisation actuelle)
- Pour chaque : P/E actuel vs historique, ROE sur 10 ans, moat économique (faible/modéré/fort) + justification, croissance EPS sur 5 ans, marge de sécurité estimée
- Répartition sectorielle équilibrée pour diversification durable
- Projection des intérêts composés sur 10-20 ans basé sur mon montant investi (scénarios conservateur/moyen/agressif)
- Estimation du rendement annuel composé moyen attendu
- Impact des intérêts composés (réinvestissement dividende/plus-values) sur la capitalisation finale
- Classement final : des plus défensives aux plus opportunistes

Présente le tout sous forme de blueprint professionnel : tableau récapitulatif clair + graphique de projection composée + commentaire stratégique global (risques, patience, moat durable).

Ton style : prudent, value-oriented, factuel comme Buffett — données récentes (2025-2026), sans spéculation.

Ma situation :
- Tolérance au risque : {d['risque']}
- Montant total investi : {d['montant']}
- Horizon : {d['horizon']}
- Secteurs préférés : {d['secteurs']}

IMPORTANT : Présente IMMÉDIATEMENT le tableau des actions sans aucune introduction. Commence directement par le tableau récapitulatif. Pas de phrases d'introduction, pas d'espace vide. Structure : 1) Tableau actions 2) Répartition sectorielle 3) Projection composée 4) Commentaire global."""
    },

    "🎓 Harvard Endowment — Dividendes": {
        "description": "Portefeuille dividendes passifs style Harvard Endowment",
        "color": "#1a0808",
        "border": "#c41e3a",
        "champs": [
            ("montant", "Montant total investi", "ex: 20 000€"),
            ("objectif_revenu", "Objectif de revenu mensuel passif", "ex: 500€/mois"),
            ("compte", "Type de compte", "PEA / CTO / Assurance-vie / PER"),
            ("imposition", "Tranche d'imposition", "0% / 11% / 30% / 41% / 45%"),
        ],
        "prompt": lambda d: f"""Tu es le Chief Investment Strategist du Harvard University Endowment (dotation de plus de 50 milliards de dollars), expert mondial en stratégies actions génératrices de revenus passifs durables.

Je souhaite construire un portefeuille axé sur les dividendes fiables et croissants, capable de produire un revenu passif stable et croissant. Construis et présente :
- Une sélection de 15 à 20 actions à dividendes de très haute qualité (avec tickers et rendement actuel)
- Pour chaque action : score de sécurité du dividende (1-10) + nombre d'années consécutives de croissance du dividende
- Analyse du payout ratio et commentaire sur la soutenabilité
- Répartition sectorielle équilibrée pour minimiser la concentration
- Projection du revenu mensuel passif basé sur mon montant investi
- Estimation du taux de croissance annuel moyen des dividendes sur 5 ans
- Projection DRIP (réinvestissement automatique des dividendes) montrant la capitalisation sur 10 ans
- Implications fiscales selon mon type de compte et ma tranche d'imposition
- Classement final des valeurs : de la plus sûre à la plus dynamique

Présente le tout sous forme de blueprint de portefeuille dividendes professionnel.

Ma situation :
- Montant total investi : {d['montant']}
- Objectif de revenu mensuel passif : {d['objectif_revenu']}
- Type de compte : {d['compte']}
- Tranche d'imposition : {d['imposition']}"""
    },

    "💼 Goldman Sachs — Stock Screener": {
        "description": "Screening et sélection d'actions style Goldman Sachs UHNW",
        "color": "#0a0a1a",
        "border": "#4d9fff",
        "champs": [
            ("risque", "Tolérance au risque", "CONSERVATEUR / MODÉRÉ / DYNAMIQUE / AGRESSIF"),
            ("montant", "Montant investi (total ou par titre)", "ex: 5 000€"),
            ("horizon", "Horizon d'investissement", "COURT / MOYEN / LONG TERME / 5-10 ANS / +10 ANS"),
            ("secteurs", "Secteurs préférés", "ex: TECH, SANTÉ, ÉNERGIE, CONSOMMATION, FINANCE"),
        ],
        "prompt": lambda d: f"""Tu es un analyste actions senior chez Goldman Sachs avec 20 ans d'expérience dans la sélection d'actions pour clients UHNW et fonds souverains.

J'ai besoin d'un screening et d'une analyse complète, structurée et professionnelle, adaptée à mon profil.

Fournis un rapport factuel et data-driven :
- Les 10 meilleures actions correspondant à mes critères, avec tickers boursiers
- Pour chaque action :
  - Ratio P/E actuel vs moyenne sectorielle
  - Évolution du CA sur 5 ans
  - Santé du bilan : ratio dette/fonds propres + commentaire
  - Rendement dividende + score de soutenabilité (1-10)
  - Avantage concurrentiel (faible/modéré/fort) avec justification
  - Objectif de cours à 12 mois (scénario haussier/baissier)
  - Note de risque globale (1-10) avec justification courte
  - Zone d'entrée recommandée + stop-loss

Présente tout dans un tableau récapitulatif élégant, suivi d'un commentaire global sur la sélection et les risques macro actuels. Utilise un ton senior Goldman Sachs, données récentes (2025-2026) et des comparaisons sectorielles précises sans hype.

Mon profil :
- Tolérance au risque : {d['risque']}
- Montant investi : {d['montant']}
- Horizon : {d['horizon']}
- Secteurs préférés : {d['secteurs']}

IMPORTANT : Présente IMMÉDIATEMENT le tableau des actions sans aucune introduction. Commence directement par le tableau récapitulatif. Pas de phrases d'introduction, pas d'espace vide. Structure : 1) Tableau actions 2) Répartition sectorielle 3) Projection composée 4) Commentaire global."""
    },
}


def _call_groq(prompt: str) -> str:
    """Appel API Groq."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
        if not key:
            return "❌ Clé API Groq manquante dans les secrets Streamlit."
        
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.3,
            },
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Erreur API : {e}"



def _generate_pdf(analyste_nom: str, donnees: dict, rapport: str) -> bytes:
    """Génère un PDF du rapport AM Intelligence."""
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
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=15*mm,
    )

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title  = S("t", fontName="Helvetica-Bold", fontSize=24, textColor=C_ORANGE, alignment=TA_CENTER, spaceAfter=4)
    s_sub    = S("s", fontName="Helvetica", fontSize=10, textColor=C_GREY, alignment=TA_CENTER, spaceAfter=3)
    s_sect   = S("se", fontName="Helvetica-Bold", fontSize=12, textColor=C_ORANGE, spaceBefore=10, spaceAfter=4)
    s_h1     = S("h1", fontName="Helvetica-Bold", fontSize=11, textColor=C_ORANGE, spaceBefore=8, spaceAfter=3)
    s_h2     = S("h2", fontName="Helvetica-Bold", fontSize=10, textColor=C_AMBER, spaceBefore=6, spaceAfter=2)
    s_h3     = S("h3", fontName="Helvetica-Bold", fontSize=9, textColor=C_WHITE, spaceBefore=4, spaceAfter=2)
    s_body   = S("b", fontName="Helvetica", fontSize=8, textColor=C_GREY, spaceAfter=3, leading=13)
    s_bullet = S("bl", fontName="Helvetica", fontSize=8, textColor=C_WHITE, spaceAfter=2, leading=12, leftIndent=12)
    s_param  = S("p", fontName="Helvetica", fontSize=8, textColor=C_AMBER, spaceAfter=2)
    s_footer = S("f", fontName="Helvetica", fontSize=7, textColor=C_BORDER, alignment=TA_CENTER)

    story = []

    # ── En-tête ──
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("AM-TRADING", s_title))
    story.append(Paragraph("AM INTELLIGENCE — RAPPORT D'ANALYSE", s_sub))
    story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", s_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ORANGE, spaceAfter=8))

    # ── Analyste ──
    story.append(Paragraph(f"Analyste : {analyste_nom}", s_sect))

    # ── Paramètres ──
    if donnees:
        story.append(Paragraph("Paramètres de l'analyse :", s_h2))
        for k, v in donnees.items():
            if v and str(v).strip():
                story.append(Paragraph(f"• {k.upper()} : {v}", s_param))
        story.append(Spacer(1, 3*mm))

    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=8))

    # ── Corps du rapport — parser le markdown ──
    story.append(Paragraph("RAPPORT", s_sect))

    import re
    for line in rapport.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm))
            continue

        # Nettoyer les caractères spéciaux non supportés
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Supprimer les * et # pour le texte brut
        clean = re.sub(r"[*#`]", "", line).strip()
        if not clean:
            continue

        if line.startswith("# "):
            story.append(Paragraph(re.sub(r"^#+\s*", "", clean), s_h1))
        elif line.startswith("## "):
            story.append(Paragraph(re.sub(r"^#+\s*", "", clean), s_h2))
        elif line.startswith("### "):
            story.append(Paragraph(re.sub(r"^#+\s*", "", clean), s_h3))
        elif line.startswith("- ") or line.startswith("• "):
            story.append(Paragraph(f"• {clean[2:]}", s_bullet))
        elif re.match(r"^\d+\.\s", line):
            story.append(Paragraph(clean, s_bullet))
        elif line.startswith("---"):
            story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=4))
        else:
            story.append(Paragraph(clean, s_body))

    # ── Footer ──
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "AM-Trading Bloomberg Terminal  •  Analyse générée par IA  •  Ne constitue pas un conseil en investissement",
        s_footer))

    doc.build(story)
    return buf.getvalue()

def show_am_intelligence():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&display=swap');
    .ai-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 22px; font-weight: 700;
        color: #ff6600; letter-spacing: 3px;
        margin-bottom: 4px;
    }
    .ai-sub {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px; color: #444;
        letter-spacing: 2px; margin-bottom: 24px;
    }
    .analyste-card {
        border-radius: 8px; padding: 14px 16px;
        margin-bottom: 8px; cursor: pointer;
        transition: all 0.15s;
        font-family: 'IBM Plex Mono', monospace;
    }
    .analyste-card:hover { opacity: 0.85; }
    .result-box {
        background: #080808;
        border: 1px solid #1a1a1a;
        border-radius: 8px;
        padding: 24px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        color: #ccc;
        line-height: 1.8;
        white-space: pre-wrap;
        margin-top: 16px;
    }
    .disclaimer-ai {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px; color: #333;
        border-top: 1px solid #111;
        padding-top: 8px; margin-top: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ai-header">🤖 AM INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="ai-sub">ANALYSES FINANCIÈRES PROPULSÉES PAR IA · 6 EXPERTS WALL STREET</div>', unsafe_allow_html=True)

    # Sélection analyste
    noms = list(ANALYSTES.keys())
    if "ai_analyste" not in st.session_state:
        st.session_state["ai_analyste"] = noms[0]

    # Toolbar de sélection
    choix = st.radio(
        "Choisir un expert",
        options=noms,
        index=noms.index(st.session_state["ai_analyste"]),
        label_visibility="collapsed",
        key="ai_analyste_radio"
    )
    if choix != st.session_state["ai_analyste"]:
        st.session_state["ai_analyste"] = choix
        st.rerun()

    analyste = ANALYSTES[st.session_state["ai_analyste"]]
    st.markdown(f"""
    <div style='background:{analyste["color"]};border:1px solid {analyste["border"]};
    border-radius:8px;padding:12px 16px;margin:12px 0;font-family:IBM Plex Mono,monospace;'>
    <div style='font-size:11px;color:{analyste["border"]};letter-spacing:1px;font-weight:700;'>
    {st.session_state["ai_analyste"]}</div>
    <div style='font-size:10px;color:#888;margin-top:4px;'>{analyste["description"]}</div>
    </div>
    """, unsafe_allow_html=True)

    # Formulaire
    st.markdown("##### 📋 Ton profil")
    donnees = {}
    for key, label, placeholder in analyste["champs"]:
        donnees[key] = st.text_input(label, placeholder=placeholder, key=f"ai_{key}_{st.session_state['ai_analyste']}")

    # Bouton générer
    col1, col2 = st.columns([2, 1])
    with col1:
        generer = st.button("🚀 GÉNÉRER L'ANALYSE", use_container_width=True, type="primary")
    with col2:
        if st.button("🗑 Effacer", use_container_width=True):
            if "ai_result" in st.session_state:
                del st.session_state["ai_result"]
            st.rerun()

    if generer:
        # Vérifier que les champs obligatoires sont remplis
        champs_vides = [label for key, label, _ in analyste["champs"] if not donnees.get(key, "").strip()]
        if champs_vides:
            st.warning(f"⚠️ Remplis au moins : {', '.join(champs_vides[:2])}")
        else:
            with st.spinner(f"⏳ Analyse en cours... (30-60 secondes)"):
                prompt = analyste["prompt"](donnees)
                result = _call_groq(prompt)
                st.session_state["ai_result"]   = result
                st.session_state["ai_donnees"]  = donnees
                st.session_state["ai_analyste"] = st.session_state["ai_analyste"]  # déjà mis à jour via st.radio

    # Afficher le résultat
    if "ai_result" in st.session_state and st.session_state["ai_result"]:
        st.markdown("---")
        # Affichage markdown natif (tableaux, gras, bullet points)
        st.markdown("""
        <style>
        .stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 12px !important;
            color: #ccc !important;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            font-family: 'IBM Plex Mono', monospace !important;
            color: #ff6600 !important;
            letter-spacing: 1px !important;
        }
        .stMarkdown table {
            background: #080808 !important;
            border: 1px solid #1a1a1a !important;
            width: 100% !important;
        }
        .stMarkdown th {
            background: #0d0800 !important;
            color: #ff6600 !important;
            border: 1px solid #333 !important;
            padding: 6px 10px !important;
        }
        .stMarkdown td {
            border: 1px solid #1a1a1a !important;
            padding: 5px 10px !important;
        }
        .stMarkdown strong { color: #ff6600 !important; }
        </style>
        """, unsafe_allow_html=True)
        with st.container():
            st.markdown(st.session_state["ai_result"])
        
        # Bouton PDF
        if st.button("📄 EXPORTER EN PDF", key="btn_pdf_intelligence", use_container_width=True, type="primary"):
            with st.spinner("Génération du PDF..."):
                try:
                    pdf_bytes = _generate_pdf(
                        analyste_nom = st.session_state.get("ai_analyste", ""),
                        donnees      = st.session_state.get("ai_donnees", {}),
                        rapport      = st.session_state["ai_result"],
                    )
                    fname = f"AM_Intelligence_{st.session_state.get('ai_analyste','rapport').replace(' ','_').replace('/','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    st.download_button(
                        "⬇️ Télécharger le rapport PDF",
                        data=pdf_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        key="dl_pdf_intel",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Erreur PDF : {e}")

        st.markdown("""
        <div class="disclaimer-ai">
        ⚠️ AVERTISSEMENT : Les analyses générées par AM Intelligence sont produites par une IA à des fins éducatives et informatives uniquement.
        Elles ne constituent pas un conseil en investissement. Tout investissement comporte un risque de perte en capital.
        </div>
        """, unsafe_allow_html=True)
