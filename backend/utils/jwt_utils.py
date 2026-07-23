import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'neonoble-ramp-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Short-lived access token (15 min) + long-lived refresh token (7 days).
# This limits the blast radius of a stolen access token while keeping UX seamless
# via silent refresh from the frontend.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS', '7'))
PASSWORD_RESET_TTL_HOURS = int(os.environ.get('PASSWORD_RESET_TTL_HOURS', '24'))


def _build_payload(user_id: str, email: str, role: str, expires_at: datetime, token_type: str) -> dict:
    return {
        'sub': user_id,
        'email': email,
        'role': role,
        'type': token_type,
        'exp': expires_at,
        'iat': datetime.now(timezone.utc),
    }


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create a short-lived JWT access token (15 min by default)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = _build_payload(user_id, email, role, expire, 'access')
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, email: str, role: str) -> str:
    """Create a long-lived JWT refresh token (7 days by default)."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = _build_payload(user_id, email, role, expire, 'refresh')
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token (rejects refresh tokens)."""
    payload = _decode(token)
    if payload is None:
        return None
    # Backwards compatibility: pre-existing tokens have no 'type' field — treat as access.
    if payload.get('type', 'access') != 'access':
        logger.warning("Token type mismatch: expected access token")
        return None
    return payload


def decode_refresh_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT refresh token (rejects access tokens)."""
    payload = _decode(token)
    if payload is None:
        return None
    if payload.get('type') != 'refresh':
        logger.warning("Token type mismatch: expected refresh token")
        return None
    return payload


def create_password_reset_token(user_id: str, jti: str) -> str:
    """Create a single-use password-reset token.
    `jti` is persisted on the user document — when the user resets, we
    clear the stored jti so the same token can't be replayed.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TTL_HOURS)
    payload = {
        'sub': user_id,
        'jti': jti,
        'type': 'password_reset',
        'exp': expire,
        'iat': datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_password_reset_token(token: str) -> Optional[dict]:
    """Decode + validate a password-reset token (rejects other types)."""
    payload = _decode(token)
    if payload is None:
        return None
    if payload.get('type') != 'password_reset':
        logger.warning("Token type mismatch: expected password_reset token")
        return None
    return payload


def _decode(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
