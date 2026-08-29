import io
import re
import unicodedata
from datetime import date
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from .models import IdentityVerificationAnalysis, IdentityVerificationEvent


AUTO_VERIFY_THRESHOLD = 85
MANUAL_REVIEW_THRESHOLD = 60


def normalize_text(value):
    value = unicodedata.normalize('NFKD', value or '')
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r'[^A-Za-z0-9 ]+', ' ', value).upper()
    return re.sub(r'\s+', ' ', value).strip()


def _read_bytes(field):
    """Read a Django FieldFile while preserving its caller-owned state."""
    was_closed = bool(getattr(field, 'closed', False))
    opened_here = False
    try:
        if was_closed:
            field.open('rb')
            opened_here = True
        else:
            field.seek(0)
        return field.read()
    finally:
        if opened_here:
            try:
                field.close()
            except (OSError, ValueError):
                pass
        elif not getattr(field, 'closed', False):
            try:
                field.seek(0)
            except (OSError, ValueError):
                pass


def image_quality(image_bytes):
    try:
        from PIL import Image, ImageStat
        image = Image.open(io.BytesIO(image_bytes)).convert('L')
        width, height = image.size
        if min(width, height) < 500:
            return 35, 'Image trop petite.'
        variance = ImageStat.Stat(image).var[0]
        if variance < 35:
            return 45, 'Image peu contrastée ou potentiellement floue.'
        if min(width, height) < 800:
            return 70, 'Qualité acceptable mais perfectible.'
        return 95, 'Qualité suffisante.'
    except Exception as exc:
        return None, f'Contrôle image indisponible: {exc.__class__.__name__}.'


def extract_ocr(document_bytes, filename):
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == '.pdf':
            import pdfplumber
            with pdfplumber.open(io.BytesIO(document_bytes)) as pdf:
                text = '\n'.join((page.extract_text() or '') for page in pdf.pages)
            return text.strip(), 'pdfplumber'
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(io.BytesIO(document_bytes)), lang='fra+eng')
        return text.strip(), 'tesseract'
    except Exception:
        return '', 'unavailable'


def extract_identity_data(text):
    normalized = normalize_text(text)
    dates = re.findall(r'\b(19\d{2}|20\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b', text or '')
    expiry = None
    for match in dates:
        try:
            expiry = date(int(match[0]), int(match[1]), int(match[2]))
        except ValueError:
            continue
    name = ''
    for pattern in (
        r'(?:NOM|SURNAME|LAST NAME)\s*[:\-]?\s*([A-Z][A-Z \-]{2,})',
        r'(?:PRENOM|PRENOMS|GIVEN NAMES|FIRST NAME)\s*[:\-]?\s*([A-Z][A-Z \-]{2,})',
    ):
        found = re.search(pattern, normalized)
        if found:
            name = found.group(1).strip()
            break
    return {'normalized_text': normalized, 'extracted_name': name, 'expiry_date': expiry}


def account_name(user):
    return normalize_text(' '.join(filter(None, [user.last_name, user.postname, user.first_name])))


def name_match_score(extracted, user):
    expected = account_name(user)
    candidate = normalize_text(extracted)
    if not candidate or not expected:
        return None
    expected_tokens = set(expected.split())
    candidate_tokens = set(candidate.split())
    return round(100 * len(expected_tokens & candidate_tokens) / len(expected_tokens)) if expected_tokens else None


def face_correspondence(document_bytes, selfie_bytes, filename):
    """Never use heuristic image similarity as biometric identity proof."""
    return None, 'Correspondance faciale biométrique fiable non disponible: vérification manuelle requise.'


def fraud_signals(document_bytes, filename, quality_score):
    signals = []
    suffix = Path(filename).suffix.lower()
    if quality_score is not None and quality_score < 50:
        signals.append('quality_low')
    if suffix not in {'.pdf', '.jpg', '.jpeg', '.png'}:
        signals.append('unsupported_format')
    try:
        if suffix in {'.jpg', '.jpeg', '.png'}:
            from PIL import Image
            image = Image.open(io.BytesIO(document_bytes))
            exif = image.getexif()
            if exif and any(str(k) in {'306', '36867'} for k in exif.keys()):
                signals.append('metadata_present')
    except Exception:
        signals.append('image_integrity_check_failed')
    return signals


def process_identity_verification(verification):
    user = verification.user
    document_bytes = _read_bytes(verification.document_file)
    quality_score, quality_explanation = image_quality(document_bytes) if not verification.document_file.name.lower().endswith('.pdf') else (None, 'Contrôle qualité image non applicable au PDF.')
    text, ocr_engine = extract_ocr(document_bytes, verification.document_file.name)
    extracted = extract_identity_data(text)
    name_score = name_match_score(extracted['extracted_name'], user)
    expiry_ok = extracted['expiry_date'] is None or extracted['expiry_date'] >= date.today()
    fraud = fraud_signals(document_bytes, verification.document_file.name, quality_score)

    face_score = None
    face_explanation = 'Selfie non fourni.'
    if verification.facial_photo:
        face_score, face_explanation = face_correspondence(document_bytes, _read_bytes(verification.facial_photo), verification.document_file.name)

    checks = []
    if quality_score is not None:
        checks.append(quality_score >= 60)
    checks.append(bool(text) if ocr_engine != 'unavailable' else False)
    checks.append(name_score is not None and name_score >= 70)
    checks.append(expiry_ok)
    checks.append(not fraud or fraud == ['metadata_present'])
    checks.append(face_score is not None and face_score >= 70)

    available_scores = [s for s in (quality_score, name_score, face_score) if s is not None]
    base = sum(available_scores) / len(available_scores) if available_scores else 0
    fraud_penalty = 10 * len([x for x in fraud if x != 'metadata_present'])
    ocr_bonus = 10 if ocr_engine != 'unavailable' and text else 0
    confidence = round(max(0, min(100, base + ocr_bonus - fraud_penalty)))

    reasons = []
    if quality_explanation:
        reasons.append(quality_explanation)
    if name_score is None:
        reasons.append('Le nom n’a pas pu être extrait ou comparé automatiquement.')
    elif name_score < 70:
        reasons.append(f'Correspondance du nom insuffisante ({name_score}%).')
    if not expiry_ok:
        reasons.append('La pièce semble expirée.')
    if fraud and fraud != ['metadata_present']:
        reasons.append('Signaux techniques nécessitant une vérification humaine: ' + ', '.join(fraud) + '.')
    if face_score is None:
        reasons.append(face_explanation)
    elif face_score < 70:
        reasons.append(f'Correspondance faciale insuffisante ({face_score}%).')
    if ocr_engine == 'unavailable':
        reasons.append('OCR indisponible: passage en vérification manuelle.')

    dependencies_missing = ocr_engine == 'unavailable' or face_score is None
    if all(checks) and confidence >= AUTO_VERIFY_THRESHOLD and not dependencies_missing:
        decision, status, facial_status = 'AUTO_VERIFIED', 'VERIFIED', 'VERIFIED'
    elif confidence >= MANUAL_REVIEW_THRESHOLD or dependencies_missing:
        decision, status, facial_status = 'MANUAL_REVIEW', 'IN_REVIEW', 'IN_REVIEW'
    else:
        decision, status, facial_status = 'REJECTED', 'RETRY', 'RETRY'

    with transaction.atomic():
        analysis, _ = IdentityVerificationAnalysis.objects.select_for_update().get_or_create(verification=verification)
        analysis.quality_score = quality_score
        analysis.ocr_engine = ocr_engine
        analysis.ocr_text = text[:20000]
        analysis.extracted_name = extracted['extracted_name']
        analysis.name_match_score = name_score
        analysis.expiry_date = extracted['expiry_date']
        analysis.expiry_ok = expiry_ok
        analysis.fraud_signals = fraud
        analysis.face_match_score = face_score
        analysis.face_explanation = face_explanation
        analysis.confidence_score = confidence
        analysis.decision = decision
        analysis.explanation = ' '.join(reasons) or 'Tous les contrôles sont satisfaisants.'
        analysis.processed_at = timezone.now()
        analysis.save()

        old_status = verification.status
        old_face = verification.facial_status
        verification.status = status
        verification.facial_status = facial_status
        verification.rejection_reason = analysis.explanation if decision == 'REJECTED' else ''
        verification.verified_at = timezone.now() if decision == 'AUTO_VERIFIED' else None
        verification.save()
        IdentityVerificationEvent.objects.create(
            verification=verification,
            actor=None,
            event_type='AUTOMATED_CHECK',
            from_status=old_status,
            to_status=verification.status,
            from_facial_status=old_face,
            to_facial_status=verification.facial_status,
            reason=analysis.explanation,
            metadata={'confidence': confidence, 'decision': decision, 'ocr_engine': ocr_engine},
        )
    return analysis
