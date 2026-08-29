import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import IdentityVerification, User


class UserSecurityTests(TestCase):
    def make_user(self, email, phone):
        return User.objects.create_user(email=email, password='A-secure-password-123', phone=phone, last_name='Test', first_name='User')

    def make_document(self, name='passport.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')

    def make_facial_photo(self, name='selfie.jpg'):
        buffer = io.BytesIO()
        Image.effect_noise((32, 32), 80).convert('RGB').save(buffer, format='JPEG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')

    def test_fasthome_id_is_generated_and_unique(self):
        first = self.make_user('one@example.com', '+243900000001')
        second = self.make_user('two@example.com', '+243900000002')
        self.assertTrue(first.fasthome_id.startswith('FH-'))
        self.assertNotEqual(first.fasthome_id, second.fasthome_id)

    def test_document_can_be_verified_before_face_without_certifying_user(self):
        user = self.make_user('cert@example.com', '+243900000003')
        verification = IdentityVerification(user=user, document_type='PASSPORT', document_file=self.make_document(), status='VERIFIED', facial_status='PENDING')
        verification.save()
        user.refresh_from_db()
        self.assertFalse(user.is_certified)

    def test_facial_verification_cannot_be_final_without_document(self):
        user = self.make_user('cert-face@example.com', '+243900000007')
        verification = IdentityVerification(user=user, document_type='PASSPORT', document_file=self.make_document(), status='PENDING', facial_status='VERIFIED', facial_photo=self.make_facial_photo())
        with self.assertRaises(ValidationError):
            verification.full_clean()

    def test_final_certification_requires_facial_photo(self):
        user = self.make_user('cert-photo-required@example.com', '+243900000011')
        verification = IdentityVerification(user=user, document_type='PASSPORT', document_file=self.make_document(), status='VERIFIED', facial_status='VERIFIED')
        with self.assertRaises(ValidationError):
            verification.full_clean()

    def test_user_is_certified_only_after_both_checks_and_selfie(self):
        user = self.make_user('cert2@example.com', '+243900000004')
        verification = IdentityVerification(user=user, document_type='PASSPORT', document_file=self.make_document(), status='VERIFIED', facial_status='VERIFIED', facial_photo=self.make_facial_photo())
        verification.save()
        user.refresh_from_db()
        self.assertTrue(user.is_certified)
        self.assertFalse(user.profile_photo)

    def test_closed_document_can_be_validated_again(self):
        user = self.make_user('closed-file@example.com', '+243900000012')
        verification = IdentityVerification(user=user, document_type='PASSPORT', document_file=self.make_document(), status='REJECTED', facial_status='PENDING')
        verification.save()
        verification.document_file.open('rb')
        verification.document_file.close()
        verification.status = 'PENDING'
        verification.full_clean()
        verification.save()
        self.assertEqual(verification.status, 'PENDING')

    def test_closed_facial_photo_can_be_validated_again(self):
        user = self.make_user('closed-face@example.com', '+243900000013')
        verification = IdentityVerification(user=user, document_type='PASSPORT', document_file=self.make_document(), facial_photo=self.make_facial_photo(), status='REJECTED', facial_status='PENDING')
        verification.save()
        verification.facial_photo.open('rb')
        verification.facial_photo.close()
        verification.full_clean()

    def test_user_manager_rejects_empty_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='A-secure-password-123', phone='+243900000005', last_name='Test', first_name='User')

    def test_superuser_manager_sets_required_flags(self):
        admin = User.objects.create_superuser(email='admin@example.com', password='A-secure-password-123', phone='+243900000006', last_name='Admin', first_name='User')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_pending_kyc_cannot_be_submitted_twice(self):
        user = self.make_user('duplicate@example.com', '+243900000008')
        self.client.force_login(user)
        first = self.client.post(reverse('certification'), {'document_type': 'PASSPORT', 'document_file': self.make_document('first.pdf')})
        self.assertEqual(first.status_code, 302)
        verification = IdentityVerification.objects.get(user=user)
        original_name = verification.document_file.name
        second = self.client.post(reverse('certification'), {'document_type': 'VOTER_CARD', 'document_file': self.make_document('second.pdf')})
        self.assertEqual(second.status_code, 302)
        verification.refresh_from_db()
        self.assertEqual(verification.pk, IdentityVerification.objects.get(user=user).pk)
        self.assertEqual(verification.document_file.name, original_name)
        self.assertEqual(verification.document_type, 'PASSPORT')
        self.assertEqual(IdentityVerification.objects.filter(user=user).count(), 1)

    def test_verified_kyc_cannot_be_replaced(self):
        user = self.make_user('verified@example.com', '+243900000009')
        IdentityVerification.objects.create(user=user, document_type='PASSPORT', document_file=self.make_document(), facial_photo=self.make_facial_photo(), status='VERIFIED', facial_status='VERIFIED')
        self.client.force_login(user)
        response = self.client.post(reverse('certification'), {'document_type': 'VOTER_CARD', 'document_file': self.make_document('replacement.pdf')})
        self.assertEqual(response.status_code, 302)
        verification = IdentityVerification.objects.get(user=user)
        self.assertEqual(verification.status, 'VERIFIED')
        self.assertEqual(verification.document_type, 'PASSPORT')

    def test_rejected_kyc_can_be_replaced(self):
        user = self.make_user('retry@example.com', '+243900000010')
        old = IdentityVerification.objects.create(user=user, document_type='PASSPORT', document_file=self.make_document(), status='REJECTED', facial_status='PENDING', rejection_reason='Document illisible')
        self.client.force_login(user)
        response = self.client.post(reverse('certification'), {'document_type': 'VOTER_CARD', 'document_file': self.make_document('replacement.pdf')})
        self.assertEqual(response.status_code, 302)
        verification = IdentityVerification.objects.get(user=user)
        self.assertEqual(verification.pk, old.pk)
        self.assertEqual(verification.status, 'PENDING')
        self.assertEqual(verification.document_type, 'VOTER_CARD')
        self.assertEqual(verification.rejection_reason, '')
