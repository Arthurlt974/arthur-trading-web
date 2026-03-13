"""
kelly.py — Kelly Criterion · Position Sizing Engine
====================================================
Calculs 100% NumPy, aucune dépendance externe hors numpy.

Fonctions publiques
-------------------
  kelly_trade(p, b)                       → fraction Kelly discrète classique
  kelly_continuous(returns)               → fraction Kelly continue (μ/σ²)
  estimate_kelly_params(closes)           → auto-estimation p, b, μ, σ depuis prix
  kelly_full_analysis(closes, capital, …) → dict complet pour injection JS

Usage depuis chart.py
---------------------
  from kelly import kelly_full_analysis
  kp = kelly_full_analysis(closes_list, capital=10_000)
  # → injecter kp dans le template HTML via f-string
"""

from __future__ import annotations
import numpy as np
from typing import Union

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

_FRACTIONS = {
    "full":    1.0,
    "half":    0.5,
    "quarter": 0.25,
}

_MIN_CANDLES = 30   # minimum de bougies pour une estimation fiable


# ─────────────────────────────────────────────────────────────────────────────
#  1. MODE TRADE  —  Kelly discret  f* = p − q / b
# ─────────────────────────────────────────────────────────────────────────────

def kelly_trade(
    p: float,
    b: float,
    max_fraction: float = 1.0,
) -> dict:
    """
    Critère de Kelly discret (trade par trade).

    Paramètres
    ----------
    p : float  — win rate  [0, 1]
    b : float  — ratio gain/perte  (ex : 1.5 = on gagne 1.5x la mise)
    max_fraction : float — cap de la fraction (défaut 1.0 = full Kelly)

    Retourne
    --------
    dict avec :
      f_full   : fraction Kelly complète
      f_half   : demi-Kelly
      f_quarter: quart-Kelly
      edge     : espérance par unité risquée  E[R] = p*b − q
      ev       : espérance nette (E[R] normalisée)
      ruin_risk: probabilité de ruine estimée  (formule de Gambler's ruin)
      valid    : bool — False si paramètres hors limites ou edge ≤ 0
    """
    p = float(np.clip(p, 1e-6, 1.0 - 1e-6))
    b = float(max(b, 1e-6))
    q = 1.0 - p

    # Formule de Kelly : f* = (p*b − q) / b
    f_raw  = (p * b - q) / b
    f_full = float(np.clip(f_raw, 0.0, max_fraction))

    edge = p * b - q          # espérance brute par unité risquée
    ev   = edge / b           # normalisée

    # Probabilité de ruine approximative (modèle Gambler's ruin simplifié)
    # p_ruin ≈ (q/p)^N  où N = 1 / f*
    if f_full > 0 and p > 0:
        odds_ratio = q / p
        n_bets     = 1.0 / f_full if f_full > 0 else np.inf
        ruin_risk  = float(np.power(odds_ratio, n_bets)) if odds_ratio < 1 else 1.0
        ruin_risk  = float(np.clip(ruin_risk, 0.0, 1.0))
    else:
        ruin_risk = 1.0

    return {
        "mode":      "trade",
        "p":         round(p, 4),
        "q":         round(q, 4),
        "b":         round(b, 4),
        "edge":      round(edge, 4),
        "ev":        round(ev, 4),
        "f_full":    round(f_full, 4),
        "f_half":    round(f_full * 0.5, 4),
        "f_quarter": round(f_full * 0.25, 4),
        "ruin_risk": round(ruin_risk, 4),
        "valid":     bool(f_raw > 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  2. MODE RENDEMENT  —  Kelly continu  f* = μ / σ²
# ─────────────────────────────────────────────────────────────────────────────

def kelly_continuous(
    returns: Union[list, np.ndarray],
    annualize: bool = True,
    freq: str = "4h",
) -> dict:
    """
    Critère de Kelly continu sur série de rendements log.

    Paramètres
    ----------
    returns  : array-like — rendements log (ln(Ct/Ct-1))
    annualize: bool       — annualiser μ et σ avant calcul
    freq     : str        — fréquence des bougies pour l'annualisation

    Retourne
    --------
    dict avec :
      mu        : dérive moyenne (annualisée si annualize=True)
      sigma     : volatilité    (annualisée si annualize=True)
      f_full    : fraction Kelly complète  μ/σ²
      f_half    : demi-Kelly
      f_quarter : quart-Kelly
      sharpe    : ratio de Sharpe annualisé  (rf=0)
      valid     : bool
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]

    if len(r) < 2:
        return _empty_result("continuous")

    # ── Facteur d'annualisation ──
    _periods_per_year = {
        "1m":  525_600, "5m": 105_120, "15m": 35_040,
        "30m": 17_520,  "1h": 8_760,   "4h":  2_190,
        "1d":  365,     "1w": 52,
    }
    ann_factor = _periods_per_year.get(freq.lower(), 2_190)  # défaut 4h

    mu_raw    = float(np.mean(r))
    sigma_raw = float(np.std(r, ddof=1))

    if annualize:
        mu    = mu_raw    * ann_factor
        sigma = sigma_raw * np.sqrt(ann_factor)
    else:
        mu    = mu_raw
        sigma = sigma_raw

    if sigma <= 0:
        return _empty_result("continuous")

    # f* = μ / σ²
    f_raw  = mu / (sigma ** 2)
    f_full = float(np.clip(f_raw, 0.0, 1.0))

    sharpe = mu / sigma if sigma > 0 else 0.0

    return {
        "mode":       "continuous",
        "mu":         round(mu,    4),
        "sigma":      round(sigma, 4),
        "mu_pct":     round(mu    * 100, 2),
        "sigma_pct":  round(sigma * 100, 2),
        "f_raw":      round(f_raw,  4),
        "f_full":     round(f_full, 4),
        "f_half":     round(f_full * 0.5, 4),
        "f_quarter":  round(f_full * 0.25, 4),
        "sharpe":     round(sharpe, 4),
        "valid":      bool(f_raw > 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  3. AUTO-ESTIMATION des paramètres depuis l'historique de prix
# ─────────────────────────────────────────────────────────────────────────────

def estimate_kelly_params(
    closes: Union[list, np.ndarray],
    freq:   str = "4h",
) -> dict:
    """
    Estime automatiquement win_rate, ratio W/L et les rendements log
    depuis une série de prix de clôture.

    Paramètres
    ----------
    closes : array-like — prix de clôture chronologiques
    freq   : str        — timeframe (pour annualisation)

    Retourne
    --------
    dict avec :
      win_rate   : taux de victoire sur les rendements positifs  [0,1]
      ratio_wl   : ratio gain moyen / perte moyenne absolue
      returns    : array numpy des rendements log
      mu_pct     : dérive annualisée en %
      sigma_pct  : volatilité annualisée en %
      n_candles  : nombre de bougies utilisées
      reliable   : bool — estimation fiable (≥ MIN_CANDLES bougies)
    """
    c = np.asarray(closes, dtype=float)
    c = c[np.isfinite(c) & (c > 0)]

    if len(c) < 2:
        return _default_params()

    # Rendements log
    log_ret = np.diff(np.log(c))
    log_ret = log_ret[np.isfinite(log_ret)]

    if len(log_ret) < 2:
        return _default_params()

    # Win rate
    wins   = log_ret[log_ret > 0]
    losses = log_ret[log_ret < 0]

    win_rate = float(len(wins) / len(log_ret)) if len(log_ret) > 0 else 0.5

    # Ratio W/L
    avg_win  = float(np.mean(wins))   if len(wins)   > 0 else 0.01
    avg_loss = float(np.mean(np.abs(losses))) if len(losses) > 0 else 0.01
    ratio_wl = float(avg_win / avg_loss) if avg_loss > 0 else 1.5

    # Annualisation
    _periods_per_year = {
        "1m":  525_600, "5m": 105_120, "15m": 35_040,
        "30m": 17_520,  "1h": 8_760,   "4h":  2_190,
        "1d":  365,     "1w": 52,
    }
    ann = _periods_per_year.get(freq.lower(), 2_190)

    mu_ann    = float(np.mean(log_ret)) * ann
    sigma_ann = float(np.std(log_ret, ddof=1)) * np.sqrt(ann)

    return {
        "win_rate":  round(win_rate, 4),
        "win_rate_pct": round(win_rate * 100, 1),
        "ratio_wl":  round(ratio_wl, 4),
        "returns":   log_ret,
        "mu_pct":    round(mu_ann    * 100, 2),
        "sigma_pct": round(sigma_ann * 100, 2),
        "n_candles": int(len(c)),
        "reliable":  bool(len(c) >= _MIN_CANDLES),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  4. ANALYSE COMPLÈTE  —  entrée principale pour chart.py
# ─────────────────────────────────────────────────────────────────────────────

def kelly_full_analysis(
    closes:    Union[list, np.ndarray],
    capital:   float = 10_000.0,
    freq:      str   = "4h",
    fraction:  float = 0.5,          # fraction recommandée par défaut (demi-Kelly)
) -> dict:
    """
    Analyse Kelly complète à injecter dans le template HTML de chart.py.

    Paramètres
    ----------
    closes   : array-like — prix de clôture
    capital  : float      — capital de référence en USDT
    freq     : str        — timeframe Binance
    fraction : float      — fraction Kelly à utiliser pour sizing (0.5 = demi-Kelly)

    Retourne
    --------
    dict plat avec TOUTES les valeurs prêtes à injecter via f-string :

      kelly_win_rate        : win rate auto-estimé en %  (ex: 54.2)
      kelly_ratio_wl        : ratio W/L auto-estimé      (ex: 1.38)
      kelly_f_full          : fraction Kelly complète     (ex: 0.1823)
      kelly_f_half          : demi-Kelly                  (ex: 0.0912)
      kelly_f_quarter       : quart-Kelly                 (ex: 0.0456)
      kelly_f_pct           : fraction recommandée en %  (ex: 9.12)
      kelly_pos_size        : taille de position en USDT  (ex: 912.0)
      kelly_edge_pct        : edge en %                   (ex: 3.4)
      kelly_ruin_risk_pct   : risque de ruine en %        (ex: 2.1)
      kelly_mu_pct          : dérive annualisée %         (ex: 48.3)
      kelly_sigma_pct       : vol annualisée %            (ex: 76.1)
      kelly_sharpe          : ratio de Sharpe             (ex: 0.63)
      kelly_reliable        : "1" | "0"  (données fiables)
      kelly_n_candles       : nombre de bougies analysées
    """
    # ── Estimation des paramètres depuis l'historique ──
    params = estimate_kelly_params(closes, freq=freq)

    # ── Mode Trade (discret) ──
    kt = kelly_trade(
        p=params["win_rate"],
        b=params["ratio_wl"],
    )

    # ── Mode Rendement (continu) ──
    kc = kelly_continuous(
        returns=params["returns"],
        annualize=True,
        freq=freq,
    )

    # ── Fraction recommandée et sizing ──
    # On moyenne les deux approches si les deux sont valides
    if kt["valid"] and kc["valid"]:
        f_full_merged = float(np.mean([kt["f_full"], kc["f_full"]]))
    elif kt["valid"]:
        f_full_merged = kt["f_full"]
    elif kc["valid"]:
        f_full_merged = kc["f_full"]
    else:
        f_full_merged = 0.0

    f_full_merged = float(np.clip(f_full_merged, 0.0, 1.0))
    f_recommended = f_full_merged * fraction        # demi-Kelly par défaut
    pos_size      = round(capital * f_recommended, 2)

    # ── Retour plat pour injection JS ──
    return {
        # Paramètres estimés
        "kelly_win_rate":       params["win_rate_pct"],
        "kelly_ratio_wl":       round(params["ratio_wl"], 2),
        "kelly_n_candles":      params["n_candles"],
        "kelly_reliable":       "1" if params["reliable"] else "0",

        # Résultats Kelly Trade
        "kelly_edge_pct":       round(kt["edge"] * 100, 2) if kt["valid"] else 0.0,
        "kelly_ruin_risk_pct":  round(kt["ruin_risk"] * 100, 2),

        # Résultats Kelly Continu
        "kelly_mu_pct":         params["mu_pct"],
        "kelly_sigma_pct":      params["sigma_pct"],
        "kelly_sharpe":         round(kc.get("sharpe", 0.0), 2),

        # Fractions Kelly fusionnées
        "kelly_f_full":         round(f_full_merged, 4),
        "kelly_f_half":         round(f_full_merged * 0.5, 4),
        "kelly_f_quarter":      round(f_full_merged * 0.25, 4),
        "kelly_f_pct":          round(f_recommended * 100, 2),

        # Sizing
        "kelly_pos_size":       pos_size,
        "kelly_capital":        round(capital, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS INTERNES
# ─────────────────────────────────────────────────────────────────────────────

def _empty_result(mode: str) -> dict:
    """Retourne un dict vide/neutre quand les données sont insuffisantes."""
    return {
        "mode":      mode,
        "f_full":    0.0,
        "f_half":    0.0,
        "f_quarter": 0.0,
        "valid":     False,
    }


def _default_params() -> dict:
    """Paramètres par défaut si closes insuffisants."""
    return {
        "win_rate":     0.50,
        "win_rate_pct": 50.0,
        "ratio_wl":     1.50,
        "returns":      np.array([]),
        "mu_pct":       50.0,
        "sigma_pct":    80.0,
        "n_candles":    0,
        "reliable":     False,
    }