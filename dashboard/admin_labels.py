"""Libellés français centralisés pour l'interface Django Admin.

Les noms de classes, champs et identifiants Python restent inchangés : cette
couche ne modifie que les textes affichés dans l'administration et n'exige
aucune migration de base de données.
"""

from django.contrib import admin


MODEL_LABELS = {
    'User': ('Utilisateur', 'Utilisateurs'),
    'IdentityVerification': ('Vérification d’identité', 'Vérifications d’identité'),
    'IdentityVerificationAnalysis': ('Analyse de vérification', 'Analyses de vérification'),
    'IdentityVerificationEvent': ('Historique de vérification', 'Historique des vérifications'),
    'Property': ('Logement', 'Logements'),
    'PropertyType': ('Type de logement', 'Types de logements'),
    'PropertyPublication': ('Publication de logement', 'Publications de logements'),
    'PropertyDeclaration': ('Déclaration de logement', 'Déclarations de logements'),
    'PropertyPhoto': ('Photo de logement', 'Photos de logements'),
    'PropertyFeature': ('Caractéristique du logement', 'Caractéristiques des logements'),
    'Bedroom': ('Chambre', 'Chambres'),
    'LivingRoom': ('Salon', 'Salons'),
    'Kitchen': ('Cuisine', 'Cuisines'),
    'Bathroom': ('Salle de bain', 'Salles de bain'),
    'Toilet': ('Toilettes', 'Toilettes'),
    'CollaborationConsent': ('Consentement de collaboration', 'Consentements de collaboration'),
    'Favorite': ('Favori', 'Favoris'),
    'Visit': ('Visite', 'Visites'),
    'VisitRequest': ('Demande de visite', 'Demandes de visite'),
    'Lease': ('Location', 'Locations'),
    'LeaseExit': ('Sortie de location', 'Sorties de location'),
    'RenewalRequest': ('Demande de renouvellement', 'Demandes de renouvellement'),
    'Contract': ('Contrat', 'Contrats'),
    'Incident': ('Incident', 'Incidents'),
    'Payment': ('Paiement', 'Paiements'),
    'PaymentRecord': ('Enregistrement de paiement', 'Enregistrements de paiement'),
    'Receipt': ('Reçu', 'Reçus'),
    'Notification': ('Notification', 'Notifications'),
    'InspectionReport': ('Rapport d’inspection', 'Rapports d’inspection'),
    'AuditLog': ('Journal d’audit', 'Journal d’audit'),
    'LogEntry': ('Entrée du journal', 'Entrées du journal'),
    'MatchingProfile': ('Profil de recherche', 'Profils de recherche'),
    'Match': ('Correspondance', 'Correspondances'),
}

FIELD_LABELS = {
    'username': "Nom d’utilisateur",
    'email': 'Adresse e-mail', 'phone': 'Téléphone',
    'first_name': 'Prénom', 'last_name': 'Nom', 'postname': 'Postnom',
    'birth_date': 'Date de naissance', 'sex': 'Sexe', 'profession': 'Profession',
    'fasthome_id': 'Identifiant Fasthome', 'profile_photo': 'Photo de profil',
    'is_active': 'Compte actif', 'is_staff': 'Accès administrateur',
    'is_superuser': 'Superadministrateur', 'is_phone_verified': 'Téléphone vérifié',
    'is_email_verified': 'E-mail vérifié', 'is_certified': 'Identité certifiée',
    'can_review_kyc': 'Autorisé à vérifier les identités',
    'created_at': 'Date de création', 'updated_at': 'Dernière modification',
    'owner': 'Propriétaire', 'property_type': 'Type de logement',
    'property_id': 'Identifiant du logement', 'publication_id': 'Identifiant de publication',
    'status': 'Statut', 'furnished': 'Meublé', 'province': 'Province',
    'city_or_territory': 'Ville / territoire', 'administrative_subdivision': 'Subdivision administrative',
    'neighborhood': 'Quartier', 'avenue_street': 'Avenue / rue', 'address_number': 'Numéro',
    'exact_address': 'Adresse exacte', 'latitude': 'Latitude', 'longitude': 'Longitude',
    'google_maps_url': 'Lien Google Maps', 'bedroom_count': 'Nombre de chambres',
    'living_room_count': 'Nombre de salons', 'has_kitchen': 'Cuisine disponible',
    'bathroom_count': 'Nombre de salles de bain', 'toilet_count': 'Nombre de toilettes',
    'floor': 'Étage', 'ceiling_type': 'Type de plafond', 'floor_type': 'Type de sol',
    'electricity_source': 'Source d’électricité', 'electricity_days_per_week': 'Jours d’électricité par semaine',
    'water_source': 'Source d’eau', 'water_days_per_week': 'Jours d’eau par semaine',
    'monthly_rent': 'Loyer mensuel', 'guarantee_amount': 'Montant de la garantie',
    'max_occupants': 'Nombre maximal d’occupants', 'furniture_condition': 'État du mobilier',
    'property': 'Logement', 'publication': 'Publication', 'image': 'Image', 'category': 'Catégorie',
    'is_primary': 'Photo principale', 'order': 'Ordre', 'relationship_to_property': 'Relation avec le logement',
    'right_to_offer_confirmed': 'Droit de proposer confirmé', 'accuracy_confirmed': 'Exactitude confirmée',
    'photos_authentic_confirmed': 'Authenticité des photos confirmée',
    'authorization_confirmed': 'Autorisation confirmée', 'acknowledged_responsibility': 'Responsabilité reconnue',
    'accepted_at': 'Accepté le', 'verification_accepted': 'Vérification acceptée',
    'presentation_accepted': 'Présentation acceptée', 'visits_accepted': 'Visites acceptées',
    'management_accepted': 'Gestion acceptée', 'collaboration_accepted': 'Collaboration acceptée',
    'terms_version': 'Version des conditions', 'user': 'Utilisateur',
    'assigned_reviewer': 'Agent vérificateur', 'document_type': 'Type de document',
    'document_file': 'Pièce d’identité', 'facial_photo': 'Photo selfie', 'facial_status': 'Statut de la vérification faciale',
    'submitted_at': 'Soumis le', 'verified_at': 'Vérifié le', 'rejection_reason': 'Motif du rejet',
    'quality_score': 'Score de qualité', 'ocr_engine': 'Moteur OCR', 'ocr_text': 'Texte OCR',
    'extracted_name': 'Nom extrait', 'name_match_score': 'Score de correspondance du nom',
    'expiry_date': 'Date d’expiration', 'expiry_ok': 'Expiration valide', 'fraud_signals': 'Signaux de falsification',
    'face_match_score': 'Score de correspondance faciale', 'face_explanation': 'Explication de la correspondance faciale',
    'confidence_score': 'Score de confiance', 'decision': 'Décision', 'explanation': 'Explication',
    'processed_at': 'Traité le', 'event_type': 'Type d’événement', 'actor': 'Agent',
    'from_status': 'Statut précédent', 'to_status': 'Nouveau statut',
    'from_facial_status': 'Statut facial précédent', 'to_facial_status': 'Nouveau statut facial',
    'reason': 'Motif', 'metadata': 'Informations techniques',
}


def apply_french_admin_labels():
    """Applique les libellés français aux ModelAdmin et à leurs champs."""
    for model, model_admin in admin.site._registry.items():
        labels = MODEL_LABELS.get(model.__name__)
        if labels:
            model_admin.verbose_name, model_admin.verbose_name_plural = labels

        for field in model._meta.fields:
            label = FIELD_LABELS.get(field.name)
            if label:
                field.verbose_name = label

    # Les modèles Django natifs sont déjà traduits par Django avec
    # LANGUAGE_CODE='fr-fr'.
