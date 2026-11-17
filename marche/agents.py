"""Les agents du marché.

Chaque type d'agent incarne une stratégie classique de la littérature des
marchés artificiels (Chiarella & Iori 2002, Lux & Marchesi 1999, etc.) :

- Fondamentaliste : surpondère quand le titre est sous-évalué, sous-pondère sinon.
- Chartiste       : suit la tendance récente (momentum).
- Bruiteur        : trade sans information, apporte liquidité et bruit.
- Teneur de marché: affiche en continu un prix d'achat et de vente, gère son stock.

Logique de gestion « active » : chaque agent part d'une dotation neutre
(son benchmark) et choisit une position cible = neutre ± position_max x tanh(signal).
Il exécute l'écart par tranches (pas plus de `taille_max_ordre` à la fois).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from .carnet import ACHAT, VENTE

if TYPE_CHECKING:
    from .simulation import Marche


class Agent:
    type_nom = "agent"

    def __init__(self, agent_id: int, cash: float, actions: int, credit_max: float,
                 rng: np.random.Generator, p: dict) -> None:
        self.id = agent_id
        self.cash = float(cash)
        self.actions = int(actions)
        self.neutre = float(actions)        # exposition de référence (benchmark)
        self.neutre_initial = float(actions)
        self.position_max = p["position_max"]  # écart maximal au benchmark
        self.credit_max = credit_max        # découvert autorisé (achat sur marge)
        self.plancher_reglementaire = -math.inf  # ex. 0 si vente à découvert interdite
        self.rng = rng
        self.ordres: list[int] = []
        # Appels de marge : plus haut historique du capital, liquidation en cours, suspension
        self.plus_haut = self.cash + self.actions * 100.0
        self.a_liquider = 0
        self.suspendu_jusqua = -1

    def richesse(self, prix: float) -> float:
        """Valorisation au prix de marché (mark-to-market)."""
        return self.cash + self.actions * prix

    def quantite_autorisee(self, cote: int, quantite: int, prix: float) -> int:
        """Borne la quantité selon la limite de position et la marge disponible."""
        if cote == ACHAT:
            q = min(quantite, self.neutre + self.position_max - self.actions)
            if math.isfinite(self.credit_max):
                pouvoir_achat = max(self.cash + self.credit_max, 0.0)
                q = min(q, int(pouvoir_achat // max(prix, 1e-9)))
        else:
            q = min(quantite, self.actions - self.plancher)
        return max(int(q), 0)

    @property
    def plancher(self) -> float:
        """Position minimale autorisée (vente à découvert bornée)."""
        return max(self.neutre - self.position_max, self.plancher_reglementaire)

    def annuler_tout(self, marche: "Marche") -> None:
        for oid in self.ordres:
            marche.carnet.annuler(oid)
        self.ordres.clear()

    def viser(self, signal: float) -> tuple[int, int]:
        """Traduit un signal en (côté, quantité) pour se rapprocher de la cible."""
        cible = self.neutre + self.position_max * math.tanh(signal)
        ecart = cible - self.actions
        if abs(ecart) < 1:
            return ACHAT, 0
        cote = ACHAT if ecart > 0 else VENTE
        return cote, min(int(round(abs(ecart))), self.taille_max)

    def agir(self, t: int, marche: "Marche") -> None:  # pragma: no cover
        raise NotImplementedError


class Fondamentaliste(Agent):
    """Estime une valeur (biais personnel persistant) et parie sur le retour vers elle."""

    type_nom = "Fondamentaliste"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        p = kwargs["p"]
        self.biais = self.rng.normal(0.0, p["dispersion_estimation"])
        # Un gérant « value » raisonne en euros : sa surpondération maximale est un montant,
        # pas un nombre de titres (sinon, en plein krach, il ne peut plus acheter à bas prix).
        self.exposition_max_euros = self.position_max * p.get("prix_reference_limite", 100.0)
        self.echelle = p["echelle_ecart"] * self.rng.uniform(0.5, 1.5)
        self.agressivite = self.rng.uniform(*p["agressivite"])
        self.taille_max = p["taille_max_ordre"]
        self.duree = p["duree_ordre"]

    def agir(self, t: int, marche: "Marche") -> None:
        self.annuler_tout(marche)
        prix = marche.prix_reference()
        valeur = marche.valeur_fondamentale * math.exp(self.biais)
        ecart = math.log(valeur / prix)  # > 0 : sous-évalué
        self.position_max = self.exposition_max_euros / prix
        if abs(ecart) < marche.zone_morte:  # le gain espéré ne couvre pas les frais
            return
        cote, quantite = self.viser(ecart / self.echelle)
        quantite = self.quantite_autorisee(cote, quantite, prix)
        # Ordre limite entre le prix actuel et la valeur estimée : patient mais décidé.
        prix_limite = prix * math.exp(self.agressivite * ecart)
        marche.envoyer_limite(self, cote, prix_limite, quantite, self.duree)


class Chartiste(Agent):
    """Extrapole la tendance observée sur sa fenêtre d'analyse."""

    type_nom = "Chartiste"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        p = kwargs["p"]
        self.fenetre = int(self.rng.integers(p["fenetre_min"], p["fenetre_max"] + 1))
        self.horizon = 0  # groupe d'horizon d'attention (attribué par le marché)
        self.echelle = p["echelle_tendance"] * self.rng.uniform(0.5, 1.5)
        self.proba_marche = p["proba_ordre_marche"]
        self.taille_max = p["taille_max_ordre"]
        self.duree = p["duree_ordre"]

    def agir(self, t: int, marche: "Marche") -> None:
        tendance = marche.rendement(self.fenetre)
        if tendance is None:
            return
        self.annuler_tout(marche)
        if abs(tendance) < marche.zone_morte:
            return
        prix = marche.prix_reference()
        cote, quantite = self.viser(tendance / self.echelle)
        quantite = self.quantite_autorisee(cote, quantite, prix)
        if self.rng.random() < self.proba_marche:
            marche.envoyer_marche(self, cote, quantite)
        else:
            # Prêt à payer un peu plus (ou vendre un peu moins cher) pour suivre le mouvement.
            prix_limite = prix * math.exp(cote * abs(tendance) * 0.5)
            marche.envoyer_limite(self, cote, prix_limite, quantite, self.duree)


class Bruiteur(Agent):
    """Trader non informé : direction aléatoire, prix proche du marché."""

    type_nom = "Bruiteur"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        p = kwargs["p"]
        self.proba_marche = p["proba_ordre_marche"]
        self.dispersion = p["dispersion_prix"]
        self.taille = p["taille_ordre"]
        self.duree = p["duree_ordre"]

    def agir(self, t: int, marche: "Marche") -> None:
        prix = marche.prix_reference()
        cote = ACHAT if self.rng.random() < 0.5 else VENTE
        quantite = self.quantite_autorisee(cote, int(self.rng.integers(1, self.taille + 1)), prix)
        if self.rng.random() < self.proba_marche:
            marche.envoyer_marche(self, cote, quantite)
        else:
            # Décalage positif = ordre passif (en retrait du marché).
            decalage = self.rng.normal(self.dispersion, self.dispersion)
            prix_limite = prix * math.exp(-cote * decalage)
            marche.envoyer_limite(self, cote, prix_limite, quantite, self.duree)


class TeneurDeMarche(Agent):
    """Cote en permanence un prix d'achat et de vente autour du prix de marché.

    - Le spread s'élargit quand la volatilité monte (protection contre le risque).
    - Les prix sont décalés selon le stock détenu (skew) pour revenir à l'équilibre.
    - Au-delà de sa limite de stock, il ne cote plus que d'un côté.
    """

    type_nom = "Teneur de marché"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        p = kwargs["p"]
        self.demi_spread_min = p["demi_spread_min"]
        self.demi_spread_max = p["demi_spread_max"]
        self.aversion_vol = p["aversion_volatilite"]
        self.skew = p["skew_inventaire"]
        self.taille = p["taille_cotation"]
        self.credit_max = math.inf  # financé par sa banque : seul l'inventaire est borné

    def agir(self, t: int, marche: "Marche") -> None:
        prix = marche.reference_teneurs
        vol = marche.volatilite_recente()
        demi_spread = min(max(self.demi_spread_min + marche.taxe, self.aversion_vol * vol),
                          self.demi_spread_max)
        stock = (self.actions - self.neutre) / self.position_max  # entre -1 et 1
        centre = prix * math.exp(-self.skew * stock)
        bid = centre * math.exp(-demi_spread)
        ask = centre * math.exp(demi_spread)
        marche.envoyer_limite(self, ACHAT, bid, self.quantite_autorisee(ACHAT, self.taille, bid), duree=1)
        marche.envoyer_limite(self, VENTE, ask, self.quantite_autorisee(VENTE, self.taille, ask), duree=1)


class ActeurExterne(Agent):
    """Acteur extérieur des scénarios (fonds en liquidation, raid acheteur) : sans limites."""

    type_nom = "Externe"

    def __init__(self, cash: float = 0.0) -> None:
        super().__init__(-1, cash=cash, actions=0, credit_max=math.inf,
                         rng=None, p={"position_max": 10 ** 12})

    def agir(self, t: int, marche: "Marche") -> None:
        pass


TYPES_AGENTS = {
    "fondamentalistes": Fondamentaliste,
    "chartistes": Chartiste,
    "bruiteurs": Bruiteur,
    "teneurs_de_marche": TeneurDeMarche,
}
