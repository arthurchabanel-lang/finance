"""Phase 3 : validation Monte-Carlo du simulateur face aux faits stylisés.

Utilisation :
    python valider.py                 # 20 univers de 30 000 pas
    python valider.py --univers 50    # plus précis (plus long)

Produit docs/validation.md (rapport) et docs/validation.png (graphiques).
"""

from __future__ import annotations

import argparse
import time
import tomllib
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from marche.validation import HORIZON, HORIZONS_AGREGATION, valider

ICI = Path(__file__).parent


def figure(v, chemin: Path) -> None:
    u = v.univers
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
    fig.suptitle(f"Validation Monte-Carlo : {len(u)} univers indépendants", x=0.06, ha="left",
                 fontsize=15, fontweight="bold")
    gris, encre, orange = "#9aa1ad", "#22252b", "#e0712b"

    def style(ax, titre):
        ax.set_title(titre, loc="left", fontsize=11, fontweight="bold")
        ax.grid(color="#e6e8ec")
        ax.set_axisbelow(True)
        for c in ("top", "right"):
            ax.spines[c].set_visible(False)

    # 1. Mémoire de la volatilité, en log-log
    ax = axes[0, 0]
    courbes = np.array([m["acf_abs_courbe"] for m in u])
    k = np.arange(1, courbes.shape[1] + 1)
    moy = courbes.mean(axis=0)
    for c in courbes:
        ax.plot(k, np.where(c > 0, c, np.nan), color=gris, alpha=0.25, lw=0.8)
    ax.plot(k, np.where(moy > 0, moy, np.nan), "o-", color=orange, lw=2, ms=4, label="Simulation (moyenne)")
    ax.plot(k, moy[0] * k ** -0.3, "--", color=encre, lw=1.3, label="Marchés réels : k^(-0,3)")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_ylim(5e-3, 1)
    ax.set_xlabel(f"retard (× {HORIZON} pas)"); ax.set_ylabel("ACF des |rendements|")
    ax.legend(frameon=False, fontsize=9)
    style(ax, "Mémoire de la volatilité : trop courte")

    # 2. Indice de queue
    ax = axes[0, 1]
    hill = [m["hill"] for m in u]
    ax.axvspan(2, 5, color="#1a9e6e", alpha=0.10, label="Zone réaliste (2 à 5)")
    ax.axvline(3, color="#1a9e6e", lw=1.5, ls="--", label="Loi cubique inverse (3)")
    ax.hist(hill, bins=np.linspace(0.5, 6, 23), color=orange, alpha=0.9, label="Simulation (un univers = 1)")
    ax.set_xlabel("indice de queue de Hill α"); ax.set_ylabel("nombre d'univers")
    ax.legend(frameon=False, fontsize=9)
    style(ax, "Queues : trop épaisses (α trop petit)")

    # 3. Effet de levier
    ax = axes[1, 0]
    lev = np.array([m["levier_courbe"] for m in u])
    kk = np.arange(1, lev.shape[1] + 1)
    lo, hi = np.percentile(lev, [10, 90], axis=0)
    ax.fill_between(kk, lo, hi, color=orange, alpha=0.15, label="Simulation (10e–90e centile)")
    ax.plot(kk, lev.mean(axis=0), "o-", color=orange, lw=2, ms=4, label="Simulation (moyenne)")
    ax.axhline(0, color=gris)
    ax.plot(kk, -0.08 * np.exp(-kk / 5), "--", color=encre, lw=1.3, label="Marchés réels : négatif (allure)")
    ax.set_xlabel(f"retard k (× {HORIZON} pas)"); ax.set_ylabel("corr(r_t , r²_{t+k})")
    ax.legend(frameon=False, fontsize=9)
    style(ax, "Effet de levier : absent")

    # 4. Normalité par agrégation
    ax = axes[1, 1]
    ks = np.array([[m[f"kurtosis_h{h}"] for h in HORIZONS_AGREGATION] for m in u])
    for row in ks:
        ax.plot(HORIZONS_AGREGATION, row, color=gris, alpha=0.3, lw=0.8)
    ax.plot(HORIZONS_AGREGATION, np.median(ks, axis=0), "o-", color=orange, lw=2, label="Simulation (médiane)")
    ax.axhline(0, color="#1a9e6e", ls="--", lw=1.3, label="Loi normale")
    ax.set_xscale("log"); ax.set_yscale("symlog", linthresh=1)
    ax.set_xticks(HORIZONS_AGREGATION, [str(h) for h in HORIZONS_AGREGATION])
    ax.set_xlabel("horizon des rendements (pas)"); ax.set_ylabel("kurtosis excédentaire")
    ax.legend(frameon=False, fontsize=9)
    style(ax, "Normalité aux horizons longs : reproduite")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(chemin, dpi=110)
    plt.close(fig)


def rapport(v, n_pas: int, chemin: Path) -> None:
    lignes = [
        "# Validation Monte-Carlo du simulateur",
        "",
        f"*Générée le {date.today():%d/%m/%Y} par `python valider.py` : {len(v.univers)} univers "
        f"indépendants de {n_pas:_} pas, rendements sur {HORIZON} pas.*".replace("_", " "),
        "",
        "Chaque univers a sa propre graine aléatoire. Pour chaque fait stylisé, on donne la part "
        "d'univers qui le reproduisent, la moyenne et son intervalle de confiance à 95 %.",
        "",
        "| Fait stylisé | Univers OK | Moyenne | IC 95 % | Marchés réels |",
        "|---|---|---|---|---|",
    ]
    for r in v.resultats:
        f = r.critere.format
        lo, hi = r.ic95
        statut = "✅" if r.reussites >= 0.8 * r.n else ("⚠️" if r.reussites >= 0.5 * r.n else "❌")
        lignes.append(f"| {statut} {r.critere.nom} | {r.reussites}/{r.n} | {f.format(r.moyenne)} | "
                      f"[{f.format(lo)} ; {f.format(hi)}] | {r.critere.reference} |")
    lignes += [
        "",
        "Pour « Queues épaisses émergentes », la valeur est la kurtosis du prix dans l'expérience "
        "témoin sans news. Pour « Normalité aux horizons longs », c'est la kurtosis sur 250 pas.",
        "",
        "![Graphiques de validation](validation.png)",
        "",
        "Références : Cont (2001), *Quantitative Finance* 1(2) ; Gopikrishnan et al. (1999), "
        "*Phys. Rev. E* 60 ; Bouchaud, Matacz & Potters (2001), *Phys. Rev. Lett.* 87.",
        "",
    ]
    chemin.write_text("\n".join(lignes), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Validation Monte-Carlo")
    p.add_argument("--config", default=ICI / "config.toml", type=Path)
    p.add_argument("--univers", type=int, default=20)
    p.add_argument("--pas", type=int, default=30000)
    p.add_argument("--sortie", default=ICI / "docs", type=Path)
    a = p.parse_args()
    with open(a.config, "rb") as f:
        config = tomllib.load(f)
    a.sortie.mkdir(parents=True, exist_ok=True)
    print(f"🔬 Validation sur {a.univers} univers de {a.pas} pas…")
    t = time.time()
    v = valider(config, a.univers, a.pas,
                progression=lambda k, n: print(f"\r   univers {k}/{n}", end="", flush=True))
    print(f"\n   terminé en {time.time() - t:.0f} s\n")
    for r in v.resultats:
        print(f"   {r.reussites:3d}/{r.n}  {r.critere.nom}")
    figure(v, a.sortie / "validation.png")
    rapport(v, a.pas, a.sortie / "validation.md")
    print(f"\n📄 {a.sortie / 'validation.md'}\n📊 {a.sortie / 'validation.png'}")


if __name__ == "__main__":
    main()
