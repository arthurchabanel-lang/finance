"""Le marché : relie le carnet d'ordres, les agents et la valeur fondamentale.

Mécanismes (voir config.toml) :
- attention des chartistes, répartis en groupes d'horizons différents (court, moyen,
  long terme) et plus sensibles aux baisses qu'aux hausses (aversion aux pertes) ;
- réactivité des fondamentalistes à l'écart de valorisation ;
- appels de marge : un fonds dont le capital recule trop par rapport à son plus haut
  doit couper sa position au marché, puis reste suspendu un moment ;
- régulations optionnelles : taxe sur les transactions, coupe-circuit,
  interdiction de la vente à découvert.
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from .agents import TYPES_AGENTS, Agent, TeneurDeMarche
from .carnet import ACHAT, VENTE, CarnetOrdres, Transaction

REGULATION_PAR_DEFAUT = {
    "taxe_transaction": 0.0,          # ex. 0.001 = 0,1 % payé par chaque partie
    "sensibilite_bruiteurs": 0.001,   # coût qui divise par e l'activité des bruiteurs
    "coupe_circuit_seuil": 0.0,       # ex. 0.05 : arrêt si le prix bouge de 5 %...
    "coupe_circuit_fenetre": 200,     # ... sur cette fenêtre (pas)
    "coupe_circuit_duree": 100,       # durée de l'arrêt (pas)
    "interdiction_vente_decouvert": False,
}
MARGE_PAR_DEFAUT = {"actif": False}


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

        # Volatilités moyennes mobiles exponentielles (EMA des r²) : une de référence
        # (long terme) et une par horizon d'attention des chartistes.
        self._demi_vie_ref = cm["memoire_volatilite"]
        pc = config["agents"]["chartistes"]
        self.horizons = list(pc.get("horizons_attention", [cm["fenetre_volatilite"]]))
        self._var: dict[int, float | None] = {h: None for h in [self._demi_vie_ref, *self.horizons]}
        self._ema_r: dict[int, float] = {h: 0.0 for h in self.horizons}  # tendance par horizon

        # Régulation
        self.reg = {**REGULATION_PAR_DEFAUT, **config.get("regulation", {})}
        self.taxe = self.reg["taxe_transaction"]
        self.zone_morte = 2.0 * self.taxe  # un trade doit rapporter plus que l'aller-retour
        self.arret_jusqua = -1
        self.marge = {**MARGE_PAR_DEFAUT, **config.get("marge", {})}

        # Historique (une valeur par pas de temps)
        self.hist_prix: list[float] = [self.dernier_prix]
        self.hist_fondamental: list[float] = [self.valeur_fondamentale]
        self.hist_spread: list[float] = [math.nan]
        self.hist_volume: list[int] = [0]
        self.hist_attention: list[float] = [1.0]
        self.hist_news: list[tuple[int, float]] = []
        self.hist_appels: list[tuple[int, int]] = []     # (pas, nombre d'appels de marge)
        self.hist_arrets: list[int] = []                 # pas où un coupe-circuit se déclenche
        self.hist_richesse: dict[str, list[float]] = defaultdict(list)
        self.hist_richesse_t: list[int] = []
        self.taxes_collectees = 0.0
        self.capital_injecte = 0.0                       # apports des fonds qui remplacent les faillis
        self.hist_faillites: list[tuple[int, str]] = []
        self._volume_pas = 0
        self.scenario: dict | None = None

        self._creer_agents(config)
        # Apprentissage (phase 5) : score récent de chaque stratégie et évolution des paramètres
        ca = config.get("apprentissage", {})
        self.intensite_choix = ca.get("intensite_choix", 0.0)
        self._alpha_score = 1.0 - 0.5 ** (1.0 / ca.get("memoire_scores", 2000))
        self.score = {"fondamentaliste": 0.0, "chartiste": 0.0}
        self._signaux = (0.0, 0.0)
        self.hist_part_fondamentaliste: list[float] = []
        self.evolution = config.get("evolution", {"actif": False})
        self.hist_evolution: list[dict] = []
        self.strategique = config.get("acheteur_strategique", {"actif": False})
        if self.strategique["actif"]:
            from .agents import ActeurExterne
            self.acheteur = self.ajouter_agent(ActeurExterne())
            self.acheteur.type_nom = "Acheteur stratégique"

    # ----------------------------------------------------------- population
    def _creer_agents(self, config: dict) -> None:
        cm = config["marche"]
        self.agents: list[Agent] = []
        for cle, classe in TYPES_AGENTS.items():
            p = config["agents"].get(cle, {"nombre": 0})
            for _ in range(p["nombre"]):
                agent = classe(len(self.agents), cash=p.get("cash_initial", cm["cash_initial"]),
                               actions=cm["actions_initiales"],
                               credit_max=p.get("credit_max", cm["credit_max"]), rng=self.rng, p=p)
                agent.plus_haut = agent.richesse(cm["prix_initial"])
                if self.reg["interdiction_vente_decouvert"] and not isinstance(agent, TeneurDeMarche):
                    agent.plancher_reglementaire = 0
                self.agents.append(agent)
        self.teneurs = [a for a in self.agents if isinstance(a, TeneurDeMarche)]
        self.traders = [a for a in self.agents if not isinstance(a, TeneurDeMarche)]
        self.groupes = {cle: [a for a in self.traders if isinstance(a, classe)]
                        for cle, classe in TYPES_AGENTS.items() if classe is not TeneurDeMarche}
        chartistes = self.groupes.pop("chartistes")
        for i, a in enumerate(chartistes):
            a.horizon = i % len(self.horizons)
        self.groupes_chartistes = [[a for a in chartistes if a.horizon == k]
                                   for k in range(len(self.horizons))]
        self.soumis_marge = [a for a in self.traders
                             if a.type_nom in self.marge.get("types", [])] if self.marge["actif"] else []
        self.types = list(dict.fromkeys(a.type_nom for a in self.agents))
        for a in self.agents:
            a.richesse_debut = a.capital_initial = a.richesse(cm["prix_initial"])

    # ------------------------------------------------------- apprentissage
    def proba_fondamentaliste(self) -> float:
        """Probabilité logit (Brock et Hommes) de jouer la stratégie fondamentaliste."""
        ref = self._var[self._demi_vie_ref]
        # Période d'observation : pas d'apprentissage tant que les scores n'ont pas d'historique.
        if not ref or self.t < 1.0 / self._alpha_score:
            return 0.5
        # Écart de score en « t-statistique » : rapporté à la volatilité et à la longueur de la
        # mémoire. d = 2 signifie qu'une stratégie bat nettement l'autre ces derniers temps.
        d = (self.score["fondamentaliste"] - self.score["chartiste"]) / math.sqrt(ref) \
            * math.sqrt(1.0 / self._alpha_score)
        return 1.0 / (1.0 + math.exp(-max(min(self.intensite_choix * d, 50.0), -50.0)))

    def _maj_scores(self) -> None:
        """Gain du dernier pas d'un portefeuille qui suit chaque stratégie (signal en [-1, 1])."""
        r = math.log(self.hist_prix[-1] / self.hist_prix[-2])
        sf, sc = self._signaux
        a = self._alpha_score
        self.score["fondamentaliste"] += a * (sf * r - self.score["fondamentaliste"])
        self.score["chartiste"] += a * (sc * r - self.score["chartiste"])
        tendance = self.rendement(100) or 0.0
        self._signaux = (math.tanh(math.log(self.valeur_fondamentale / self.hist_prix[-1]) / 0.03),
                         math.tanh(tendance / 0.03))

    def _evoluer(self) -> None:
        """Sélection : les moins performants copient (avec mutation) les plus performants."""
        ev = self.evolution
        prix = self.hist_prix[-1]
        cliche = {"t": self.t}
        for nom, genes in (("Fondamentaliste", ("biais", "echelle", "agressivite")),
                           ("Chartiste", ("fenetre", "echelle"))):
            groupe = [a for a in self.traders if a.type_nom == nom]
            if len(groupe) < 10:
                continue
            perf = np.array([(a.richesse(prix) - a.richesse_debut) / abs(a.richesse_debut)
                             for a in groupe])
            ordre = np.argsort(perf)
            n_out = int(len(groupe) * ev["part_remplacee"])
            modeles = ordre[-int(len(groupe) * ev["part_modeles"]):]
            mu = ev["mutation"]
            for i in ordre[:n_out]:
                perdant, modele = groupe[i], groupe[int(self.rng.choice(modeles))]
                for g in genes:
                    setattr(perdant, g, getattr(modele, g))
                perdant.echelle *= math.exp(self.rng.normal(0.0, mu))
                if nom == "Fondamentaliste":
                    perdant.biais += self.rng.normal(0.0, mu * 0.01)
                    perdant.agressivite = min(max(perdant.agressivite + self.rng.normal(0.0, mu * 0.2), 0.0), 1.0)
                else:
                    perdant.fenetre = int(min(max(round(perdant.fenetre * math.exp(self.rng.normal(0.0, mu))), 2), 2000))
            for g in genes:
                cliche[f"{nom}.{g}"] = np.array([getattr(a, g) for a in groupe], dtype=float)
        for a in self.agents:
            a.richesse_debut = a.richesse(prix)
        self.hist_evolution.append(cliche)

    def ajouter_agent(self, agent: Agent) -> Agent:
        """Ajoute un acteur extérieur (scénarios, fonds multi-actifs) hors des groupes."""
        agent.id = len(self.agents)
        self.agents.append(agent)
        return agent

    # ---------------------------------------------- informations pour agents
    def prix_reference(self) -> float:
        """Milieu de fourchette si le carnet est des deux côtés.

        Sinon, le dernier prix échangé, mais jamais sous la meilleure offre d'achat ni au-dessus
        de la meilleure offre de vente : un carnet sans vendeurs où des acheteurs offrent plus
        que le dernier cours ne doit pas geler le prix (bug corrigé en phase 5).
        """
        bid = self.carnet.meilleur_achat(self.t)
        ask = self.carnet.meilleure_vente(self.t)
        if bid and ask:
            return 0.5 * (bid.prix + ask.prix) * self.tick
        if bid:
            return max(self.dernier_prix, bid.prix * self.tick)
        if ask:
            return min(self.dernier_prix, ask.prix * self.tick)
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

    def stress(self, horizon: int | None = None) -> float:
        """Volatilité récente rapportée à la normale de long terme (1 = calme habituel).

        Sans horizon : fenêtre glissante courte (affichage, régime de marché).
        Avec horizon : volatilité EMA de cette demi-vie (attention des chartistes).
        """
        ref = self._var[self._demi_vie_ref]
        if not ref or self.t < 2 * self.fenetre_vol:
            return 1.0
        if horizon is None:
            return self.volatilite_recente() / math.sqrt(ref)
        return math.sqrt(self._var[horizon] / ref)

    def _maj_volatilites(self) -> None:
        r = math.log(self.hist_prix[-1] / self.hist_prix[-2])
        for h, v in self._var.items():
            # Au démarrage : simple moyenne (pas d'historique), puis moyenne exponentielle.
            alpha = max(1.0 - 0.5 ** (1.0 / h), 1.0 / self.t)
            self._var[h] = r * r if v is None else v + alpha * (r * r - v)
            if h in self._ema_r:
                self._ema_r[h] += alpha * (r - self._ema_r[h])

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
        """Règlement-livraison immédiat : cash contre titres (moins la taxe éventuelle)."""
        for tr in transactions:
            montant = tr.prix * self.tick * tr.quantite
            acheteur, vendeur = self.agents[tr.acheteur], self.agents[tr.vendeur]
            frais = self.taxe * montant
            acheteur.cash -= montant + frais
            acheteur.actions += tr.quantite
            vendeur.cash += montant - frais
            vendeur.actions -= tr.quantite
            self.taxes_collectees += 2 * frais
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

    def choc_fondamental(self, taille_log: float) -> None:
        self.valeur_fondamentale *= math.exp(taille_log)

    def lancer_scenario(self, agent: Agent, cote: int, total: int, par_pas: int = 40) -> None:
        """Un acteur extérieur exécute un gros ordre au marché, par tranches."""
        self.scenario = {"agent": agent, "cote": cote, "restant": total, "par_pas": par_pas}

    def _appels_de_marge(self) -> None:
        """Le courtier vérifie le capital de chaque fonds endetté."""
        m = self.marge
        prix = self.hist_prix[-1]
        n = 0
        # L'appétit pour le risque se reconstitue lentement après un désendettement.
        rappel = 1.0 - 0.5 ** (m["frequence_controle"] / m["demi_vie_reprise"])
        for a in self.soumis_marge:
            a.neutre += rappel * (a.neutre_initial - a.neutre)
            if a.a_liquider:
                continue
            capital = a.richesse(prix)
            if capital > a.plus_haut:
                a.plus_haut = capital
            elif (capital < a.plus_haut * (1.0 - m["seuil_perte"])
                  and (a.cash < 0 or a.actions < 0)):
                # Seules les positions financées par emprunt (cash ou titres empruntés) sont
                # exposées à un appel de marge ; un fonds sans dette n'en reçoit pas.
                # Appel de marge : réduire l'exposition d'une fraction, au marché.
                a.a_liquider = int(round(a.actions * m["reduction"]))
                if a.a_liquider > 0:  # le fonds réduit son exposition cible, dans une limite
                    plancher = a.neutre_initial * (1.0 - m.get("reduction_cible_max", 1.0))
                    a.neutre = max(a.neutre - a.a_liquider, plancher)
                a.annuler_tout(self)
                n += 1
        if n:
            self.hist_appels.append((self.t, n))

    def _liquidations(self) -> None:
        """Exécute les ventes (ou rachats) forcés, par tranches, au marché."""
        m = self.marge
        for a in self.soumis_marge:
            if not a.a_liquider:
                continue
            cote = VENTE if a.a_liquider > 0 else ACHAT
            avant = a.actions
            self.envoyer_marche(a, cote, min(abs(a.a_liquider), m["tranche_liquidation"]))
            a.a_liquider += a.actions - avant  # se rapproche de 0 (reste si pas de contrepartie)
            if a.a_liquider == 0:
                a.suspendu_jusqua = self.t + int(self.rng.exponential(m["duree_suspension"]))
                a.plus_haut = a.richesse(self.hist_prix[-1])

    def _coupe_circuit(self) -> bool:
        """Renvoie True si la cotation est suspendue à ce pas."""
        if self.t < self.arret_jusqua:
            return True
        seuil, fen = self.reg["coupe_circuit_seuil"], self.reg["coupe_circuit_fenetre"]
        if seuil > 0 and len(self.hist_prix) > fen and self.t >= self.arret_jusqua + fen:
            if abs(math.log(self.hist_prix[-1] / self.hist_prix[-1 - fen])) > seuil:
                self.arret_jusqua = self.t + self.reg["coupe_circuit_duree"]
                self.hist_arrets.append(self.t)
                for a in self.agents:
                    a.annuler_tout(self)
                return True
        return False

    def _intensite_chartistes(self, horizon: int) -> float:
        pc = self.config["agents"]["chartistes"]
        surchauffe = max(self.stress(horizon) - 1.0, 0.0)
        if self._ema_r[horizon] < 0:  # le marché baisse : la peur amplifie l'attention
            surchauffe *= 1.0 + pc.get("aversion_pertes", 0.0)
        return min(1.0 + pc["attention"] * surchauffe, pc["attention_max"])

    def pas(self) -> None:
        self.t += 1
        self._volume_pas = 0
        self._evoluer_fondamental()
        multiplicateur = 1.0

        if not self._coupe_circuit():
            # Les teneurs de marché retirent d'abord toutes leurs cotations, puis lisent
            # le carnet « réel » : sinon ils coteraient autour de leurs propres prix
            # et se courraient après (dérive à cliquet).
            for teneur in self.teneurs:
                teneur.annuler_tout(self)
            self.reference_teneurs = self.prix_reference()
            for teneur in self.teneurs:
                teneur.agir(self.t, self)

            if self.scenario:
                sc = self.scenario
                q = min(sc["par_pas"], sc["restant"])
                self.envoyer_marche(sc["agent"], sc["cote"], q)
                sc["restant"] -= q
                if sc["restant"] <= 0:
                    self.scenario = None

            if self.marge["actif"]:
                self._liquidations()

            # Acheteur de dernier ressort : sous une forte décote, une OPA devient rentable.
            if self.strategique["actif"]:
                ref = self.prix_reference()
                plafond = self.strategique["decote"] * self.valeur_fondamentale
                if ref < plafond:
                    self.acheteur.annuler_tout(self)
                    self.envoyer_limite(self.acheteur, ACHAT, plafond,
                                        self.strategique["titres_par_pas"], duree=1)

            # Qui agit à ce pas ? Chaque type a sa fréquence propre.
            ecart = math.log(self.prix_reference() / self.valeur_fondamentale)
            actifs: list[Agent] = []

            def tirer(groupe: list[Agent], intensite: float) -> None:
                n = self.rng.poisson(intensite)
                actifs.extend(groupe[i] for i in self.rng.integers(0, len(groupe), size=n))

            pf = self.config["agents"]["fondamentalistes"]
            tirer(self.groupes["fondamentalistes"],
                  pf["activite"] * (1.0 + pf["reactivite_ecart"] * abs(ecart) / pf["echelle_ecart"]))
            if self.groupes.get("adaptatifs"):
                tirer(self.groupes["adaptatifs"], self.config["agents"]["adaptatifs"]["activite"])
            pb = self.config["agents"]["bruiteurs"]
            tirer(self.groupes["bruiteurs"],
                  pb["activite"] * math.exp(-self.taxe / self.reg["sensibilite_bruiteurs"]))
            pc = self.config["agents"]["chartistes"]
            mults = []
            for k, h in enumerate(self.horizons):
                mult = self._intensite_chartistes(h)
                mults.append(mult)
                tirer(self.groupes_chartistes[k], pc["activite"] / len(self.horizons) * mult)
            multiplicateur = float(np.mean(mults))

            for i in self.rng.permutation(len(actifs)):
                a = actifs[i]
                if a.a_liquider or self.t < a.suspendu_jusqua:
                    continue  # en cours de liquidation ou suspendu par son courtier
                a.agir(self.t, self)

        bid = self.carnet.meilleur_achat(self.t)
        ask = self.carnet.meilleure_vente(self.t)
        self.hist_prix.append(self.prix_reference())
        self.hist_fondamental.append(self.valeur_fondamentale)
        self.hist_spread.append((ask.prix - bid.prix) * self.tick if bid and ask else math.nan)
        self.hist_volume.append(self._volume_pas)
        self.hist_attention.append(multiplicateur)
        self._maj_volatilites()
        self._maj_scores()
        if self.groupes.get("adaptatifs"):
            self.hist_part_fondamentaliste.append(self.proba_fondamentaliste())
        if self.evolution["actif"] and self.t % self.evolution["periode"] == 0:
            self._evoluer()

        if self.marge["actif"] and self.t % self.marge["frequence_controle"] == 0:
            self._appels_de_marge()
        if self.t % self.config["marche"]["frequence_bilan"] == 0:
            self._faillites()
            self._bilan()

    def _faillites(self) -> None:
        """Un trader dont le capital tombe sous le seuil ferme ; un nouveau fonds reprend son
        portefeuille avec des capitaux frais (les titres sont conservés, l'apport est compté)."""
        seuil = self.config["marche"].get("seuil_faillite", 0.0)
        if seuil <= 0:
            return
        prix = self.hist_prix[-1]
        cm = self.config["marche"]
        for a in self.traders:
            capital_initial = a.capital_initial
            capital = a.richesse(prix)
            if capital < seuil * capital_initial:
                apport = capital_initial - capital
                a.cash += apport
                self.capital_injecte += apport
                a.neutre = a.neutre_initial
                a.a_liquider = 0
                a.suspendu_jusqua = -1
                a.plus_haut = capital_initial
                a.richesse_debut = capital_initial
                self.hist_faillites.append((self.t, a.type_nom))

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
