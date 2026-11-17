"""Phase 4 : expériences de régulation (Monte-Carlo apparié).

Utilisation :
    python experimenter.py               # 5 politiques x 20 univers (~5 min sur 4 cœurs)
    python experimenter.py --univers 40  # plus précis

Produit docs/experiences.md (rapport) et docs/experiences.png (graphiques).
"""

from __future__ import annotations

import argparse
import math
import time
import tomllib
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from marche.experiences import (DESCRIPTIONS, POLITIQUES, STRESS_T, STRESS_TITRES, comparer,
                                experimenter)

ICI = Path(__file__).parent

# (clé, libellé, unité, sens souhaitable : -1 = plus bas est mieux, +1 = plus haut est mieux)
INDICATEURS = [
    ("volatilite", "Volatilité", "{:.2%}", -1),
    ("krachs", "Krachs (rendements < −3 % sur 50 pas)", "{:.1f}", -1),
    ("chute_max", "Pire chute depuis un plus haut", "{:.1%}", -1),
    ("inefficience", "Écart moyen prix / valeur", "{:.2%}", -1),
    ("spread", "Fourchette moyenne", "{:.3f} €", -1),
    ("volume", "Volume par pas", "{:.1f}", +1),
]
INDICATEURS_STRESS = [
    ("chute_stress", "Chute pendant la liquidation", "{:.1%}", -1),
    ("recuperation", "Temps de récupération (pas)", "{:.0f}", -1),
]
COULEURS = {"Référence": "#22252b", "Taxe 0,1 %": "#2f6fd0", "Coupe-circuit 3 %": "#db6a21",
            "Vente à découvert interdite": "#a33ea1", "Levier limité": "#17936a"}


def verdict(c: dict, sens: int) -> str:
    lo, hi = c["ic"]
    if math.isnan(lo):
        return "—"
    if lo > 0 or hi < 0:
        mieux = (c["effet"] > 0) == (sens > 0)
        return "✅ mieux" if mieux else "❌ pire"
    return "≈ pas d'effet significatif"


def figure(res: dict, chemin: Path) -> None:
    politiques = [p for p in res if p != "Référence"]
    fig = plt.figure(figsize=(15, 13))
    gs = fig.add_gridspec(3, 4, height_ratios=[1, 1, 1.25], hspace=0.55, wspace=0.35)
    fig.suptitle("Expériences de régulation : effet de chaque politique par rapport à la référence",
                 x=0.05, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.05, 0.935, "Différence appariée sur les mêmes univers, en % de la référence. "
             "Barre d'erreur = IC 95 %. Vert : amélioration significative. Rouge : dégradation "
             "significative. Gris : non significatif.", fontsize=10, color="#555b66")

    tous = INDICATEURS + INDICATEURS_STRESS
    for k, (cle, lib, _, sens) in enumerate(tous):
        ax = fig.add_subplot(gs[k // 4, k % 4])
        for i, p in enumerate(politiques):
            c = comparer(res, cle, p)
            lo, hi = c["ic"]
            if math.isnan(c["effet"]):
                continue
            signif = lo > 0 or hi < 0
            mieux = (c["effet"] > 0) == (sens > 0)
            coul = ("#17845f" if mieux else "#c93f55") if signif else "#aab0bb"
            ax.barh(i, c["effet"], color=coul, height=0.6)
            ax.errorbar(c["effet"], i, xerr=[[c["effet"] - lo], [hi - c["effet"]]],
                        color="#22252b", capsize=3, lw=1)
        ax.axvline(0, color="#22252b", lw=0.8)
        ax.set_yticks(range(len(politiques)), politiques if k % 4 == 0 else [""] * len(politiques),
                      fontsize=9)
        ax.invert_yaxis()
        ax.set_title(lib, loc="left", fontsize=10, fontweight="bold")
        ax.set_xlabel("effet (%)", fontsize=8.5)
        ax.grid(axis="x", color="#e6e8ec")
        ax.set_axisbelow(True)
        for c in ("top", "right"):
            ax.spines[c].set_visible(False)

    ax = fig.add_subplot(gs[2, :])
    for p in res:
        traj = np.array([r["trajectoire"] for r in res[p].values()])
        x = np.arange(traj.shape[1]) - 500
        ax.plot(x, 100 * (np.median(traj, axis=0) - 1), color=COULEURS.get(p, "#888"),
                lw=2.2 if p == "Référence" else 1.6, label=p)
    ax.axvspan(0, STRESS_TITRES / 40, color="#c93f55", alpha=0.08,
               label=f"Liquidation de {STRESS_TITRES:_} titres".replace("_", " "))
    ax.axhline(0, color="#aab0bb", lw=0.8)
    ax.set_xlabel("pas depuis le début de la liquidation forcée")
    ax.set_ylabel("prix vs niveau d'avant (%)")
    ax.set_title("Stress test : trajectoire médiane du prix pendant et après une liquidation forcée",
                 loc="left", fontsize=11, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, ncol=3)
    ax.grid(color="#e6e8ec")
    for c in ("top", "right"):
        ax.spines[c].set_visible(False)
    fig.savefig(chemin, dpi=110, bbox_inches="tight")
    plt.close(fig)


def rapport(res: dict, n_pas: int, chemin: Path) -> None:
    n = len(res["Référence"])
    L = [
        "# Expériences de régulation",
        "",
        f"*Générées le {date.today():%d/%m/%Y} par `python experimenter.py` : {len(res)} politiques "
        f"× {n} univers appariés, {n_pas:_} pas par univers, plus un stress test par univers.*"
        .replace("_", " "),
        "",
        "Chaque politique est simulée sur exactement les mêmes univers que la référence (mêmes "
        "graines, donc mêmes news). L'effet est la différence moyenne entre les deux, avec un "
        "intervalle de confiance à 95 %. Un effet n'est retenu que si cet intervalle exclut 0.",
        "",
        "## Les politiques testées",
        "",
    ]
    L += [f"- **{p}** : {DESCRIPTIONS[p]}" for p in res]
    for titre, inds in [("## Marché normal", INDICATEURS),
                        (f"## Stress test : liquidation forcée de {STRESS_TITRES:_} titres au pas "
                         f"{STRESS_T:_}".replace("_", " "), INDICATEURS_STRESS)]:
        L += ["", titre, ""]
        for cle, lib, fmt, sens in inds:
            L += [f"### {lib}", "", "| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |",
                  "|---|---|---|---|---|"]
            ref = comparer(res, cle, "Référence")
            L.append(f"| Référence | {fmt.format(ref['ref'])} | — | — | — |")
            for p in res:
                if p == "Référence":
                    continue
                c = comparer(res, cle, p)
                lo, hi = c["ic"]
                L.append(f"| {p} | {fmt.format(c['pol'])} | {c['effet']:+.1f} % | "
                         f"[{lo:+.1f} % ; {hi:+.1f} %] | {verdict(c, sens)} |")
            L.append("")
    L += ["![Graphiques des expériences](experiences.png)", ""]
    chemin.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    a = argparse.ArgumentParser(description="Expériences de régulation")
    a.add_argument("--config", default=ICI / "config.toml", type=Path)
    a.add_argument("--univers", type=int, default=20)
    a.add_argument("--pas", type=int, default=30000)
    a.add_argument("--sortie", default=ICI / "docs", type=Path)
    args = a.parse_args()
    with open(args.config, "rb") as f:
        config = tomllib.load(f)
    args.sortie.mkdir(parents=True, exist_ok=True)
    print(f"🧪 {len(POLITIQUES)} politiques × {args.univers} univers…")
    t = time.time()
    res = experimenter(config, args.univers, args.pas,
                       progression=lambda k, n: print(f"\r   simulation {k}/{n}", end="", flush=True))
    print(f"\n   terminé en {time.time() - t:.0f} s\n")
    for cle, lib, _, sens in INDICATEURS + INDICATEURS_STRESS:
        print(f"   {lib}")
        for p in res:
            if p != "Référence":
                c = comparer(res, cle, p)
                print(f"      {p:<30} {c['effet']:+7.1f} %   {verdict(c, sens)}")
    figure(res, args.sortie / "experiences.png")
    rapport(res, args.pas, args.sortie / "experiences.md")
    print(f"\n📄 {args.sortie / 'experiences.md'}\n📊 {args.sortie / 'experiences.png'}")


if __name__ == "__main__":
    main()
