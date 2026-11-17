"""Tableau de bord visuel d'une simulation."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analyse import Rapport, rendements

COULEURS = {
    "Fondamentaliste": "#2a78d6",
    "Chartiste": "#e0712b",
    "Bruiteur": "#8a8f98",
    "Teneur de marché": "#1a9e6e",
}
ENCRE = "#22252b"
GRILLE = "#e6e8ec"


def _style(ax, titre: str) -> None:
    ax.set_title(titre, loc="left", fontsize=11, fontweight="bold", color=ENCRE, pad=8)
    ax.grid(color=GRILLE, linewidth=0.8)
    ax.set_axisbelow(True)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        ax.spines[cote].set_color("#b9bec7")
    ax.tick_params(colors="#555b66", labelsize=8.5)


def tableau_de_bord(marche, rapport: Rapport, chemin: str) -> None:
    s = marche.series()
    t = np.arange(len(s["prix"]))
    h = rapport.horizon
    cm = marche.config["marche"]
    richesse_initiale = cm["cash_initial"] + cm["actions_initiales"] * cm["prix_initial"]

    fig = plt.figure(figsize=(15, 16), facecolor="white")
    gs = fig.add_gridspec(4, 2, height_ratios=[1.25, 0.8, 1, 1], hspace=0.42, wspace=0.18,
                          top=0.935)
    fig.suptitle("Marché artificiel multi-agents — tableau de bord", x=0.07, ha="left",
                 fontsize=16, fontweight="bold", color=ENCRE, y=0.985)
    score = sum(v.reussi for v in rapport.verdicts)
    fig.text(0.07, 0.962, f"{len(marche.agents)} agents · {marche.t:,} pas de temps · "
             f"{score}/{len(rapport.verdicts)} faits stylisés reproduits".replace(",", " "),
             fontsize=10.5, color="#555b66")

    # 1. Prix vs valeur fondamentale ------------------------------------------
    ax = fig.add_subplot(gs[0, :])
    ax.plot(t, s["fondamental"], color="#9aa1ad", lw=1.1, label="Valeur fondamentale")
    ax.plot(t, s["prix"], color=ENCRE, lw=0.9, label="Prix de marché (milieu de fourchette)")
    for tn, taille in marche.hist_news:
        ax.axvline(tn, color="#2a78d6" if taille > 0 else "#d64545", alpha=0.18, lw=0.8)
    ax.plot([], [], color="#2a78d6", alpha=0.5, label="News positive / négative")
    ax.plot([], [], color="#d64545", alpha=0.5)
    ax.set_ylabel("€", color="#555b66")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.92, facecolor="white",
              edgecolor="none")
    _style(ax, "Prix et valeur fondamentale")

    # 2. Rendements -----------------------------------------------------------
    ax = fig.add_subplot(gs[1, :])
    r = rendements(s["prix"], h)
    ax.bar(np.arange(len(r)) * h, 100 * r, width=h, color=ENCRE, linewidth=0)
    ax.set_ylabel("%", color="#555b66")
    ax.set_xlim(0, len(s["prix"]))
    _style(ax, f"Rendements sur {h} pas : périodes calmes et périodes agitées alternent")

    # 3. Distribution ---------------------------------------------------------
    ax = fig.add_subplot(gs[2, 0])
    z = (r - r.mean()) / r.std()
    bornes = np.linspace(-8, 8, 41)
    dens, _ = np.histogram(z, bins=bornes, density=True)
    centres = 0.5 * (bornes[1:] + bornes[:-1])
    ax.semilogy(centres[dens > 0], dens[dens > 0], "o", ms=4, color="#e0712b",
                label="Simulation")
    xs = np.linspace(-8, 8, 400)
    ax.semilogy(xs, np.exp(-xs ** 2 / 2) / np.sqrt(2 * np.pi), color="#9aa1ad", lw=1.5,
                label="Loi normale")
    ax.set_ylim(1e-5, 1)
    ax.set_xlabel("rendement normalisé (écarts-types)", color="#555b66", fontsize=9)
    ax.legend(frameon=False, fontsize=9)
    _style(ax, f"Queues épaisses (kurtosis excédentaire {rapport.stats['kurtosis']:.1f})")

    # 4. Autocorrélations -----------------------------------------------------
    ax = fig.add_subplot(gs[2, 1])
    lags = np.arange(1, len(rapport.acf_r) + 1)
    ax.plot(lags, rapport.acf_abs, "o-", ms=3.5, color="#e0712b", lw=1.4,
            label="|rendements| (volatilité)")
    ax.plot(lags, rapport.acf_r, "o-", ms=3.5, color=ENCRE, lw=1.4, label="rendements")
    ax.plot(lags, rapport.acf_abs_fondamental, "--", color="#9aa1ad", lw=1.2,
            label="|rendements| de la valeur fondamentale")
    ax.axhline(0, color="#b9bec7", lw=1)
    ax.set_xlabel(f"retard (× {h} pas)", color="#555b66", fontsize=9)
    ax.legend(frameon=False, fontsize=9)
    _style(ax, "Autocorrélations : mémoire de la volatilité, pas des prix")

    # 5. Performance par type d'agent ----------------------------------------
    ax = fig.add_subplot(gs[3, 0])
    tb = np.asarray(marche.hist_richesse_t)
    for nom, valeurs in marche.hist_richesse.items():
        perf = 100 * (np.asarray(valeurs) / richesse_initiale - 1)
        ax.plot(tb, perf, color=COULEURS.get(nom), lw=1.8, label=nom)
    bench = cm["cash_initial"] + cm["actions_initiales"] * s["prix"][tb]
    ax.plot(tb, 100 * (bench / richesse_initiale - 1), color=ENCRE, lw=1.0, ls=":",
            label="Benchmark (buy & hold)")
    ax.axhline(0, color="#b9bec7", lw=1)
    ax.set_ylabel("performance moyenne (%)", color="#555b66", fontsize=9)
    ax.legend(frameon=False, fontsize=9)
    _style(ax, "Qui gagne ? Performance moyenne par stratégie")

    # 6. Volume et attention --------------------------------------------------
    ax = fig.add_subplot(gs[3, 1])
    n = len(s["volume"]) // h * h
    vol_bloc = s["volume"][:n].reshape(-1, h).sum(axis=1)
    att_bloc = s["attention"][:n].reshape(-1, h).mean(axis=1)
    xb = np.arange(len(vol_bloc)) * h
    ax.bar(xb, vol_bloc, width=h, color="#c9ced6", linewidth=0, label="Volume échangé")
    ax.set_ylabel(f"titres échangés / {h} pas", color="#555b66", fontsize=9)
    ax2 = ax.twinx()
    ax2.plot(xb, att_bloc, color="#e0712b", lw=1.2, label="Activité des chartistes (×)")
    ax2.set_ylim(0.8, max(3.2, att_bloc.max() * 1.05))
    ax2.tick_params(colors="#e0712b", labelsize=8.5)
    for cote in ("top",):
        ax2.spines[cote].set_visible(False)
    l1, n1 = ax.get_legend_handles_labels()
    l2, n2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, n1 + n2, frameon=False, fontsize=9, loc="upper left")
    _style(ax, "Volume et frénésie des chartistes")

    fig.savefig(chemin, dpi=110, bbox_inches="tight")
    plt.close(fig)
