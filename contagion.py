"""Phase 6 : contagion systémique par les fonds multi-actifs endettés.

Trois actifs aux valeurs fondamentales indépendantes. Au pas CHOC, une liquidation forcée
frappe UNIQUEMENT l'actif A. On compare, sur les mêmes univers :
- des fonds multi-actifs endettés (levier 3, appels de marge) ;
- les mêmes fonds sans dette (levier 1 : aucune marge à appeler).
Les actifs B et C chutent-ils aussi ? Les corrélations montent-elles en crise ?

Utilisation :
    python contagion.py          # 2 scénarios x 20 univers (~3 min sur 4 cœurs)
Produit docs/contagion.md et docs/contagion.png.
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

from marche.agents import ActeurExterne
from marche.carnet import VENTE
from marche.experiences import appliquer
from marche.multi import MarcheMulti

ICI = Path(__file__).parent
CHOC, APRES, TITRES = 8000, 3000, 4000
SCENARIOS = {
    "Fonds endettés (levier 3)": {"multi.levier": 3.0},
    "Fonds sans dette (levier 1)": {"multi.levier": 1.0},
    "Fonds endettés, sans choc (témoin)": {"multi.levier": 3.0},
}
SANS_CHOC = "Fonds endettés, sans choc (témoin)"
COULEURS = {"Fonds endettés (levier 3)": "#c93f55", "Fonds sans dette (levier 1)": "#2f6fd0",
            SANS_CHOC: "#9aa1ad"}
NOMS = ["A (choqué)", "B", "C"]


def correlation_moyenne(series: list[np.ndarray], debut: int, fin: int, h: int) -> float:
    r = [np.diff(np.log(s[debut:fin:h])) for s in series]
    c = [np.corrcoef(r[i], r[j])[0, 1] for i in range(3) for j in range(i + 1, 3)]
    return float(np.mean(c))


def _une(args):
    nom, config, graine = args
    mm = MarcheMulti(appliquer(config, SCENARIOS[nom]), graine)
    mm.executer(CHOC)
    if nom != SANS_CHOC:
        vendeur = mm.marches[0].ajouter_agent(ActeurExterne())
        mm.marches[0].lancer_scenario(vendeur, VENTE, TITRES, par_pas=40)
    appels_avant = sum(n for t, n in mm.hist_appels)
    mm.executer(APRES)
    prix = [np.asarray(m.hist_prix) for m in mm.marches]
    res = {"chute": [], "trajectoire": []}
    for p in prix:
        avant = float(np.mean(p[CHOC - 200:CHOC]))
        res["chute"].append(math.log(avant / p[CHOC:CHOC + APRES].min()))
        res["trajectoire"].append((p[CHOC - 500:CHOC + APRES] / avant).astype(np.float32))
    res["corr_calme"] = correlation_moyenne(prix, 1000, CHOC, 20)
    res["corr_crise"] = correlation_moyenne(prix, CHOC, CHOC + 2000, 20)
    res["appels_crise"] = sum(n for t, n in mm.hist_appels) - appels_avant
    res["appels_calme"] = appels_avant
    res["faillites"] = len(mm.hist_faillites)
    return nom, graine, res


def ic(v):
    v = np.asarray(v, dtype=float)
    d = 1.96 * v.std(ddof=1) / math.sqrt(len(v))
    return v.mean(), v.mean() - d, v.mean() + d


def main() -> None:
    a = argparse.ArgumentParser(description="Phase 6 : contagion")
    a.add_argument("--univers", type=int, default=20)
    a.add_argument("--sortie", default=ICI / "docs", type=Path)
    args = a.parse_args()
    config = tomllib.loads((ICI / "config.toml").read_text())
    t0 = time.time()
    print(f"🌐 Contagion : {len(SCENARIOS)} scénarios × {args.univers} univers…")
    with ProcessPoolExecutor() as pool:
        res = list(pool.map(_une, [(n, config, 5000 + g) for n in SCENARIOS for g in range(args.univers)]))
    print(f"   terminé en {time.time() - t0:.0f} s")
    par = {n: {g: r for nn, g, r in res if nn == n} for n in SCENARIOS}
    lev, sans, temoin = list(SCENARIOS)
    graines = sorted(par[lev])

    # Différences appariées (endettés − sans dette) sur les mêmes univers.
    def apparie(f, autre=None):
        autre = autre or sans
        return ic([f(par[lev][g]) - f(par[autre][g]) for g in graines])

    # ------------------------------------------------------------------ figure
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1], hspace=0.45, wspace=0.28)
    fig.suptitle("Phase 6 : un choc sur l'actif A contamine-t-il B et C ?", x=0.05, ha="left",
                 fontsize=15, fontweight="bold")
    fig.text(0.05, 0.935, f"Liquidation forcée de {TITRES:_} titres sur l'actif A uniquement. Valeurs "
             "fondamentales indépendantes. Médiane de {n} univers.".replace("_", " ").replace("{n}", str(len(graines))),
             fontsize=10, color="#555b66")
    for k in range(3):
        ax = fig.add_subplot(gs[0, k])
        for n in SCENARIOS:
            tr = np.array([par[n][g]["trajectoire"][k] for g in graines])
            x = np.arange(tr.shape[1]) - 500
            ax.plot(x, 100 * (np.median(tr, axis=0) - 1), color=COULEURS[n], lw=2, label=n)
            lo, hi = np.percentile(tr, [25, 75], axis=0)
            ax.fill_between(x, 100 * (lo - 1), 100 * (hi - 1), color=COULEURS[n], alpha=0.12)
        ax.axvspan(0, TITRES / 40, color="#888", alpha=0.08)
        ax.axhline(0, color="#aab0bb", lw=0.8)
        ax.set_title(f"Actif {NOMS[k]}", loc="left", fontsize=11, fontweight="bold")
        ax.set_xlabel("pas depuis le choc")
        if k == 0:
            ax.set_ylabel("prix vs avant le choc (%)")
            ax.legend(frameon=False, fontsize=9, loc="lower right")
        ax.grid(color="#e6e8ec")
        for c in ("top", "right"):
            ax.spines[c].set_visible(False)

    ax = fig.add_subplot(gs[1, 0:2])
    largeur = 0.27
    for i, n in enumerate(SCENARIOS):
        m_ = [ic([par[n][g]["chute"][k] for g in graines]) for k in range(3)]
        ax.bar(np.arange(3) + (i - 1) * largeur, [100 * x[0] for x in m_], largeur, color=COULEURS[n], label=n,
               yerr=[[100 * (x[0] - x[1]) for x in m_], [100 * (x[2] - x[0]) for x in m_]], capsize=4)
    ax.set_xticks(range(3), [f"Actif {x}" for x in NOMS])
    ax.set_ylabel("pire chute après le choc (%)")
    ax.set_title("Chute de chaque actif (moyenne, IC 95 %)", loc="left", fontsize=11, fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(axis="y", color="#e6e8ec")
    for c in ("top", "right"):
        ax.spines[c].set_visible(False)

    ax = fig.add_subplot(gs[1, 2])
    for i, n in enumerate(SCENARIOS):
        for j, (cle, lib) in enumerate([("corr_calme", "calme"), ("corr_crise", "crise")]):
            m_, lo, hi = ic([par[n][g][cle] for g in graines])
            ax.bar(j + (i - 1) * largeur, m_, largeur, color=COULEURS[n], yerr=[[m_ - lo], [hi - m_]], capsize=4)
    ax.set_xticks([0, 1], ["Avant le choc", "Pendant la crise"])
    ax.axhline(0, color="#22252b", lw=0.8)
    ax.set_title("Corrélation moyenne entre actifs", loc="left", fontsize=11, fontweight="bold")
    ax.grid(axis="y", color="#e6e8ec")
    for c in ("top", "right"):
        ax.spines[c].set_visible(False)
    fig.savefig(args.sortie / "contagion.png", dpi=110, bbox_inches="tight")
    plt.close(fig)

    # ----------------------------------------------------------------- rapport
    L = ["# Phase 6 : contagion systémique", "",
         f"*Généré le {date.today():%d/%m/%Y} par `python contagion.py` : {len(graines)} univers appariés par scénario.*", "",
         "Trois actifs, chacun avec son propre marché (402 agents locaux) et une valeur fondamentale "
         "**indépendante**. Vingt fonds multi-actifs détiennent chacun 300 titres de chaque actif, "
         "sur un compte unique. Au pas 8 000, une liquidation forcée de 4 000 titres frappe "
         "**uniquement l'actif A**.", "",
         "Les deux scénarios ont exactement les mêmes fonds, avec les mêmes positions. Seule la dette diffère :",
         "", "- **Fonds endettés (levier 3)** : 30 000 € de capital pour 90 000 € de titres, soumis aux appels de marge ;",
         "- **Fonds sans dette (levier 1)** : 90 000 € de capital, donc aucune marge à appeler.", "",
         "- **Témoin** : les fonds endettés, mais sans aucun choc. Il sépare l'effet du choc de la "
         "fragilité de fond due à l'endettement.", "",
         "| Mesure | Fonds endettés | Fonds sans dette | Témoin sans choc | Effet du choc à dette égale (endettés − témoin) | Effet de la dette à choc égal (endettés − sans dette) |",
         "|---|---|---|---|---|---|"]
    lignes = [(f"Pire chute de l'actif {NOMS[k]}", (lambda r, k=k: r["chute"][k]), "{:.1%}") for k in range(3)]
    lignes += [("Corrélation entre actifs avant le choc", lambda r: r["corr_calme"], "{:+.3f}"),
               ("Corrélation entre actifs pendant la crise", lambda r: r["corr_crise"], "{:+.3f}"),
               ("Appels de marge avant le choc", lambda r: r["appels_calme"], "{:.0f}"),
               ("Appels de marge pendant la crise", lambda r: r["appels_crise"], "{:.0f}")]
    for lib, f, fmt in lignes:
        a_, b_, c_ = (ic([f(par[n][g]) for g in graines])[0] for n in (lev, sans, temoin))
        d1, lo1, hi1 = apparie(f, temoin)
        d2, lo2, hi2 = apparie(f, sans)
        L.append(f"| {lib} | {fmt.format(a_)} | {fmt.format(b_)} | {fmt.format(c_)} | "
                 f"{fmt.format(d1)} [{fmt.format(lo1)} ; {fmt.format(hi1)}] | "
                 f"{fmt.format(d2)} [{fmt.format(lo2)} ; {fmt.format(hi2)}] |")
    L += ["", "![Graphiques de la contagion](contagion.png)", ""]
    (args.sortie / "contagion.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[13:]))


if __name__ == "__main__":
    main()
