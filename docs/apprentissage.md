# Phase 5 : des agents qui apprennent

*Généré le 18/11/2026 par `python apprendre.py`.*

## Expérience A : agents adaptatifs (Brock et Hommes 1998)

100 agents adaptatifs remplacent 50 fondamentalistes et 50 chartistes. Avant chaque décision, ils choisissent leur stratégie avec une probabilité logit fondée sur le score récent des deux stratégies (demi-vie de 2 000 pas). 12 univers par intensité, 30 000 pas.

| Intensité | Part en mode chartiste | Volatilité | Kurtosis | Écart prix / valeur | Pire chute | corr(part chartiste, volatilité suivante) |
|---|---|---|---|---|---|---|
| 0.0 | 50% | 0.94% | 30.0 | 0.53% | 22.6% | +nan |
| 0.5 | 43% | 0.83% | 33.9 | 0.47% | 17.0% | +0.05 |
| 2.0 | 38% | 2.16% | 44.4 | 1.02% | 61.5% | +0.30 |
| 5.0 | 35% | 2.14% | 43.2 | 1.45% | 63.0% | +0.42 |

## Expérience B : évolution des stratégies (8 univers de 100 000 pas, avec et sans évolution)

Tous les 2 000 pas, les 10 % de fondamentalistes et de chartistes les moins performants copient les paramètres d'un des 20 % les meilleurs, avec mutation.

| Indicateur | Début | Fin |
|---|---|---|
| Fondamentalistes : erreur moyenne d'estimation |biais| | 0.79% | 0.33% |
| Fondamentalistes : agressivité médiane | 0.25 | 0.23 |
| Chartistes : horizon médian (pas) | 90 | 12 |
| Chartistes : échelle de tendance médiane | 0.030 | 0.037 |

Efficience du marché par tranche de 10 000 pas (écart moyen prix / valeur) :

| Tranche | Sans évolution | Avec évolution |
|---|---|---|
| 0–10 k | 0.51% | 0.47% |
| 10–20 k | 0.92% | 0.45% |
| 20–30 k | 0.58% | 0.42% |
| 30–40 k | 1.38% | 0.42% |
| 40–50 k | 5.08% | 0.51% |
| 50–60 k | 7.84% | 0.38% |
| 60–70 k | 8.17% | 0.39% |
| 70–80 k | 8.61% | 0.33% |
| 80–90 k | 9.04% | 0.44% |
| 90–100 k | 7.94% | 0.40% |

| Sur toute la durée | Sans évolution | Avec évolution |
|---|---|---|
| Volatilité | 1.73% [1.02% ; 2.43%] | 0.81% [0.75% ; 0.87%] |
| Kurtosis | 52.1 [-0.8 ; 105.0] | 36.7 [30.2 ; 43.2] |
| Écart prix / valeur | 5.05% [-0.16% ; 10.27%] | 0.42% [0.36% ; 0.48%] |
| Pire chute | 61.3% [47.8% ; 74.8%] | 27.6% [24.0% ; 31.3%] |

![Graphiques de la phase 5](apprentissage.png)
