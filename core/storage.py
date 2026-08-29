from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileSystemStorage(FileSystemStorage):
    """Storage outside MEDIA_ROOT so KYC files are never publicly served."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', Path(settings.PRIVATE_MEDIA_ROOT))
        kwargs.setdefault('base_url', None)
        super().__init__(*args, **kwargs)
