# Fasthome

Plateforme de recherche, publication et gestion professionnelle de logements.

## Stack
- Django 4.2+
- PostgreSQL en production / SQLite en développement
- Templates Django + JavaScript léger
- Pas de paiement en ligne

## Démarrage local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py seed_property_types
python manage.py runserver
```

Créer un administrateur :

```bash
python manage.py createsuperuser
```

## Parcours métier

Compte → certification → recherche/matching → logement → demande de visite → validation Fasthome + bailleur → visite effectuée → choix du locataire → dossier → deux contrats → PV → officialisation → réception des loyers → versements au bailleur → renouvellement/sortie.

## Règles essentielles

- Un utilisateur peut être locataire et bailleur.
- Publication et demande de visite nécessitent un compte certifié.
- Le Matching utilise uniquement : meublé, province, ville/territoire, subdivision administrative, quartier, salons, chambres, budget maximum et occupants.
- Les résultats principaux sont de 60 % à 100 %.
- Prix et adresse exacte restent masqués publiquement.
- Aucun paiement en ligne.
- Les paiements reçus par Fasthome et les versements aux bailleurs sont enregistrés séparément.
- Une visite doit être validée par Fasthome et le bailleur ; l'identité du demandeur reste masquée au bailleur à cette étape.
- Après « visite effectuée », le locataire peut prendre ou refuser le logement.
- Une location produit deux contrats : Fasthome/locataire et Fasthome/bailleur.
- Le PV d'entrée est commun aux parties.
