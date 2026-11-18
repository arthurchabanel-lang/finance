# Expériences de régulation

*Générées le 18/11/2026 par `python experimenter.py` : 6 politiques × 20 univers appariés, 30 000 pas par univers, plus un stress test par univers.*

Chaque politique est simulée sur exactement les mêmes univers que la référence (mêmes graines, donc mêmes news). L'effet est la différence moyenne entre les deux, avec un intervalle de confiance à 95 %. Un effet n'est retenu que si cet intervalle exclut 0.

## Les politiques testées

- **Référence** : aucune régulation
- **Taxe 0,1 %** : chaque partie paie 0,1 % du montant échangé (taxe de type Tobin)
- **Coupe-circuit 3 %** : cotation suspendue 100 pas si le prix bouge de plus de 3 % en 200 pas
- **Vente à découvert interdite** : aucun agent (hors teneurs de marché) ne peut détenir moins de 0 titre
- **Levier des hedge funds limité** : découvert des chartistes (hedge funds) réduit de 10 000 € à 2 000 €
- **Crédit restreint pour tous** : découvert de tous les agents réduit de 10 000 € à 2 000 € (y compris les investisseurs value)

## Marché normal

### Volatilité

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 1.04% | — | — | — |
| Taxe 0,1 % | 1.02% | -1.1 % | [-12.0 % ; +9.8 %] | ≈ pas d'effet significatif |
| Coupe-circuit 3 % | 1.14% | +10.3 % | [-0.6 % ; +21.3 %] | ≈ pas d'effet significatif |
| Vente à découvert interdite | 1.00% | -3.8 % | [-15.0 % ; +7.3 %] | ≈ pas d'effet significatif |
| Levier des hedge funds limité | 0.93% | -10.4 % | [-20.7 % ; -0.1 %] | ✅ mieux |
| Crédit restreint pour tous | 0.93% | -10.3 % | [-20.7 % ; -0.0 %] | ✅ mieux |

### Krachs (rendements < −3 % sur 50 pas)

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 7.0 | — | — | — |
| Taxe 0,1 % | 7.2 | +4.3 % | [-26.4 % ; +35.0 %] | ≈ pas d'effet significatif |
| Coupe-circuit 3 % | 9.6 | +38.1 % | [+8.0 % ; +68.2 %] | ❌ pire |
| Vente à découvert interdite | 7.7 | +10.1 % | [-13.4 % ; +33.6 %] | ≈ pas d'effet significatif |
| Levier des hedge funds limité | 6.7 | -3.6 % | [-30.3 % ; +23.1 %] | ≈ pas d'effet significatif |
| Crédit restreint pour tous | 6.8 | -2.9 % | [-29.8 % ; +24.1 %] | ≈ pas d'effet significatif |

### Pire chute depuis un plus haut

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 20.7% | — | — | — |
| Taxe 0,1 % | 21.7% | +4.8 % | [-5.3 % ; +15.0 %] | ≈ pas d'effet significatif |
| Coupe-circuit 3 % | 21.5% | +4.1 % | [-5.6 % ; +13.8 %] | ≈ pas d'effet significatif |
| Vente à découvert interdite | 20.8% | +0.8 % | [-9.7 % ; +11.2 %] | ≈ pas d'effet significatif |
| Levier des hedge funds limité | 20.8% | +0.6 % | [-13.3 % ; +14.5 %] | ≈ pas d'effet significatif |
| Crédit restreint pour tous | 20.8% | +0.6 % | [-13.3 % ; +14.5 %] | ≈ pas d'effet significatif |

### Écart moyen prix / valeur

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 0.79% | — | — | — |
| Taxe 0,1 % | 0.93% | +18.1 % | [+10.5 % ; +25.8 %] | ❌ pire |
| Coupe-circuit 3 % | 0.81% | +2.9 % | [-4.3 % ; +10.1 %] | ≈ pas d'effet significatif |
| Vente à découvert interdite | 0.78% | -1.1 % | [-6.4 % ; +4.2 %] | ≈ pas d'effet significatif |
| Levier des hedge funds limité | 0.76% | -4.1 % | [-9.4 % ; +1.3 %] | ≈ pas d'effet significatif |
| Crédit restreint pour tous | 0.76% | -4.1 % | [-9.5 % ; +1.2 %] | ≈ pas d'effet significatif |

### Fourchette moyenne

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 0.111 € | — | — | — |
| Taxe 0,1 % | 0.210 € | +89.6 % | [+80.5 % ; +98.8 %] | ❌ pire |
| Coupe-circuit 3 % | 0.107 € | -3.4 % | [-10.5 % ; +3.8 %] | ≈ pas d'effet significatif |
| Vente à découvert interdite | 0.113 € | +1.8 % | [-3.4 % ; +7.0 %] | ≈ pas d'effet significatif |
| Levier des hedge funds limité | 0.106 € | -4.2 % | [-9.5 % ; +1.2 %] | ≈ pas d'effet significatif |
| Crédit restreint pour tous | 0.106 € | -4.2 % | [-9.6 % ; +1.1 %] | ≈ pas d'effet significatif |

### Volume par pas

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 15.4 | — | — | — |
| Taxe 0,1 % | 11.7 | -23.7 % | [-27.0 % ; -20.5 %] | ❌ pire |
| Coupe-circuit 3 % | 13.9 | -9.6 % | [-12.1 % ; -7.0 %] | ❌ pire |
| Vente à découvert interdite | 15.2 | -1.3 % | [-3.3 % ; +0.6 %] | ≈ pas d'effet significatif |
| Levier des hedge funds limité | 14.4 | -6.5 % | [-9.0 % ; -3.9 %] | ❌ pire |
| Crédit restreint pour tous | 14.4 | -6.5 % | [-9.0 % ; -4.0 %] | ❌ pire |


## Stress test : liquidation forcée de 4 000 titres au pas 12 000

### Chute pendant la liquidation

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 25.0% | — | — | — |
| Taxe 0,1 % | 22.8% | -8.5 % | [-36.7 % ; +19.8 %] | ≈ pas d'effet significatif |
| Coupe-circuit 3 % | 20.2% | -18.9 % | [-51.9 % ; +14.1 %] | ≈ pas d'effet significatif |
| Vente à découvert interdite | 16.4% | -34.3 % | [-55.4 % ; -13.2 %] | ✅ mieux |
| Levier des hedge funds limité | 27.9% | +11.8 % | [-18.4 % ; +41.9 %] | ≈ pas d'effet significatif |
| Crédit restreint pour tous | 49.4% | +97.8 % | [+29.5 % ; +166.2 %] | ❌ pire |

### Temps de récupération (pas)

| Politique | Valeur | Effet vs référence | IC 95 % | Verdict |
|---|---|---|---|---|
| Référence | 795 | — | — | — |
| Taxe 0,1 % | 879 | +33.6 % | [-105.7 % ; +172.9 %] | ≈ pas d'effet significatif |
| Coupe-circuit 3 % | 1057 | +35.3 % | [-62.3 % ; +133.0 %] | ≈ pas d'effet significatif |
| Vente à découvert interdite | 183 | -79.0 % | [-145.5 % ; -12.5 %] | ✅ mieux |
| Levier des hedge funds limité | 916 | +27.5 % | [-103.7 % ; +158.7 %] | ≈ pas d'effet significatif |
| Crédit restreint pour tous | 561 | -31.8 % | [-103.7 % ; +40.1 %] | ≈ pas d'effet significatif |

![Graphiques des expériences](experiences.png)
