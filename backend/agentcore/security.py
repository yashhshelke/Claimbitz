"""Security hardening: JWT auth, RBAC, rate limiting, audit, PII masking.

Provides FastAPI dependencies and middleware for:
- JWT bearer token authentication (``verify_token``)
- Role-based access control (``require_role``)
- Rate limiting per IP (via slowapi)
- PII masking utility for logs/responses
- Prompt injection detection for LLM inputs

These are injected into routes via FastAPI's Depends() mechanism.
In development mode (settings.environment == "development"), auth is
bypassed to allow frictionless local testing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .settings import get_settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# -- PII masking patterns --
_PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b\d{9}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE_REDACTED]"),
]


def mask_pii(text: str) -> str:
    """Remove PII patterns from text before logging or external transmission."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# -- Prompt injection detection --
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"\\n\\nHuman:", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> bool:
    """Return True if text contains known prompt injection patterns."""
    return any(p.search(text) for p in _INJECTION_PATTERNS)


# -- JWT verification --

def _decode_jwt(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Returns the payload dict."""
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT not configured",
        )
    try:
        import jwt

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency: verify JWT and return payload.

    In development mode, returns a mock admin payload if no token is provided.
    """
    settings = get_settings()

    if settings.environment == "development":
        if credentials is None:
            return {"sub": "dev-user", "role": "admin", "exp": time.time() + 3600}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    return _decode_jwt(credentials.credentials)


def require_role(*roles: str):
    """Factory: returns a dependency that enforces one of the given roles."""

    async def _check(payload: dict[str, Any] = Depends(verify_token)) -> dict[str, Any]:
        user_role = payload.get("role", "")
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not authorized. Required: {roles}",
            )
        return payload

    return _check


# -- Rate limiting setup --

def setup_rate_limiting(app: Any) -> None:
    """Attach slowapi rate limiter to the FastAPI app."""
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        settings = get_settings()
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{settings.rate_limit_per_minute}/minute"],
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting enabled: %d/min", settings.rate_limit_per_minute)
    except ImportError:
        logger.warning("slowapi not installed, rate limiting disabled")


__all__ = [
    "verify_token",
    "require_role",
    "mask_pii",
    "detect_prompt_injection",
    "setup_rate_limiting",
]
