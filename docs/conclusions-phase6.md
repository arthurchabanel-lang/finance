# Phase 6 : ce que dit l'expérience de contagion

Chiffres bruts et graphiques : [`contagion.md`](contagion.md). Script : `python contagion.py`.

## Le dispositif

- **Trois actifs** (A, B et C), chacun avec son propre marché complet : carnet d'ordres et
  402 agents locaux. Leurs **valeurs fondamentales sont indépendantes** : rien, dans
  l'économie réelle, ne relie les trois actifs.
- **Vingt fonds multi-actifs** détiennent chacun 300 titres de chaque actif, sur un **compte
  unique**. Une perte sur un actif réduit donc le capital qui garantit les positions sur les
  deux autres.
- **Au pas 8 000**, une liquidation forcée de 4 000 titres frappe **uniquement l'actif A**.
- **Trois scénarios**, sur les mêmes 20 univers :
  - des fonds endettés (levier 3, appels de marge) ;
  - les mêmes fonds sans dette ;
  - un témoin : les fonds endettés, sans aucun choc.

## Résultats

1. **La contagion existe, et elle passe par la dette.** Avec des fonds endettés, le choc sur A
   fait chuter B de 7,6 points de plus [3,1 ; 12,0] et C de 9,9 points de plus [4,5 ; 15,2]
   que dans le témoin sans choc. Sans dette, B et C ne bougent quasiment pas (chute de 6 %,
   le bruit ordinaire). Le mécanisme se lit dans les appels de marge, que le choc fait
   doubler (27 → 57) :
   1. les pertes sur A entament le capital des fonds ;
   2. les appels de marge les forcent à vendre toutes leurs positions ;
   3. B et C chutent sans aucune mauvaise nouvelle les concernant.

   Ce sont les **ventes forcées** (« fire sales ») de Shleifer et Vishny (1992), au cœur des
   crises de 1998 (LTCM) et de 2007 (le « quant quake » d'août 2007).
2. **L'endettement fragilise le système même sans choc.** Dans le témoin, B chute déjà de
   15 % en moyenne sur la même fenêtre de 3 000 pas, contre 6 % sans dette. Les fonds
   endettés subissent 61 appels de marge avant même le choc. **Sans ce témoin, on aurait
   surestimé la contagion d'un facteur deux environ** : comparer seulement « endettés » et
   « sans dette » mélange l'effet du choc et l'effet de la fragilité de fond.
3. **Détenir les mêmes actifs crée de la corrélation.** Avec des fonds endettés, des actifs
   aux fondamentaux indépendants affichent une corrélation de +0,15 en temps calme, contre
   0,00 sans dette. Cette corrélation monte à +0,23 pendant la crise, mais la hausse par
   rapport au témoin n'est pas statistiquement significative (+0,08 [−0,06 ; +0,21]). La
   littérature empirique trouve ce même effet de la détention commune (Anton et Polk 2014).

## Leçon

Dans ce marché artificiel, **le risque systémique ne vient pas des actifs, mais des bilans
qui les relient**. Un choc local devient global quand des investisseurs endettés détiennent
plusieurs actifs à la fois. C'est le raisonnement derrière les stress tests macroprudentiels
qui s'intéressent aux expositions communes des fonds, et pas seulement à chaque actif pris
isolément.

## Limites

- Les fonds suivent une règle simple : garder des positions cibles et se désendetter sur
  appel de marge. Ils n'anticipent pas les ventes des autres fonds, ce qui joue un rôle
  important dans les vraies crises (ventes préventives, course à la sortie).
- Les agents locaux de chaque actif ignorent les autres marchés. Il n'y a pas d'arbitrage
  entre actifs, ni d'investisseur qui viendrait racheter B « trop bas » parce que A va mal.
- Il n'y a ni banques ni prêteurs dont la solidité dépendrait des fonds. La contagion ne
  passe que par les prix, pas par les défauts de paiement en chaîne.
