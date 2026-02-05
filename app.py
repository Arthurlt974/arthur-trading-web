import streamlit as st
import os

# Configuration du site
st.set_page_config(page_title="AM Trading - Arthur & Milan", layout="wide")

st.sidebar.title("🚀 AM Trading")
choix = st.sidebar.radio("Choisir un programme :", 
    ["Analyse Graham (Screener)", "Session Live", "Fear & Greed", "Duel d'Actions"])

# Fonction pour exécuter tes fichiers tels quels
def executer_fichier(nom_fichier):
    with open(nom_fichier, "r", encoding="utf-8") as f:
        code = f.read()
    exec(code, globals())

# Affichage selon le choix
if choix == "Analyse Graham (Screener)":
    st.header("📊 Programme : Screener.py")
    executer_fichier("Screener.py")

elif choix == "Session Live":
    st.header("🌍 Programme : Session.py")
    # Note : Session.py contient une boucle infinie (while True). 
    # Pour le web, il est préférable de l'exécuter une seule fois.
    executer_fichier("Session.py")

elif choix == "Fear & Greed":
    st.header("🔍 Programme : Fear and Greed Index")
    executer_fichier("fear and gread index.py")

elif choix == "Duel d'Actions":
    st.header("⚔️ Programme : Duel V2")
    executer_fichier("Duel V2.py")
