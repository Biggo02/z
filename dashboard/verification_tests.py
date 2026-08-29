import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from users.models import IdentityVerification, User


def valid_selfie(name='selfie.jpg'):
    buffer = io.BytesIO()
    Image.effect_noise((256, 256), 80).convert('RGB').save(buffer, format='JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class VerificationModerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='kyc-user@example.com', password='A-secure-password-123', phone='+243900009101', last_name='KYC', first_name='User')
        self.staff = User.objects.create_user(email='kyc-staff@example.com', password='A-secure-password-123', phone='+243900009102', last_name='KYC', first_name='Staff', is_staff=True, can_review_kyc=True)
        self.other_reviewer = User.objects.create_user(email='kyc-other@example.com', password='A-secure-password-123', phone='+243900009103', last_name='KYC', first_name='Other', is_staff=True, can_review_kyc=True)
        self.verification = IdentityVerification.objects.create(user=self.user, assigned_reviewer=self.staff, document_type='PASSPORT', document_file=SimpleUploadedFile('identity.pdf', b'%PDF-1.4 test'), facial_photo=valid_selfie())

    def test_document_then_face_makes_user_certified_without_promoting_biometric_photo(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'})
        self.verification.refresh_from_db(); self.user.refresh_from_db(); self.assertEqual(self.verification.status, 'VERIFIED'); self.assertFalse(self.user.is_certified)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'})
        self.verification.refresh_from_db(); self.user.refresh_from_db(); self.assertEqual(self.verification.facial_status, 'VERIFIED'); self.assertTrue(self.user.is_certified); self.assertFalse(bool(self.user.profile_photo))

    def test_face_cannot_be_finalized_before_document(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'}, follow=True)
        self.assertEqual(response.status_code, 200); self.verification.refresh_from_db(); self.assertEqual(self.verification.status, 'PENDING'); self.assertEqual(self.verification.facial_status, 'PENDING')

    def test_face_requires_selfie(self):
        self.verification.facial_photo = None; self.verification.save(); self.client.force_login(self.staff)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'})
        response = self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'}, follow=True)
        self.assertEqual(response.status_code, 200); self.verification.refresh_from_db(); self.user.refresh_from_db(); self.assertEqual(self.verification.facial_status, 'PENDING'); self.assertFalse(self.user.is_certified)

    def test_rejection_requires_reason_and_revokes_certification(self):
        self.client.force_login(self.staff); self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'}); self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_face'}); self.user.refresh_from_db(); self.assertTrue(self.user.is_certified)
        self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'reject', 'reason': 'Document illisible.'}); self.verification.refresh_from_db(); self.user.refresh_from_db(); self.assertEqual(self.verification.status, 'RETRY'); self.assertEqual(self.verification.facial_status, 'RETRY'); self.assertFalse(self.user.is_certified)

    def test_non_staff_cannot_moderate_kyc(self):
        self.client.force_login(self.user); self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'}, follow=True); self.verification.refresh_from_db(); self.assertEqual(self.verification.status, 'PENDING')

    def test_kyc_reviewer_cannot_access_unassigned_verification(self):
        self.client.force_login(self.other_reviewer); response = self.client.get(reverse('office_verification_document', args=[self.verification.pk])); self.assertEqual(response.status_code, 404); response = self.client.post(reverse('office_verification_decision', args=[self.verification.pk]), {'action': 'verify_document'}); self.assertEqual(response.status_code, 404)

    def test_kyc_reviewer_cannot_list_unassigned_verification(self):
        self.client.force_login(self.other_reviewer); response = self.client.get(reverse('office_verifications')); self.assertEqual(response.status_code, 200); self.assertNotContains(response, self.verification.user.fasthome_id)

    def test_assigned_kyc_reviewer_can_download_document(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('office_verification_document', args=[self.verification.pk]))
        self.assertEqual(response.status_code, 200)
        filename = self.verification.document_file.name.rsplit('/', 1)[-1]
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{filename}"')
