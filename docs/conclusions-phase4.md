# Phase 4 : ce que disent les expériences de régulation

Ce document complète [`experiences.md`](experiences.md), qui contient les chiffres bruts. Il
explique les mécanismes derrière chaque résultat et ce que le modèle ne permet pas de conclure.
Protocole : 20 univers appariés par politique (mêmes graines, donc mêmes news), plus un stress
test de liquidation forcée de 4 000 titres par univers. Un effet n'est retenu que si son
intervalle de confiance à 95 % exclut 0.

*Version du 18/11/2026, établie sur le modèle corrigé pendant la phase 5 : bruiteurs qui
rééquilibrent, appels de marge réservés aux positions financées par emprunt, chartistes
endettés, faillites. Les conclusions de la veille, tirées du modèle bogué, sont remplacées.*

## Taxe sur les transactions (0,1 %)

- **Résultat** : la fourchette augmente de 90 %, le volume baisse de 24 % et le prix s'écarte
  davantage de la valeur (+18 %). La stabilité ne s'améliore pas de façon significative.
- **Mécanisme** : les teneurs de marché répercutent la taxe dans leur fourchette, et les
  traders non informés tradent moins. Les petits écarts de valorisation ne valent plus la
  peine d'être arbitrés : le prix s'éloigne donc un peu plus de la valeur.
- **Limite** : la baisse de l'activité des bruiteurs (`sensibilite_bruiteurs`) est une
  hypothèse du modèle, pas une mesure. Le résultat va dans le sens des études qui trouvent
  qu'une taxe réduit la liquidité sans calmer les prix (Umlauf 1993 sur la Suède ; Colliard et
  Hoffmann 2017 sur la taxe française de 2012).

## Coupe-circuit (arrêt de 100 pas si le prix bouge de plus de 3 % en 200 pas)

- **Résultat** : les krachs sont plus fréquents (+38 %) et le volume baisse de 10 %. La chute
  pendant la liquidation n'est pas significativement réduite.
- **Mécanisme** : l'arrêt suspend la cotation, mais pas les raisons de vendre. À la reprise, les
  ordres accumulés et la liquidation en cours se déversent d'un coup sur un carnet vidé par
  l'annulation des ordres. (Les agents n'anticipent pas l'arrêt : l'« effet aimant » de la
  littérature, où les vendeurs se pressent avant le seuil, n'est pas modélisé.)
- **Limite** : la reprise se fait en continu, sans fixing de réouverture. Les vrais
  coupe-circuits (comme les réservations d'Euronext) rouvrent par une enchère qui regroupe la
  liquidité. Ce résultat juge donc un coupe-circuit mal conçu, pas les coupe-circuits en général.

## Interdiction de la vente à découvert

- **Résultat** : aucun effet en marché normal. Pendant une liquidation forcée, la chute est
  réduite de 34 % [−55 % ; −13 %] et le temps de récupération de 79 %.
- **Mécanisme vérifié** : dans la référence, les chartistes vendent à découvert dans la baisse.
  Jusqu'au creux, ils cèdent 4 111 titres, contre 1 607 avec l'interdiction, et la chute
  médiane passe de −18,4 % à −14,7 %. Les appels de marge passent de 213 à 129.
- **Limite importante** : dans le modèle, seuls les chartistes (momentum) vendent à découvert.
  Les fondamentalistes, des investisseurs value non endettés, ne le font pas. L'interdiction ne
  supprime donc que la vente à découvert déstabilisante. Dans la réalité, les vendeurs à
  découvert sont aussi des arbitragistes qui dégonflent les bulles, et les études sur les
  interdictions de 2008 concluent qu'elles ont dégradé la liquidité sans soutenir les prix
  (Beber et Pagano 2013 ; Boehmer, Jones et Zhang 2013). **Ce résultat ne doit pas être lu
  comme un argument en faveur de l'interdiction.**

## Levier

- **Levier des hedge funds limité** (découvert des chartistes ramené à 2 000 €) : la volatilité
  baisse légèrement (−10 %, à la limite de la significativité) et le volume de 6,5 %. Pas
  d'effet significatif pendant la liquidation forcée.
- **Crédit restreint pour tous** : en marché normal, l'effet est identique au cas précédent.
  Les investisseurs value n'ont pas besoin de crédit quand tout va bien. Mais pendant la
  liquidation forcée, **la chute double (+98 %)**. C'est la **spirale de liquidité**
  (Brunnermeier et Pedersen 2009) : au moment où il faudrait acheter les titres bradés, les
  investisseurs value n'ont plus de quoi les financer.
- **Leçon** : une règle de crédit peut sembler sans effet en temps normal et s'avérer
  dangereuse en crise. Resserrer le crédit sans distinction prive le marché de ses acheteurs
  de dernier ressort, précisément quand on en a besoin.

## À retenir

Le simulateur reproduit des résultats connus de la littérature : une taxe coûteuse en
liquidité, et une spirale de liquidité quand le crédit se resserre. Il montre aussi que :

1. la conclusion dépend fortement de **qui** est concerné par une règle (vente à découvert, levier) ;
2. une règle doit être jugée **en crise**, pas seulement en temps normal (crédit restreint pour tous) ;
3. les **détails de conception** comptent (coupe-circuit sans enchère de réouverture).

C'est précisément l'intérêt d'un modèle à agents hétérogènes.
