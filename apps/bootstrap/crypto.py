import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError


def _fernet():
    raw_key = settings.BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY
    if not raw_key:
        raise ImproperlyConfigured("BOOTSTRAP_CREDENTIAL_ENCRYPTION_KEY is required for bootstrap credentials.")
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_payload(payload):
    return _fernet().encrypt(payload.encode("utf-8")).decode("ascii")


def decrypt_payload(encrypted_payload):
    try:
        return _fernet().decrypt(encrypted_payload.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValidationError("Bootstrap credential payload cannot be decrypted.") from exc

