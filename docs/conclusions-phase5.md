# Phase 5 : ce que disent les agents qui apprennent

Chiffres bruts et graphiques : [`apprentissage.md`](apprentissage.md). Script : `python apprendre.py`.

## Ce que les simulations longues ont révélé sur le modèle

Faire tourner le marché sur 100 000 pas (contre 30 000 jusque-là) a mis au jour quatre
défauts. Chacun faisait lentement dériver le prix, jusqu'à 30 % sous la valeur dans certains
univers :

1. **Prix gelé** quand un seul côté du carnet était rempli : le prix de référence restait au
   dernier cours, même si des acheteurs proposaient plus haut.
2. **Bruiteurs sans allocation de long terme** : servant de réservoir passif, leur stock
   s'épuisait lentement. Ils rééquilibrent désormais vers leur allocation.
3. **Faux appels de marge** : ils se déclenchaient même pour un fonds sans dette, ce qui en
   faisait de simples stop-loss en cascade. Ils ne touchent plus que les positions financées
   par emprunt.
4. **Pas de faillite** : des fonds ruinés continuaient à trader à crédit. Un fonds qui perd
   75 % de son capital ferme désormais, et un nouveau reprend son portefeuille.

**Conséquence importante pour la phase 3** : l'effet de levier obtenu alors venait en partie
du défaut n° 3. Avec des appels de marge corrects, il n'apparaît que si les chartistes sont
réellement endettés, ce qui est le cas des hedge funds. C'est désormais le réglage par défaut,
et l'effet de levier est reproduit dans 18 univers sur 20. Tous les rapports ont été
régénérés sur le modèle corrigé.

## Expérience A : agents adaptatifs (Brock et Hommes 1998)

100 agents choisissent, avant chaque décision, entre la casquette fondamentaliste et la
casquette chartiste, selon le score récent des deux stratégies. L'intensité règle la force de
l'apprentissage : à 0, ils choisissent au hasard ; à 5, ils suivent presque toujours la
stratégie gagnante.

- **Les fondamentalistes gagnent en moyenne** : plus l'apprentissage est fort, plus la part
  en mode chartiste baisse (50 % → 21 %), et plus le prix colle à la valeur (écart moyen
  0,54 % → 0,34 %).
- **Mais les queues s'épaississent** : la kurtosis triple (18 → 54). Le marché est plus calme
  en temps normal, et ses crises sont plus violentes.
- **Le mécanisme est un cycle**, visible dans le graphique de l'univers d'exemple :
  1. en période calme, suivre la tendance rapporte, et la part de chartistes monte lentement ;
  2. le marché, porté par des suiveurs de tendance, devient fragile ;
  3. un krach éclate, à chaque fois au pic de la part de chartistes ;
  4. les pertes discréditent le suivi de tendance, la part de chartistes s'effondre, et le cycle recommence.

  La corrélation entre la part de chartistes et la volatilité qui suit croît avec l'intensité
  de l'apprentissage (+0,14 → +0,37).
- **Lecture** : c'est l'idée de Minsky, « la stabilité engendre l'instabilité », obtenue ici
  sans l'avoir programmée.
- **Correction en cours de route** : sans période d'observation, les agents apprenaient sur
  quelques pas de bruit au démarrage et formaient des bulles géantes (prix multiplié par 60).
  Ce n'était pas un résultat économique. L'apprentissage ne démarre désormais qu'une fois la
  mémoire des scores remplie (2 000 pas).

## Expérience B : évolution darwinienne des stratégies

Tous les 2 000 pas, les 10 % de fondamentalistes et de chartistes les moins performants
copient les paramètres d'un des 20 % les meilleurs, avec mutation. 8 univers de 100 000 pas.

- **Les chartistes raccourcissent massivement leur horizon** : l'horizon médian passe de
  88 pas à 10. Seul le momentum très court terme survit. Les tendances longues ne sont pas
  exploitables dans ce marché, où les fondamentalistes ramènent le prix vers la valeur.
- **Les fondamentalistes estiment un peu mieux la valeur** : l'erreur moyenne passe de
  0,77 % à 0,64 %. C'est modeste, et un univers fait exception : la valeur y a monté
  durablement, et ce sont les fondamentalistes optimistes qui ont été récompensés. La
  sélection récompense ce qui a rapporté, pas ce qui est juste.
- **L'agressivité des fondamentalistes ne converge pas** : elle reste autour de 0,24. Aucune
  valeur ne domine, ce qui suggère plusieurs stratégies viables.
- **Le marché devient plus efficient et plus calme** : l'écart prix/valeur passe de 1,11 % à
  0,66 %, la volatilité de 1,16 % à 0,80 % et la pire chute de 29 % à 24 %. La kurtosis
  monte toutefois légèrement (22 → 27) : comme dans l'expérience A, plus calme ne veut pas
  dire plus sûr dans les extrêmes.

## Limites

- Les agents apprennent **quelle stratégie** suivre ou **quels paramètres** garder, mais pas
  de nouvelles stratégies. Un apprentissage par renforcement libre serait l'étape suivante.
- Le score d'une stratégie est celui d'un portefeuille virtuel, sans coûts de transaction.
- Sans évolution, l'écart prix/valeur augmente encore légèrement avec le temps (0,6 % → 1,4 %
  sur 100 000 pas) : il reste une dérive lente, modeste mais à surveiller.
