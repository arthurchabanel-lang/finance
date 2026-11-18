# Phase 4 : ce que disent les expériences de régulation

Ce document complète [`experiences.md`](experiences.md), qui contient les chiffres bruts. Il
explique les mécanismes derrière chaque résultat et ce que le modèle ne permet pas de conclure.
Protocole : 20 univers appariés par politique (mêmes graines, donc mêmes news), plus un stress
test de liquidation forcée de 4 000 titres par univers. Un effet n'est retenu que si son
intervalle de confiance à 95 % exclut 0.

## Taxe sur les transactions (0,1 %)

- **Résultat** : la fourchette double, le volume baisse de 22 % et la stabilité ne
  s'améliore pas de façon significative.
- **Mécanisme** : les teneurs de marché répercutent la taxe dans leur fourchette, et les
  traders non informés tradent moins.
- **Limite** : la baisse de l'activité des bruiteurs (`sensibilite_bruiteurs`) est une
  hypothèse du modèle, pas une mesure. Le résultat penche du côté des études qui trouvent
  qu'une taxe réduit la liquidité sans calmer les prix (Umlauf 1993 sur la Suède ; Colliard et
  Hoffmann 2017 sur la taxe française de 2012).

## Coupe-circuit (arrêt de 100 pas si le prix bouge de plus de 3 % en 200 pas)

- **Résultat** : aucun effet significatif sur la volatilité, les krachs ou la chute pendant
  une liquidation, et un volume en baisse de 8 %.
- **Mécanisme** : l'arrêt suspend la cotation, mais pas les raisons de vendre. À la reprise, la
  liquidation forcée continue là où elle s'était arrêtée.
- **Limite** : la reprise se fait en continu, sans fixing de réouverture. Les vrais
  coupe-circuits (comme les réservations d'Euronext) rouvrent par une enchère qui regroupe la
  liquidité. C'est une piste d'amélioration.

## Interdiction de la vente à découvert

- **Résultat** : la chute pendant la liquidation diminue (médiane −11,8 % contre −15,7 %) et le
  prix reste plus proche de la valeur.
- **Mécanisme vérifié** : dans la référence, les chartistes vendent à découvert dans la baisse.
  Jusqu'au creux, ils cèdent 7 810 titres contre 4 072 avec l'interdiction, et leur découvert
  cumulé atteint −2 285 titres. Les appels de marge passent de 208 à 139.
- **Attention à la moyenne** : l'effet moyen (−65 %) est tiré par quelques univers extrêmes ;
  en médiane, la réduction est d'environ 25 %.
- **Limite importante** : dans le modèle, seuls les chartistes (momentum) vendent à découvert.
  Les fondamentalistes, des investisseurs value non endettés, ne le font pas. L'interdiction ne
  supprime donc que la vente à découvert déstabilisante. Dans la réalité, les vendeurs à
  découvert sont aussi des arbitragistes qui dégonflent les bulles, et les études sur les
  interdictions de 2008 concluent qu'elles ont dégradé la liquidité sans soutenir les prix
  (Beber et Pagano 2013 ; Boehmer, Jones et Zhang 2013). **Ce résultat ne doit pas être lu
  comme un argument en faveur de l'interdiction.**

## Levier

- **Levier des hedge funds limité** (découvert des chartistes ramené à 2 000 €) : aucun effet
  significatif. Leurs positions sont déjà bornées par `position_max` ; le crédit n'est pas la
  contrainte qui compte pour eux.
- **Crédit restreint pour tous** : volatilité +55 %, pire chute +53 %, chute pendant la
  liquidation +38 %. C'est la **spirale de liquidité** (Brunnermeier et Pedersen 2009). Les
  investisseurs value, eux aussi privés de crédit, ne peuvent plus acheter les titres bradés,
  et la force de rappel disparaît.
- **Leçon** : resserrer le crédit sans distinction prive le marché de ses acheteurs de
  dernier ressort. Il vaut mieux cibler les acteurs dont le levier est déstabilisant.

## À retenir

Le simulateur reproduit des résultats connus de la littérature : une taxe coûteuse en
liquidité, et une spirale de liquidité quand le crédit se resserre. Il montre aussi que la
conclusion dépend fortement de **qui** est concerné par une règle, comme pour la vente à
découvert et le levier. C'est précisément l'intérêt d'un modèle à agents hétérogènes.
