"""Phase 5 : des agents qui apprennent.

Expérience A (Brock et Hommes) : 100 agents adaptatifs remplacent la moitié des
fondamentalistes et des chartistes. On fait varier l'intensité du choix (0 = au hasard,
élevée = tout le monde suit la stratégie gagnante) et on mesure la stabilité du marché.

Expérience B (évolution) : les paramètres des fondamentalistes et des chartistes
évoluent par sélection et mutation, sur 100 000 pas. Quelles stratégies survivent ?
Le marché devient-il plus efficient ?

Utilisation :
    python apprendre.py               # ~5 min sur 4 cœurs
Produit docs/apprentissage.md et docs/apprentissage.png.
"""

from __future__ import annotations

import argparse
import math
import time
import tomllib
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from marche.analyse import kurtosis_excedentaire, rendements
from marche.experiences import appliquer, chute_max
from marche.simulation import Marche

ICI = Path(__file__).parent
INTENSITES = [0.0, 0.5, 2.0, 5.0]
POPULATION_ADAPTATIVE = {"agents.adaptatifs.nombre": 100, "agents.fondamentalistes.nombre": 50,
                         "agents.chartistes.nombre": 50}
BLOC = 10000  # taille des blocs pour suivre l'évolution dans le temps


def mesures(m: Marche) -> dict:
    s = m.series()
    prix, fond = s["prix"][1000:], s["fondamental"][1000:]
    r = rendements(prix, 50)
    return {"volatilite": float(r.std()), "kurtosis": kurtosis_excedentaire(r),
            "inefficience": float(np.mean(np.abs(np.log(prix / fond)))),
            "chute_max": chute_max(prix)}


def _brock_hommes(args):
    config, intensite, graine, n_pas = args
    c = appliquer(config, {**POPULATION_ADAPTATIVE, "apprentissage.intensite_choix": intensite})
    m = Marche(c, graine)
    m.executer(n_pas)
    res = mesures(m)
    part = np.asarray(m.hist_part_fondamentaliste)
    res["part_chartiste"] = float(1 - part.mean())
    # Lien entre la part de chartistes et la volatilité qui suit (par blocs de 500 pas).
    r = np.diff(np.log(np.asarray(m.hist_prix)))
    n = (len(part) - 500) // 500
    pc = [1 - part[i * 500:(i + 1) * 500].mean() for i in range(n)]
    vol_suiv = [r[(i + 1) * 500:(i + 2) * 500].std() for i in range(n)]
    res["corr_part_vol"] = float(np.corrcoef(pc, vol_suiv)[0, 1]) if np.std(pc) > 0 else math.nan
    res["serie"] = (np.asarray(m.hist_prix, dtype=np.float32), np.asarray(m.hist_fondamental, dtype=np.float32),
                    (1 - part).astype(np.float32))
    return intensite, graine, res


def _evolution(args):
    config, actif, graine, n_pas = args
    c = appliquer(config, {"evolution.actif": actif})
    m = Marche(c, graine)
    m.executer(n_pas)
    s = m.series()
    prix, fond = s["prix"], s["fondamental"]
    blocs = []
    for b in range(1, n_pas // BLOC + 1):
        p, f = prix[(b - 1) * BLOC + 1:b * BLOC + 1], fond[(b - 1) * BLOC + 1:b * BLOC + 1]
        rb = rendements(p, 50)
        blocs.append({"inefficience": float(np.mean(np.abs(np.log(p / f)))), "volatilite": float(rb.std())})
    res = mesures(m)
    res["blocs"] = blocs
    if actif:
        g = m.hist_evolution
        res["genes"] = {
            "t": [c["t"] for c in g],
            "biais_abs": [float(np.mean(np.abs(c["Fondamentaliste.biais"]))) for c in g],
            "agressivite": [float(np.median(c["Fondamentaliste.agressivite"])) for c in g],
            "fenetre": [float(np.median(c["Chartiste.fenetre"])) for c in g],
            "echelle_chart": [float(np.median(c["Chartiste.echelle"])) for c in g],
        }
        res["fenetres_finales"] = g[-1]["Chartiste.fenetre"]
    return actif, graine, res


def ic(v):
    v = np.asarray([x for x in v if not math.isnan(x)])
    d = 1.96 * v.std(ddof=1) / math.sqrt(len(v))
    return v.mean(), v.mean() - d, v.mean() + d


def main() -> None:
    a = argparse.ArgumentParser(description="Phase 5 : apprentissage")
    a.add_argument("--univers", type=int, default=12)
    a.add_argument("--pas", type=int, default=30000)
    a.add_argument("--pas-evolution", type=int, default=100000)
    a.add_argument("--sortie", default=ICI / "docs", type=Path)
    args = a.parse_args()
    config = tomllib.loads((ICI / "config.toml").read_text())
    t0 = time.time()

    print("🧠 Expérience A : agents adaptatifs (Brock et Hommes)…")
    with ProcessPoolExecutor() as pool:
        bh = list(pool.map(_brock_hommes, [(config, i, 3000 + g, args.pas)
                                           for i in INTENSITES for g in range(args.univers)]))
    print("🧬 Expérience B : évolution des stratégies…")
    with ProcessPoolExecutor() as pool:
        ev = list(pool.map(_evolution, [(config, act, 4000 + g, args.pas_evolution)
                                        for act in (False, True) for g in range(args.univers // 2 + 2)]))
    print(f"   terminé en {time.time() - t0:.0f} s")

    # ---------------------------------------------------------------- figure
    fig = plt.figure(figsize=(15, 13))
    gs = fig.add_gridspec(3, 3, hspace=0.5, wspace=0.3)
    fig.suptitle("Phase 5 : des agents qui apprennent", x=0.05, ha="left", fontsize=15, fontweight="bold")

    def style(ax, titre):
        ax.set_title(titre, loc="left", fontsize=10.5, fontweight="bold")
        ax.grid(color="#e6e8ec"); ax.set_axisbelow(True)
        for c in ("top", "right"):
            ax.spines[c].set_visible(False)

    # A1. trajectoire d'un univers à intensité forte
    ax = fig.add_subplot(gs[0, :2])
    prix, fond, pc = next(r["serie"] for i, g, r in bh if i == 5.0)
    ax.plot(fond, color="#9aa1ad", lw=1.2, label="Valeur fondamentale")
    ax.plot(prix, color="#22252b", lw=0.8, label="Prix")
    ax.set_ylabel("€")
    ax2 = ax.twinx()
    ax2.fill_between(np.arange(len(pc)), 0, pc, color="#db6a21", alpha=0.18, label="Part en mode chartiste")
    ax2.set_ylim(0, 1); ax2.set_ylabel("part des adaptatifs en mode chartiste", color="#db6a21")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper left")
    style(ax, "Un univers avec apprentissage fort (intensité 5) : les modes de stratégie se succèdent")

    # A2-A5. effets de l'intensité
    for k, (cle, lib) in enumerate([("part_chartiste", "Part moyenne en mode chartiste"),
                                    ("volatilite", "Volatilité (50 pas)"),
                                    ("kurtosis", "Kurtosis"),
                                    ("inefficience", "Écart moyen prix / valeur")]):
        ax = fig.add_subplot(gs[[0, 1, 1, 1][k], [2, 0, 1, 2][k]])
        m_, lo, hi = zip(*[ic([r[cle] for i, g, r in bh if i == I]) for I in INTENSITES])
        ax.errorbar(range(len(INTENSITES)), m_, yerr=[np.array(m_) - lo, np.array(hi) - m_], fmt="o-",
                    color="#2f6fd0", capsize=4, lw=1.6)
        ax.set_xticks(range(len(INTENSITES)), [str(i) for i in INTENSITES])
        ax.set_xlabel("intensité de l'apprentissage")
        style(ax, lib)

    # B. évolution
    evo = [r for act, g, r in ev if act]
    ref = [r for act, g, r in ev if not act]
    for k, (cle, lib) in enumerate([("biais_abs", "Fondamentalistes : erreur moyenne d'estimation |biais|"),
                                    ("fenetre", "Chartistes : horizon médian (pas)"),
                                    ("agressivite", "Fondamentalistes : agressivité médiane")]):
        ax = fig.add_subplot(gs[2, k])
        for r in evo:
            ax.plot(np.asarray(r["genes"]["t"]) / 1000, r["genes"][cle], color="#17936a", alpha=0.35, lw=1)
        moy = np.mean([r["genes"][cle] for r in evo], axis=0)
        ax.plot(np.asarray(evo[0]["genes"]["t"]) / 1000, moy, color="#17936a", lw=2.4, label="Moyenne des univers")
        ax.set_xlabel("milliers de pas (générations tous les 2 000 pas)")
        ax.legend(frameon=False, fontsize=9)
        style(ax, lib)
    fig.savefig(args.sortie / "apprentissage.png", dpi=110, bbox_inches="tight")
    plt.close(fig)

    # --------------------------------------------------------------- rapport
    L = ["# Phase 5 : des agents qui apprennent", "",
         f"*Généré le {date.today():%d/%m/%Y} par `python apprendre.py`.*", "",
         "## Expérience A : agents adaptatifs (Brock et Hommes 1998)", "",
         f"100 agents adaptatifs remplacent 50 fondamentalistes et 50 chartistes. Avant chaque "
         f"décision, ils choisissent leur stratégie avec une probabilité logit fondée sur le score "
         f"récent des deux stratégies (demi-vie de 2 000 pas). {args.univers} univers par intensité, "
         f"{args.pas:_} pas.".replace("_", " "), "",
         "| Intensité | Part en mode chartiste | Volatilité | Kurtosis | Écart prix / valeur | Pire chute | corr(part chartiste, volatilité suivante) |",
         "|---|---|---|---|---|---|---|"]
    for I in INTENSITES:
        R = [r for i, g, r in bh if i == I]
        f = lambda c, fmt: fmt.format(ic([r[c] for r in R])[0])
        L.append(f"| {I} | {f('part_chartiste', '{:.0%}')} | {f('volatilite', '{:.2%}')} | "
                 f"{f('kurtosis', '{:.1f}')} | {f('inefficience', '{:.2%}')} | {f('chute_max', '{:.1%}')} | "
                 f"{f('corr_part_vol', '{:+.2f}')} |")
    L += ["", f"## Expérience B : évolution des stratégies ({len(evo)} univers de "
          f"{args.pas_evolution:_} pas, avec et sans évolution)".replace("_", " "), "",
          "Tous les 2 000 pas, les 10 % de fondamentalistes et de chartistes les moins performants "
          "copient les paramètres d'un des 20 % les meilleurs, avec mutation.", "",
          "| Indicateur | Début | Fin |", "|---|---|---|"]
    for cle, lib, fmt in [("biais_abs", "Fondamentalistes : erreur moyenne d'estimation |biais|", "{:.2%}"),
                          ("agressivite", "Fondamentalistes : agressivité médiane", "{:.2f}"),
                          ("fenetre", "Chartistes : horizon médian (pas)", "{:.0f}"),
                          ("echelle_chart", "Chartistes : échelle de tendance médiane", "{:.3f}")]:
        debut = np.mean([r["genes"][cle][0] for r in evo]); fin = np.mean([r["genes"][cle][-1] for r in evo])
        L.append(f"| {lib} | {fmt.format(debut)} | {fmt.format(fin)} |")
    L += ["", "Efficience du marché par tranche de 10 000 pas (écart moyen prix / valeur) :", "",
          "| Tranche | Sans évolution | Avec évolution |", "|---|---|---|"]
    for b in range(len(ref[0]["blocs"])):
        s0 = np.mean([r["blocs"][b]["inefficience"] for r in ref]); s1 = np.mean([r["blocs"][b]["inefficience"] for r in evo])
        L.append(f"| {b * 10}–{(b + 1) * 10} k | {s0:.2%} | {s1:.2%} |")
    L += ["", "| Sur toute la durée | Sans évolution | Avec évolution |", "|---|---|---|"]
    for cle, lib, fmt in [("volatilite", "Volatilité", "{:.2%}"), ("kurtosis", "Kurtosis", "{:.1f}"),
                          ("inefficience", "Écart prix / valeur", "{:.2%}"), ("chute_max", "Pire chute", "{:.1%}")]:
        a0, lo0, hi0 = ic([r[cle] for r in ref]); a1, lo1, hi1 = ic([r[cle] for r in evo])
        L.append(f"| {lib} | {fmt.format(a0)} [{fmt.format(lo0)} ; {fmt.format(hi0)}] | "
                 f"{fmt.format(a1)} [{fmt.format(lo1)} ; {fmt.format(hi1)}] |")
    L += ["", "![Graphiques de la phase 5](apprentissage.png)", ""]
    (args.sortie / "apprentissage.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[8:]))


if __name__ == "__main__":
    main()
