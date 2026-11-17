# Validation Monte-Carlo du simulateur

*Générée le 17/11/2026 par `python valider.py` : 20 univers indépendants de 30 000 pas, rendements sur 50 pas.*

Chaque univers a sa propre graine aléatoire. Pour chaque fait stylisé, on donne la part d'univers qui le reproduisent, la moyenne et son intervalle de confiance à 95 %.

| Fait stylisé | Univers OK | Moyenne | IC 95 % | Marchés réels |
|---|---|---|---|---|
| ✅ Queues épaisses | 20/20 | 19.0 | [14.4 ; 23.5] | kurtosis excédentaire nettement > 0 |
| ⚠️ Indice de queue (Hill) | 12/20 | 2.11 | [1.89 ; 2.32] | ≈ 3, entre 2 et 5 (loi cubique inverse) |
| ✅ Queues épaisses émergentes | 20/20 | 42.1 | [28.7 ; 55.5] | (test propre au modèle) persistent sans news |
| ⚠️ Rendements imprévisibles | 11/20 | 0.131 | [0.100 ; 0.161] | |ACF| des rendements ≈ 0 au-delà de quelques minutes |
| ✅ Volatilité en grappes | 19/20 | 0.271 | [0.215 ; 0.327] | ACF des |rendements| > 0 |
| ⚠️ Mémoire longue de la volatilité | 10/20 | 0.59 | [0.45 ; 0.73] | décroissance en k^(-β), β ≈ 0,2 à 0,4 |
| ✅ Normalité aux horizons longs | 19/20 | 6.3 | [3.0 ; 9.6] | la kurtosis baisse quand l'horizon s'allonge |
| ❌ Effet de levier | 9/20 | -0.037 | [-0.062 ; -0.013] | corr(rendement, volatilité future) < 0 |
| ⚠️ Asymétrie gains / pertes | 14/20 | -0.32 | [-0.68 ; +0.03] | skewness < 0 (krachs plus violents que les envolées) |
| ✅ Volume ↔ volatilité | 20/20 | 0.63 | [0.60 ; 0.67] | corrélation positive |
| ✅ Ancrage sur la valeur | 20/20 | 0.86% | [0.53% ; 1.19%] | (test propre au modèle) écart moyen < 5 % |

Pour « Queues épaisses émergentes », la valeur est la kurtosis du prix dans l'expérience témoin sans news. Pour « Normalité aux horizons longs », c'est la kurtosis sur 250 pas.

![Graphiques de validation](validation.png)

Références : Cont (2001), *Quantitative Finance* 1(2) ; Gopikrishnan et al. (1999), *Phys. Rev. E* 60 ; Bouchaud, Matacz & Potters (2001), *Phys. Rev. Lett.* 87.
