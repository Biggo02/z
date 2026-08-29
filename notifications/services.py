from django.contrib.auth import get_user_model
from .models import Notification


def _staff_ids(exclude_ids=()):
    return list(get_user_model().objects.filter(is_active=True, is_staff=True).exclude(pk__in=list(exclude_ids)).values_list('pk', flat=True))


def notify(recipient, *, level='INFO', title, message, object_type='', object_id='', unique=True):
    if not recipient or not getattr(recipient, 'is_active', True):
        return None
    if unique and object_type and object_id and Notification.objects.filter(recipient=recipient, object_type=object_type, object_id=str(object_id), title=title).exists():
        return None
    return Notification.objects.create(recipient=recipient, level=level, title=title, message=message, object_type=object_type, object_id=str(object_id or ''))


def notify_ids(user_ids, *, level='INFO', title, message, object_type='', object_id='', unique=True):
    rows = []
    existing = set()
    ids = {uid for uid in user_ids if uid}
    if unique and object_type and object_id and ids:
        existing = set(Notification.objects.filter(recipient_id__in=ids, object_type=object_type, object_id=str(object_id), title=title).values_list('recipient_id', flat=True))
    for user_id in ids - existing:
        rows.append(Notification(recipient_id=user_id, level=level, title=title, message=message, object_type=object_type, object_id=str(object_id or '')))
    if rows:
        Notification.objects.bulk_create(rows)
    return rows


def staff(**kwargs):
    exclude = kwargs.pop('exclude_ids', ())
    return notify_ids(_staff_ids(exclude), **kwargs)


# VISITES
def visit_requested(visit):
    notify(visit.property.owner, level='ACTION', title='Demande de visite à valider', message='Une demande de visite pour votre logement nécessite votre validation.', object_type='VisitRequest', object_id=visit.visit_id)
    staff(level='ACTION', title='Nouvelle demande de visite', message='Une nouvelle demande de visite est en attente de traitement.', object_type='VisitRequest', object_id=visit.visit_id, exclude_ids=(visit.requester_id,))


def visit_landlord_approved(visit):
    # Une acceptation du bailleur reste interne tant que Fasthome n'a pas validé.
    staff(level='ACTION', title='Validation du bailleur à traiter', message='Le bailleur a accepté cette demande. Votre validation Fasthome est maintenant nécessaire.', object_type='VisitRequest', object_id=visit.visit_id)


def visit_landlord_refused(visit):
    # Un refus du bailleur reste interne à Fasthome.
    staff(level='INFO', title='Demande de visite refusée par le bailleur', message='Le bailleur a refusé cette demande de visite.', object_type='VisitRequest', object_id=visit.visit_id)


def visit_fasthome_approved(visit):
    # Si Fasthome accepte en premier, aucune notification n'est envoyée.
    # Si le bailleur accepte ensuite, visit_confirmed() notifie les trois acteurs.
    return None


def visit_fasthome_refused(visit):
    notify(visit.requester, level='ACTION', title='Demande de visite refusée', message='Fasthome n’a pas validé cette demande de visite.', object_type='VisitRequest', object_id=visit.visit_id)
    notify(visit.property.owner, level='INFO', title='Demande de visite non validée', message='Fasthome n’a pas validé cette demande de visite.', object_type='VisitRequest', object_id=visit.visit_id)


def visit_confirmed(visit):
    notify_ids([visit.requester_id, visit.property.owner_id], level='SUCCESS', title='Visite définitivement confirmée', message='Le bailleur et Fasthome ont accepté la demande de visite.', object_type='VisitRequest', object_id=visit.visit_id)
    staff(level='SUCCESS', title='Visite confirmée', message='La visite a reçu toutes les validations nécessaires.', object_type='VisitRequest', object_id=visit.visit_id)


def visit_completed(visit):
    notify(visit.requester, level='SUCCESS', title='Visite effectuée', message='La visite du logement a été enregistrée par Fasthome.', object_type='VisitRequest', object_id=visit.visit_id)


# PUBLICATIONS
def publication_submitted(publication):
    staff(level='ACTION', title='Nouvelle publication à vérifier', message='Un logement vient d’être soumis et attend une vérification.', object_type='PropertyPublication', object_id=publication.publication_id)


def publication_approved(publication):
    notify(publication.property.owner, level='SUCCESS', title='Logement publié', message=f'Votre logement {publication.property.property_id} a été validé et est maintenant visible sur Fasthome.', object_type='PropertyPublication', object_id=publication.publication_id)


def publication_correction_required(publication, reason):
    notify(publication.property.owner, level='ACTION', title='Publication à compléter', message=f'Votre publication doit être corrigée. Motif : {reason}', object_type='PropertyPublication', object_id=publication.publication_id)


def publication_rejected(publication, reason):
    notify(publication.property.owner, level='ACTION', title='Publication rejetée', message=f'Votre publication a été rejetée. Motif : {reason}', object_type='PropertyPublication', object_id=publication.publication_id)


# KYC
def verification_submitted(verification):
    staff(level='ACTION', title='Nouvelle vérification à traiter', message='Une nouvelle vérification d’identité est en attente.', object_type='IdentityVerification', object_id=verification.pk)


def verification_in_review(verification):
    notify(verification.user, level='INFO', title='Vérification en cours', message='Votre vérification d’identité est actuellement examinée par Fasthome.', object_type='IdentityVerification', object_id=verification.pk)


def verification_document_verified(verification):
    notify(verification.user, level='INFO', title='Pièce d’identité validée', message='Votre pièce d’identité a été validée. La vérification faciale reste à finaliser.', object_type='IdentityVerification', object_id=verification.pk)


def verification_decided(verification, approved, reason=''):
    notify(verification.user, level='SUCCESS' if approved else 'ACTION', title='Identité certifiée' if approved else 'Vérification à corriger', message='Votre identité est maintenant certifiée sur Fasthome.' if approved else f'Votre vérification nécessite une correction. {reason}'.strip(), object_type='IdentityVerification', object_id=verification.pk)


def verification_manual_review(verification):
    staff(level='ACTION', title='Vérification humaine requise', message='Les contrôles automatiques demandent une vérification humaine.', object_type='IdentityVerification', object_id=verification.pk)


# LOCATION / CONTRATS
def rental_case_created(case):
    notify(case.tenant, level='INFO', title='Dossier de location créé', message='Votre dossier de location a été créé et sera traité par Fasthome.', object_type='RentalCase', object_id=case.case_id)
    staff(level='ACTION', title='Nouveau dossier de location', message='Un nouveau dossier de location nécessite un traitement.', object_type='RentalCase', object_id=case.case_id)


def rental_case_accepted(case):
    notify(case.tenant, level='SUCCESS', title='Dossier accepté', message='Votre dossier de location a été accepté et passe à la contractualisation.', object_type='RentalCase', object_id=case.case_id)


def contract_created(contract):
    notify(contract.lease.tenant, level='ACTION', title='Contrat disponible', message='Votre contrat est disponible dans votre espace et nécessite votre attention.', object_type='Contract', object_id=contract.contract_id)
    notify(contract.lease.landlord, level='ACTION', title='Contrat disponible', message='Votre contrat est disponible dans votre espace et nécessite votre attention.', object_type='Contract', object_id=contract.contract_id)


def contract_uploaded(contract):
    staff(level='ACTION', title='Contrat signé reçu', message='Un contrat signé vient d’être téléversé et doit être vérifié.', object_type='Contract', object_id=contract.contract_id)


def contract_validated(contract):
    notify(contract.lease.tenant, level='SUCCESS', title='Contrat validé', message='Le contrat a été vérifié et validé par Fasthome.', object_type='Contract', object_id=contract.contract_id)
    notify(contract.lease.landlord, level='SUCCESS', title='Contrat validé', message='Le contrat a été vérifié et validé par Fasthome.', object_type='Contract', object_id=contract.contract_id)


def contract_rejected(contract, reason=''):
    notify(contract.lease.tenant, level='ACTION', title='Contrat à corriger', message=f'Le contrat nécessite une correction. {reason}'.strip(), object_type='Contract', object_id=contract.contract_id)
    notify(contract.lease.landlord, level='ACTION', title='Contrat à corriger', message=f'Le contrat nécessite une correction. {reason}'.strip(), object_type='Contract', object_id=contract.contract_id)


def inspection_validated(report):
    notify(report.lease.tenant, level='SUCCESS', title='PV validé', message='Le procès-verbal d’entrée a été validé par Fasthome.', object_type='InspectionReport', object_id=report.report_id)
    notify(report.lease.landlord, level='SUCCESS', title='PV validé', message='Le procès-verbal d’entrée a été validé par Fasthome.', object_type='InspectionReport', object_id=report.report_id)


def payment_recorded(receipt):
    installment = receipt.installment
    remaining = installment.remaining_to_receive()
    if installment.status == 'PARTIAL':
        title = 'Paiement partiel enregistré'
        message = f'Un paiement de {receipt.amount} a été enregistré auprès de Fasthome. Solde restant : {remaining}.'
    elif installment.status == 'PAID':
        title = 'Échéance entièrement réglée'
        message = f'Le paiement de {receipt.amount} a soldé votre échéance auprès de Fasthome.'
    else:
        title = 'Paiement enregistré'
        message = f'Un paiement de {receipt.amount} a été enregistré auprès de Fasthome.'
    # Flux 1 : locataire -> Fasthome. Seuls le locataire et Fasthome sont concernés.
    notify(installment.lease.tenant, level='SUCCESS', title=title, message=message, object_type='PaymentReceipt', object_id=receipt.pk)
    staff(level='INFO', title='Paiement locataire enregistré', message=f'Paiement {receipt.payment_id} enregistré pour {installment.lease.lease_id}.', object_type='PaymentReceipt', object_id=receipt.pk)


def payment_overdue(installment):
    notify(installment.lease.tenant, level='ACTION', title='Échéance de loyer dépassée', message='Une échéance de loyer n’a pas encore été régularisée.', object_type='RentInstallment', object_id=installment.pk)
    staff(level='ACTION', title='Échéance de loyer en retard', message='Une échéance de loyer nécessite un suivi.', object_type='RentInstallment', object_id=installment.pk)


def payout_completed(payout):
    # Flux 2 : Fasthome -> bailleur. Le bailleur reçoit le versement ; Fasthome conserve la trace interne.
    notify(payout.lease.landlord, level='SUCCESS', title='Versement effectué', message=f'Le versement de {payout.amount} concernant votre location a été enregistré.', object_type='LandlordPayout', object_id=payout.pk)
    staff(level='INFO', title='Versement bailleur enregistré', message=f'Le versement {payout.payout_id} a été enregistré.', object_type='LandlordPayout', object_id=payout.pk)


def lease_officialized(lease):
    notify_ids([lease.tenant_id, lease.landlord_id], level='SUCCESS', title='Location officialisée', message=f'La location {lease.lease_id} est maintenant officielle.', object_type='Lease', object_id=lease.lease_id)
    staff(level='SUCCESS', title='Location officialisée', message=f'La location {lease.lease_id} est maintenant active.', object_type='Lease', object_id=lease.lease_id)


# CYCLE DE LOCATION
def renewal_requested(renewal):
    notify(renewal.lease.landlord, level='ACTION', title='Demande de renouvellement', message=f'Une demande de renouvellement concerne la location {renewal.lease.lease_id}.', object_type='RenewalRequest', object_id=renewal.request_id)
    staff(level='ACTION', title='Nouvelle demande de renouvellement', message=f'Une demande de renouvellement concerne {renewal.lease.lease_id}.', object_type='RenewalRequest', object_id=renewal.request_id)


def renewal_decided(renewal, approved):
    notify(renewal.lease.tenant, level='SUCCESS' if approved else 'ACTION', title='Renouvellement accepté' if approved else 'Renouvellement refusé', message='Votre renouvellement a été accepté.' if approved else 'Votre demande de renouvellement a été refusée.', object_type='RenewalRequest', object_id=renewal.request_id)
    notify(renewal.lease.landlord, level='INFO', title='Renouvellement traité', message='La demande de renouvellement a été traitée par Fasthome.', object_type='RenewalRequest', object_id=renewal.request_id)


def exit_requested(exit_request):
    notify(exit_request.lease.landlord, level='ACTION', title='Demande de sortie', message=f'Une demande de sortie concerne la location {exit_request.lease.lease_id}.', object_type='LeaseExit', object_id=exit_request.exit_id)
    staff(level='ACTION', title='Nouvelle demande de sortie', message=f'Une demande de sortie concerne {exit_request.lease.lease_id}.', object_type='LeaseExit', object_id=exit_request.exit_id)


def exit_decided(exit_request, approved):
    notify(exit_request.lease.tenant, level='SUCCESS' if approved else 'ACTION', title='Sortie validée' if approved else 'Sortie refusée', message='Votre demande de sortie a été validée.' if approved else 'Votre demande de sortie a été refusée.', object_type='LeaseExit', object_id=exit_request.exit_id)
    notify(exit_request.lease.landlord, level='INFO', title='Demande de sortie traitée', message='La demande de sortie a été traitée par Fasthome.', object_type='LeaseExit', object_id=exit_request.exit_id)
