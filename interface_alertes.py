"""
interface_alertes.py — AM-Trading | Système d'Alertes avec notifications Email
4 types d'alertes : Prix cible, Variation %, RSI, Croisement MA
Stockage : Firebase Firestore (champ 'alerts')
Notifications : Gmail SMTP via st.secrets
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import plotly.graph_objects as go
from translations import t, get_lang

# ══════════════════════════════════════════════
#  HELPERS FIREBASE (réutilise firebase_auth)
# ══════════════════════════════════════════════

def _save_alerts(alerts: list):
    """Sauvegarde les alertes dans Firebase + session state."""
    from firebase_auth import _save_current_session_config
    st.session_state["alerts"] = alerts
    try:
        _save_current_session_config()
    except Exception:
        pass

# ══════════════════════════════════════════════
#  EMAIL
# ══════════════════════════════════════════════

def _send_email(subject: str, body_html: str) -> bool:
    """
    Envoie un email via Gmail SMTP.
    Destinataire = email du compte connecté (st.session_state.user_email).
    Expéditeur SMTP configuré dans st.secrets (SMTP_USER + SMTP_PASSWORD).
    """
    try:
        smtp_user = st.secrets.get("SMTP_USER", "")
        smtp_pass = st.secrets.get("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_pass:
            return False

        # Destinataire = email du compte connecté, pas un secrets séparé
        to_email = st.session_state.get("user_email", "")
        if not to_email or to_email == "Invité" or "@" not in to_email:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"AM-Trading 🔔 <{smtp_user}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Email non envoyé : {e}")
        return False


def _email_body(alert: dict, current_price: float, change_pct: float, extra: str = "") -> str:
    color = "#00ff88" if "au-dessus" in alert["type"] or "positive" in alert["type"] else "#ff4444"
    return f"""
    <div style="background:#0d0d0d;color:#fff;font-family:monospace;padding:30px;border-radius:12px;max-width:600px;margin:auto;border:2px solid #ff9800;">
      <h2 style="color:#ff9800;margin:0 0 20px 0;">🔔 ALERTE DÉCLENCHÉE — AM-Trading</h2>
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="color:#aaa;padding:8px 0;">Ticker</td>
            <td style="color:#fff;font-weight:bold;font-size:18px;">{alert['ticker']}</td></tr>
        <tr><td style="color:#aaa;padding:8px 0;">Type</td>
            <td style="color:#ff9800;">{alert['type']}</td></tr>
        <tr><td style="color:#aaa;padding:8px 0;">Seuil</td>
            <td style="color:#fff;">{alert['value']}</td></tr>
        <tr><td style="color:#aaa;padding:8px 0;">Prix actuel</td>
            <td style="color:{color};font-size:20px;font-weight:bold;">{current_price:.2f}</td></tr>
        <tr><td style="color:#aaa;padding:8px 0;">Variation 24h</td>
            <td style="color:{color};">{change_pct:+.2f}%</td></tr>
        {'<tr><td style="color:#aaa;padding:8px 0;">Info</td><td style="color:#fff;">' + extra + '</td></tr>' if extra else ''}
        <tr><td style="color:#aaa;padding:8px 0;">Heure</td>
            <td style="color:#fff;">{datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}</td></tr>
      </table>
      <p style="color:#555;font-size:12px;margin:20px 0 0 0;">AM-Trading Bloomberg Terminal</p>
    </div>
    """

# ══════════════════════════════════════════════
#  CALCULS TECHNIQUES
# ══════════════════════════════════════════════

def _get_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 50.0


def _get_ma_cross(closes: pd.Series, fast: int = 20, slow: int = 50) -> dict:
    """Retourne la position relative des MAs et si croisement récent."""
    if len(closes) < slow + 5:
        return {"cross": None, "fast_val": None, "slow_val": None}
    ma_fast = closes.rolling(fast).mean()
    ma_slow = closes.rolling(slow).mean()
    # Croisement haussier : fast passe au-dessus de slow dans les 3 dernières bougies
    cross_up   = (ma_fast.iloc[-1] > ma_slow.iloc[-1]) and (ma_fast.iloc[-4] < ma_slow.iloc[-4])
    cross_down = (ma_fast.iloc[-1] < ma_slow.iloc[-1]) and (ma_fast.iloc[-4] > ma_slow.iloc[-4])
    return {
        "cross":    "up" if cross_up else ("down" if cross_down else None),
        "fast_val": round(float(ma_fast.iloc[-1]), 2),
        "slow_val": round(float(ma_slow.iloc[-1]), 2),
    }


def _check_alert(alert: dict, df: pd.DataFrame) -> tuple[bool, float, float, str]:
    """
    Vérifie si une alerte est déclenchée.
    Retourne : (triggered, current_price, change_pct, extra_info)
    """
    closes = df["Close"].squeeze()
    current_price = float(closes.iloc[-1])
    prev_close    = float(closes.iloc[-2]) if len(closes) >= 2 else current_price
    change_pct    = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
    extra         = ""
    triggered     = False

    t = alert["type"]

    if t == "Prix au-dessus":
        triggered = current_price >= float(alert["value"])

    elif t == "Prix en-dessous":
        triggered = current_price <= float(alert["value"])

    elif t == "Variation % positive":
        triggered = change_pct >= float(alert["value"])

    elif t == "Variation % négative":
        triggered = change_pct <= -float(alert["value"])

    elif t == "RSI survente":
        rsi = _get_rsi(closes)
        triggered = rsi <= float(alert["value"])
        extra = f"RSI actuel : {rsi:.1f}"

    elif t == "RSI surachat":
        rsi = _get_rsi(closes)
        triggered = rsi >= float(alert["value"])
        extra = f"RSI actuel : {rsi:.1f}"

    elif t == "Croisement MA haussier":
        res = _get_ma_cross(closes, int(alert.get("ma_fast", 20)), int(alert.get("ma_slow", 50)))
        triggered = res["cross"] == "up"
        extra = f"MA{alert.get('ma_fast',20)}={res['fast_val']} / MA{alert.get('ma_slow',50)}={res['slow_val']}"

    elif t == "Croisement MA baissier":
        res = _get_ma_cross(closes, int(alert.get("ma_fast", 20)), int(alert.get("ma_slow", 50)))
        triggered = res["cross"] == "down"
        extra = f"MA{alert.get('ma_fast',20)}={res['fast_val']} / MA{alert.get('ma_slow',50)}={res['slow_val']}"

    return triggered, current_price, change_pct, extra

# ══════════════════════════════════════════════
#  UI PRINCIPALE
# ══════════════════════════════════════════════

def show_alertes():
    st.markdown("""
        <div style='text-align:center;padding:30px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
                    border:3px solid #ff9800;border-radius:15px;margin-bottom:20px;'>
            <h1 style='color:#ff9800;margin:0;font-size:48px;text-shadow:0 0 20px #ff9800;'>🔔 ALERTS MANAGER</h1>
            <p style='color:#ffb84d;margin:10px 0 0 0;font-size:18px;'>Prix cible · Variation % · RSI · Croisement MA · Email</p>
        </div>
    """, unsafe_allow_html=True)

    # Init session
    if "alerts"          not in st.session_state: st.session_state.alerts          = []
    if "triggered_alerts" not in st.session_state: st.session_state.triggered_alerts = []

    alerts   = st.session_state.alerts
    active   = [a for a in alerts if a.get("active", True)]
    inactive = [a for a in alerts if not a.get("active", True)]

    # ── KPIs ──
    smtp_ok    = bool(st.secrets.get("SMTP_USER","") and st.secrets.get("SMTP_PASSWORD",""))
    user_email = st.session_state.get("user_email", "")
    email_ok   = smtp_ok and bool(user_email and user_email != "Invité" and "@" in user_email)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total alertes", len(alerts))
    c2.metric("Actives",       len(active))
    c3.metric("Déclenchées",   len(st.session_state.triggered_alerts))
    c4.metric("Email",         f"✅ {user_email}" if email_ok else ("⚠️ SMTP manquant" if not smtp_ok else "⚠️ Non connecté"))

    if not smtp_ok:
        st.info("""
        **📧 Pour activer les notifications email**, ajoutez dans `.streamlit/secrets.toml` :
        ```toml
        SMTP_USER     = "votre@gmail.com"
        SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"   # App Password Gmail
        ```
        Les alertes seront envoyées directement à l'email du compte connecté.
        👉 Générez un App Password : **Google Account → Sécurité → Mots de passe d'application**
        """)
    elif not email_ok:
        st.warning("Connectez-vous avec un compte pour recevoir les alertes par email.")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["➕ CRÉER UNE ALERTE", "📋 MES ALERTES", "✅ HISTORIQUE"])

    # ════════════════════════════════════════════
    #  TAB 1 — CRÉER
    # ════════════════════════════════════════════
    with tab1:
        st.markdown("### ➕ NOUVELLE ALERTE")
        c_left, c_right = st.columns(2)

        with c_left:
            ticker_input = st.text_input(t("ticker"), value="NVDA", key="new_alert_ticker").upper().strip()
            alert_type   = st.selectbox("TYPE D'ALERTE", [
                "Prix au-dessus", "Prix en-dessous",
                "Variation % positive", "Variation % négative",
                "RSI survente", "RSI surachat",
                "Croisement MA haussier", "Croisement MA baissier",
            ], key="new_alert_type")
            alert_name   = st.text_input("NOM (optionnel)", placeholder="Ex: NVDA breakout", key="new_alert_name")

        with c_right:
            # Valeur seuil selon type
            if "Prix" in alert_type:
                # Afficher le prix actuel en hint
                try:
                    fi = yf.Ticker(ticker_input).fast_info
                    current = getattr(fi, "last_price", None)
                    hint = f"Prix actuel : {current:.2f}" if current else ""
                except Exception:
                    hint = ""
                alert_value = st.number_input(
                    f"PRIX CIBLE {'▲' if 'au-dessus' in alert_type else '▼'}",
                    min_value=0.01, value=150.0, step=1.0, key="new_alert_val_prix"
                )
                if hint:
                    st.caption(hint)
                ma_fast = ma_slow = None

            elif "Variation" in alert_type:
                alert_value = st.number_input(
                    "VARIATION % SEUIL",
                    min_value=0.1, value=5.0, step=0.5, key="new_alert_val_var"
                )
                st.caption("Variation sur la dernière clôture (24h)")
                ma_fast = ma_slow = None

            elif "RSI" in alert_type:
                default_rsi = 30.0 if "survente" in alert_type else 70.0
                alert_value = st.number_input(
                    "SEUIL RSI (14)",
                    min_value=1.0, max_value=99.0, value=default_rsi, step=1.0, key="new_alert_val_rsi"
                )
                st.caption("RSI 14 périodes — survente < 30 / surachat > 70")
                ma_fast = ma_slow = None

            else:  # Croisement MA
                alert_value = 0.0
                col_ma1, col_ma2 = st.columns(2)
                ma_fast = col_ma1.number_input("MA rapide", min_value=2, max_value=50,  value=20, step=1, key="new_ma_fast")
                ma_slow = col_ma2.number_input("MA lente",  min_value=10, max_value=200, value=50, step=1, key="new_ma_slow")
                st.caption("Croisement détecté sur les 3 dernières bougies")

            notify_email = st.checkbox("📧 Notifier par email", value=email_ok, key="new_alert_email", disabled=not email_ok)

        # Bouton créer
        if st.button("🚀 CRÉER L'ALERTE", key="btn_create_alert", use_container_width=True, type="primary"):
            new_alert = {
                "id":           str(uuid.uuid4())[:8],
                "ticker":       ticker_input,
                "type":         alert_type,
                "value":        alert_value,
                "name":         alert_name if alert_name else f"{ticker_input} — {alert_type}",
                "created_at":   datetime.now().strftime("%d/%m/%Y %H:%M"),
                "active":       True,
                "notify_email": notify_email,
            }
            if ma_fast: new_alert["ma_fast"] = ma_fast
            if ma_slow: new_alert["ma_slow"] = ma_slow

            alerts.append(new_alert)
            _save_alerts(alerts)
            st.success(f"✅ Alerte créée : **{new_alert['name']}**")
            st.rerun()

    # ════════════════════════════════════════════
    #  TAB 2 — MES ALERTES
    # ════════════════════════════════════════════
    with tab2:
        if not active:
            st.info("Aucune alerte active. Créez votre première alerte !")
        else:
            col_btn1, col_btn2 = st.columns([2, 1])
            with col_btn1:
                run_check = st.button("🔍 VÉRIFIER TOUTES LES ALERTES MAINTENANT", key="btn_check_all", use_container_width=True, type="primary")
            with col_btn2:
                if st.button("🗑️ Tout supprimer", key="btn_del_all", use_container_width=True):
                    st.session_state.alerts = []
                    _save_alerts([])
                    st.rerun()

            if run_check:
                emails_sent = 0
                triggered_count = 0
                progress = st.progress(0, text="Vérification en cours...")

                for i, alert in enumerate(active):
                    progress.progress((i + 1) / len(active), text=f"Vérification {alert['ticker']}...")
                    try:
                        df = yf.download(alert["ticker"], period="60d", progress=False, auto_adjust=True)
                        if df.empty: continue
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        if len(df) < 5: continue

                        triggered, current_price, change_pct, extra = _check_alert(alert, df)

                        if triggered:
                            triggered_count += 1
                            alert["active"] = False
                            st.session_state.triggered_alerts.append({
                                "alert":         dict(alert),
                                "triggered_at":  datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                "current_price": current_price,
                                "change_pct":    change_pct,
                                "extra":         extra,
                            })
                            # Envoi email
                            if alert.get("notify_email") and email_ok:
                                subj = f"🔔 Alerte déclenchée : {alert['ticker']} — {alert['type']}"
                                html = _email_body(alert, current_price, change_pct, extra)
                                if _send_email(subj, html):
                                    emails_sent += 1
                    except Exception:
                        continue

                progress.empty()
                _save_alerts(alerts)

                if triggered_count:
                    st.success(f"✅ {triggered_count} alerte(s) déclenchée(s) !" + (f" · {emails_sent} email(s) envoyé(s)" if emails_sent else ""))
                else:
                    st.info("Aucune alerte déclenchée pour le moment.")
                st.rerun()

            st.markdown("---")

            # Affichage des alertes
            TYPE_EMOJI = {
                "Prix au-dessus": "📈", "Prix en-dessous": "📉",
                "Variation % positive": "🚀", "Variation % négative": "⚠️",
                "RSI survente": "📊", "RSI surachat": "📊",
                "Croisement MA haussier": "🔼", "Croisement MA baissier": "🔽",
            }
            for alert in active:
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    emoji = TYPE_EMOJI.get(alert["type"], "🔔")
                    notif = "📧" if alert.get("notify_email") else ""
                    val_display = (
                        f"MA{alert.get('ma_fast',20)}/MA{alert.get('ma_slow',50)}"
                        if "MA" in alert["type"]
                        else f"{alert['value']}" + ("%" if "Variation" in alert["type"] else "")
                    )
                    st.markdown(f"""
                        <div style='padding:15px;background:linear-gradient(135deg,#1a1a1a,#0d0d0d);
                                    border-radius:10px;margin:8px 0;border:2px solid #ff9800;'>
                            <div style='display:flex;justify-content:space-between;'>
                                <span style='color:#ff9800;font-weight:bold;font-size:16px;'>{emoji} {alert['name']} {notif}</span>
                                <span style='color:#555;font-size:12px;'>{alert['created_at']}</span>
                            </div>
                            <p style='color:#ccc;margin:5px 0 0 0;font-size:13px;'>
                                <b style='color:#fff;'>{alert['ticker']}</b> &nbsp;·&nbsp; {alert['type']} &nbsp;·&nbsp; Seuil : <b style='color:#ffb84d;'>{val_display}</b>
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{alert['id']}", help=t("supprimer")):
                        alerts.remove(alert)
                        _save_alerts(alerts)
                        st.rerun()

    # ════════════════════════════════════════════
    #  TAB 3 — HISTORIQUE
    # ════════════════════════════════════════════
    with tab3:
        triggered_history = st.session_state.triggered_alerts
        if not triggered_history:
            st.info("Aucune alerte déclenchée pour le moment.")
        else:
            if st.button("🗑️ Effacer l'historique", key="btn_clear_history"):
                st.session_state.triggered_alerts = []
                st.rerun()
            st.markdown("---")
            for item in sorted(triggered_history, key=lambda x: x["triggered_at"], reverse=True):
                alert       = item["alert"]
                price       = item["current_price"]
                change      = item["change_pct"]
                color_chg   = "#00ff88" if change >= 0 else "#ff4444"
                extra       = item.get("extra", "")
                st.markdown(f"""
                    <div style='padding:20px;background:#00ff0011;border-radius:10px;
                                margin:12px 0;border:2px solid #00ff88;'>
                        <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <h3 style='color:#00ff88;margin:0;'>✅ {alert['name']}</h3>
                            <span style='color:#00ff88;font-weight:bold;'>DÉCLENCHÉE</span>
                        </div>
                        <p style='color:#ccc;margin:8px 0 4px 0;'>
                            <b>{alert['ticker']}</b> &nbsp;·&nbsp; {alert['type']} &nbsp;·&nbsp; Seuil : {alert['value']}
                        </p>
                        <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
                                    background:#0a0a0a;padding:12px;border-radius:8px;margin-top:8px;'>
                            <div><p style='color:#999;font-size:11px;margin:0;'>PRIX</p>
                                 <b style='color:#fff;font-size:16px;'>{price:.2f}</b></div>
                            <div><p style='color:#999;font-size:11px;margin:0;'>VARIATION 24H</p>
                                 <b style='color:{color_chg};font-size:16px;'>{change:+.2f}%</b></div>
                            <div><p style='color:#999;font-size:11px;margin:0;'>INFO</p>
                                 <b style='color:#ffb84d;font-size:13px;'>{extra if extra else "—"}</b></div>
                        </div>
                        <p style='color:#555;font-size:12px;margin:10px 0 0 0;'>🕐 {item['triggered_at']}</p>
                    </div>
                """, unsafe_allow_html=True)
