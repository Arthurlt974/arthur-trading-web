# ============================================================
#  interface_finance_marche.py
#  Secteur : FINANCE DE MARCHÉ — Outils Ingénieur Quant
# ============================================================

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
from scipy.stats import norm
from scipy.optimize import brentq
import warnings
warnings.filterwarnings("ignore")

# ── Style commun ──────────────────────────────────────────
PLOTLY_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="#000000",
    plot_bgcolor="#0a0a0a",
    font=dict(family="IBM Plex Mono", color="#e0e0e0", size=11),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=dict(gridcolor="#1a1a1a", showgrid=True),
    yaxis=dict(gridcolor="#1a1a1a", showgrid=True),
)

def _metric(label, value, delta=None):
    if delta:
        try:
            delta_val = float(str(delta).replace("%","").replace("+",""))
            delta_color = "#00C853" if delta_val >= 0 else "#FF3B30"
        except:
            delta_color = "#4d9fff"
        delta_html = f"<div style='font-size:11px;color:{delta_color};'>{delta}</div>"
    else:
        delta_html = ""
    col_css = f"""
    <div style='background:#080808;border:1px solid #1a1a1a;border-radius:4px;
                padding:12px 16px;margin:4px 0;font-family:IBM Plex Mono,monospace;'>
        <div style='font-size:9px;color:#4d9fff;letter-spacing:1px;'>{label}</div>
        <div style='font-size:20px;font-weight:700;color:#ff6600;margin:4px 0;'>{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(col_css, unsafe_allow_html=True)

def _section(title):
    st.markdown(f"""
    <div style='border-left:3px solid #ff6600;padding:4px 12px;margin:16px 0 8px;
                font-family:IBM Plex Mono,monospace;font-size:12px;
                color:#ff6600;letter-spacing:1px;'>{title}</div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  1. PRICING OPTIONS — BLACK-SCHOLES + GREEKS
# ════════════════════════════════════════════════════════════
def show_options_pricing():
    st.markdown("## ⚙️ OPTION PRICER — Black-Scholes")
    st.caption("Pricing européen + sensibilités (Greeks) en temps réel")

    c1, c2, c3 = st.columns(3)
    with c1:
        S  = st.number_input("Spot (S)", value=182.65, step=1.0, key="bs_s")
        K  = st.number_input("Strike (K)", value=185.0, step=1.0, key="bs_k")
        T  = st.number_input("Maturité (années)", value=0.25, step=0.01, min_value=0.01, key="bs_t")
    with c2:
        r  = st.number_input("Taux sans risque (%)", value=4.5, step=0.1, key="bs_r") / 100
        sigma = st.number_input("Volatilité implicite (%)", value=35.0, step=0.5, key="bs_sigma") / 100
        q  = st.number_input("Dividende continu (%)", value=0.0, step=0.1, key="bs_q") / 100
    with c3:
        opt_type = st.selectbox("Type", ["Call", "Put"], key="bs_type")
        style    = st.selectbox("Style", ["Européen", "Américain (approx)"], key="bs_style")
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Calcul Black-Scholes ──
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if opt_type == "Call":
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = np.exp(-q * T) * norm.cdf(d1)
        theta = (-(S * norm.pdf(d1) * sigma * np.exp(-q * T)) / (2 * np.sqrt(T))
                 - r * K * np.exp(-r * T) * norm.cdf(d2)
                 + q * S * np.exp(-q * T) * norm.cdf(d1)) / 365
        rho   = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
        delta = -np.exp(-q * T) * norm.cdf(-d1)
        theta = (-(S * norm.pdf(d1) * sigma * np.exp(-q * T)) / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)
                 - q * S * np.exp(-q * T) * norm.cdf(-d1)) / 365
        rho   = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100

    gamma = norm.pdf(d1) * np.exp(-q * T) / (S * sigma * np.sqrt(T))
    vega  = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100
    moneyness = "ITM" if (opt_type == "Call" and S > K) or (opt_type == "Put" and S < K) else ("ATM" if abs(S-K)/K < 0.01 else "OTM")

    _section("RÉSULTAT DU PRICING")
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1: _metric("PRIX OPTION", f"${price:.4f}")
    with r2: _metric("MONEYNESS", moneyness)
    with r3: _metric("d1", f"{d1:.4f}")
    with r4: _metric("d2", f"{d2:.4f}")
    with r5: _metric("VALEUR TEMPS", f"${max(0, price - max(0, (S-K) if opt_type=='Call' else (K-S))):.4f}")

    _section("GREEKS — SENSIBILITÉS")
    g1, g2, g3, g4, g5 = st.columns(5)
    with g1: _metric("DELTA (Δ)", f"{delta:.4f}", f"{'+' if delta>0 else ''}{delta*100:.1f}% du spot")
    with g2: _metric("GAMMA (Γ)", f"{gamma:.6f}")
    with g3: _metric("THETA (Θ)", f"${theta:.4f}/j")
    with g4: _metric("VEGA (ν)", f"${vega:.4f}/1%")
    with g5: _metric("RHO (ρ)", f"${rho:.4f}/1%")

    _section("PROFIL DE PAYOFF")
    spots = np.linspace(S * 0.7, S * 1.3, 200)
    if opt_type == "Call":
        payoff    = np.maximum(spots - K, 0)
        pnl       = payoff - price
        d1_arr = (np.log(spots / K) + (r - q + 0.5*sigma**2) * T) / (sigma * np.sqrt(T))
        d2_arr = d1_arr - sigma * np.sqrt(T)
        theo   = spots * np.exp(-q*T) * norm.cdf(d1_arr) - K * np.exp(-r*T) * norm.cdf(d2_arr)
    else:
        payoff = np.maximum(K - spots, 0)
        pnl    = payoff - price
        d1_arr = (np.log(spots / K) + (r - q + 0.5*sigma**2) * T) / (sigma * np.sqrt(T))
        d2_arr = d1_arr - sigma * np.sqrt(T)
        theo   = K * np.exp(-r*T) * norm.cdf(-d2_arr) - spots * np.exp(-q*T) * norm.cdf(-d1_arr)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spots, y=payoff, name="Payoff à expiry",
        line=dict(color="#4d9fff", width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(x=spots, y=theo, name="Prix théorique (BS)",
        line=dict(color="#ff6600", width=2.5)))
    fig.add_trace(go.Scatter(x=spots, y=pnl, name="P&L net",
        line=dict(color="#00C853", width=1.5),
        fill="tozeroy", fillcolor="rgba(0,200,83,0.05)"))
    fig.add_vline(x=S, line=dict(color="#fff", width=1, dash="dash"), annotation_text="Spot")
    fig.add_vline(x=K, line=dict(color="#ff6600", width=1, dash="dash"), annotation_text="Strike")
    fig.add_hline(y=0, line=dict(color="#333", width=1))
    fig.update_layout(**PLOTLY_DARK, height=380, title=f"{opt_type} {K} | σ={sigma*100:.1f}% | T={T:.2f}y")
    st.plotly_chart(fig, use_container_width=True)

    _section("SENSIBILITÉ DELTA vs SPOT")
    deltas_call = norm.cdf((np.log(spots/K) + (r-q+0.5*sigma**2)*T) / (sigma*np.sqrt(T)))
    deltas_put  = deltas_call - 1
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=spots, y=deltas_call, name="Delta Call", line=dict(color="#00C853", width=2)))
    fig2.add_trace(go.Scatter(x=spots, y=deltas_put, name="Delta Put", line=dict(color="#FF3B30", width=2)))
    fig2.add_vline(x=S, line=dict(color="#fff", width=1, dash="dash"))
    fig2.update_layout(**PLOTLY_DARK, height=280, yaxis_title="Delta", xaxis_title="Spot")
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  2. SURFACE DE VOLATILITÉ IMPLICITE
# ════════════════════════════════════════════════════════════
def show_vol_surface():
    st.markdown("## 📊 SURFACE DE VOLATILITÉ IMPLICITE")
    st.caption("Smile et term structure de la volatilité — modèle paramétrique SVI")

    c1, c2, c3 = st.columns(3)
    with c1:
        S0 = st.number_input("Spot", value=100.0, key="vs_s")
        r0 = st.number_input("Taux (%)", value=4.5, key="vs_r") / 100
    with c2:
        atm_vol  = st.slider("Vol ATM (%)", 10, 80, 25, key="vs_atm") / 100
        skew     = st.slider("Skew (pente)", -0.5, 0.5, -0.15, step=0.01, key="vs_skew")
    with c3:
        convex   = st.slider("Convexité (smile)", 0.0, 1.0, 0.2, step=0.01, key="vs_conv")
        term_str = st.slider("Term structure (%/an)", -5, 5, 1, key="vs_term") / 100

    strikes  = np.linspace(S0 * 0.7, S0 * 1.3, 30)
    maturities = [1/12, 2/12, 3/12, 6/12, 1.0, 1.5, 2.0]
    mat_labels = ["1M","2M","3M","6M","1Y","18M","2Y"]

    moneyness = np.log(strikes / S0)
    vol_matrix = np.zeros((len(maturities), len(strikes)))
    for i, T in enumerate(maturities):
        term_adj = atm_vol + term_str * T
        vol_matrix[i] = term_adj + skew * moneyness + convex * moneyness**2

    vol_matrix = np.clip(vol_matrix, 0.01, 2.0)

    fig = go.Figure(data=[go.Surface(
        z=vol_matrix * 100,
        x=strikes,
        y=mat_labels,
        colorscale=[[0,"#000080"],[0.3,"#4d9fff"],[0.6,"#ff6600"],[1,"#ff0000"]],
        colorbar=dict(title="Vol %", tickfont=dict(color="#e0e0e0")),
    )])
    fig.update_layout(
        **{k:v for k,v in PLOTLY_DARK.items() if k not in ["xaxis","yaxis"]},
        scene=dict(
            xaxis=dict(title="Strike", gridcolor="#1a1a1a", backgroundcolor="#000"),
            yaxis=dict(title="Maturité", gridcolor="#1a1a1a", backgroundcolor="#000"),
            zaxis=dict(title="Vol impl. %", gridcolor="#1a1a1a", backgroundcolor="#000"),
            bgcolor="#000",
        ),
        height=500,
        title="Surface de Volatilité Implicite (SVI paramétrique)"
    )
    st.plotly_chart(fig, use_container_width=True)

    _section("SMILE PAR MATURITÉ")
    fig2 = go.Figure()
    colors = ["#4d9fff","#ff6600","#00C853","#FF3B30","#FABE2C","#e040fb","#26c6da"]
    for i, (T, lbl) in enumerate(zip(maturities, mat_labels)):
        term_adj = atm_vol + term_str * T
        vols = (term_adj + skew * moneyness + convex * moneyness**2) * 100
        fig2.add_trace(go.Scatter(
            x=strikes, y=np.clip(vols, 1, 200),
            name=lbl, line=dict(color=colors[i], width=2)
        ))
    fig2.add_vline(x=S0, line=dict(color="#fff", dash="dash"), annotation_text="ATM")
    fig2.update_layout(**PLOTLY_DARK, height=320,
                       xaxis_title="Strike", yaxis_title="Vol impl. (%)")
    st.plotly_chart(fig2, use_container_width=True)

    _section("TERM STRUCTURE ATM")
    atm_vols = [(atm_vol + term_str * T) * 100 for T in maturities]
    fig3 = go.Figure(go.Scatter(
        x=mat_labels, y=atm_vols, mode="lines+markers",
        line=dict(color="#ff6600", width=2.5),
        marker=dict(size=8, color="#ff6600")
    ))
    fig3.update_layout(**PLOTLY_DARK, height=260,
                       xaxis_title="Maturité", yaxis_title="Vol ATM (%)")
    st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  3. COURBE DES TAUX & OBLIGATIONS
# ════════════════════════════════════════════════════════════
def show_yield_curve():
    st.markdown("## 📈 COURBE DES TAUX & OBLIGATIONS")
    st.caption("Construction de courbe, pricing obligataire, duration, convexité")

    tab1, tab2 = st.tabs(["📐 Courbe des taux", "💰 Pricer Obligation"])

    with tab1:
        _section("PARAMÈTRES NELSON-SIEGEL")
        c1, c2, c3, c4 = st.columns(4)
        beta0 = c1.slider("β₀ (long terme %)", 0.0, 10.0, 4.5, step=0.1, key="ns_b0")
        beta1 = c2.slider("β₁ (court terme)", -5.0, 5.0, -1.5, step=0.1, key="ns_b1")
        beta2 = c3.slider("β₂ (bosse)", -5.0, 5.0, 2.0, step=0.1, key="ns_b2")
        tau   = c4.slider("τ (vitesse)", 0.1, 5.0, 1.5, step=0.1, key="ns_tau")

        mats = np.linspace(0.25, 30, 200)
        def nelson_siegel(t, b0, b1, b2, tau):
            f = (1 - np.exp(-t/tau)) / (t/tau)
            return b0 + b1 * f + b2 * (f - np.exp(-t/tau))

        yields = nelson_siegel(mats, beta0, beta1, beta2, tau)
        fwd_yields = np.gradient(mats * yields, mats)  # taux forward approx

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.65, 0.35], vertical_spacing=0.05)
        fig.add_trace(go.Scatter(x=mats, y=yields, name="Taux spot",
            line=dict(color="#ff6600", width=2.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=mats, y=fwd_yields, name="Taux forward",
            line=dict(color="#4d9fff", width=1.5, dash="dot")), row=2, col=1)
        fig.add_hline(y=0, line=dict(color="#333"), row=1, col=1)
        fig.update_layout(**PLOTLY_DARK, height=420,
                          title="Courbe des taux — Nelson-Siegel")
        fig.update_yaxes(title_text="Taux (%)", row=1, col=1)
        fig.update_yaxes(title_text="Fwd (%)", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)

        # Métriques clés
        y2 = float(nelson_siegel(2, beta0, beta1, beta2, tau))
        y10 = float(nelson_siegel(10, beta0, beta1, beta2, tau))
        y30 = float(nelson_siegel(30, beta0, beta1, beta2, tau))
        spread_2_10 = y10 - y2
        m1, m2, m3, m4 = st.columns(4)
        with m1: _metric("2Y", f"{y2:.2f}%")
        with m2: _metric("10Y", f"{y10:.2f}%")
        with m3: _metric("30Y", f"{y30:.2f}%")
        with m4: _metric("Spread 2s10s", f"{spread_2_10*100:.0f} bps",
                         f"{'Normale ✅' if spread_2_10>0 else 'Inversée ⚠️'}")

    with tab2:
        _section("PARAMÈTRES DE L'OBLIGATION")
        c1, c2, c3 = st.columns(3)
        face   = c1.number_input("Nominal ($)", value=1000, step=100, key="ob_face")
        coupon = c2.number_input("Coupon annuel (%)", value=5.0, step=0.1, key="ob_coupon") / 100
        maturity_y = c3.number_input("Maturité (années)", value=10, min_value=1, max_value=50, key="ob_mat")
        c4, c5, c6 = st.columns(3)
        ytm    = c4.number_input("YTM (%)", value=4.5, step=0.1, key="ob_ytm") / 100
        freq   = c5.selectbox("Fréquence coupon", [1, 2, 4], index=1, key="ob_freq",
                               format_func=lambda x: {1:"Annuel",2:"Semi-annuel",4:"Trimestriel"}[x])

        # Calcul prix obligation
        n_periods = maturity_y * freq
        coupon_pmt = face * coupon / freq
        r_period   = ytm / freq
        t_range    = np.arange(1, n_periods + 1)
        cash_flows = np.full(n_periods, coupon_pmt)
        cash_flows[-1] += face
        discount   = (1 + r_period) ** t_range
        pv_flows   = cash_flows / discount
        price_bond = np.sum(pv_flows)

        # Duration & Convexité
        weights    = pv_flows / price_bond
        duration_mac = np.sum(weights * t_range / freq)
        duration_mod = duration_mac / (1 + ytm / freq)
        convexity  = np.sum(pv_flows * t_range * (t_range + 1)) / (price_bond * (1 + r_period)**2 * freq**2)
        dv01       = -duration_mod * price_bond * 0.0001

        r1, r2, r3, r4, r5 = st.columns(5)
        with r1: _metric("PRIX", f"${price_bond:.2f}", f"{'Prime' if price_bond>face else 'Décote'}")
        with r2: _metric("DURATION MAC.", f"{duration_mac:.2f}y")
        with r3: _metric("DURATION MOD.", f"{duration_mod:.2f}")
        with r4: _metric("CONVEXITÉ", f"{convexity:.2f}")
        with r5: _metric("DV01", f"${dv01:.2f}")

        _section("STRUCTURE DES FLUX")
        ytm_range = np.linspace(ytm * 0.5, ytm * 1.5, 100)
        prices    = []
        for y in ytm_range:
            rp = y / freq
            cf = np.full(n_periods, coupon_pmt)
            cf[-1] += face
            prices.append(np.sum(cf / (1 + rp) ** t_range))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ytm_range*100, y=prices,
            name="Prix", line=dict(color="#ff6600", width=2.5)))
        fig.add_vline(x=ytm*100, line=dict(color="#fff", dash="dash"),
                      annotation_text=f"YTM={ytm*100:.1f}%")
        fig.add_hline(y=face, line=dict(color="#4d9fff", dash="dot"),
                      annotation_text="Pair")
        fig.update_layout(**PLOTLY_DARK, height=300,
                          xaxis_title="YTM (%)", yaxis_title="Prix ($)",
                          title="Relation Prix / YTM")
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  4. VALUE AT RISK & STRESS TESTS
# ════════════════════════════════════════════════════════════
def show_var():
    st.markdown("## 🎯 VALUE AT RISK & STRESS TESTS")
    st.caption("VaR paramétrique, historique, Monte Carlo + Expected Shortfall")

    import yfinance as yf

    c1, c2, c3 = st.columns(3)
    tickers_input = c1.text_input("Tickers (séparés par virgule)", value="NVDA,AAPL,MSFT", key="var_tickers")
    confidence    = c2.slider("Niveau de confiance (%)", 90, 99, 95, key="var_conf") / 100
    horizon       = c3.number_input("Horizon (jours)", value=1, min_value=1, max_value=30, key="var_hor")

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    with st.spinner("Chargement des données..."):
        try:
            raw = yf.download(tickers, period="2y", progress=False, auto_adjust=True)
            if isinstance(raw.columns, pd.MultiIndex):
                prices = raw["Close"]
            else:
                prices = raw[["Close"]] if "Close" in raw.columns else raw
            prices.columns = [c if isinstance(c, str) else c[0] for c in prices.columns]
            returns = prices.pct_change().dropna()
            if returns.empty:
                st.error("Données indisponibles.")
                return
        except Exception as e:
            st.error(f"Erreur chargement : {e}")
            return

    # Poids équipondérés
    n = len(tickers)
    weights = np.array([1/n] * n)
    available = [t for t in tickers if t in returns.columns]
    returns   = returns[available]
    weights   = np.array([1/len(available)] * len(available))

    port_returns = returns.dot(weights)
    mu    = port_returns.mean()
    sigma = port_returns.std()

    # ── VaR Paramétrique ──
    z_score = norm.ppf(1 - confidence)
    var_param = -(mu + z_score * sigma) * np.sqrt(horizon)

    # ── VaR Historique ──
    var_hist = -np.percentile(port_returns, (1-confidence)*100) * np.sqrt(horizon)

    # ── VaR Monte Carlo ──
    np.random.seed(42)
    sims = np.random.normal(mu, sigma, 10000) * np.sqrt(horizon)
    var_mc = -np.percentile(sims, (1-confidence)*100)

    # ── Expected Shortfall ──
    es = -port_returns[port_returns <= -var_hist/np.sqrt(horizon)].mean() * np.sqrt(horizon)

    _section(f"RÉSULTATS VaR — Confiance {confidence*100:.0f}% | Horizon {horizon}j")
    v1, v2, v3, v4 = st.columns(4)
    with v1: _metric("VaR Paramétrique", f"{var_param*100:.2f}%")
    with v2: _metric("VaR Historique", f"{var_hist*100:.2f}%")
    with v3: _metric("VaR Monte Carlo", f"{var_mc*100:.2f}%")
    with v4: _metric("Expected Shortfall", f"{es*100:.2f}%", "CVaR")

    _section("DISTRIBUTION DES RENDEMENTS")
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=port_returns*100, nbinsx=80,
        name="Rendements", marker_color="#4d9fff",
        marker_line_color="#000", marker_line_width=0.5, opacity=0.8))
    fig.add_vline(x=-var_param*100, line=dict(color="#ff6600", dash="dash", width=2),
                  annotation_text=f"VaR Param {confidence*100:.0f}%")
    fig.add_vline(x=-var_hist*100, line=dict(color="#FF3B30", dash="dot", width=2),
                  annotation_text=f"VaR Hist")
    # Courbe normale
    x_range = np.linspace(port_returns.min()*100, port_returns.max()*100, 200)
    y_norm  = norm.pdf(x_range, mu*100, sigma*100) * len(port_returns) * (port_returns.std()*100 * 80/len(port_returns))
    fig.add_trace(go.Scatter(x=x_range, y=y_norm, name="Normale théorique",
        line=dict(color="#ff6600", width=2)))
    fig.update_layout(**PLOTLY_DARK, height=350,
                      xaxis_title="Rendement (%)", yaxis_title="Fréquence",
                      title="Distribution des rendements du portefeuille")
    st.plotly_chart(fig, use_container_width=True)

    _section("STRESS TESTS")
    scenarios = {
        "COVID Mars 2020":    -0.34,
        "Crise 2008 (1 sem)": -0.20,
        "Black Monday 1987":  -0.23,
        "Flash Crash 2010":   -0.10,
        "Hausse taux +200bps": -0.08,
        "Scénario bull +10%": +0.10,
    }
    stress_df = pd.DataFrame([
        {"Scénario": k, "Choc (%)" : f"{v*100:+.1f}%",
         "P&L estimé": f"${v * 100000:,.0f}",
         "Signal": "🔴" if v < -0.15 else ("🟡" if v < 0 else "🟢")}
        for k, v in scenarios.items()
    ])
    st.dataframe(stress_df, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
#  5. OPTIMISATION DE PORTEFEUILLE — MARKOWITZ
# ════════════════════════════════════════════════════════════
def show_markowitz():
    st.markdown("## 🎯 OPTIMISATION MARKOWITZ — Frontière Efficiente")
    st.caption("Frontière efficiente, portefeuille de Sharpe max, minimum variance")

    import yfinance as yf

    c1, c2 = st.columns([3,1])
    tickers_input = c1.text_input("Tickers", value="AAPL,NVDA,MSFT,TSLA,JPM,GLD", key="mk_tickers")
    rf = c2.number_input("Taux sans risque (%)", value=4.5, step=0.1, key="mk_rf") / 100

    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()][:10]

    with st.spinner("Calcul de la frontière efficiente..."):
        try:
            raw = yf.download(tickers, period="2y", progress=False, auto_adjust=True)
            prices = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            if isinstance(prices.columns, pd.MultiIndex):
                prices.columns = prices.columns.get_level_values(0)
            prices = prices.dropna(axis=1)
            available = list(prices.columns)
            returns   = prices.pct_change().dropna()
            if returns.empty or len(available) < 2:
                st.error("Données insuffisantes.")
                return
        except Exception as e:
            st.error(f"Erreur : {e}")
            return

    mu_assets = returns.mean() * 252
    cov_mat   = returns.cov() * 252
    n         = len(available)

    # Simulation Monte Carlo de portefeuilles
    np.random.seed(42)
    N_SIMS = 3000
    sim_ret, sim_vol, sim_sharpe, sim_weights = [], [], [], []
    for _ in range(N_SIMS):
        w = np.random.dirichlet(np.ones(n))
        r_p = float(w @ mu_assets.values)
        v_p = float(np.sqrt(w @ cov_mat.values @ w))
        sh  = (r_p - rf) / v_p if v_p > 0 else 0
        sim_ret.append(r_p); sim_vol.append(v_p)
        sim_sharpe.append(sh); sim_weights.append(w)

    sim_ret    = np.array(sim_ret)
    sim_vol    = np.array(sim_vol)
    sim_sharpe = np.array(sim_sharpe)

    # Portefeuille Sharpe max & Min Variance
    idx_sharpe = np.argmax(sim_sharpe)
    idx_minvar = np.argmin(sim_vol)
    w_sharpe   = sim_weights[idx_sharpe]
    w_minvar   = sim_weights[idx_minvar]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sim_vol*100, y=sim_ret*100, mode="markers",
        marker=dict(color=sim_sharpe, colorscale="RdYlGn", size=3,
                    colorbar=dict(title="Sharpe", tickfont=dict(color="#e0e0e0"))),
        name="Portefeuilles simulés", opacity=0.6
    ))
    fig.add_trace(go.Scatter(
        x=[sim_vol[idx_sharpe]*100], y=[sim_ret[idx_sharpe]*100],
        mode="markers", marker=dict(color="#ff6600", size=16, symbol="star"),
        name=f"Max Sharpe ({sim_sharpe[idx_sharpe]:.2f})"
    ))
    fig.add_trace(go.Scatter(
        x=[sim_vol[idx_minvar]*100], y=[sim_ret[idx_minvar]*100],
        mode="markers", marker=dict(color="#4d9fff", size=14, symbol="diamond"),
        name="Min Variance"
    ))
    for i, t in enumerate(available):
        fig.add_trace(go.Scatter(
            x=[float(np.sqrt(cov_mat.iloc[i,i]))*100],
            y=[float(mu_assets.iloc[i])*100],
            mode="markers+text", text=[t],
            textposition="top center", textfont=dict(size=9, color="#fff"),
            marker=dict(color="#fff", size=8, symbol="circle"),
            showlegend=False
        ))
    fig.update_layout(**PLOTLY_DARK, height=480,
                      xaxis_title="Volatilité (%)", yaxis_title="Rendement annualisé (%)",
                      title="Frontière Efficiente de Markowitz")
    st.plotly_chart(fig, use_container_width=True)

    _section("ALLOCATION OPTIMALE")
    col_sharpe, col_minvar = st.columns(2)
    with col_sharpe:
        st.markdown("**🟠 Max Sharpe Ratio**")
        df_sh = pd.DataFrame({"Actif": available, "Poids (%)": (w_sharpe*100).round(1)})
        df_sh = df_sh[df_sh["Poids (%)"] > 0.5].sort_values("Poids (%)", ascending=False)
        fig_pie = go.Figure(go.Pie(labels=df_sh["Actif"], values=df_sh["Poids (%)"],
            hole=0.4, marker_colors=["#ff6600","#4d9fff","#00C853","#FF3B30","#FABE2C","#e040fb"]))
        fig_pie.update_layout(**{k:v for k,v in PLOTLY_DARK.items() if k not in ["xaxis","yaxis"]},
                              height=280, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
        _metric("Sharpe Ratio", f"{sim_sharpe[idx_sharpe]:.3f}")
        _metric("Rendement esp.", f"{sim_ret[idx_sharpe]*100:.1f}%")
        _metric("Volatilité", f"{sim_vol[idx_sharpe]*100:.1f}%")

    with col_minvar:
        st.markdown("**🔵 Minimum Variance**")
        df_mv = pd.DataFrame({"Actif": available, "Poids (%)": (w_minvar*100).round(1)})
        df_mv = df_mv[df_mv["Poids (%)"] > 0.5].sort_values("Poids (%)", ascending=False)
        fig_pie2 = go.Figure(go.Pie(labels=df_mv["Actif"], values=df_mv["Poids (%)"],
            hole=0.4, marker_colors=["#4d9fff","#ff6600","#00C853","#FF3B30","#FABE2C","#e040fb"]))
        fig_pie2.update_layout(**{k:v for k,v in PLOTLY_DARK.items() if k not in ["xaxis","yaxis"]},
                               height=280, showlegend=True)
        st.plotly_chart(fig_pie2, use_container_width=True)
        _metric("Sharpe Ratio", f"{sim_sharpe[idx_minvar]:.3f}")
        _metric("Rendement esp.", f"{sim_ret[idx_minvar]*100:.1f}%")
        _metric("Volatilité", f"{sim_vol[idx_minvar]*100:.1f}%")


# ════════════════════════════════════════════════════════════
#  6. BACKTEST STRATÉGIES QUANTITATIVES
# ════════════════════════════════════════════════════════════
def show_backtest_quant():
    st.markdown("## 🔁 BACKTEST STRATÉGIES QUANTITATIVES")
    st.caption("Mean reversion, momentum, pairs trading — signaux, métriques, drawdown")

    import yfinance as yf

    c1, c2, c3 = st.columns(3)
    ticker   = c1.text_input("Ticker", value="NVDA", key="bq_ticker").upper()
    strategy = c2.selectbox("Stratégie", [
        "Mean Reversion (Bollinger)",
        "Momentum (SMA Crossover)",
        "RSI Reversal",
        "Breakout Volatilité",
    ], key="bq_strat")
    capital  = c3.number_input("Capital ($)", value=100000, step=10000, key="bq_cap")

    c4, c5 = st.columns(2)
    period  = c4.selectbox("Période", ["1y","2y","3y","5y"], index=1, key="bq_period")
    fees    = c5.number_input("Frais aller-retour (%)", value=0.1, step=0.01, key="bq_fees") / 100

    with st.spinner("Backtest en cours..."):
        try:
            raw = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            df = raw[["Open","High","Low","Close","Volume"]].copy().dropna()
            if df.empty or len(df) < 50:
                st.error("Données insuffisantes.")
                return
        except Exception as e:
            st.error(f"Erreur : {e}")
            return

    df["returns"] = df["Close"].pct_change()

    if strategy == "Mean Reversion (Bollinger)":
        w = 20
        df["sma"]   = df["Close"].rolling(w).mean()
        df["std"]   = df["Close"].rolling(w).std()
        df["upper"] = df["sma"] + 2 * df["std"]
        df["lower"] = df["sma"] - 2 * df["std"]
        df["signal"] = 0
        df.loc[df["Close"] < df["lower"], "signal"] = 1   # achat
        df.loc[df["Close"] > df["upper"], "signal"] = -1  # vente
        signal_name = "Bollinger Bands (20,2)"

    elif strategy == "Momentum (SMA Crossover)":
        df["sma_fast"] = df["Close"].rolling(20).mean()
        df["sma_slow"] = df["Close"].rolling(50).mean()
        df["signal"]   = np.where(df["sma_fast"] > df["sma_slow"], 1, -1)
        signal_name    = "SMA 20/50 Crossover"

    elif strategy == "RSI Reversal":
        delta   = df["Close"].diff()
        gain    = delta.where(delta > 0, 0).rolling(14).mean()
        loss    = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs      = gain / loss
        df["rsi"] = 100 - 100 / (1 + rs)
        df["signal"] = 0
        df.loc[df["rsi"] < 30, "signal"] = 1
        df.loc[df["rsi"] > 70, "signal"] = -1
        signal_name = "RSI(14) 30/70"

    else:  # Breakout Volatilité
        df["atr"]    = df["High"].rolling(14).max() - df["Low"].rolling(14).min()
        df["signal"] = np.where(df["Close"] > df["Close"].shift(1) + df["atr"]*0.5, 1,
                       np.where(df["Close"] < df["Close"].shift(1) - df["atr"]*0.5, -1, 0))
        signal_name = "ATR Breakout"

    df["position"]    = df["signal"].shift(1).fillna(0)
    df["strat_ret"]   = df["position"] * df["returns"] - abs(df["position"].diff().fillna(0)) * fees
    df["cum_ret"]     = (1 + df["returns"]).cumprod()
    df["cum_strat"]   = (1 + df["strat_ret"]).cumprod()
    df["equity"]      = capital * df["cum_strat"]
    df["drawdown"]    = (df["equity"] / df["equity"].cummax()) - 1

    # Métriques
    total_ret  = float(df["cum_strat"].iloc[-1]) - 1
    bh_ret     = float(df["cum_ret"].iloc[-1]) - 1
    n_years    = len(df) / 252
    cagr       = (1 + total_ret) ** (1/n_years) - 1 if n_years > 0 else 0
    vol_ann    = float(df["strat_ret"].std()) * np.sqrt(252)
    sharpe     = (cagr - 0.045) / vol_ann if vol_ann > 0 else 0
    max_dd     = float(df["drawdown"].min())
    n_trades   = int((df["position"].diff().fillna(0) != 0).sum())
    win_rate   = float((df.loc[df["strat_ret"] != 0, "strat_ret"] > 0).mean()) if n_trades > 0 else 0

    _section("MÉTRIQUES DE PERFORMANCE")
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    with m1: _metric("Total Return", f"{total_ret*100:+.1f}%")
    with m2: _metric("CAGR", f"{cagr*100:.1f}%")
    with m3: _metric("Sharpe", f"{sharpe:.2f}")
    with m4: _metric("Max Drawdown", f"{max_dd*100:.1f}%")
    with m5: _metric("Win Rate", f"{win_rate*100:.1f}%")
    with m6: _metric("Nb Trades", f"{n_trades}")

    _section(f"EQUITY CURVE — {signal_name} vs Buy & Hold")
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.55, 0.25, 0.20], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=df.index, y=df["cum_strat"]*capital,
        name="Stratégie", line=dict(color="#ff6600", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["cum_ret"]*capital,
        name="Buy & Hold", line=dict(color="#4d9fff", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["strat_ret"]*100,
        name="Rendements", marker_color=np.where(df["strat_ret"]>=0,"#00C853","#FF3B30"),
        opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["drawdown"]*100,
        name="Drawdown", line=dict(color="#FF3B30", width=1.5),
        fill="tozeroy", fillcolor="rgba(255,59,48,0.1)"), row=3, col=1)
    fig.update_layout(**PLOTLY_DARK, height=560, title=f"Backtest {ticker} — {signal_name}")
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="Ret. (%)", row=2, col=1)
    fig.update_yaxes(title_text="DD (%)", row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

    vs_bh = total_ret - bh_ret
    st.info(f"📊 **{signal_name}** : {total_ret*100:+.1f}% vs Buy & Hold {bh_ret*100:+.1f}% → **{'+' if vs_bh>=0 else ''}{vs_bh*100:.1f}% d'alpha**")


# ════════════════════════════════════════════════════════════
#  7. MODÈLES DE MONTE CARLO
# ════════════════════════════════════════════════════════════
def show_monte_carlo():
    st.markdown("## 🎲 SIMULATION MONTE CARLO")
    st.caption("GBM, prix futurs, intervalles de confiance, pricing d'options par simulation")

    import yfinance as yf

    c1, c2, c3 = st.columns(3)
    ticker   = c1.text_input("Ticker", value="NVDA", key="mc_ticker").upper()
    n_sims   = c2.select_slider("Nombre de simulations", [100,500,1000,5000,10000], value=1000, key="mc_nsims")
    horizon  = c3.number_input("Horizon (jours)", value=252, min_value=1, max_value=756, key="mc_hor")

    with st.spinner("Simulation..."):
        try:
            raw = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)
            prices = raw["Close"].dropna()
            if prices.empty:
                st.error("Données indisponibles.")
                return
        except Exception as e:
            st.error(f"Erreur : {e}")
            return

    log_ret = np.log(prices / prices.shift(1)).dropna()
    mu      = log_ret.mean()
    sigma   = log_ret.std()
    S0      = float(prices.iloc[-1])
    dt      = 1/252

    # Simulation GBM
    np.random.seed(42)
    drift   = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)
    Z       = np.random.standard_normal((horizon, n_sims))
    log_paths = np.cumsum(drift + diffusion * Z, axis=0)
    paths   = S0 * np.exp(log_paths)

    # Statistiques
    final_prices = paths[-1, :]
    p5  = np.percentile(final_prices, 5)
    p25 = np.percentile(final_prices, 25)
    p50 = np.percentile(final_prices, 50)
    p75 = np.percentile(final_prices, 75)
    p95 = np.percentile(final_prices, 95)
    prob_up = (final_prices > S0).mean()

    m1,m2,m3,m4,m5 = st.columns(5)
    with m1: _metric("Spot actuel", f"${S0:.2f}")
    with m2: _metric("Médiane", f"${p50:.2f}", f"{(p50/S0-1)*100:+.1f}%")
    with m3: _metric("P5 (bear)", f"${p5:.2f}", f"{(p5/S0-1)*100:+.1f}%")
    with m4: _metric("P95 (bull)", f"${p95:.2f}", f"{(p95/S0-1)*100:+.1f}%")
    with m5: _metric("P(hausse)", f"{prob_up*100:.1f}%")

    _section(f"TRAJECTOIRES GBM — {n_sims} simulations sur {horizon} jours")
    t_axis = np.arange(horizon)
    fig = go.Figure()
    # Intervalles de confiance
    fig.add_trace(go.Scatter(
        x=np.concatenate([t_axis, t_axis[::-1]]),
        y=np.concatenate([np.percentile(paths, 95, axis=1), np.percentile(paths, 5, axis=1)[::-1]]),
        fill="toself", fillcolor="rgba(77,159,255,0.1)",
        line=dict(color="rgba(0,0,0,0)"), name="IC 90%"
    ))
    fig.add_trace(go.Scatter(
        x=np.concatenate([t_axis, t_axis[::-1]]),
        y=np.concatenate([np.percentile(paths, 75, axis=1), np.percentile(paths, 25, axis=1)[::-1]]),
        fill="toself", fillcolor="rgba(77,159,255,0.2)",
        line=dict(color="rgba(0,0,0,0)"), name="IC 50%"
    ))
    # Quelques trajectoires individuelles
    for i in range(min(50, n_sims)):
        fig.add_trace(go.Scatter(x=t_axis, y=paths[:,i],
            line=dict(color="rgba(255,102,0,0.15)", width=0.5), showlegend=False))
    fig.add_trace(go.Scatter(x=t_axis, y=np.percentile(paths, 50, axis=1),
        line=dict(color="#ff6600", width=2.5), name="Médiane"))
    fig.add_hline(y=S0, line=dict(color="#fff", dash="dash", width=1), annotation_text="Spot")
    fig.update_layout(**PLOTLY_DARK, height=400,
                      xaxis_title="Jours", yaxis_title=f"Prix {ticker} ($)",
                      title=f"Monte Carlo GBM — μ={mu*252*100:.1f}%/an, σ={sigma*np.sqrt(252)*100:.1f}%/an")
    st.plotly_chart(fig, use_container_width=True)

    _section("DISTRIBUTION DES PRIX FINAUX")
    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(x=final_prices, nbinsx=80,
        marker_color="#4d9fff", opacity=0.8, name="Prix finaux"))
    for p, lbl, col in [(p5,"P5","#FF3B30"),(p50,"P50","#ff6600"),(p95,"P95","#00C853")]:
        fig2.add_vline(x=p, line=dict(color=col, dash="dash"), annotation_text=lbl)
    fig2.add_vline(x=S0, line=dict(color="#fff", width=1.5), annotation_text="Spot")
    fig2.update_layout(**PLOTLY_DARK, height=300,
                       xaxis_title=f"Prix final {ticker}", yaxis_title="Fréquence")
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  8. RÉGRESSION & FACTEURS — CAPM / FAMA-FRENCH
# ════════════════════════════════════════════════════════════
def show_factor_analysis():
    st.markdown("## 📐 ANALYSE FACTORIELLE — CAPM & Fama-French")
    st.caption("Alpha, Bêta, R², tracking error, décomposition factorielle")

    import yfinance as yf

    c1, c2, c3 = st.columns(3)
    ticker    = c1.text_input("Actif à analyser", value="NVDA", key="fa_ticker").upper()
    benchmark = c2.text_input("Benchmark", value="SPY", key="fa_bench").upper()
    period    = c3.selectbox("Période", ["1y","2y","3y","5y"], index=2, key="fa_period")

    rf_annual = st.sidebar.number_input("Taux sans risque (%)", value=4.5, key="fa_rf") / 100 / 252

    with st.spinner("Chargement..."):
        try:
            raw = yf.download([ticker, benchmark, "^VIX"], period=period,
                              progress=False, auto_adjust=True)
            prices = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            if isinstance(prices.columns, pd.MultiIndex):
                prices.columns = prices.columns.get_level_values(0)
            prices = prices.dropna()
            if ticker not in prices.columns or benchmark not in prices.columns:
                st.error("Ticker ou benchmark non trouvé.")
                return
        except Exception as e:
            st.error(f"Erreur : {e}")
            return

    ret_asset = prices[ticker].pct_change().dropna()
    ret_bench = prices[benchmark].pct_change().dropna()
    idx_common = ret_asset.index.intersection(ret_bench.index)
    ra = ret_asset.loc[idx_common] - rf_annual
    rb = ret_bench.loc[idx_common] - rf_annual

    # ── CAPM ──
    beta, alpha, r_value, p_value, std_err = stats.linregress(rb, ra)
    r2          = r_value**2
    alpha_ann   = alpha * 252
    te          = (ra - beta * rb).std() * np.sqrt(252)
    info_ratio  = alpha_ann / te if te > 0 else 0
    sharpe_a    = (ra.mean() * 252) / (ra.std() * np.sqrt(252))
    sharpe_b    = (rb.mean() * 252) / (rb.std() * np.sqrt(252))

    _section("CAPM — RÉSULTATS")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: _metric("Alpha (α) ann.", f"{alpha_ann*100:+.2f}%")
    with c2: _metric("Bêta (β)", f"{beta:.3f}")
    with c3: _metric("R²", f"{r2:.3f}")
    with c4: _metric("Tracking Error", f"{te*100:.2f}%")
    with c5: _metric("Info Ratio", f"{info_ratio:.2f}")
    with c6: _metric("Sharpe actif", f"{sharpe_a:.2f}")

    _section("DROITE DE RÉGRESSION CAPM")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rb*100, y=ra*100, mode="markers",
        marker=dict(color="#4d9fff", size=3, opacity=0.5), name="Observations"))
    x_reg = np.linspace(rb.min(), rb.max(), 100)
    y_reg = alpha + beta * x_reg
    fig.add_trace(go.Scatter(x=x_reg*100, y=y_reg*100,
        line=dict(color="#ff6600", width=2.5),
        name=f"Régression β={beta:.3f} α={alpha_ann*100:+.2f}%/an"))
    fig.add_hline(y=0, line=dict(color="#333")); fig.add_vline(x=0, line=dict(color="#333"))
    fig.update_layout(**PLOTLY_DARK, height=380,
                      xaxis_title=f"Rendement exc. {benchmark} (%)",
                      yaxis_title=f"Rendement exc. {ticker} (%)",
                      title=f"Security Market Line — {ticker} vs {benchmark}")
    st.plotly_chart(fig, use_container_width=True)

    _section("RENDEMENTS CUMULÉS")
    cum_a = (1 + ret_asset.loc[idx_common]).cumprod()
    cum_b = (1 + ret_bench.loc[idx_common]).cumprod()
    fig2  = go.Figure()
    fig2.add_trace(go.Scatter(x=cum_a.index, y=cum_a,
        name=ticker, line=dict(color="#ff6600", width=2)))
    fig2.add_trace(go.Scatter(x=cum_b.index, y=cum_b,
        name=benchmark, line=dict(color="#4d9fff", width=1.5, dash="dot")))
    fig2.update_layout(**PLOTLY_DARK, height=300,
                       xaxis_title="Date", yaxis_title="Performance cumulée")
    st.plotly_chart(fig2, use_container_width=True)

    _section("ROLLING BETA (63 jours)")
    roll_beta = ret_asset.loc[idx_common].rolling(63).cov(ret_bench.loc[idx_common]) / \
                ret_bench.loc[idx_common].rolling(63).var()
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=roll_beta.index, y=roll_beta,
        line=dict(color="#ff6600", width=2), name="Beta roulant 63j"))
    fig3.add_hline(y=1, line=dict(color="#4d9fff", dash="dash"), annotation_text="β=1")
    fig3.add_hline(y=beta, line=dict(color="#fff", dash="dot"),
                   annotation_text=f"β moyen={beta:.2f}")
    fig3.update_layout(**PLOTLY_DARK, height=260,
                       xaxis_title="Date", yaxis_title="Beta")
    st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE PRINCIPAL
# ════════════════════════════════════════════════════════════
def show_finance_marche():
    # CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&display=swap');
    [data-testid="stSidebar"] { background: #050505 !important; }
    .block-container { padding-top: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div style='font-family:IBM Plex Mono,monospace;font-size:10px;
                color:#ff6600;letter-spacing:2px;padding:8px 0;'>
    ⚙ FINANCE DE MARCHÉ
    </div>
    """, unsafe_allow_html=True)

    import streamlit as _st
    _outils_fm = [
        "⚙️ Pricing Options (BS + Greeks)",
        "📊 Surface de Volatilité",
        "📈 Courbe des Taux & Obligations",
        "🎯 VaR & Stress Tests",
        "🏆 Optimisation Markowitz",
        "🔁 Backtest Quantitatif",
        "🎲 Monte Carlo (GBM)",
        "📐 CAPM & Analyse Factorielle",
    ]
    if "fm_outil" not in st.session_state:
        st.session_state["fm_outil"] = _outils_fm[0]

    # Toolbar horizontale style app-3
    st.markdown("""
    <style>
    div[data-testid="stRadio"][aria-label="fm_outil"] > div {
        display: flex !important; flex-wrap: wrap !important; gap: 5px !important;
        background: #080808 !important; border: 1px solid #1a1a1a !important;
        border-radius: 6px !important; padding: 8px 12px !important; margin-bottom: 16px !important;
    }
    div[data-testid="stRadio"][aria-label="fm_outil"] label {
        font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important;
        color: #555 !important; background: transparent !important;
        border: 1px solid #1c1c1c !important; border-radius: 3px !important;
        padding: 4px 10px !important; cursor: pointer !important; white-space: nowrap !important;
    }
    div[data-testid="stRadio"][aria-label="fm_outil"] label:hover {
        color: #ccc !important; border-color: #333 !important; background: #0f0f0f !important;
    }
    div[data-testid="stRadio"][aria-label="fm_outil"] label[data-checked="true"] {
        color: #ff6600 !important; border-color: #ff6600 !important;
        background: #0d0800 !important; font-weight: 600 !important;
    }
    div[data-testid="stRadio"][aria-label="fm_outil"] input[type="radio"] { display: none !important; }
    div[data-testid="stRadio"][aria-label="fm_outil"] [data-testid="stMarkdownContainer"] p {
        font-size: 10px !important; margin: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _cur_idx = _outils_fm.index(st.session_state["fm_outil"]) if st.session_state["fm_outil"] in _outils_fm else 0
    outil = st.radio("fm_outil", options=_outils_fm, index=_cur_idx,
                     horizontal=True, label_visibility="collapsed", key="fm_outil_radio")
    if outil != st.session_state["fm_outil"]:
        st.session_state["fm_outil"] = outil
        st.rerun()

    if outil == "⚙️ Pricing Options (BS + Greeks)":
        show_options_pricing()
    elif outil == "📊 Surface de Volatilité":
        show_vol_surface()
    elif outil == "📈 Courbe des Taux & Obligations":
        show_yield_curve()
    elif outil == "🎯 VaR & Stress Tests":
        show_var()
    elif outil == "🏆 Optimisation Markowitz":
        show_markowitz()
    elif outil == "🔁 Backtest Quantitatif":
        show_backtest_quant()
    elif outil == "🎲 Monte Carlo (GBM)":
        show_monte_carlo()
    elif outil == "📐 CAPM & Analyse Factorielle":
        show_factor_analysis()
