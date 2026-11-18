# Où en est le projet

*Dernière mise à jour : 17/11/2026, fin de session.*

## Fait

- **Phase 1** : moteur Python. Carnet d'ordres, 4 types d'agents, faits stylisés, tableau de bord (`python lancer.py`).
- **Phase 2** : salle des marchés interactive dans le navigateur (`web/salle-des-marches.html`).
  Elle tourne encore avec le modèle de la phase 1 : elle sera mise à jour à la fin.
- **Phase 3** : validation Monte-Carlo sur 20 univers (`python valider.py`, rapport dans
  [`validation.md`](validation.md)). Trois mécanismes ont été ajoutés : horizons
  hétérogènes, aversion aux pertes, appels de marge.
- **Corrections apparues pendant la phase 4** :
  - la limite des investisseurs value est désormais exprimée en euros et non plus en titres ;
  - un acheteur stratégique (OPA) intervient sous 50 % de la valeur.

  Sans ces deux corrections, le prix pouvait s'effondrer jusqu'à 0,01 € dans certains univers.

## En cours : phase 4, expériences de régulation

`python experimenter.py` lance 6 politiques × 20 univers appariés, plus un stress test de
liquidation. Les résultats sont dans [`experiences.md`](experiences.md), et leur interprétation dans [`conclusions-phase4.md`](conclusions-phase4.md).

**Premiers résultats, à analyser et à vérifier avant d'en tirer des conclusions :**
- **Taxe 0,1 %** : la fourchette double et le volume baisse de 22 %, sans gain de stabilité significatif.
- **Interdiction de la vente à découvert** : la chute pendant la liquidation est réduite de 65 %.
  Hypothèse à vérifier : dans la référence, les chartistes vendent à découvert dans le
  mouvement et amplifient la chute.
- **Crédit restreint pour tous** : volatilité +55 %, pire chute +53 %. C'est la spirale de
  liquidité : les investisseurs value n'ont plus les moyens d'absorber les ventes forcées.
- **Levier des hedge funds limité** et **coupe-circuit 3 %** : aucun effet significatif sur 20 univers.

## Reste à faire

1. Phase 4 : vérifier les mécanismes derrière les résultats (surtout la vente à découvert),
   puis rédiger l'interprétation.
2. Phase 5 : agents adaptatifs (bascule fondamentaliste/chartiste selon la performance, à la
   Brock et Hommes) et évolution darwinienne des paramètres.
3. Phase 6 : plusieurs actifs, fonds endettés multi-actifs, contagion par les appels de marge.
4. Mettre à jour la salle des marchés (JavaScript) avec le modèle final et vérifier
   la parité avec le moteur Python.

## Points ouverts du modèle

- Indice de queue de Hill ≈ 2,1, contre ≈ 3 dans la réalité : les queues sont encore un peu trop épaisses.
- Mémoire de la volatilité β ≈ 0,6, contre 0,2 à 0,4 dans la réalité.
- Rendements légèrement trop autocorrélés (|ACF| moyenne ≈ 0,13).
