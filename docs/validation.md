# Validation Monte-Carlo du simulateur

*Générée le 17/11/2026 par `python valider.py` : 20 univers indépendants de 30 000 pas, rendements sur 50 pas.*

Chaque univers a sa propre graine aléatoire. Pour chaque fait stylisé, on donne la part d'univers qui le reproduisent, la moyenne et son intervalle de confiance à 95 %.

| Fait stylisé | Univers OK | Moyenne | IC 95 % | Marchés réels |
|---|---|---|---|---|
| ✅ Queues épaisses | 20/20 | 27.7 | [17.7 ; 37.8] | kurtosis excédentaire nettement > 0 |
| ❌ Indice de queue (Hill) | 4/20 | 1.76 | [1.53 ; 1.99] | ≈ 3, entre 2 et 5 (loi cubique inverse) |
| ✅ Queues épaisses émergentes | 20/20 | 26.6 | [18.8 ; 34.5] | (test propre au modèle) persistent sans news |
| ⚠️ Rendements imprévisibles | 13/20 | 0.116 | [0.092 ; 0.140] | |ACF| des rendements ≈ 0 au-delà de quelques minutes |
| ✅ Volatilité en grappes | 19/20 | 0.216 | [0.153 ; 0.279] | ACF des |rendements| > 0 |
| ❌ Mémoire longue de la volatilité | 7/20 | 0.75 | [0.60 ; 0.89] | décroissance en k^(-β), β ≈ 0,2 à 0,4 |
| ✅ Normalité aux horizons longs | 20/20 | 5.6 | [2.5 ; 8.7] | la kurtosis baisse quand l'horizon s'allonge |
| ⚠️ Effet de levier | 11/20 | -0.036 | [-0.059 ; -0.013] | corr(rendement, volatilité future) < 0 |
| ⚠️ Asymétrie gains / pertes | 14/20 | -0.80 | [-1.25 ; -0.34] | skewness < 0 (krachs plus violents que les envolées) |
| ✅ Volume ↔ volatilité | 18/20 | 0.53 | [0.43 ; 0.64] | corrélation positive |
| ✅ Ancrage sur la valeur | 18/20 | 2.51% | [-0.26% ; 5.28%] | (test propre au modèle) écart moyen < 5 % |

Pour « Queues épaisses émergentes », la valeur est la kurtosis du prix dans l'expérience témoin sans news. Pour « Normalité aux horizons longs », c'est la kurtosis sur 250 pas.

![Graphiques de validation](validation.png)

Références : Cont (2001), *Quantitative Finance* 1(2) ; Gopikrishnan et al. (1999), *Phys. Rev. E* 60 ; Bouchaud, Matacz & Potters (2001), *Phys. Rev. Lett.* 87.
