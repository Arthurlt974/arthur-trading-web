import streamlit as st
import sys
import io
import contextlib

# Configuration de la page
st.set_page_config(page_title="AM Trading - Arthur & Milan", layout="wide")

# Sidebar
st.sidebar.title("🚀 AM Trading")
choix = st.sidebar.radio("Choisir un programme :", 
    ["Analyse Graham (Screener)", "Session Live", "Fear & Greed", "Duel d'Actions"])

# --- LA FONCTION MAGIQUE POUR TES CODES ---
def lancer_programme_terminal(nom_fichier):
    st.subheader(f"🖥️ Sortie du programme : {nom_fichier}")
    
    # On crée une zone de texte vide pour simuler le terminal
    zone_terminal = st.empty()
    
    # On intercepte les "print" du code original
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            with open(nom_fichier, "r", encoding="utf-8") as f:
                code_brut = f.read()
            
            # On remplace les inputs (qui bloquent le web) par des valeurs vides pour éviter le crash
            # Et on exécute ton code exact
            exec(code_brut, globals())
            
        except Exception as e:
            print(f"\n❌ Erreur dans le code : {e}")

    # On affiche le résultat final dans un bloc de code (style terminal)
    zone_terminal.code(output.getvalue())

# --- AFFICHAGE À DROITE ---
if choix == "Analyse Graham (Screener)":
    lancer_programme_terminal("Screener.py")

elif choix == "Session Live":
    # On retire la boucle infinie pour le web pour que ça s'affiche
    lancer_programme_terminal("Session.py")

elif choix == "Fear & Greed":
    lancer_programme_terminal("fear and gread index.py")

elif choix == "Duel d'Actions":
    st.warning("⚠️ Le mode Duel original utilise 'input()'. Pour le Web, il faudra taper les tickers dans le code ou utiliser une version adaptée.")
    lancer_programme_terminal("Duel V2.py")
