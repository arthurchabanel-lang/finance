"""Validation Monte-Carlo : le simulateur face aux faits stylisés de la littérature.

Une seule simulation peut être chanceuse. Ici, on fait tourner N univers
aléatoires indépendants, on mesure chaque fait stylisé dans chacun, et on
rapporte la moyenne, un intervalle de confiance à 95 % et la part d'univers
qui reproduisent le fait.

Valeurs de référence des marchés réels :
- Cont (2001), Quantitative Finance 1(2) : faits stylisés généraux ;
- Gopikrishnan et al. (1999), Phys. Rev. E 60 : « loi cubique inverse » (alpha ≈ 3) ;
- Bouchaud, Matacz & Potters (2001), Phys. Rev. Lett. 87 : effet de levier.
"""

from __future__ import annotations

import copy
import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np

from .analyse import autocorrelation, indice_de_queue, kurtosis_excedentaire, rendements
from .simulation import Marche

HORIZON = 50              # horizon de base des rendements (pas)
HORIZONS_AGREGATION = (10, 50, 250)
ECHAUFFEMENT = 1000       # pas ignorés au démarrage
LAGS_MEMOIRE = 30


def asymetrie(x: np.ndarray) -> float:
    """Skewness : < 0 quand les fortes baisses dominent les fortes hausses."""
    z = (x - x.mean()) / x.std()
    return float(np.mean(z ** 3))


def fonction_levier(r: np.ndarray, lags: int = 10) -> np.ndarray:
    """L(k) = corr(r_t, r_{t+k}^2) : négative si les baisses font monter la volatilité future."""
    r = r - r.mean()
    r2 = r ** 2
    out = []
    for k in range(1, lags + 1):
        a, b = r[:-k], r2[k:]
        out.append(float(np.corrcoef(a, b)[0, 1]))
    return np.array(out)


def exposant_memoire(acf_abs: np.ndarray) -> float:
    """Ajuste ACF(|r|)(k) ≈ A·k^(-beta) en log-log sur les retards où l'ACF est positive.

    Marchés réels : décroissance lente en loi de puissance, beta ≈ 0,2 à 0,4.
    Une décroissance exponentielle (mémoire courte) donne un beta élevé et un mauvais ajustement.
    """
    k = np.arange(1, len(acf_abs) + 1)
    ok = acf_abs > 0.01
    # On n'utilise que le début contigu de la courbe positive.
    if not ok[0]:
        return math.nan
    fin = np.argmin(ok) if not ok.all() else len(ok)
    if fin < 4:
        return math.nan
    pente = np.polyfit(np.log(k[:fin]), np.log(acf_abs[:fin]), 1)[0]
    return float(-pente)


def mesurer(series: dict[str, np.ndarray]) -> dict[str, float | np.ndarray]:
    prix = series["prix"][ECHAUFFEMENT:]
    fond = series["fondamental"][ECHAUFFEMENT:]
    volume = series["volume"][ECHAUFFEMENT:]
    r = rendements(prix, HORIZON)
    vol_bloc = volume[: len(r) * HORIZON].reshape(len(r), HORIZON).sum(axis=1)
    acf_r = autocorrelation(r, LAGS_MEMOIRE)
    acf_abs = autocorrelation(np.abs(r), LAGS_MEMOIRE)
    levier = fonction_levier(r)
    m = {
        "kurtosis": kurtosis_excedentaire(r),
        "hill": indice_de_queue(r),
        "acf_moy_abs": float(np.mean(np.abs(acf_r[:10]))),
        "acf_vol": float(np.mean(acf_abs[:10])),
        "beta_memoire": exposant_memoire(acf_abs),
        "levier": float(np.mean(levier)),
        "asymetrie": asymetrie(r),
        "corr_vol_volume": float(np.corrcoef(np.abs(r), vol_bloc)[0, 1]),
        "ecart_moyen": float(np.mean(np.abs(np.log(prix / fond)))),
        "acf_abs_courbe": acf_abs,
        "levier_courbe": levier,
    }
    for h in HORIZONS_AGREGATION:
        m[f"kurtosis_h{h}"] = kurtosis_excedentaire(rendements(prix, h))
    return m


def _un_univers(args) -> dict:
    config, graine, n_pas = args
    marche = Marche(config, graine)
    marche.executer(n_pas)
    m = mesurer(marche.series())
    # Expérience témoin : même univers, sans news (valeur fondamentale gaussienne).
    temoin_cfg = copy.deepcopy(config)
    temoin_cfg["fondamental"]["proba_news"] = 0.0
    temoin = Marche(temoin_cfg, graine)
    temoin.executer(n_pas)
    st = temoin.series()
    r = rendements(st["prix"][ECHAUFFEMENT:], HORIZON)
    rf = rendements(st["fondamental"][ECHAUFFEMENT:], HORIZON)
    m["kurtosis_temoin"] = kurtosis_excedentaire(r)
    m["kurtosis_fondamental_temoin"] = kurtosis_excedentaire(rf)
    m["graine"] = graine
    return m


@dataclass
class Critere:
    cle: str
    nom: str
    reference: str            # ce qu'on observe sur les marchés réels
    test: callable            # valeur d'un univers -> reproduit ?
    format: str = "{:.2f}"


CRITERES = [
    Critere("kurtosis", "Queues épaisses", "kurtosis excédentaire nettement > 0",
            lambda m: m["kurtosis"] > 1, "{:.1f}"),
    Critere("hill", "Indice de queue (Hill)", "≈ 3, entre 2 et 5 (loi cubique inverse)",
            lambda m: 2.0 <= m["hill"] <= 5.0),
    Critere("emergence", "Queues épaisses émergentes", "(test propre au modèle) persistent sans news",
            lambda m: m["kurtosis_temoin"] > m["kurtosis_fondamental_temoin"] + 2, "{:.1f}"),
    Critere("acf_moy_abs", "Rendements imprévisibles", "|ACF| des rendements ≈ 0 au-delà de quelques minutes",
            lambda m: m["acf_moy_abs"] < 0.12, "{:.3f}"),
    Critere("acf_vol", "Volatilité en grappes", "ACF des |rendements| > 0",
            lambda m: m["acf_vol"] > 0.05, "{:.3f}"),
    Critere("beta_memoire", "Mémoire longue de la volatilité", "décroissance en k^(-β), β ≈ 0,2 à 0,4",
            lambda m: 0.1 <= m["beta_memoire"] <= 0.6),
    Critere("agregation", "Normalité aux horizons longs", "la kurtosis baisse quand l'horizon s'allonge",
            lambda m: m["kurtosis_h10"] > m["kurtosis_h50"] > m["kurtosis_h250"], "{:.1f}"),
    Critere("levier", "Effet de levier", "corr(rendement, volatilité future) < 0",
            lambda m: m["levier"] < -0.02, "{:+.3f}"),
    Critere("asymetrie", "Asymétrie gains / pertes", "skewness < 0 (krachs plus violents que les envolées)",
            lambda m: m["asymetrie"] < -0.1, "{:+.2f}"),
    Critere("corr_vol_volume", "Volume ↔ volatilité", "corrélation positive",
            lambda m: m["corr_vol_volume"] > 0.1),
    Critere("ecart_moyen", "Ancrage sur la valeur", "(test propre au modèle) écart moyen < 5 %",
            lambda m: m["ecart_moyen"] < 0.05, "{:.2%}"),
]


def valeur(m: dict, cle: str) -> float:
    if cle == "emergence":
        return m["kurtosis_temoin"]
    if cle == "agregation":
        return m["kurtosis_h250"]
    return m[cle]


@dataclass
class ResultatCritere:
    critere: Critere
    valeurs: np.ndarray
    reussites: int
    n: int

    @property
    def moyenne(self) -> float:
        return float(np.nanmean(self.valeurs))

    @property
    def ic95(self) -> tuple[float, float]:
        v = self.valeurs[~np.isnan(self.valeurs)]
        if len(v) < 2:
            return (math.nan, math.nan)
        demi = 1.96 * v.std(ddof=1) / math.sqrt(len(v))
        return (v.mean() - demi, v.mean() + demi)


@dataclass
class Validation:
    univers: list[dict]
    resultats: list[ResultatCritere] = field(default_factory=list)


def valider(config: dict, n_univers: int = 20, n_pas: int = 30000, graine0: int = 1000,
            processus: int | None = None, progression=None) -> Validation:
    taches = [(config, graine0 + i, n_pas) for i in range(n_univers)]
    univers = []
    with ProcessPoolExecutor(max_workers=processus) as pool:
        for k, m in enumerate(pool.map(_un_univers, taches), 1):
            univers.append(m)
            if progression:
                progression(k, n_univers)
    v = Validation(univers)
    for c in CRITERES:
        vals = np.array([valeur(m, c.cle) for m in univers], dtype=float)
        ok = sum(bool(c.test(m)) for m in univers if not math.isnan(valeur(m, c.cle)))
        v.resultats.append(ResultatCritere(c, vals, ok, len(univers)))
    return v
