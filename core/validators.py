from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def _read_upload_bytes(uploaded_file):
    """Read a Django upload/FieldFile without leaving it in a bad state.

    Model.save() calls validators again. KYC processing can legitimately close a
    FieldFile after reading it, so validators must not assume that ``seek()`` is
    safe on entry. If we open a closed file here, we close only the handle that
    we opened and never close a handle owned by the caller.
    """
    was_closed = bool(getattr(uploaded_file, 'closed', False))
    opened_here = False
    try:
        if was_closed:
            uploaded_file.open('rb')
            opened_here = True
        elif hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
        data = uploaded_file.read()
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError('Le contenu du fichier est invalide.')
        return bytes(data)
    except (OSError, ValueError, AttributeError) as exc:
        raise ValidationError('Impossible de lire le fichier envoyé.') from exc
    finally:
        if opened_here:
            try:
                uploaded_file.close()
            except (OSError, ValueError):
                pass
        elif hasattr(uploaded_file, 'seek') and not getattr(uploaded_file, 'closed', False):
            try:
                uploaded_file.seek(0)
            except (OSError, ValueError):
                pass


def validate_file_size(uploaded_file, max_bytes: int, label: str = 'Fichier') -> None:
    size = getattr(uploaded_file, 'size', None)
    if size is None:
        raise ValidationError(f'{label} invalide.')
    if size > max_bytes:
        raise ValidationError(f'{label} trop volumineux. Taille maximale : {max_bytes // (1024 * 1024)} Mo.')


def validate_image_upload(uploaded_file) -> None:
    validate_file_size(uploaded_file, MAX_IMAGE_SIZE, 'Image')
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError('Format d’image non autorisé. Utilisez JPG, JPEG, PNG ou WebP.')

    data = _read_upload_bytes(uploaded_file)
    try:
        from PIL import Image
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise ValidationError('Le fichier image est illisible ou invalide.') from exc


def validate_identity_document(uploaded_file) -> None:
    validate_file_size(uploaded_file, MAX_DOCUMENT_SIZE, 'Document')
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError('Format de document non autorisé. Utilisez PDF, JPG, JPEG ou PNG.')

    data = _read_upload_bytes(uploaded_file)
    if suffix == '.pdf':
        if not data.startswith(b'%PDF-'):
            raise ValidationError('Le fichier PDF est invalide.')
    else:
        # Reuse the same byte-level image validation without depending on the
        # current open/closed state of the Django upload object.
        try:
            from PIL import Image
            with Image.open(BytesIO(data)) as image:
                image.verify()
        except Exception as exc:
            raise ValidationError('Le document image est illisible ou invalide.') from exc


image_extension_validator = FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])
