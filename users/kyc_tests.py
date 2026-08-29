import io
from unittest.mock import patch

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .kyc_services import process_identity_verification
from .models import IdentityVerification, IdentityVerificationEvent, User


def image_file(name='document.jpg', size=(1200, 900)):
    buffer = io.BytesIO()
    Image.effect_noise(size, 70).convert('RGB').save(buffer, format='JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


class AutomatedKycPipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='auto-kyc@example.com', password='A-secure-password-123',
            phone='+243900009111', last_name='NTAMBWE', first_name='ELITE',
        )
        self.verification = IdentityVerification.objects.create(
            user=self.user,
            document_type='PASSPORT',
            document_file=image_file(),
            facial_photo=image_file('selfie.jpg'),
        )

    @patch('users.kyc_services.face_correspondence', return_value=(95, 'test face match'))
    @patch('users.kyc_services.extract_ocr', return_value=('NOM: NTAMBWE\nPRENOM: ELITE', 'tesseract'))
    def test_all_checks_pass_auto_certifies(self, _ocr, _face):
        analysis = process_identity_verification(self.verification)
        self.verification.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(analysis.decision, 'AUTO_VERIFIED')
        self.assertEqual(self.verification.status, 'VERIFIED')
        self.assertEqual(self.verification.facial_status, 'VERIFIED')
        self.assertTrue(self.user.is_certified)
        self.assertTrue(IdentityVerificationEvent.objects.filter(event_type='AUTOMATED_CHECK').exists())

    @patch('users.kyc_services.extract_ocr', return_value=('', 'unavailable'))
    @patch('users.kyc_services.face_correspondence', return_value=(None, 'OpenCV indisponible'))
    def test_missing_dependencies_route_to_manual_review(self, _ocr, _face):
        analysis = process_identity_verification(self.verification)
        self.verification.refresh_from_db()
        self.assertEqual(analysis.decision, 'MANUAL_REVIEW')
        self.assertEqual(self.verification.status, 'IN_REVIEW')
        self.assertEqual(self.verification.facial_status, 'IN_REVIEW')

    def test_normalization(self):
        from .kyc_services import normalize_text
        self.assertEqual(normalize_text(' Ntambwé  Élite '), 'NTAMBWE ELITE')
