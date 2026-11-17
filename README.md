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

## Structure du code

```
marche/carnet.py      carnet d'ordres (le moteur de la Bourse)
marche/agents.py      les stratégies
marche/simulation.py  l'horloge du marché, la valeur fondamentale, la comptabilité
marche/analyse.py     les tests statistiques
marche/graphiques.py  le tableau de bord
tests/                tests automatiques (python -m pytest)
```

## Limites connues (prochaines phases)

- Indice de queue de Hill proche de 2, contre environ 3 sur les actions réelles :
  les queues sont un peu *trop* épaisses
- Légère autocorrélation négative des rendements à court terme (effet de sur-réaction)
- Un seul actif, des stratégies fixes (pas encore d'apprentissage)
