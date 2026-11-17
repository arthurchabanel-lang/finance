"""Analyse statistique : le simulateur reproduit-il les faits stylisés des marchés ?

Références : Cont (2001), « Empirical properties of asset returns: stylized
facts and statistical issues », Quantitative Finance 1(2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def rendements(prix: np.ndarray, horizon: int) -> np.ndarray:
    """Log-rendements échantillonnés tous les `horizon` pas."""
    return np.diff(np.log(prix[::horizon]))


def autocorrelation(x: np.ndarray, lags: int) -> np.ndarray:
    x = x - x.mean()
    denom = np.dot(x, x)
    return np.array([np.dot(x[:-k], x[k:]) / denom for k in range(1, lags + 1)])


def kurtosis_excedentaire(x: np.ndarray) -> float:
    """0 pour une loi normale ; > 0 = queues plus épaisses que la normale."""
    z = (x - x.mean()) / x.std()
    return float(np.mean(z ** 4) - 3.0)


def indice_de_queue(x: np.ndarray, fraction: float = 0.05) -> float:
    """Estimateur de Hill sur les `fraction` plus grands |rendements|.

    Sur les actions réelles on trouve typiquement ~3 (« loi cubique inverse »).
    Une loi normale donne des valeurs élevées (queues fines).
    """
    a = np.sort(np.abs(x[x != 0]))[::-1]
    k = max(int(len(a) * fraction), 10)
    queue = a[: k + 1]
    return float(1.0 / np.mean(np.log(queue[:-1] / queue[-1])))


@dataclass
class Verdict:
    nom: str
    reussi: bool
    detail: str


@dataclass
class Rapport:
    horizon: int
    stats: dict[str, float]
    acf_r: np.ndarray
    acf_abs: np.ndarray
    acf_abs_fondamental: np.ndarray
    verdicts: list[Verdict]


def analyser(series: dict[str, np.ndarray], horizon: int = 50, lags: int = 30,
             echauffement: int = 1000) -> Rapport:
    prix = series["prix"][echauffement:]
    fond = series["fondamental"][echauffement:]
    volume = series["volume"][echauffement:]

    r = rendements(prix, horizon)
    rf = rendements(fond, horizon)
    vol_par_periode = volume[: len(r) * horizon].reshape(len(r), horizon).sum(axis=1)

    acf_r = autocorrelation(r, lags)
    acf_abs = autocorrelation(np.abs(r), lags)
    acf_abs_f = autocorrelation(np.abs(rf), lags)
    ecart = np.log(prix / fond)

    s = {
        "volatilite": float(r.std()),
        "volatilite_fondamental": float(rf.std()),
        "kurtosis": kurtosis_excedentaire(r),
        "kurtosis_fondamental": kurtosis_excedentaire(rf),
        "indice_queue": indice_de_queue(r),
        "acf1": float(acf_r[0]),
        "acf_moy_abs_1_10": float(np.mean(np.abs(acf_r[:10]))),
        "acf_vol_1_10": float(np.mean(acf_abs[:10])),
        "acf_vol_fondamental_1_10": float(np.mean(acf_abs_f[:10])),
        "corr_volume_volatilite": float(np.corrcoef(np.abs(r), vol_par_periode)[0, 1]),
        "ecart_moyen": float(np.mean(np.abs(ecart))),
        "ecart_max": float(np.max(np.abs(ecart))),
        "pire_rendement": float(r.min()),
        "meilleur_rendement": float(r.max()),
    }

    v = [
        Verdict("Queues épaisses",
                s["kurtosis"] > 1.0,
                f"kurtosis excédentaire = {s['kurtosis']:.1f} (loi normale : 0) ; "
                f"indice de queue de Hill = {s['indice_queue']:.1f} (actions réelles : ~3)"),
        Verdict("Rendements quasi imprévisibles",
                s["acf_moy_abs_1_10"] < 0.12,
                f"autocorrélation moyenne |ACF| (retards 1-10) = {s['acf_moy_abs_1_10']:.3f} ; "
                f"retard 1 = {s['acf1']:+.3f}"),
        Verdict("Volatilité en grappes",
                s["acf_vol_1_10"] > 0.05 and s["acf_vol_1_10"] > s["acf_vol_fondamental_1_10"] + 0.03,
                f"ACF moyenne des |rendements| (retards 1-10) = {s['acf_vol_1_10']:.3f} "
                f"(fondamental : {s['acf_vol_fondamental_1_10']:.3f})"),
        Verdict("Volume corrélé à la volatilité",
                s["corr_volume_volatilite"] > 0.1,
                f"corrélation(|rendement|, volume) = {s['corr_volume_volatilite']:.2f}"),
        Verdict("Prix ancré sur la valeur fondamentale",
                s["ecart_moyen"] < 0.05,
                f"écart moyen |prix/valeur| = {100 * s['ecart_moyen']:.1f} %, "
                f"max = {100 * s['ecart_max']:.1f} %"),
    ]
    return Rapport(horizon, s, acf_r, acf_abs, acf_abs_f, v)


def verdict_emergence(series_temoin: dict[str, np.ndarray], horizon: int = 50,
                      echauffement: int = 1000) -> Verdict:
    """Expérience témoin : même marché, mais valeur fondamentale purement gaussienne.

    Si les queues épaisses persistent, elles sont créées par les interactions
    entre agents, et non simplement héritées des news.
    """
    r = rendements(series_temoin["prix"][echauffement:], horizon)
    rf = rendements(series_temoin["fondamental"][echauffement:], horizon)
    k, kf = kurtosis_excedentaire(r), kurtosis_excedentaire(rf)
    return Verdict("Queues épaisses émergentes (expérience témoin sans news)",
                   k > kf + 2.0,
                   f"valeur fondamentale gaussienne (kurtosis {kf:.1f}) → "
                   f"prix de marché : kurtosis {k:.1f}")


def texte_rapport(rapport: Rapport) -> str:
    lignes = [f"FAITS STYLISÉS (rendements sur {rapport.horizon} pas)", "=" * 60]
    for v in rapport.verdicts:
        lignes.append(f"{'✅' if v.reussi else '❌'} {v.nom}")
        lignes.append(f"    {v.detail}")
    n = sum(v.reussi for v in rapport.verdicts)
    lignes.append("=" * 60)
    lignes.append(f"Score : {n}/{len(rapport.verdicts)} faits stylisés reproduits")
    return "\n".join(lignes)
