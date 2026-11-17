"""Le marché : relie le carnet d'ordres, les agents et la valeur fondamentale."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from .agents import TYPES_AGENTS, Agent, TeneurDeMarche
from .carnet import ACHAT, CarnetOrdres, Transaction


class Marche:
    def __init__(self, config: dict, graine: int | None = None) -> None:
        self.config = config
        self.rng = np.random.default_rng(graine)
        cm = config["marche"]
        self.tick = cm["tick"]
        self.carnet = CarnetOrdres()
        self.t = 0
        self.valeur_fondamentale = cm["prix_initial"]
        self.dernier_prix = cm["prix_initial"]
        self.fenetre_vol = cm["fenetre_volatilite"]
        self.bande_prix = cm["bande_prix"]
        self._vol_cache: tuple[int, float] = (-1, 0.0)
        # Volatilité « normale » de long terme (moyenne mobile exponentielle des r²)
        self._alpha_vol = 1.0 - 0.5 ** (1.0 / cm["memoire_volatilite"])
        self._var_longue: float | None = None

        # Historique (une valeur par pas de temps)
        self.hist_prix: list[float] = [self.dernier_prix]
        self.hist_fondamental: list[float] = [self.valeur_fondamentale]
        self.hist_spread: list[float] = [math.nan]
        self.hist_volume: list[int] = [0]
        self.hist_attention: list[float] = [1.0]
        self.hist_news: list[tuple[int, float]] = []
        self.hist_richesse: dict[str, list[float]] = defaultdict(list)
        self.hist_richesse_t: list[int] = []
        self._volume_pas = 0

        self._creer_agents(config)

    # ----------------------------------------------------------- population
    def _creer_agents(self, config: dict) -> None:
        cm = config["marche"]
        self.agents: list[Agent] = []
        for cle, classe in TYPES_AGENTS.items():
            p = config["agents"][cle]
            for _ in range(p["nombre"]):
                agent = classe(len(self.agents), cash=cm["cash_initial"],
                               actions=cm["actions_initiales"],
                               credit_max=cm["credit_max"], rng=self.rng, p=p)
                self.agents.append(agent)
        self.teneurs = [a for a in self.agents if isinstance(a, TeneurDeMarche)]
        self.traders = [a for a in self.agents if not isinstance(a, TeneurDeMarche)]
        self.groupes = {cle: [a for a in self.traders if isinstance(a, classe)]
                        for cle, classe in TYPES_AGENTS.items() if classe is not TeneurDeMarche}
        self.types = list(dict.fromkeys(a.type_nom for a in self.agents))

    # ---------------------------------------------- informations pour agents
    def prix_reference(self) -> float:
        """Milieu de fourchette si le carnet est des deux côtés, sinon dernier prix."""
        bid = self.carnet.meilleur_achat(self.t)
        ask = self.carnet.meilleure_vente(self.t)
        if bid and ask:
            return 0.5 * (bid.prix + ask.prix) * self.tick
        return self.dernier_prix

    def rendement(self, fenetre: int) -> float | None:
        if len(self.hist_prix) <= fenetre:
            return None
        return math.log(self.hist_prix[-1] / self.hist_prix[-1 - fenetre])

    def volatilite_recente(self) -> float:
        """Écart-type des rendements par pas sur la fenêtre récente."""
        if self._vol_cache[0] == self.t:
            return self._vol_cache[1]
        prix = np.asarray(self.hist_prix[-self.fenetre_vol - 1:])
        vol = float(np.std(np.diff(np.log(prix)))) if len(prix) > 2 else 0.0
        self._vol_cache = (self.t, vol)
        return vol

    def stress(self) -> float:
        """Volatilité récente rapportée à la volatilité normale (1 = marché calme habituel)."""
        if not self._var_longue or self.t < 2 * self.fenetre_vol:
            return 1.0
        return self.volatilite_recente() / math.sqrt(self._var_longue)

    def _maj_volatilite_longue(self) -> None:
        r2 = math.log(self.hist_prix[-1] / self.hist_prix[-2]) ** 2
        # Au démarrage : simple moyenne (pas d'historique), puis moyenne exponentielle.
        alpha = max(self._alpha_vol, 1.0 / self.t)
        self._var_longue = r2 if self._var_longue is None else \
            self._var_longue + alpha * (r2 - self._var_longue)

    # ------------------------------------------------------ passage d'ordres
    def envoyer_limite(self, agent: Agent, cote: int, prix: float,
                       quantite: int, duree: int) -> None:
        if quantite <= 0 or not math.isfinite(prix):
            return
        # Bande de prix (comme sur Euronext) : un ordre trop loin du marché est ramené à la borne.
        reference = self.prix_reference()
        prix = min(max(prix, reference * math.exp(-self.bande_prix)),
                   reference * math.exp(self.bande_prix))
        # Arrondi au tick, toujours en faveur de l'agent (plus prudent).
        ticks = math.floor(prix / self.tick) if cote == ACHAT else math.ceil(prix / self.tick)
        ordre, transactions = self.carnet.ordre_limite(agent.id, cote, max(ticks, 1),
                                                       quantite, self.t, duree)
        self._regler(transactions)
        if ordre is not None:
            agent.ordres.append(ordre.id)

    def envoyer_marche(self, agent: Agent, cote: int, quantite: int) -> None:
        self._regler(self.carnet.ordre_marche(agent.id, cote, quantite, self.t))

    def _regler(self, transactions: list[Transaction]) -> None:
        """Règlement-livraison immédiat : cash contre titres."""
        for tr in transactions:
            montant = tr.prix * self.tick * tr.quantite
            acheteur, vendeur = self.agents[tr.acheteur], self.agents[tr.vendeur]
            acheteur.cash -= montant
            acheteur.actions += tr.quantite
            vendeur.cash += montant
            vendeur.actions -= tr.quantite
            self.dernier_prix = tr.prix * self.tick
            self._volume_pas += tr.quantite

    # ------------------------------------------------------------ dynamique
    def _evoluer_fondamental(self) -> None:
        cf = self.config["fondamental"]
        choc = self.rng.normal(0.0, cf["volatilite"])
        if self.rng.random() < cf["proba_news"]:
            news = self.rng.normal(0.0, cf["amplitude_news"])
            choc += news
            self.hist_news.append((self.t, news))
        self.valeur_fondamentale *= math.exp(choc)

    def pas(self) -> None:
        self.t += 1
        self._volume_pas = 0
        self._evoluer_fondamental()

        # Les teneurs de marché retirent d'abord toutes leurs cotations, puis lisent
        # le carnet « réel » : sinon ils coteraient autour de leurs propres prix
        # et se courraient après (dérive à cliquet).
        for teneur in self.teneurs:
            teneur.annuler_tout(self)
        self.reference_teneurs = self.prix_reference()
        for teneur in self.teneurs:
            teneur.agir(self.t, self)

        # Qui agit à ce pas ? Chaque type a sa fréquence propre ; les types dotés
        # d'« attention » s'activent davantage quand le marché est agité.
        stress = self.stress()
        ecart = math.log(self.prix_reference() / self.valeur_fondamentale)
        multiplicateur = 1.0
        actifs: list[Agent] = []
        for cle, groupe in self.groupes.items():
            p = self.config["agents"][cle]
            intensite = p["activite"]
            if p.get("attention", 0.0) > 0:
                multiplicateur = min(1.0 + p["attention"] * max(stress - 1.0, 0.0),
                                     p["attention_max"])
                intensite *= multiplicateur
            if p.get("reactivite_ecart", 0.0) > 0:
                # Plus le titre est mal valorisé, plus les investisseurs « value » se ruent.
                intensite *= 1.0 + p["reactivite_ecart"] * abs(ecart) / p["echelle_ecart"]
            n = self.rng.poisson(intensite)
            actifs.extend(groupe[i] for i in self.rng.integers(0, len(groupe), size=n))
        for i in self.rng.permutation(len(actifs)):
            actifs[i].agir(self.t, self)

        bid = self.carnet.meilleur_achat(self.t)
        ask = self.carnet.meilleure_vente(self.t)
        self.hist_prix.append(self.prix_reference())
        self.hist_fondamental.append(self.valeur_fondamentale)
        self.hist_spread.append((ask.prix - bid.prix) * self.tick if bid and ask else math.nan)
        self.hist_volume.append(self._volume_pas)
        self.hist_attention.append(multiplicateur)
        self._maj_volatilite_longue()

        if self.t % self.config["marche"]["frequence_bilan"] == 0:
            self._bilan()

    def _bilan(self) -> None:
        prix = self.hist_prix[-1]
        par_type: dict[str, list[float]] = defaultdict(list)
        for a in self.agents:
            par_type[a.type_nom].append(a.richesse(prix))
        self.hist_richesse_t.append(self.t)
        for nom in self.types:
            self.hist_richesse[nom].append(float(np.mean(par_type[nom])))

    def executer(self, n_pas: int, progression=None) -> None:
        for k in range(n_pas):
            self.pas()
            if progression and (k + 1) % max(n_pas // 20, 1) == 0:
                progression(k + 1, n_pas)

    # ---------------------------------------------------------- résultats
    def series(self) -> dict[str, np.ndarray]:
        return {
            "prix": np.asarray(self.hist_prix),
            "fondamental": np.asarray(self.hist_fondamental),
            "spread": np.asarray(self.hist_spread),
            "volume": np.asarray(self.hist_volume),
            "attention": np.asarray(self.hist_attention),
        }
