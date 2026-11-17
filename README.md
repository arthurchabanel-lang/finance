# 🏛️ Marché artificiel multi-agents

Simulateur scientifique de marché financier : des centaines d'agents aux stratégies
différentes échangent un titre via un **carnet d'ordres** réaliste. Bulles, krachs,
queues épaisses et volatilité en grappes **émergent** de leurs interactions, sans
être programmés.

## Lancer une simulation

```bash
pip install -r requirements.txt
python lancer.py
```

Résultats dans `resultats/` :
- `tableau_de_bord.png` : les graphiques
- `rapport.txt` : le bilan des faits stylisés
- `series.csv` : prix, valeur fondamentale, spread et volume pas à pas (s'ouvre dans Excel)

Options : `--pas 50000` (durée), `--graine 7` (autre univers aléatoire), `--config fichier.toml`.

**Tous les réglages sont dans `config.toml`**, commentés en français. Exemples d'expériences :
- `chartistes.attention = 0` → la volatilité en grappes disparaît ;
- `fondamentalistes.reactivite_ecart = 0` → les bulles deviennent bien plus violentes ;
- `teneurs_de_marche.nombre = 0` → que devient la liquidité ?

## Les acteurs

| Agent | Stratégie | Rôle dans la dynamique |
|---|---|---|
| **Fondamentaliste** | Surpondère quand le titre est sous sa valeur estimée (biais d'estimation personnel). Se rue d'autant plus que l'écart est grand. | Force de rappel |
| **Chartiste** | Momentum sur sa propre fenêtre (10 à 200 pas). Trade plus souvent quand le marché est agité (*attention*). | Amplificateur |
| **Bruiteur** | Achète ou vend au hasard, près du prix. | Liquidité et bruit |
| **Teneur de marché** | Cote en continu ; élargit la fourchette avec la volatilité ; décale ses prix selon son stock. | Liquidité |

Chaque agent gère une **position active par rapport à un benchmark** (sa dotation
initiale) : cible = neutre ± position_max × tanh(signal), exécutée par tranches, avec
achat sur marge borné.

## Le marché

- Carnet d'ordres à priorité prix-temps, avec ordres limites (avec durée de vie) et
  ordres au marché, au tick de 0,01 €
- Bandes de prix : un ordre limite ne peut s'écarter de plus de 2 % du prix
- Valeur fondamentale : marche aléatoire, plus des news ponctuelles

## Validation scientifique

À chaque lancement, le simulateur vérifie automatiquement les **faits stylisés**
(Cont, 2001) :
1. Queues épaisses (kurtosis, indice de queue de Hill)
2. Queues épaisses **émergentes** : une *expérience témoin* relance le même marché
   sans aucune news (valeur fondamentale gaussienne) ; les queues épaisses doivent persister
3. Rendements quasi imprévisibles (autocorrélation ≈ 0)
4. Volatilité en grappes (autocorrélation des |rendements| > 0)
5. Corrélation volume–volatilité
6. Ancrage du prix sur la valeur fondamentale

Robustesse avec la configuration actuelle : 34 critères réussis sur 36, sur 6 graines aléatoires
(les échecs sont des cas limites : peu de crises dans un univers, autocorrélation à 0,12 pour un seuil de 0,12).

## Phase 2 : la salle des marchés

`web/salle-des-marches.html` est le même moteur, porté en JavaScript. Le marché tourne en
direct dans le navigateur, avec des curseurs de comportement et des crises à provoquer.
Il suffit d'ouvrir le fichier dans un navigateur.

## Phase 3 : validation Monte-Carlo

```bash
python valider.py
```

Ce script fait tourner 20 univers indépendants et confronte le simulateur à 11 faits
stylisés de la littérature, avec intervalles de confiance. Le dernier rapport est dans
[`docs/validation.md`](docs/validation.md).

## Structure du code

```
marche/carnet.py      carnet d'ordres (le moteur de la Bourse)
marche/agents.py      les stratégies
marche/simulation.py  l'horloge du marché, la valeur fondamentale, la comptabilité
marche/analyse.py     les tests statistiques
marche/graphiques.py  le tableau de bord
marche/validation.py  la validation Monte-Carlo (phase 3)
web/                  la salle des marchés interactive (phase 2)
docs/                 rapports de validation
tests/                tests automatiques (python -m pytest)
```

## Mécanismes ajoutés en phase 3

- **Horizons hétérogènes** : les chartistes forment trois groupes (court, moyen et long terme).
  Chaque groupe mesure l'agitation sur sa propre échelle de temps.
- **Aversion aux pertes** : en marché baissier, l'attention des chartistes réagit deux fois plus fort.
- **Appels de marge** : un chartiste (hedge fund endetté) dont le capital recule de 5 % sous son
  plus haut doit couper la moitié de sa position au marché. Il est ensuite suspendu un temps
  aléatoire, et son exposition cible ne se reconstitue que lentement.

Résultat validé sur 20 univers : effet de levier et asymétrie gains/pertes désormais
reproduits, avec des intervalles de confiance qui excluent 0.

## Limites connues

- **Queues trop épaisses** : indice de Hill d'environ 1,8, contre environ 3 sur les actions réelles
- **Mémoire de la volatilité encore un peu courte** : β ≈ 0,75, contre 0,2 à 0,4 sur les marchés réels
- **Appels de marge sur les fondamentalistes** : s'ils y sont aussi soumis, le marché devient
  instable (limites de l'arbitrage, Shleifer et Vishny 1997)
