# Où en est le projet

*Dernière mise à jour : 18/11/2026.*

## Fait

- **Phase 1** : moteur Python. Carnet d'ordres, agents, faits stylisés, tableau de bord (`python lancer.py`).
- **Phase 2** : salle des marchés interactive dans le navigateur (`web/salle-des-marches.html`).
  Elle tourne encore avec le modèle de la phase 1 : elle sera mise à jour à la fin.
- **Phase 3** : validation Monte-Carlo sur 20 univers (`python valider.py`, rapport
  [`validation.md`](validation.md)). Mécanismes ajoutés : horizons hétérogènes, aversion aux
  pertes, appels de marge.
- **Phase 4** : expériences de régulation (`python experimenter.py`). Chiffres dans
  [`experiences.md`](experiences.md), interprétation dans [`conclusions-phase4.md`](conclusions-phase4.md).
- **Phase 5** : agents adaptatifs et évolution (`python apprendre.py`). Chiffres dans
  [`apprentissage.md`](apprentissage.md), interprétation dans [`conclusions-phase5.md`](conclusions-phase5.md).
  Les simulations longues ont révélé quatre défauts du modèle, tous corrigés (détails dans
  les conclusions de la phase 5). Tous les rapports ont été régénérés sur le modèle corrigé.

- **Phase 6** : contagion entre trois actifs par des fonds multi-actifs endettés
  (`python contagion.py`). Chiffres dans [`contagion.md`](contagion.md), interprétation dans
  [`conclusions-phase6.md`](conclusions-phase6.md).

## Reste à faire

1. Mettre à jour la salle des marchés (JavaScript) avec le modèle final et vérifier la
   parité avec le moteur Python.

## Points ouverts du modèle

- Indice de queue de Hill ≈ 1,9, contre ≈ 3 dans la réalité : les queues sont encore trop épaisses.
- Mémoire de la volatilité β ≈ 0,8, contre 0,2 à 0,4 dans la réalité. Elle est bonne (≈ 0,4)
  avec des chartistes non endettés, mais on perd alors l'effet de levier : il y a un arbitrage.
- Légère dérive de l'écart prix/valeur sur très longue durée (≈ 0,6 % → 1,4 % sur 100 000 pas).
