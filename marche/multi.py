"""Phase 6 : plusieurs actifs et contagion par les fonds endettés.

Chaque actif a son propre marché complet (carnet, agents locaux, valeur fondamentale
indépendante). Des fonds multi-actifs détiennent des positions sur tous les actifs avec un
seul compte : une perte sur un actif réduit le capital qui garantit les autres positions.
Si le fonds est endetté, un appel de marge le force à vendre PARTOUT : c'est le canal de
contagion (« fire sales », Shleifer et Vishny 1992 ; Cont et Wagalath 2016).
"""

from __future__ import annotations

import math

import numpy as np

from .agents import Agent
from .carnet import ACHAT, VENTE
from .simulation import Marche


class Fonds:
    """Un fonds multi-actifs : un compte, une position par marché."""

    def __init__(self, nom: str, cash: float) -> None:
        self.nom = nom
        self.cash = cash
        self.comptes: list[CompteFonds] = []
        self.cibles: list[float] = []
        self.cibles_initiales: list[float] = []
        self.plus_haut = 0.0
        self.capital_initial = 0.0
        self.a_liquider: list[int] = []
        self.suspendu_jusqua = -1

    def capital(self, prix: list[float]) -> float:
        return self.cash + sum(c.actions * p for c, p in zip(self.comptes, prix))


class CompteFonds(Agent):
    """Position d'un fonds sur un marché : le cash est celui du fonds (compte unique)."""

    type_nom = "Fonds multi-actifs"

    def __init__(self, fonds: Fonds, actions: int) -> None:
        self._fonds = fonds
        super().__init__(-1, cash=0.0, actions=actions, credit_max=math.inf, rng=None,
                         p={"position_max": 10 ** 9})

    @property
    def cash(self) -> float:
        return self._fonds.cash

    @cash.setter
    def cash(self, valeur: float) -> None:
        self._fonds.cash = valeur

    def agir(self, t: int, marche: Marche) -> None:  # piloté par MarcheMulti
        pass


class MarcheMulti:
    def __init__(self, config: dict, graine: int) -> None:
        cmu = config["multi"]
        self.cfg = cmu
        self.rng = np.random.default_rng(graine)
        self.marches = [Marche(config, graine * 100 + k) for k in range(cmu["nombre_actifs"])]
        self.t = 0
        p0 = config["marche"]["prix_initial"]
        n_actifs = len(self.marches)
        exposition = cmu["titres_par_actif"] * p0 * n_actifs
        capital = exposition / cmu["levier"]
        self.fonds: list[Fonds] = []
        for i in range(cmu["nombre_fonds"]):
            f = Fonds(f"Fonds {i + 1}", cash=0.0)
            for m in self.marches:
                f.comptes.append(m.ajouter_agent(CompteFonds(f, cmu["titres_par_actif"])))
            f.cash = capital - exposition          # dette = exposition - capital
            f.cibles = [float(cmu["titres_par_actif"])] * n_actifs
            f.cibles_initiales = list(f.cibles)
            f.plus_haut = f.capital_initial = capital
            f.a_liquider = [0] * n_actifs
            self.fonds.append(f)
        self.hist_appels: list[tuple[int, int]] = []
        self.hist_faillites: list[int] = []
        self.capital_injecte = 0.0

    def prix(self) -> list[float]:
        return [m.hist_prix[-1] for m in self.marches]

    # ------------------------------------------------------------------ fonds
    def _controle_marge(self) -> None:
        c = self.cfg
        prix = self.prix()
        rappel = 1.0 - 0.5 ** (c["frequence_controle"] / c["demi_vie_reprise"])
        n = 0
        for f in self.fonds:
            f.cibles = [x + rappel * (x0 - x) for x, x0 in zip(f.cibles, f.cibles_initiales)]
            if any(f.a_liquider):
                continue
            cap = f.capital(prix)
            if cap < c["seuil_faillite"] * f.capital_initial:
                # Faillite : un nouveau fonds reprend le portefeuille avec des capitaux frais.
                apport = f.capital_initial - cap
                f.cash += apport
                self.capital_injecte += apport
                f.plus_haut = f.capital_initial
                self.hist_faillites.append(self.t)
                continue
            if cap > f.plus_haut:
                f.plus_haut = cap
            elif c["appels_de_marge"] and f.cash < 0 and cap < f.plus_haut * (1.0 - c["seuil_perte"]):
                # Appel de marge : vendre une fraction de TOUTES les positions.
                f.a_liquider = [int(round(cpt.actions * c["reduction"])) for cpt in f.comptes]
                f.cibles = [max(x * (1.0 - c["reduction"]), x0 * 0.5)
                            for x, x0 in zip(f.cibles, f.cibles_initiales)]
                for cpt, m in zip(f.comptes, self.marches):
                    cpt.annuler_tout(m)
                n += 1
        if n:
            self.hist_appels.append((self.t, n))

    def _liquider(self) -> None:
        tranche = self.cfg["tranche_liquidation"]
        for f in self.fonds:
            if not any(f.a_liquider):
                continue
            for k, (cpt, m) in enumerate(zip(f.comptes, self.marches)):
                reste = f.a_liquider[k]
                if reste <= 0:
                    continue
                avant = cpt.actions
                m.envoyer_marche(cpt, VENTE, min(reste, tranche))
                f.a_liquider[k] -= avant - cpt.actions
            if not any(x > 0 for x in f.a_liquider):
                f.a_liquider = [0] * len(self.marches)
                f.suspendu_jusqua = self.t + int(self.rng.exponential(self.cfg["duree_suspension"]))
                f.plus_haut = f.capital(self.prix())

    def _reequilibrer(self) -> None:
        """Les fonds se rapprochent lentement de leurs positions cibles (ordres limites)."""
        c = self.cfg
        for f in self.fonds:
            if any(f.a_liquider) or self.t < f.suspendu_jusqua or self.rng.random() > c["proba_reequilibrage"]:
                continue
            for cpt, m, cible in zip(f.comptes, self.marches, f.cibles):
                ecart = cible - cpt.actions
                if abs(ecart) < 1:
                    continue
                cote = ACHAT if ecart > 0 else VENTE
                q = min(int(abs(ecart)), c["tranche_reequilibrage"])
                cpt.annuler_tout(m)
                m.envoyer_limite(cpt, cote, m.prix_reference(), q, duree=20)

    # ------------------------------------------------------------- dynamique
    def pas(self) -> None:
        self.t += 1
        for m in self.marches:
            m.pas()
        self._liquider()
        self._reequilibrer()
        if self.t % self.cfg["frequence_controle"] == 0:
            self._controle_marge()

    def executer(self, n_pas: int) -> None:
        for _ in range(n_pas):
            self.pas()
