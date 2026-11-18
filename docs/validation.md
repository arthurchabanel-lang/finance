# Validation Monte-Carlo du simulateur

*Générée le 18/11/2026 par `python valider.py` : 20 univers indépendants de 30 000 pas, rendements sur 50 pas.*

Chaque univers a sa propre graine aléatoire. Pour chaque fait stylisé, on donne la part d'univers qui le reproduisent, la moyenne et son intervalle de confiance à 95 %.

| Fait stylisé | Univers OK | Moyenne | IC 95 % | Marchés réels |
|---|---|---|---|---|
| ✅ Queues épaisses | 20/20 | 20.4 | [16.8 ; 24.1] | kurtosis excédentaire nettement > 0 |
| ❌ Indice de queue (Hill) | 7/20 | 1.91 | [1.71 ; 2.11] | ≈ 3, entre 2 et 5 (loi cubique inverse) |
| ✅ Queues épaisses émergentes | 20/20 | 33.3 | [22.7 ; 44.0] | (test propre au modèle) persistent sans news |
| ✅ Rendements imprévisibles | 19/20 | 0.089 | [0.082 ; 0.096] | |ACF| des rendements ≈ 0 au-delà de quelques minutes |
| ✅ Volatilité en grappes | 20/20 | 0.166 | [0.135 ; 0.197] | ACF des |rendements| > 0 |
| ❌ Mémoire longue de la volatilité | 2/20 | 0.84 | [0.74 ; 0.95] | décroissance en k^(-β), β ≈ 0,2 à 0,4 |
| ✅ Normalité aux horizons longs | 20/20 | 5.6 | [3.2 ; 7.9] | la kurtosis baisse quand l'horizon s'allonge |
| ✅ Effet de levier | 18/20 | -0.038 | [-0.045 ; -0.032] | corr(rendement, volatilité future) < 0 |
| ⚠️ Asymétrie gains / pertes | 13/20 | -0.39 | [-0.79 ; +0.01] | skewness < 0 (krachs plus violents que les envolées) |
| ✅ Volume ↔ volatilité | 20/20 | 0.63 | [0.61 ; 0.66] | corrélation positive |
| ✅ Ancrage sur la valeur | 20/20 | 0.76% | [0.71% ; 0.81%] | (test propre au modèle) écart moyen < 5 % |

Pour « Queues épaisses émergentes », la valeur est la kurtosis du prix dans l'expérience témoin sans news. Pour « Normalité aux horizons longs », c'est la kurtosis sur 250 pas.

![Graphiques de validation](validation.png)

Références : Cont (2001), *Quantitative Finance* 1(2) ; Gopikrishnan et al. (1999), *Phys. Rev. E* 60 ; Bouchaud, Matacz & Potters (2001), *Phys. Rev. Lett.* 87.
