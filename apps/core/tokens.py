import secrets

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac


def generate_raw_token():
    return secrets.token_urlsafe(32)


def hash_token(raw_token):
    return salted_hmac(
        "matrix_scanner.agent_token",
        raw_token,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def token_matches(raw_token, token_hash):
    return constant_time_compare(hash_token(raw_token), token_hash)
