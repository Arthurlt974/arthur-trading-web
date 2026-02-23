"""
interface_economie.py
Section ÉCONOMIE MONDIALE pour AM-Trading Terminal
Indicateurs : Chômage, Inflation, PIB, Taux directeurs, Confiance, Dette
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ══════════════════════════════════════════════
#  DONNÉES MACRO (mises à jour manuellement)
#  Sources : Banques centrales, Eurostat, BLS, INSEE
# ══════════════════════════════════════════════

PAYS_CONFIG = {
    "🇺🇸 USA":       {"code": "us",  "couleur": "#4fc3f7"},
    "🇪🇺 Zone Euro": {"code": "eu",  "couleur": "#ffb74d"},
    "🇫🇷 France":    {"code": "fr",  "couleur": "#81c784"},
    "🇨🇳 Chine":     {"code": "cn",  "couleur": "#e57373"},
    "🇯🇵 Japon":     {"code": "jp",  "couleur": "#ce93d8"},
    "🇬🇧 UK":        {"code": "gb",  "couleur": "#80cbc4"},
}

# ── Taux de chômage (%) ──
CHOMAGE = {
    "🇺🇸 USA":       {"actuel": 3.7,  "precedent": 3.9,  "historique": [4.0, 3.9, 3.8, 3.7, 3.6, 3.5, 3.7, 3.8, 3.9, 3.7, 3.6, 3.7]},
    "🇪🇺 Zone Euro": {"actuel": 6.4,  "precedent": 6.5,  "historique": [6.8, 6.7, 6.6, 6.5, 6.4, 6.5, 6.6, 6.5, 6.4, 6.3, 6.4, 6.4]},
    "🇫🇷 France":    {"actuel": 7.3,  "precedent": 7.4,  "historique": [7.6, 7.5, 7.4, 7.4, 7.3, 7.2, 7.3, 7.4, 7.5, 7.3, 7.2, 7.3]},
    "🇨🇳 Chine":     {"actuel": 5.0,  "precedent": 5.1,  "historique": [5.5, 5.3, 5.2, 5.1, 5.0, 5.1, 5.2, 5.0, 4.9, 5.0, 5.1, 5.0]},
    "🇯🇵 Japon":     {"actuel": 2.4,  "precedent": 2.5,  "historique": [2.6, 2.5, 2.5, 2.4, 2.4, 2.5, 2.6, 2.5, 2.4, 2.3, 2.4, 2.4]},
    "🇬🇧 UK":        {"actuel": 4.2,  "precedent": 4.3,  "historique": [4.5, 4.4, 4.3, 4.3, 4.2, 4.1, 4.2, 4.3, 4.4, 4.2, 4.1, 4.2]},
}

# ── Inflation CPI (%) ──
INFLATION = {
    "🇺🇸 USA":       {"actuel": 3.2,  "precedent": 3.4,  "cible": 2.0, "historique": [8.2, 7.1, 6.5, 5.0, 4.0, 3.7, 3.4, 3.2, 3.1, 3.2, 3.4, 3.2]},
    "🇪🇺 Zone Euro": {"actuel": 2.9,  "precedent": 3.4,  "cible": 2.0, "historique": [9.9, 8.5, 6.9, 5.3, 4.3, 3.4, 2.9, 2.6, 2.4, 2.9, 3.1, 2.9]},
    "🇫🇷 France":    {"actuel": 3.1,  "precedent": 3.5,  "cible": 2.0, "historique": [6.2, 5.9, 5.2, 4.9, 4.0, 3.5, 3.1, 2.9, 2.7, 3.1, 3.3, 3.1]},
    "🇨🇳 Chine":     {"actuel": 0.3,  "precedent": 0.1,  "cible": 3.0, "historique": [2.1, 1.8, 1.5, 0.7, 0.1, 0.2, 0.3, 0.4, 0.5, 0.3, 0.2, 0.3]},
    "🇯🇵 Japon":     {"actuel": 2.8,  "precedent": 3.0,  "cible": 2.0, "historique": [3.6, 3.7, 4.0, 3.5, 3.1, 3.0, 2.8, 2.6, 2.5, 2.8, 2.9, 2.8]},
    "🇬🇧 UK":        {"actuel": 4.0,  "precedent": 4.6,  "cible": 2.0, "historique": [10.1, 9.2, 8.7, 6.7, 5.2, 4.6, 4.0, 3.8, 3.4, 4.0, 4.2, 4.0]},
}

# ── PIB / Croissance (%) ──
PIB = {
    "🇺🇸 USA":       {"actuel": 2.5,  "precedent": 2.1,  "historique": [2.1, 1.9, 2.0, 2.1, 2.4, 2.5, 2.6, 2.5, 2.4, 2.5, 2.3, 2.5]},
    "🇪🇺 Zone Euro": {"actuel": 0.1,  "precedent": 0.0,  "historique": [0.8, 0.5, 0.2, 0.1, 0.0, 0.1, 0.2, 0.1, 0.0, 0.1, 0.2, 0.1]},
    "🇫🇷 France":    {"actuel": 0.7,  "precedent": 0.9,  "historique": [1.2, 1.0, 0.9, 0.8, 0.7, 0.8, 0.9, 0.8, 0.7, 0.7, 0.8, 0.7]},
    "🇨🇳 Chine":     {"actuel": 5.2,  "precedent": 4.9,  "historique": [4.5, 6.3, 4.9, 5.2, 5.3, 5.2, 5.1, 5.0, 5.2, 5.2, 5.1, 5.2]},
    "🇯🇵 Japon":     {"actuel": 1.2,  "precedent": -0.7, "historique": [1.0, 0.8, 1.2, 0.4, -0.7, 1.2, 1.0, 0.8, 1.1, 1.2, 0.9, 1.2]},
    "🇬🇧 UK":        {"actuel": 0.1,  "precedent": -0.1, "historique": [0.4, 0.3, 0.1, -0.1, 0.0, 0.1, 0.2, 0.1, 0.0, 0.1, 0.2, 0.1]},
}

# ── Taux directeurs banques centrales (%) ──
TAUX_DIRECTEURS = {
    "🇺🇸 USA":       {"banque": "FED",   "actuel": 5.50, "precedent": 5.25, "prochaine_reunion": "Jan 2025", "historique": [0.25, 1.00, 2.50, 4.50, 5.00, 5.25, 5.50, 5.50, 5.50, 5.50, 5.50, 5.50]},
    "🇪🇺 Zone Euro": {"banque": "BCE",   "actuel": 4.50, "precedent": 4.00, "prochaine_reunion": "Jan 2025", "historique": [0.00, 0.50, 2.00, 3.50, 4.00, 4.50, 4.50, 4.50, 4.50, 4.50, 4.50, 4.50]},
    "🇫🇷 France":    {"banque": "BCE",   "actuel": 4.50, "precedent": 4.00, "prochaine_reunion": "Jan 2025", "historique": [0.00, 0.50, 2.00, 3.50, 4.00, 4.50, 4.50, 4.50, 4.50, 4.50, 4.50, 4.50]},
    "🇨🇳 Chine":     {"banque": "PBOC",  "actuel": 3.45, "precedent": 3.55, "prochaine_reunion": "Fév 2025", "historique": [3.85, 3.70, 3.65, 3.55, 3.45, 3.45, 3.45, 3.45, 3.45, 3.45, 3.45, 3.45]},
    "🇯🇵 Japon":     {"banque": "BOJ",   "actuel": 0.10, "precedent": -0.10,"prochaine_reunion": "Jan 2025", "historique": [-0.10, -0.10, -0.10, -0.10, -0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10]},
    "🇬🇧 UK":        {"banque": "BOE",   "actuel": 5.25, "precedent": 5.00, "prochaine_reunion": "Fév 2025", "historique": [0.25, 1.00, 2.25, 4.00, 5.00, 5.25, 5.25, 5.25, 5.25, 5.25, 5.25, 5.25]},
}

# ── Indice de confiance consommateur ──
CONFIANCE = {
    "🇺🇸 USA":       {"actuel": 110.7, "precedent": 108.7, "historique": [95.3, 98.7, 102.5, 104.2, 107.8, 108.7, 110.7, 109.5, 108.2, 110.7, 111.2, 110.7]},
    "🇪🇺 Zone Euro": {"actuel": -16.9, "precedent": -17.9, "historique": [-20.2, -19.0, -18.3, -17.6, -17.9, -16.9, -16.0, -15.8, -16.2, -16.9, -17.1, -16.9]},
    "🇫🇷 France":    {"actuel": 90.0,  "precedent": 89.0,  "historique": [85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 90.5, 89.8, 90.0, 90.2, 90.0]},
    "🇨🇳 Chine":     {"actuel": 86.2,  "precedent": 85.5,  "historique": [90.1, 88.5, 87.2, 86.0, 85.5, 86.2, 86.8, 86.5, 86.0, 86.2, 86.5, 86.2]},
    "🇯🇵 Japon":     {"actuel": 36.2,  "precedent": 36.7,  "historique": [34.5, 35.2, 35.8, 36.0, 36.7, 36.2, 35.9, 36.1, 36.4, 36.2, 36.0, 36.2]},
    "🇬🇧 UK":        {"actuel": -22.0, "precedent": -24.0, "historique": [-45.0, -40.0, -36.0, -30.0, -25.0, -24.0, -22.0, -21.0, -20.5, -22.0, -22.5, -22.0]},
}

# ── Dette publique (% du PIB) ──
DETTE = {
    "🇺🇸 USA":       {"actuel": 123.3, "precedent": 121.4, "historique": [108.2, 111.5, 118.3, 121.4, 123.3]},
    "🇪🇺 Zone Euro": {"actuel": 88.6,  "precedent": 90.9,  "historique": [97.4, 91.6, 90.9, 88.6, 87.5]},
    "🇫🇷 France":    {"actuel": 110.6, "precedent": 111.8, "historique": [115.2, 112.9, 111.8, 110.6, 109.5]},
    "🇨🇳 Chine":     {"actuel": 83.0,  "precedent": 77.1,  "historique": [56.2, 68.9, 77.1, 83.0, 85.2]},
    "🇯🇵 Japon":     {"actuel": 255.2, "precedent": 261.3, "historique": [234.2, 250.5, 261.3, 255.2, 252.0]},
    "🇬🇧 UK":        {"actuel": 97.8,  "precedent": 101.9, "historique": [85.2, 95.3, 101.9, 97.8, 96.5]},
}

MOIS_LABELS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
ANNEES_DETTE = ["2019", "2020", "2021", "2022", "2023"]


# ══════════════════════════════════════════════
#  HELPERS UI
# ══════════════════════════════════════════════

def carte_indicateur(pays, valeur, precedent, unite="%", inverse=False):
    """Affiche une carte métrique style Bloomberg."""
    variation = valeur - precedent
    if inverse:
        couleur = "#00ff00" if variation < 0 else "#ff4b4b"
    else:
        couleur = "#00ff00" if variation >= 0 else "#ff4b4b"
    signe = "▲" if variation >= 0 else "▼"
    cfg = PAYS_CONFIG.get(pays, {"couleur": "#ff9800"})

    st.markdown(f"""
        <div style="
            background: #0d0d0d;
            border: 1px solid {cfg['couleur']};
            border-left: 4px solid {cfg['couleur']};
            border-radius: 6px;
            padding: 14px;
            margin-bottom: 10px;
        ">
            <div style="color: #888; font-size: 11px; font-family: monospace;">{pays}</div>
            <div style="color: white; font-size: 26px; font-weight: bold; margin: 4px 0;">
                {valeur}{unite}
            </div>
            <div style="color: {couleur}; font-size: 13px; font-family: monospace;">
                {signe} {abs(variation):.1f}{unite} vs précédent ({precedent}{unite})
            </div>
        </div>
    """, unsafe_allow_html=True)


def graphique_historique(titre, donnees, pays_selectionnes, unite="%", inverse=False):
    """Graphique Plotly multi-pays."""
    fig = go.Figure()
    for pays in pays_selectionnes:
        if pays in donnees:
            cfg = PAYS_CONFIG[pays]
            hist = donnees[pays]["historique"]
            labels = MOIS_LABELS[:len(hist)]
            fig.add_trace(go.Scatter(
                x=labels, y=hist,
                name=pays,
                line=dict(color=cfg["couleur"], width=2.5),
                mode="lines+markers",
                marker=dict(size=6),
                hovertemplate=f"<b>{pays}</b><br>{titre}: %{{y}}{unite}<extra></extra>"
            ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d0d0d",
        plot_bgcolor="#0d0d0d",
        title=dict(text=titre, font=dict(color="#ff9800", size=16)),
        height=380,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#333", borderwidth=1),
        xaxis=dict(gridcolor="#222", tickfont=dict(color="#888")),
        yaxis=dict(gridcolor="#222", tickfont=dict(color="#888"), ticksuffix=unite),
        hovermode="x unified"
    )
    return fig


def tableau_comparatif(titre, donnees, pays_selectionnes, unite="%", inverse=False):
    """Tableau de comparaison entre pays."""
    rows = []
    for pays in pays_selectionnes:
        if pays in donnees:
            d = donnees[pays]
            variation = d["actuel"] - d["precedent"]
            if inverse:
                tendance = "🟢 ▼" if variation < 0 else "🔴 ▲"
            else:
                tendance = "🟢 ▲" if variation >= 0 else "🔴 ▼"
            rows.append({
                "Pays": pays,
                "Actuel": f"{d['actuel']}{unite}",
                "Précédent": f"{d['precedent']}{unite}",
                "Variation": f"{variation:+.1f}{unite}",
                "Tendance": tendance
            })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
#  INTERFACE PRINCIPALE
# ══════════════════════════════════════════════

def show_economie():
    st.markdown("""
        <div style='text-align:center; padding:25px; background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
             border:2px solid #ff9800; border-radius:12px; margin-bottom:20px;'>
            <h1 style='color:#ff9800; margin:0; font-size:36px;'>🌍 MACRO ÉCONOMIE MONDIALE</h1>
            <p style='color:#ffb84d; margin:8px 0 0 0; font-size:14px;'>
                Indicateurs économiques clés — USA · Zone Euro · France · Chine · Japon · UK
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Sélecteur de pays ──
    st.markdown("### 🌐 SÉLECTION DES PAYS")
    pays_selectionnes = st.multiselect(
        "Pays à afficher",
        list(PAYS_CONFIG.keys()),
        default=list(PAYS_CONFIG.keys()),
        key="eco_pays"
    )
    if not pays_selectionnes:
        st.warning("Sélectionnez au moins un pays.")
        return

    st.markdown("---")

    # ══════════════════════════════════════════
    #  ONGLETS PAR INDICATEUR
    # ══════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 TABLEAU DE BORD",
        "👷 CHÔMAGE",
        "🔥 INFLATION",
        "📈 PIB / CROISSANCE",
        "🏦 TAUX DIRECTEURS",
        "😊 CONFIANCE CONSO.",
        "💸 DETTE PUBLIQUE"
    ])

    # ══════════════════════════════════════════
    #  ONGLET 1 — TABLEAU DE BORD GLOBAL
    # ══════════════════════════════════════════
    with tab1:
        st.markdown("### 📊 VUE GLOBALE — TOUS LES INDICATEURS")
        st.caption(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y')}")

        rows = []
        for pays in pays_selectionnes:
            rows.append({
                "Pays": pays,
                "Chômage": f"{CHOMAGE[pays]['actuel']}%",
                "Inflation": f"{INFLATION[pays]['actuel']}%",
                "PIB": f"{PIB[pays]['actuel']}%",
                "Taux Directeur": f"{TAUX_DIRECTEURS[pays]['actuel']}%",
                "Confiance": f"{CONFIANCE[pays]['actuel']}",
                "Dette/PIB": f"{DETTE[pays]['actuel']}%",
            })
        df_global = pd.DataFrame(rows)
        st.dataframe(df_global, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🎯 SCORE DE SANTÉ ÉCONOMIQUE")

        for pays in pays_selectionnes:
            cfg = PAYS_CONFIG[pays]
            score = 0
            details = []

            # Chômage (bas = bon)
            c = CHOMAGE[pays]["actuel"]
            if c < 4:    score += 2; details.append("✅ Chômage faible")
            elif c < 6:  score += 1; details.append("🟡 Chômage modéré")
            else:                    details.append("🔴 Chômage élevé")

            # Inflation (proche 2% = bon)
            inf = INFLATION[pays]["actuel"]
            if 1.5 <= inf <= 3:  score += 2; details.append("✅ Inflation maîtrisée")
            elif inf < 1:                     details.append("🟡 Risque déflation")
            else:                             details.append("🔴 Inflation excessive")

            # PIB (positif = bon)
            pib = PIB[pays]["actuel"]
            if pib > 2:   score += 2; details.append("✅ Forte croissance")
            elif pib > 0: score += 1; details.append("🟡 Croissance faible")
            else:                     details.append("🔴 Récession")

            # Dette (faible = bon)
            dette = DETTE[pays]["actuel"]
            if dette < 60:   score += 2; details.append("✅ Dette soutenable")
            elif dette < 100: score += 1; details.append("🟡 Dette modérée")
            else:                         details.append("🔴 Dette élevée")

            score_max = 8
            score_pct = (score / score_max) * 100
            couleur_score = "#00ff00" if score >= 6 else "#ff9800" if score >= 4 else "#ff4b4b"

            with st.expander(f"{pays} — Score : {score}/{score_max}"):
                col_s1, col_s2 = st.columns([1, 3])
                with col_s1:
                    st.markdown(f"""
                        <div style='text-align:center; padding:20px; border:2px solid {couleur_score};
                             border-radius:10px; background:#0d0d0d;'>
                            <div style='color:{couleur_score}; font-size:42px; font-weight:bold;'>{score}</div>
                            <div style='color:#888; font-size:12px;'>/ {score_max}</div>
                            <div style='margin-top:8px;'>
                                <div style='background:#222; border-radius:5px; height:8px;'>
                                    <div style='background:{couleur_score}; width:{score_pct}%;
                                         height:8px; border-radius:5px;'></div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_s2:
                    for d in details:
                        st.write(d)

    # ══════════════════════════════════════════
    #  ONGLET 2 — CHÔMAGE
    # ══════════════════════════════════════════
    with tab2:
        st.markdown("### 👷 TAUX DE CHÔMAGE (%)")
        st.info("💡 Un taux bas indique un marché du travail tendu (bon signe économique). Cible optimale : < 5%")

        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, CHOMAGE[pays]["actuel"], CHOMAGE[pays]["precedent"], "%", inverse=True)

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Taux de Chômage", CHOMAGE, pays_selectionnes, "%", inverse=True)
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.markdown("#### 📋 Comparatif")
            tableau_comparatif("Chômage", CHOMAGE, pays_selectionnes, "%", inverse=True)
            st.markdown("#### 💡 Analyse")
            chomages = {p: CHOMAGE[p]["actuel"] for p in pays_selectionnes}
            meilleur = min(chomages, key=chomages.get)
            pire = max(chomages, key=chomages.get)
            st.success(f"🏆 Meilleur : **{meilleur}** ({chomages[meilleur]}%)")
            st.error(f"⚠️ Plus élevé : **{pire}** ({chomages[pire]}%)")

    # ══════════════════════════════════════════
    #  ONGLET 3 — INFLATION
    # ══════════════════════════════════════════
    with tab3:
        st.markdown("### 🔥 INFLATION CPI (%)")
        st.info("💡 Cible des banques centrales : 2%. Au-dessus = politique monétaire restrictive.")

        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                cible = INFLATION[pays]["cible"]
                actuel = INFLATION[pays]["actuel"]
                diff_cible = actuel - cible
                carte_indicateur(pays, actuel, INFLATION[pays]["precedent"], "%", inverse=True)

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Inflation CPI", INFLATION, pays_selectionnes, "%")
            # Ligne cible 2%
            fig.add_hline(y=2.0, line_dash="dash", line_color="#ff9800", line_width=1.5,
                          annotation_text="Cible 2%", annotation_position="right",
                          annotation=dict(font=dict(color="#ff9800", size=11)))
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.markdown("#### 📋 Comparatif")
            tableau_comparatif("Inflation", INFLATION, pays_selectionnes, "%", inverse=True)
            st.markdown("#### 🎯 Écart vs cible (2%)")
            for pays in pays_selectionnes:
                diff = INFLATION[pays]["actuel"] - 2.0
                couleur = "#ff4b4b" if abs(diff) > 1 else "#ff9800" if abs(diff) > 0.5 else "#00ff00"
                st.markdown(f"<span style='color:{couleur}; font-family:monospace;'>"
                            f"{pays}: {diff:+.1f}% vs cible</span>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    #  ONGLET 4 — PIB / CROISSANCE
    # ══════════════════════════════════════════
    with tab4:
        st.markdown("### 📈 CROISSANCE PIB (%)")
        st.info("💡 Croissance > 2% = économie dynamique. < 0% = récession technique.")

        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, PIB[pays]["actuel"], PIB[pays]["precedent"], "%")

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Croissance PIB", PIB, pays_selectionnes, "%")
            fig.add_hline(y=0, line_dash="dash", line_color="#ff4b4b", line_width=1,
                          annotation_text="Récession", annotation_position="right",
                          annotation=dict(font=dict(color="#ff4b4b", size=10)))
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.markdown("#### 📋 Comparatif")
            tableau_comparatif("PIB", PIB, pays_selectionnes, "%")
            pibs = {p: PIB[p]["actuel"] for p in pays_selectionnes}
            en_recession = [p for p, v in pibs.items() if v < 0]
            if en_recession:
                st.error(f"🔴 En récession : {', '.join(en_recession)}")
            else:
                st.success("✅ Aucun pays en récession parmi la sélection")

    # ══════════════════════════════════════════
    #  ONGLET 5 — TAUX DIRECTEURS
    # ══════════════════════════════════════════
    with tab5:
        st.markdown("### 🏦 TAUX DIRECTEURS DES BANQUES CENTRALES (%)")
        st.info("💡 Des taux élevés freinent l'inflation mais ralentissent la croissance.")

        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                d = TAUX_DIRECTEURS[pays]
                cfg = PAYS_CONFIG[pays]
                variation = d["actuel"] - d["precedent"]
                couleur = "#ff4b4b" if variation > 0 else "#00ff00" if variation < 0 else "#888"
                signe = "▲" if variation > 0 else "▼" if variation < 0 else "→"
                st.markdown(f"""
                    <div style="background:#0d0d0d; border:1px solid {cfg['couleur']};
                         border-left:4px solid {cfg['couleur']}; border-radius:6px; padding:14px; margin-bottom:10px;">
                        <div style="color:#888; font-size:10px;">{pays} — {d['banque']}</div>
                        <div style="color:white; font-size:26px; font-weight:bold;">{d['actuel']}%</div>
                        <div style="color:{couleur}; font-size:12px;">{signe} {abs(variation):.2f}%</div>
                        <div style="color:#555; font-size:10px; margin-top:4px;">
                            Prochaine réunion : {d['prochaine_reunion']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = go.Figure()
            for pays in pays_selectionnes:
                cfg = PAYS_CONFIG[pays]
                d = TAUX_DIRECTEURS[pays]
                fig.add_trace(go.Scatter(
                    x=MOIS_LABELS[:len(d["historique"])],
                    y=d["historique"],
                    name=f"{pays} ({d['banque']})",
                    line=dict(color=cfg["couleur"], width=2.5),
                    mode="lines+markers",
                    marker=dict(size=6),
                ))
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                title=dict(text="Évolution des Taux Directeurs", font=dict(color="#ff9800", size=16)),
                height=380, margin=dict(l=40, r=20, t=50, b=40),
                xaxis=dict(gridcolor="#222"), yaxis=dict(gridcolor="#222", ticksuffix="%"),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.markdown("#### 📋 Banques Centrales")
            rows = []
            for pays in pays_selectionnes:
                d = TAUX_DIRECTEURS[pays]
                rows.append({
                    "Pays": pays, "Banque": d["banque"],
                    "Taux": f"{d['actuel']}%",
                    "Prochaine réunion": d["prochaine_reunion"]
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Divergence FED vs BCE
            if "🇺🇸 USA" in pays_selectionnes and "🇪🇺 Zone Euro" in pays_selectionnes:
                diff = TAUX_DIRECTEURS["🇺🇸 USA"]["actuel"] - TAUX_DIRECTEURS["🇪🇺 Zone Euro"]["actuel"]
                st.markdown("#### 📊 Spread FED vs BCE")
                st.metric("Écart FED - BCE", f"{diff:+.2f}%",
                          help="Un spread positif favorise le Dollar vs l'Euro")

    # ══════════════════════════════════════════
    #  ONGLET 6 — CONFIANCE CONSOMMATEUR
    # ══════════════════════════════════════════
    with tab6:
        st.markdown("### 😊 INDICE DE CONFIANCE DES CONSOMMATEURS")
        st.info("💡 Un indice en hausse = consommateurs optimistes = bonne santé économique attendue.")

        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, CONFIANCE[pays]["actuel"], CONFIANCE[pays]["precedent"], "")

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = graphique_historique("Confiance Consommateur", CONFIANCE, pays_selectionnes, "")
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.markdown("#### 📋 Comparatif")
            tableau_comparatif("Confiance", CONFIANCE, pays_selectionnes, "")
            st.markdown("#### 💡 Note")
            st.caption("USA/Chine : base 100 (positif = optimiste). "
                       "Zone Euro/UK : indice négatif normal (échelle différente).")

    # ══════════════════════════════════════════
    #  ONGLET 7 — DETTE PUBLIQUE
    # ══════════════════════════════════════════
    with tab7:
        st.markdown("### 💸 DETTE PUBLIQUE (% du PIB)")
        st.info("💡 Critère de Maastricht : < 60% du PIB. Au-delà de 100% = risque souverain.")

        cols = st.columns(len(pays_selectionnes))
        for i, pays in enumerate(pays_selectionnes):
            with cols[i % len(cols)]:
                carte_indicateur(pays, DETTE[pays]["actuel"], DETTE[pays]["precedent"], "%", inverse=True)

        st.markdown("---")
        col_g, col_t = st.columns([3, 2])
        with col_g:
            fig = go.Figure()
            for pays in pays_selectionnes:
                cfg = PAYS_CONFIG[pays]
                fig.add_trace(go.Bar(
                    x=[pays.split(" ", 1)[-1]], y=[DETTE[pays]["actuel"]],
                    name=pays, marker_color=cfg["couleur"],
                    text=f"{DETTE[pays]['actuel']}%", textposition="auto"
                ))
            fig.add_hline(y=60, line_dash="dash", line_color="#00ff00", line_width=1.5,
                          annotation_text="Seuil Maastricht 60%",
                          annotation=dict(font=dict(color="#00ff00", size=11)))
            fig.add_hline(y=100, line_dash="dash", line_color="#ff4b4b", line_width=1.5,
                          annotation_text="Zone de risque 100%",
                          annotation=dict(font=dict(color="#ff4b4b", size=11)))
            fig.update_layout(
                template="plotly_dark", paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                title=dict(text="Dette Publique / PIB", font=dict(color="#ff9800", size=16)),
                height=400, margin=dict(l=40, r=20, t=50, b=40),
                showlegend=False,
                yaxis=dict(gridcolor="#222", ticksuffix="%"),
                barmode="group"
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_t:
            st.markdown("#### 📋 Comparatif")
            tableau_comparatif("Dette", DETTE, pays_selectionnes, "%", inverse=True)
            st.markdown("#### 🚦 Statut")
            for pays in pays_selectionnes:
                d = DETTE[pays]["actuel"]
                if d < 60:
                    st.success(f"{pays} : ✅ Sous le seuil Maastricht ({d}%)")
                elif d < 100:
                    st.warning(f"{pays} : 🟡 Au-dessus de 60% ({d}%)")
                else:
                    st.error(f"{pays} : 🔴 Zone de risque ({d}%)")

    st.markdown("---")
    st.caption("⚠️ Données mises à jour manuellement. Sources : FED, BCE, BOE, BOJ, PBOC, INSEE, Eurostat, BLS.")
