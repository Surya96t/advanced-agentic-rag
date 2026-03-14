"""JWT validation with Clerk."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for extracting tokens from Authorization header
security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom exception for authentication failures."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class JWKSClient:
    """Client for fetching and caching JWKS (JSON Web Key Set) from Clerk."""

    def __init__(self):
        self._jwks: Optional[dict] = None
        self._jwks_fetched_at: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=settings.clerk_jwks_cache_ttl)

    def get_jwks(self) -> dict:
        """
        Fetch JWKS from Clerk, with caching.

        Returns:
            dict: The JWKS data containing public keys for JWT verification.

        Raises:
            AuthenticationError: If JWKS cannot be fetched.
        """
        now = datetime.utcnow()

        # Return cached JWKS if still valid
        if self._jwks and self._jwks_fetched_at:
            if now - self._jwks_fetched_at < self._cache_ttl:
                return self._jwks

        # Fetch fresh JWKS
        jwks_url = f"{settings.clerk_issuer_url}/.well-known/jwks.json"
        try:
            response = httpx.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            self._jwks = response.json()
            self._jwks_fetched_at = now
            logger.info("Fetched fresh JWKS from Clerk")
            return self._jwks
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
            raise AuthenticationError(
                "Unable to verify token: JWKS unavailable")


# Singleton instance
_jwks_client = JWKSClient()


def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode a JWT token from Clerk.

    Args:
        token: The JWT token string.

    Returns:
        dict: The decoded token payload (claims).

    Raises:
        AuthenticationError: If token is invalid, expired, or verification fails.
    """
    try:
        # Get JWKS for signature verification
        jwks = _jwks_client.get_jwks()

        # Decode and verify token
        # python-jose will automatically select the correct key from JWKS
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer_url,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
            },
        )

        logger.debug(
            f"Successfully verified JWT for user: {payload.get('sub')}")
        return payload

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        logger.error(f"Expected issuer: {settings.clerk_issuer_url}")
        # Try to decode without verification to see actual issuer (for debugging issuer mismatches)
        try:
            import base64
            import json
            payload_b64 = token.split('.')[1]
            # Add padding if needed
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload_decoded = json.loads(base64.urlsafe_b64decode(payload_b64))
            # Only log issuer for debugging - do NOT log full claims (may contain PII)
            actual_issuer = payload_decoded.get('iss', 'unknown')
            logger.error(f"Actual token issuer: {actual_issuer}")
        except Exception as decode_error:
            logger.error(
                f"Could not decode token for debugging: {decode_error}")
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {e}")
        raise AuthenticationError("Token verification failed")


def extract_user_id(payload: dict) -> str:
    """
    Extract user ID from JWT payload.

    Args:
        payload: The decoded JWT payload.

    Returns:
        str: The user ID from the 'sub' claim.

    Raises:
        AuthenticationError: If 'sub' claim is missing.
    """
    user_id = payload.get("sub")
    if not user_id:
        logger.error("JWT payload missing 'sub' claim")
        raise AuthenticationError("Invalid token: missing user ID")
    return user_id


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    FastAPI dependency to get the current authenticated user ID.

    This dependency:
    - Extracts the JWT from the Authorization header
    - Verifies the token signature and claims
    - Returns the user ID
    - Respects AUTH_ENABLED toggle (returns mock user if disabled)

    Args:
        credentials: The HTTP Authorization credentials (Bearer token).

    Returns:
        str: The authenticated user ID.

    Raises:
        AuthenticationError: If authentication fails.
    """
    # If auth is disabled, return mock user for development
    if not settings.auth_enabled:
        logger.warning("Authentication disabled - using mock user 'dev-user'")
        return "dev-user"

    # Check if token is present
    if not credentials:
        logger.warning("No authorization header provided")
        raise AuthenticationError("Missing authentication token")

    # Verify and decode token
    token = credentials.credentials
    payload = verify_jwt_token(token)

    # Extract and return user ID
    user_id = extract_user_id(payload)
    return user_id
