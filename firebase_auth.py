"""
firebase_auth.py
Module d'authentification Firebase pour AM-Trading Terminal
Gère : inscription, connexion, mode invité, sauvegarde/chargement config utilisateur
"""

import streamlit as st
import requests
import json
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIG FIREBASE
# ─────────────────────────────────────────────
FIREBASE_API_KEY        = st.secrets["FIREBASE_API_KEY"]
FIREBASE_PROJECT_ID     = st.secrets["FIREBASE_PROJECT_ID"]

AUTH_URL      = f"https://identitytoolkit.googleapis.com/v1/accounts"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"


# ══════════════════════════════════════════════
#  AUTHENTIFICATION
# ══════════════════════════════════════════════

def sign_up(email: str, password: str) -> dict:
    url = f"{AUTH_URL}:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload)
    return r.json()

def sign_in(email: str, password: str) -> dict:
    url = f"{AUTH_URL}:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload)
    return r.json()

def reset_password(email: str) -> dict:
    url = f"{AUTH_URL}:sendOobCode?key={FIREBASE_API_KEY}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    r = requests.post(url, json=payload)
    return r.json()


# ══════════════════════════════════════════════
#  FIRESTORE – HELPERS INTERNES
# ══════════════════════════════════════════════

def _firestore_headers(id_token: str) -> dict:
    return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}

def _to_firestore(value):
    if isinstance(value, bool):  return {"booleanValue": value}
    if isinstance(value, int):   return {"integerValue": str(value)}
    if isinstance(value, float): return {"doubleValue": value}
    if isinstance(value, str):   return {"stringValue": value}
    if isinstance(value, list):
        return {"arrayValue": {"values": [_to_firestore(v) for v in value]}}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {k: _to_firestore(v) for k, v in value.items()}}}
    return {"stringValue": str(value)}

def _from_firestore(field):
    if "stringValue"  in field: return field["stringValue"]
    if "integerValue" in field: return int(field["integerValue"])
    if "doubleValue"  in field: return float(field["doubleValue"])
    if "booleanValue" in field: return field["booleanValue"]
    if "arrayValue"   in field:
        return [_from_firestore(v) for v in field["arrayValue"].get("values", [])]
    if "mapValue" in field:
        return {k: _from_firestore(v) for k, v in field["mapValue"].get("fields", {}).items()}
    return None


# ══════════════════════════════════════════════
#  FIRESTORE – LECTURE / ÉCRITURE
# ══════════════════════════════════════════════

def save_user_config(id_token: str, uid: str, config: dict) -> bool:
    url = f"{FIRESTORE_URL}/users/{uid}"
    fields = {k: _to_firestore(v) for k, v in config.items()}
    r = requests.patch(url, headers=_firestore_headers(id_token), json={"fields": fields})
    return r.status_code == 200

def load_user_config(id_token: str, uid: str) -> dict:
    url = f"{FIRESTORE_URL}/users/{uid}"
    r = requests.get(url, headers=_firestore_headers(id_token))
    if r.status_code == 200:
        fields = r.json().get("fields", {})
        return {k: _from_firestore(v) for k, v in fields.items()}
    return {}

def save_user_field(id_token: str, uid: str, field_name: str, value) -> bool:
    url = f"{FIRESTORE_URL}/users/{uid}?updateMask.fieldPaths={field_name}"
    payload = {"fields": {field_name: _to_firestore(value)}}
    r = requests.patch(url, headers=_firestore_headers(id_token), json=payload)
    return r.status_code == 200


# ══════════════════════════════════════════════
#  CONFIG PAR DÉFAUT
# ══════════════════════════════════════════════

DEFAULT_CONFIG = {
    "watchlist": ["BTC-USD", "ETH-USD", "AAPL", "TSLA", "NVDA", "MC.PA", "TTE.PA"],
    "alerts": [],
    "portfolio": [
        {"symbol": "BTC", "qty": 0.0, "buy_price": 0.0},
        {"symbol": "ETH", "qty": 0.0, "buy_price": 0.0},
    ],
    "theme": {
        "accent_color": "#ff9800",
        "chart_style":  "candles",
        "default_period": "6mo",
        "default_category": "ACTIONS & BOURSE",
    },
    "created_at": datetime.now().isoformat(),
    "last_login":  datetime.now().isoformat(),
}


# ══════════════════════════════════════════════
#  UI – PAGE DE CONNEXION / INSCRIPTION
# ══════════════════════════════════════════════

def render_auth_page() -> bool:
    """
    Affiche la page d'authentification.
    Retourne True si l'utilisateur est connecté (ou en mode invité).
    """

    # ── Déjà connecté ou mode invité ──
    if st.session_state.get("user_logged_in") or st.session_state.get("guest_mode"):
        return True

    # ── CSS terminal ──
    st.markdown("""
        <style>
            .auth-box {
                max-width: 480px;
                margin: 40px auto;
                padding: 40px;
                background: #111;
                border: 2px solid #ff9800;
                border-radius: 8px;
                font-family: monospace;
            }
            .auth-title {
                text-align: center;
                color: #ff9800;
                font-size: 28px;
                font-weight: bold;
                letter-spacing: 4px;
                margin-bottom: 8px;
            }
            .auth-sub {
                text-align: center;
                color: #555;
                font-size: 12px;
                margin-bottom: 30px;
            }
            .guest-btn > button {
                background-color: #1a1a1a !important;
                color: #aaaaaa !important;
                border: 1px solid #444 !important;
                font-size: 13px !important;
            }
            .guest-btn > button:hover {
                background-color: #333 !important;
                color: #fff !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="auth-box">
            <div class="auth-title">AM-TRADING TERMINAL</div>
            <div class="auth-sub">[ SECURE ACCESS SYSTEM v2.0 ]</div>
        </div>
    """, unsafe_allow_html=True)

    # ── Code d'accès global ──
    with st.expander("🔐 CODE D'ACCÈS TERMINAL", expanded=True):
        access_code = st.text_input("CODE D'ACCÈS GLOBAL", type="password", key="access_code_input",
                                    placeholder="Code fourni par l'administrateur")
        if access_code and access_code != "1234":
            st.error("!! CODE INVALIDE")
            return False
        if not access_code:
            st.info("Entrez le code d'accès global pour accéder à l'authentification.")
            return False

    st.markdown("---")

    # ══════════════════════════════════════════
    #  BOUTON MODE INVITÉ (bien visible)
    # ══════════════════════════════════════════
    st.markdown("""
        <div style='text-align: center; margin-bottom: 10px;'>
            <span style='color: #888; font-size: 13px; font-family: monospace;'>
                Pas de compte ? Accès limité sans sauvegarde
            </span>
        </div>
    """, unsafe_allow_html=True)

    col_guest1, col_guest2, col_guest3 = st.columns([1, 2, 1])
    with col_guest2:
        if st.button("👤 CONTINUER EN MODE INVITÉ", use_container_width=True, key="btn_guest"):
            st.session_state["guest_mode"]   = True
            st.session_state["user_logged_in"] = False
            st.session_state["user_email"]   = "Invité"
            # Appliquer la config par défaut pour l'invité
            _apply_config_to_session(DEFAULT_CONFIG.copy())
            st.info("✅ Mode invité activé. Vos données ne seront pas sauvegardées.")
            st.rerun()

    st.markdown("""
        <div style='text-align: center; color: #444; font-size: 11px; margin-top: 5px; font-family: monospace;'>
            ── OU CONNECTEZ-VOUS ──
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Onglets Connexion / Inscription / Reset ──
    tab_login, tab_signup, tab_reset = st.tabs(["🔑 CONNEXION", "📝 CRÉER UN COMPTE", "🔄 MOT DE PASSE OUBLIÉ"])

    # ─────────────────
    #  CONNEXION
    # ─────────────────
    with tab_login:
        st.markdown("#### IDENTIFICATION")
        login_email = st.text_input("EMAIL", key="login_email", placeholder="votre@email.com")
        login_pwd   = st.text_input("MOT DE PASSE", type="password", key="login_pwd")

        if st.button("▶ CONNEXION", key="btn_login", use_container_width=True):
            if not login_email or not login_pwd:
                st.error("Remplissez tous les champs.")
            else:
                with st.spinner("Authentification..."):
                    res = sign_in(login_email, login_pwd)
                if "idToken" in res:
                    st.session_state["user_logged_in"]  = True
                    st.session_state["guest_mode"]      = False
                    st.session_state["user_email"]      = res["email"]
                    st.session_state["user_uid"]        = res["localId"]
                    st.session_state["user_id_token"]   = res["idToken"]

                    config = load_user_config(res["idToken"], res["localId"])
                    if not config:
                        config = DEFAULT_CONFIG.copy()
                        save_user_config(res["idToken"], res["localId"], config)
                    else:
                        config["last_login"] = datetime.now().isoformat()
                        save_user_field(res["idToken"], res["localId"], "last_login", config["last_login"])

                    _apply_config_to_session(config)
                    st.success(f"✅ Bienvenue {res['email']} !")
                    st.rerun()
                else:
                    error_msg = res.get("error", {}).get("message", "Erreur inconnue")
                    if error_msg == "EMAIL_NOT_FOUND":             st.error("Email introuvable.")
                    elif error_msg == "INVALID_PASSWORD":          st.error("Mot de passe incorrect.")
                    elif error_msg == "INVALID_LOGIN_CREDENTIALS": st.error("Email ou mot de passe incorrect.")
                    else: st.error(f"Erreur : {error_msg}")

    # ─────────────────
    #  INSCRIPTION
    # ─────────────────
    with tab_signup:
        st.markdown("#### CRÉER UN COMPTE")
        st.info("Votre configuration (watchlist, alertes, portefeuille) sera sauvegardée automatiquement.")

        signup_email = st.text_input("EMAIL", key="signup_email", placeholder="votre@email.com")
        signup_pwd   = st.text_input("MOT DE PASSE", type="password", key="signup_pwd", help="Minimum 6 caractères")
        signup_pwd2  = st.text_input("CONFIRMER LE MOT DE PASSE", type="password", key="signup_pwd2")

        if st.button("✅ CRÉER MON COMPTE", key="btn_signup", use_container_width=True):
            if not signup_email or not signup_pwd:
                st.error("Remplissez tous les champs.")
            elif signup_pwd != signup_pwd2:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(signup_pwd) < 6:
                st.error("Le mot de passe doit faire au moins 6 caractères.")
            else:
                with st.spinner("Création du compte..."):
                    res = sign_up(signup_email, signup_pwd)
                if "idToken" in res:
                    config = DEFAULT_CONFIG.copy()
                    config["created_at"] = datetime.now().isoformat()
                    save_user_config(res["idToken"], res["localId"], config)

                    st.session_state["user_logged_in"]  = True
                    st.session_state["guest_mode"]      = False
                    st.session_state["user_email"]      = res["email"]
                    st.session_state["user_uid"]        = res["localId"]
                    st.session_state["user_id_token"]   = res["idToken"]
                    _apply_config_to_session(config)

                    st.success(f"🎉 Compte créé ! Bienvenue {signup_email}")
                    st.balloons()
                    st.rerun()
                else:
                    error_msg = res.get("error", {}).get("message", "Erreur inconnue")
                    if error_msg == "EMAIL_EXISTS":        st.error("Cet email est déjà utilisé.")
                    elif "WEAK_PASSWORD" in error_msg:     st.error("Mot de passe trop faible (min. 6 caractères).")
                    elif "INVALID_EMAIL" in error_msg:     st.error("Format d'email invalide.")
                    else: st.error(f"Erreur : {error_msg}")

    # ─────────────────
    #  RESET PASSWORD
    # ─────────────────
    with tab_reset:
        st.markdown("#### RÉINITIALISATION DU MOT DE PASSE")
        reset_email = st.text_input("EMAIL DU COMPTE", key="reset_email", placeholder="votre@email.com")
        if st.button("📧 ENVOYER LE LIEN", key="btn_reset", use_container_width=True):
            if not reset_email:
                st.error("Entrez votre email.")
            else:
                with st.spinner("Envoi en cours..."):
                    res = reset_password(reset_email)
                if "email" in res:
                    st.success(f"✅ Email de réinitialisation envoyé à {reset_email}")
                else:
                    st.error("Erreur lors de l'envoi. Vérifiez l'email.")

    return False


# ══════════════════════════════════════════════
#  BARRE UTILISATEUR (sidebar)
# ══════════════════════════════════════════════

def render_user_sidebar():
    """Affiche les infos utilisateur + bouton déconnexion dans la sidebar."""
    if not st.session_state.get("user_logged_in") and not st.session_state.get("guest_mode"):
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 MON COMPTE")
    email = st.session_state.get("user_email", "")

    # ── Badge mode invité ──
    if st.session_state.get("guest_mode"):
        st.sidebar.markdown("""
            <div style='background:#1a1a1a; border:1px solid #444; border-radius:5px; padding:8px; text-align:center;'>
                <span style='color:#aaa; font-size:12px;'>👤 MODE INVITÉ</span><br>
                <span style='color:#555; font-size:10px;'>Config non sauvegardée</span>
            </div>
        """, unsafe_allow_html=True)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)

        # Bouton pour se connecter depuis la sidebar
        if st.sidebar.button("🔑 SE CONNECTER / CRÉER UN COMPTE", key="btn_login_from_guest", use_container_width=True):
            _clear_session()
            st.rerun()
    else:
        st.sidebar.markdown(f"<small style='color:#ff9800;'>📧 {email}</small>", unsafe_allow_html=True)

        if st.sidebar.button("💾 SAUVEGARDER MA CONFIG", key="btn_save_config", use_container_width=True):
            _save_current_session_config()
            st.sidebar.success("Config sauvegardée ✅")

        if st.sidebar.button("🚪 DÉCONNEXION", key="btn_logout", use_container_width=True):
            _save_current_session_config()
            _clear_session()
            st.rerun()


# ══════════════════════════════════════════════
#  HELPERS INTERNES SESSION
# ══════════════════════════════════════════════

def _apply_config_to_session(config: dict):
    if "watchlist" in config:
        st.session_state["watchlist"] = config["watchlist"]

    if "alerts" in config:
        alerts = config["alerts"]
        fixed = []
        for a in alerts:
            if isinstance(a, dict):
                if "created_at" not in a:
                    a["created_at"] = datetime.now()
                fixed.append(a)
        st.session_state["alerts"] = fixed

    if "portfolio" in config:
        st.session_state["portfolio"] = config["portfolio"]

    if "theme" in config and isinstance(config["theme"], dict):
        st.session_state["user_theme"] = config["theme"]

    st.session_state["user_config_loaded"] = True


def _save_current_session_config():
    """Sauvegarde seulement si connecté (pas en mode invité)."""
    if st.session_state.get("guest_mode"):
        return  # On ne sauvegarde pas pour les invités

    uid      = st.session_state.get("user_uid")
    id_token = st.session_state.get("user_id_token")
    if not uid or not id_token:
        return

    alerts_raw = st.session_state.get("alerts", [])
    alerts_serializable = []
    for a in alerts_raw:
        a2 = dict(a)
        if "created_at" in a2 and isinstance(a2["created_at"], datetime):
            a2["created_at"] = a2["created_at"].isoformat()
        alerts_serializable.append(a2)

    config = {
        "watchlist":  st.session_state.get("watchlist", DEFAULT_CONFIG["watchlist"]),
        "alerts":     alerts_serializable,
        "portfolio":  st.session_state.get("portfolio", DEFAULT_CONFIG["portfolio"]),
        "theme":      st.session_state.get("user_theme", DEFAULT_CONFIG["theme"]),
        "last_login": datetime.now().isoformat(),
    }
    save_user_config(id_token, uid, config)


def _clear_session():
    keys_to_remove = [
        "user_logged_in", "guest_mode", "user_email", "user_uid", "user_id_token",
        "user_config_loaded", "user_theme",
        "watchlist", "alerts", "portfolio",
        "password_correct",
    ]
    for k in keys_to_remove:
        st.session_state.pop(k, None)
