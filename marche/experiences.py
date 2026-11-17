"""Phase 4 : expériences de régulation.

Chaque politique est simulée sur les MÊMES univers (mêmes graines, donc mêmes news)
que la référence : la différence mesurée est l'effet de la politique, pas du hasard
(plan apparié, « common random numbers »).

Deux protocoles :
1. Marché normal : 30 000 pas, mesures de stabilité, d'efficience et de liquidité.
2. Stress test : au pas STRESS_T, un fonds liquide 4 000 titres au marché en urgence ;
   on mesure la chute et le temps de récupération.
"""

from __future__ import annotations

import copy
import math
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .agents import ActeurExterne
from .analyse import kurtosis_excedentaire, rendements
from .carnet import VENTE
from .simulation import Marche

POLITIQUES: dict[str, dict] = {
    "Référence": {},
    "Taxe 0,1 %": {"regulation.taxe_transaction": 0.001},
    "Coupe-circuit 3 %": {"regulation.coupe_circuit_seuil": 0.03},
    "Vente à découvert interdite": {"regulation.interdiction_vente_decouvert": True},
    "Levier des hedge funds limité": {"agents.chartistes.credit_max": 2000.0},
    "Crédit restreint pour tous": {"marche.credit_max": 2000.0},
}
DESCRIPTIONS = {
    "Référence": "aucune régulation",
    "Taxe 0,1 %": "chaque partie paie 0,1 % du montant échangé (taxe de type Tobin)",
    "Coupe-circuit 3 %": "cotation suspendue 100 pas si le prix bouge de plus de 3 % en 200 pas",
    "Vente à découvert interdite": "aucun agent (hors teneurs de marché) ne peut détenir moins de 0 titre",
    "Levier des hedge funds limité": "découvert des chartistes (hedge funds) réduit de 10 000 € à 2 000 €",
    "Crédit restreint pour tous": "découvert de tous les agents réduit de 10 000 € à 2 000 € (y compris les investisseurs value)",
}

HORIZON = 50
ECHAUFFEMENT = 1000
SEUIL_KRACH = -0.03       # un rendement sur 50 pas inférieur à -3 % compte comme un krach
STRESS_T = 12000          # début de la liquidation forcée
STRESS_TITRES = 4000
STRESS_FIN = STRESS_T + 4000


def appliquer(config: dict, surcharges: dict) -> dict:
    c = copy.deepcopy(config)
    for cle, v in surcharges.items():
        *chemin, champ = cle.split(".")
        d = c
        for k in chemin:
            d = d.setdefault(k, {})
        d[champ] = v
    return c


def chute_max(prix: np.ndarray) -> float:
    """Plus forte baisse depuis un plus haut (max drawdown), en log."""
    lp = np.log(prix)
    return float(np.max(np.maximum.accumulate(lp) - lp))


def mesures_normales(m: Marche) -> dict[str, float]:
    s = m.series()
    prix, fond = s["prix"][ECHAUFFEMENT:], s["fondamental"][ECHAUFFEMENT:]
    r = rendements(prix, HORIZON)
    return {
        "volatilite": float(r.std()),
        "kurtosis": kurtosis_excedentaire(r),
        "krachs": float(np.sum(r < SEUIL_KRACH)),
        "chute_max": chute_max(prix),
        "inefficience": float(np.mean(np.abs(np.log(prix / fond)))),
        "spread": float(np.nanmean(s["spread"][ECHAUFFEMENT:])),
        "volume": float(np.mean(s["volume"][ECHAUFFEMENT:])),
        "appels_marge": float(sum(n for _, n in m.hist_appels)),
        "arrets": float(len(m.hist_arrets)),
    }


def mesures_stress(m: Marche) -> dict:
    prix = np.asarray(m.hist_prix)
    avant = float(np.mean(prix[STRESS_T - 200:STRESS_T]))
    fenetre = prix[STRESS_T:STRESS_FIN]
    creux = int(np.argmin(fenetre))
    chute = math.log(avant / fenetre[creux])
    # Récupération : premier pas après le creux où le prix revient à 1 % de son niveau d'avant.
    apres = fenetre[creux:]
    revenu = np.nonzero(apres >= avant * 0.99)[0]
    recuperation = float(creux + revenu[0]) if len(revenu) else math.nan
    return {
        "chute_stress": chute,
        "recuperation": recuperation,
        "trajectoire": (prix[STRESS_T - 500:STRESS_FIN] / avant).astype(np.float32),
    }


def _une_simulation(args) -> tuple[str, int, dict]:
    nom, config, graine, n_pas = args
    m = Marche(config, graine)
    m.executer(n_pas)
    res = mesures_normales(m)
    # Stress test : même univers, avec la liquidation forcée.
    ms = Marche(config, graine)
    externe = ms.ajouter_agent(ActeurExterne())
    ms.executer(STRESS_T)
    ms.lancer_scenario(externe, VENTE, STRESS_TITRES, par_pas=40)
    ms.executer(STRESS_FIN - STRESS_T)
    res.update(mesures_stress(ms))
    return nom, graine, res


def experimenter(config: dict, n_univers: int = 20, n_pas: int = 30000, graine0: int = 2000,
                 politiques: dict[str, dict] | None = None, progression=None) -> dict:
    politiques = politiques or POLITIQUES
    taches = [(nom, appliquer(config, surch), graine0 + i, n_pas)
              for nom, surch in politiques.items() for i in range(n_univers)]
    resultats: dict[str, dict[int, dict]] = {nom: {} for nom in politiques}
    with ProcessPoolExecutor() as pool:
        for k, (nom, graine, res) in enumerate(pool.map(_une_simulation, taches), 1):
            resultats[nom][graine] = res
            if progression:
                progression(k, len(taches))
    return resultats


def comparer(resultats: dict, cle: str, nom: str, reference: str = "Référence") -> dict:
    """Différence appariée politique − référence, en % de la référence, avec IC 95 %."""
    graines = sorted(resultats[reference])
    ref = np.array([resultats[reference][g][cle] for g in graines], dtype=float)
    pol = np.array([resultats[nom][g][cle] for g in graines], dtype=float)
    ok = ~(np.isnan(ref) | np.isnan(pol))
    ref, pol = ref[ok], pol[ok]
    base = float(np.mean(ref))
    diff = pol - ref
    if len(diff) < 2 or base == 0:
        return {"ref": base, "pol": float(np.mean(pol)) if len(pol) else math.nan,
                "effet": math.nan, "ic": (math.nan, math.nan), "n": int(ok.sum())}
    demi = 1.96 * diff.std(ddof=1) / math.sqrt(len(diff))
    return {
        "ref": base, "pol": float(np.mean(pol)),
        "effet": 100 * diff.mean() / abs(base),
        "ic": (100 * (diff.mean() - demi) / abs(base), 100 * (diff.mean() + demi) / abs(base)),
        "n": int(ok.sum()),
    }
