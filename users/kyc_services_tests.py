from unittest.mock import patch

from django.test import SimpleTestCase

from .kyc_services import extract_ocr, face_correspondence, normalize_text


class KYCDegradedProcessingTests(SimpleTestCase):
    def test_invalid_document_fails_closed_when_ocr_cannot_process(self):
        text, engine = extract_ocr(b'not-a-real-document', 'document.jpg')
        self.assertEqual(text, '')
        self.assertEqual(engine, 'unavailable')

    @patch.dict('sys.modules', {'pytesseract': None})
    def test_missing_tesseract_degrades_to_manual_review_signal(self):
        text, engine = extract_ocr(b'not-a-real-document', 'document.jpg')
        self.assertEqual(text, '')
        self.assertEqual(engine, 'unavailable')

    def test_face_matching_never_returns_heuristic_biometric_approval(self):
        score, explanation = face_correspondence(b'document', b'selfie', 'document.jpg')
        self.assertIsNone(score)
        self.assertIn('vérification manuelle', explanation)

    def test_normalization_is_deterministic_for_identity_matching(self):
        self.assertEqual(normalize_text('Élise Ntambwé'), 'ELISE NTAMBWE')
