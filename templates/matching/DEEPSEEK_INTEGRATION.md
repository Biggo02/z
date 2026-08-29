# Intégration interface Matching DeepSeek

L'interface Matching fournie par DeepSeek est intégrée au template Django `templates/matching/index.html`.

Principes conservés :
- rendu Django avec `base.html` ;
- formulaire POST avec CSRF ;
- critères raccordés aux champs du moteur `matching` ;
- résultats alimentés par `MatchingResult` ;
- loyers et adresse exacte protégés côté interface ;
- liens de détail utilisant la route Django `property_detail` ;
- aucun changement des modèles, vues ou règles métier dans cette intégration.

Le design premium DeepSeek est conservé ; les données fictives de démonstration ne sont pas utilisées comme données métier.