import streamlit as st
import subprocess
import sys

# Configuration de la page
st.set_page_config(page_title="AM Trading", layout="wide")

st.sidebar.title("🚀 AM Trading")
choix = st.sidebar.radio("Outils :", ["Screener", "Session", "Fear & Greed", "Duel"])

def executer_et_afficher(nom_fichier):
    st.write(f"### Exécution de {nom_fichier}...")
    
    # On lance le fichier comme si on tapait "python nom_fichier.py" dans le terminal
    resultat = subprocess.run([sys.executable, nom_fichier], capture_output=True, text=True)
    
    # On affiche ce que le terminal aurait affiché
    if resultat.stdout:
        st.code(resultat.stdout)
    if resultat.stderr:
        st.error("Erreur dans le script :")
        st.code(resultat.stderr)

if choix == "Screener":
    executer_et_afficher("Screener.py")

elif choix == "Session":
    # Attention: ton Session.py a une boucle "while True", 
    # pour le web il va charger à l'infini. 
    # Il faudrait enlever le "while True" dans Session.py pour que ça s'affiche ici.
    executer_et_afficher("Session.py")

elif choix == "Fear & Greed":
    executer_et_afficher("fear and gread index.py")

elif choix == "Duel":
    st.warning("Le mode Duel demande une saisie clavier (input) qui ne marche pas sur le web.")
    executer_et_afficher("Duel V2.py")
