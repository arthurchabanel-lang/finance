"""Carnet d'ordres à enchères continues (continuous double auction).

Règles, comme sur une vraie Bourse :
- priorité prix, puis priorité temps (premier arrivé, premier servi) ;
- un ordre limite qui croise le meilleur prix opposé s'exécute immédiatement
  (en tout ou partie), le reliquat reste dans le carnet ;
- un ordre au marché consomme la liquidité disponible, le reliquat est annulé ;
- les ordres ont une durée de vie et expirent automatiquement ;
- pas d'auto-exécution : si un agent rencontre son propre ordre, l'ancien est annulé.

Les prix sont des entiers en « ticks » (ex. 1 tick = 0,01 €) pour éviter les
erreurs d'arrondi des nombres à virgule.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass

ACHAT = 1
VENTE = -1


@dataclass
class Ordre:
    id: int
    agent_id: int
    cote: int  # ACHAT ou VENTE
    prix: int  # en ticks
    quantite: int
    expire_a: int  # pas de temps à partir duquel l'ordre n'est plus valide
    actif: bool = True


@dataclass(frozen=True)
class Transaction:
    t: int
    prix: int
    quantite: int
    acheteur: int
    vendeur: int
    agresseur: int  # côté de l'ordre entrant (ACHAT ou VENTE)


class CarnetOrdres:
    def __init__(self) -> None:
        # Tas (heaps) : meilleurs prix en tête. Achats triés par prix décroissant.
        self._achats: list[tuple[int, int, Ordre]] = []
        self._ventes: list[tuple[int, int, Ordre]] = []
        self._ordres: dict[int, Ordre] = {}
        self._compteur_id = itertools.count(1)
        self._compteur_seq = itertools.count()

    # ------------------------------------------------------------------ lecture
    def _nettoyer_tete(self, tas: list, t: int) -> None:
        while tas:
            ordre = tas[0][2]
            if ordre.actif and ordre.quantite > 0 and ordre.expire_a > t:
                return
            heapq.heappop(tas)
            ordre.actif = False
            self._ordres.pop(ordre.id, None)

    def meilleur_achat(self, t: int) -> Ordre | None:
        self._nettoyer_tete(self._achats, t)
        return self._achats[0][2] if self._achats else None

    def meilleure_vente(self, t: int) -> Ordre | None:
        self._nettoyer_tete(self._ventes, t)
        return self._ventes[0][2] if self._ventes else None

    def profondeur(self, t: int, niveaux: int = 10) -> tuple[list, list]:
        """Quantités agrégées par prix sur les `niveaux` meilleurs prix de chaque côté."""
        def agreger(tas, signe):
            par_prix: dict[int, int] = {}
            for _, _, o in tas:
                if o.actif and o.quantite > 0 and o.expire_a > t:
                    par_prix[o.prix] = par_prix.get(o.prix, 0) + o.quantite
            prix = sorted(par_prix, key=lambda p: -signe * p)[:niveaux]
            return [(p, par_prix[p]) for p in prix]
        return agreger(self._achats, ACHAT), agreger(self._ventes, VENTE)

    def ordre(self, ordre_id: int) -> Ordre | None:
        return self._ordres.get(ordre_id)

    # ------------------------------------------------------------- écriture
    def annuler(self, ordre_id: int) -> None:
        ordre = self._ordres.pop(ordre_id, None)
        if ordre is not None:
            ordre.actif = False  # retrait paresseux du tas

    def ordre_limite(self, agent_id: int, cote: int, prix: int, quantite: int,
                     t: int, duree: int) -> tuple[Ordre | None, list[Transaction]]:
        """Soumet un ordre limite. Renvoie (ordre resté au carnet ou None, transactions)."""
        if quantite <= 0 or prix <= 0:
            return None, []
        transactions = self._executer(agent_id, cote, quantite, t, prix_limite=prix)
        reste = quantite - sum(tr.quantite for tr in transactions)
        if reste <= 0:
            return None, transactions
        ordre = Ordre(next(self._compteur_id), agent_id, cote, prix, reste, t + duree)
        cle = -prix if cote == ACHAT else prix
        heapq.heappush(self._achats if cote == ACHAT else self._ventes,
                       (cle, next(self._compteur_seq), ordre))
        self._ordres[ordre.id] = ordre
        return ordre, transactions

    def ordre_marche(self, agent_id: int, cote: int, quantite: int,
                     t: int) -> list[Transaction]:
        if quantite <= 0:
            return []
        return self._executer(agent_id, cote, quantite, t, prix_limite=None)

    def _executer(self, agent_id: int, cote: int, quantite: int, t: int,
                  prix_limite: int | None) -> list[Transaction]:
        transactions: list[Transaction] = []
        tas_oppose = self._ventes if cote == ACHAT else self._achats
        while quantite > 0:
            self._nettoyer_tete(tas_oppose, t)
            if not tas_oppose:
                break
            contrepartie = tas_oppose[0][2]
            if prix_limite is not None:
                if cote == ACHAT and contrepartie.prix > prix_limite:
                    break
                if cote == VENTE and contrepartie.prix < prix_limite:
                    break
            if contrepartie.agent_id == agent_id:  # pas d'auto-exécution
                self.annuler(contrepartie.id)
                continue
            q = min(quantite, contrepartie.quantite)
            contrepartie.quantite -= q
            quantite -= q
            if cote == ACHAT:
                acheteur, vendeur = agent_id, contrepartie.agent_id
            else:
                acheteur, vendeur = contrepartie.agent_id, agent_id
            # Le prix d'exécution est celui de l'ordre déjà présent au carnet.
            transactions.append(Transaction(t, contrepartie.prix, q, acheteur, vendeur, cote))
            if contrepartie.quantite == 0:
                contrepartie.actif = False
                self._ordres.pop(contrepartie.id, None)
        return transactions
