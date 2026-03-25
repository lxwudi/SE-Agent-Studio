from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from app.core.clock import utc_now
from app.core.config import settings


PBKDF2_ITERATIONS = 600_000


def utcnow() -> datetime:
    return utc_now()


def generate_uid() -> str:
    return uuid4().hex


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("utf-8")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("utf-8")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, encoded_salt, encoded_digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    iterations = int(iterations_text)
    salt = base64.urlsafe_b64decode(encoded_salt.encode("utf-8"))
    expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("utf-8"))
    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(user_uid: str) -> str:
    expires_at = utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_uid,
        "exp": int(expires_at.timestamp()),
        "iat": int(utcnow().timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError:
        return None
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        return None
    return subject
