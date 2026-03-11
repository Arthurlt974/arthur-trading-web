"""
quant/monte_carlo.py
═══════════════════════════════════════════════════════════════
Moteur Monte Carlo — Merton Jump-Diffusion (1976)
Calculs 100 % vectorisés NumPy → vitesse C-level via BLAS/LAPACK

Modèle :
    dS = S [μ dt + σ dW + dJ]

où J est un processus de Poisson composé :
    • λ  : intensité des sauts / an
    • μ_J : taille moyenne des sauts (log-normal)
    • σ_J : dispersion des sauts (log-normal)

Correction de dérive de Merton :
    μ_c = μ − λ · (e^{μ_J + ½σ_J²} − 1)
═══════════════════════════════════════════════════════════════
"""
from __future__ import annotations
from typing import List, Dict, Optional

import numpy as np


# ── Facteurs d'annualisation par timeframe ─────────────────
_ANN: Dict[str, float] = {
    "1m": 525_600, "5m": 105_120, "15m": 35_040, "30m": 17_520,
    "1h": 8_760,   "4h": 2_190,   "1d": 252,     "1w": 52,
}


def estimate_params(closes: List[float], freq: str = "1d") -> Dict[str, float]:
    """
    Estime μ et σ annualisés depuis une série de prix de clôture.

    Paramètres
    ----------
    closes : liste de prix de clôture (chronologique)
    freq   : timeframe OHLCV ('1m','5m','15m','1h','4h','1d','1w')

    Retourne
    --------
    {mu, sigma, factor, mu_per, sig_per}
    """
    factor = _ANN.get(freq.lower(), 252)

    if len(closes) < 10:
        return {"mu": 0.0, "sigma": 0.5, "factor": factor,
                "mu_per": 0.0, "sig_per": 0.02}

    c       = np.array(closes, dtype=np.float64)
    c       = c[c > 0]          # sécurité : pas de prix nuls
    lr      = np.diff(np.log(c))
    mu_per  = float(np.mean(lr))
    sig_per = float(np.std(lr, ddof=1))

    return {
        "mu":     mu_per  * factor,
        "sigma":  sig_per * np.sqrt(factor),
        "factor": float(factor),
        "mu_per": mu_per,
        "sig_per": sig_per,
    }


def merton_jd(
    S0:       float,
    mu:       float,
    sigma:    float,
    lam:      float          = 3.0,
    mu_j:     float          = -0.05,
    sigma_j:  float          = 0.10,
    horizon:  int            = 90,
    n_sim:    int            = 5_000,
    freq:     str            = "1d",
    seed:     Optional[int]  = None,
) -> Dict:
    """
    Monte Carlo Merton Jump-Diffusion — entièrement vectorisé NumPy.

    Paramètres
    ----------
    S0      : prix initial
    mu      : dérive annualisée  (ex: 0.50 = +50 %/an)
    sigma   : volatilité annualisée (ex: 0.80 = 80 %/an)
    lam     : intensité sauts / an  (λ, ex: 3)
    mu_j    : taille log-moyenne des sauts (ex: -0.05 = -5 %)
    sigma_j : dispersion log des sauts     (ex: 0.10  = 10 %)
    horizon : nombre de pas simulés (jours / périodes selon freq)
    n_sim   : nombre de trajectoires Monte Carlo
    freq    : fréquence des pas ('1d', '4h', etc.)
    seed    : graine aléatoire (None = aléatoire)

    Retourne
    --------
    dict contenant :
      paths        → dict de trajectoires percentiles (p5..p95), listes Python
      n_steps      → horizon + 1 points par trajectoire
      mean, p5, p25, p50, p75, p95   → stats finales
      prob_profit  → % de trajectoires terminant > S0
      var_95       → VaR 95 % (perte)
      cvar_95      → CVaR / Expected Shortfall 95 %
      S0, params   → données d'entrée
    """
    factor = _ANN.get(freq.lower(), 252)
    dt     = 1.0 / factor

    rng = np.random.default_rng(seed)

    # ── Correction de dérive Merton ──────────────────────────
    k     = np.exp(mu_j + 0.5 * sigma_j ** 2) - 1.0   # saut moyen exp
    mu_c  = mu - lam * k                                # dérive corrigée

    # ── Composante brownienne  (n_sim × horizon) ─────────────
    Z     = rng.standard_normal((n_sim, horizon))

    # ── Processus de Poisson  → nombre de sauts par pas ──────
    N_j   = rng.poisson(lam * dt, (n_sim, horizon))

    # ── Amplitudes log-normales des sauts  ────────────────────
    #    Pour chaque case on tire N_j sauts et on les somme.
    #    Optimisation : on génère le max possible et on masque.
    max_j = int(N_j.max()) if N_j.max() > 0 else 1
    J_raw = rng.normal(mu_j, sigma_j, (n_sim, horizon, max_j))
    mask  = np.arange(max_j)[None, None, :] < N_j[:, :, None]
    J     = (J_raw * mask).sum(axis=2)   # somme des sauts réels

    # ── Log-returns par pas  ──────────────────────────────────
    lr    = (mu_c - 0.5 * sigma ** 2) * dt \
            + sigma * np.sqrt(dt) * Z \
            + J

    # ── Trajectoires de prix  (n_sim × horizon+1) ────────────
    log_cum = np.cumsum(lr, axis=1)
    paths   = S0 * np.exp(
        np.hstack([np.zeros((n_sim, 1), dtype=np.float64), log_cum])
    )

    # ── Statistiques terminales ───────────────────────────────
    finals     = paths[:, -1]

    PCTS = [5, 10, 25, 50, 75, 90, 95]
    perc_paths = {
        f"p{p}": np.percentile(paths, p, axis=0).tolist()
        for p in PCTS
    }

    p5_val  = float(np.percentile(finals, 5))
    cvar_mask = finals[finals <= p5_val]
    cvar95  = float(cvar_mask.mean() - S0) if len(cvar_mask) > 0 else float(p5_val - S0)

    return {
        # Trajectoires pour affichage graphique
        "paths":       perc_paths,
        "n_steps":     horizon + 1,

        # Stats résumées
        "mean":        float(np.mean(finals)),
        "p5":          float(p5_val),
        "p25":         float(np.percentile(finals, 25)),
        "p50":         float(np.percentile(finals, 50)),
        "p75":         float(np.percentile(finals, 75)),
        "p95":         float(np.percentile(finals, 95)),
        "prob_profit": float(np.mean(finals > S0) * 100),
        "var_95":      float(p5_val - S0),
        "cvar_95":     cvar95,

        # Méta
        "S0":   float(S0),
        "params": {
            "mu": mu, "sigma": sigma, "lam": lam,
            "mu_j": mu_j, "sigma_j": sigma_j,
            "horizon": horizon, "n_sim": n_sim, "freq": freq,
        },
    }
