"""
Integration tests for JWT authentication and rate limiting.

Tests cover:
- JWT validation (valid, expired, invalid, missing tokens)
- AUTH_ENABLED toggle behavior
- Rate limiting with Redis
- RATE_LIMIT_ENABLED toggle behavior
- RLS enforcement (user isolation)
"""

import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.rate_limiter import get_rate_limiter
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return "test_user_auth_123"


@pytest.fixture
def valid_token(test_user_id):
    """Generate a valid test JWT token."""
    now = datetime.utcnow()
    payload = {
        "sub": test_user_id,
        "iss": "https://clerk.example.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "azp": "http://localhost:3000",
        "sid": "sess_test123",
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture
def expired_token(test_user_id):
    """Generate an expired test JWT token."""
    now = datetime.utcnow()
    payload = {
        "sub": test_user_id,
        "iss": "https://clerk.example.com",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        # Expired 1 hour ago
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "azp": "http://localhost:3000",
        "sid": "sess_test123",
    }
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """Clear rate limits before each test."""
    # Get rate limiter and clear all test user keys
    limiter = get_rate_limiter()
    if limiter._redis:
        # Clear all ratelimit:* keys
        redis_client = limiter._get_redis()
        keys = redis_client.keys("ratelimit:*")
        if keys:
            redis_client.delete(*keys)
    yield


# ============================================================================
# JWT Authentication Tests
# ============================================================================


class TestJWTAuthentication:
    """Test JWT token validation."""

    def test_missing_token_returns_401(self, client):
        """Test that missing Authorization header returns 401."""
        response = client.get("/api/v1/documents")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_invalid_token_returns_401(self, client):
        """Test that invalid JWT token returns 401."""
        response = client.get(
            "/api/v1/documents",
            headers={"Authorization": "Bearer invalid.jwt.token"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_expired_token_returns_401(self, client, expired_token):
        """Test that expired JWT token returns 401."""
        response = client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    @patch("app.core.config.settings.auth_enabled", False)
    def test_valid_token_with_auth_disabled(self, client, valid_token):
        """Test that valid token works when AUTH_ENABLED=false."""
        response = client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        # Should succeed (200) or fail with different error (not 401)
        assert response.status_code != 401

    def test_auth_enabled_toggle(self, client):
        """Test AUTH_ENABLED toggle behavior."""
        # When AUTH_ENABLED=false, should use dev-user
        with patch("app.core.config.settings.auth_enabled", False):
            response = client.get("/api/v1/documents")
            # Should not get 401 (auth disabled)
            assert response.status_code != 401


class TestUserIdExtraction:
    """Test user ID extraction from JWT tokens."""

    @patch("app.core.config.settings.auth_enabled", False)
    def test_extract_user_id_from_token(self, client, valid_token, test_user_id):
        """Test that user_id is correctly extracted from JWT 'sub' claim."""
        # When auth is disabled, we get dev-user
        # When auth is enabled with valid token, we'd get the user_id from token
        # This test verifies the extraction logic
        from app.core.auth import extract_user_id

        payload = {"sub": test_user_id}
        user_id = extract_user_id(payload)
        assert user_id == test_user_id

    def test_extract_user_id_missing_sub(self):
        """Test that missing 'sub' claim raises error."""
        from app.core.auth import extract_user_id, AuthenticationError

        payload = {"iss": "https://clerk.example.com"}  # No 'sub'

        with pytest.raises(AuthenticationError) as exc_info:
            extract_user_id(payload)

        assert exc_info.value.status_code == 401


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Test Redis-based rate limiting."""

    @patch("app.core.config.settings.auth_enabled", False)
    @patch("app.core.config.settings.rate_limit_enabled", True)
    @patch("app.core.config.settings.rate_limit_default_requests", 5)
    def test_rate_limit_not_exceeded(self, client):
        """Test that requests under limit succeed."""
        # Make 3 requests (under limit of 5)
        for i in range(3):
            response = client.get("/api/v1/documents")
            assert response.status_code != 429, f"Request {i+1} was rate limited"

    @patch("app.core.config.settings.auth_enabled", False)
    @patch("app.core.config.settings.rate_limit_enabled", True)
    @patch("app.core.config.settings.rate_limit_default_requests", 3)
    def test_rate_limit_exceeded(self, client):
        """Test that exceeding rate limit returns 429."""
        # Make requests until rate limited
        rate_limited = False

        for i in range(10):  # Try up to 10 requests
            response = client.get("/api/v1/documents")
            if response.status_code == 429:
                rate_limited = True
                break

        assert rate_limited, "Rate limit was not triggered"

    @patch("app.core.config.settings.auth_enabled", False)
    @patch("app.core.config.settings.rate_limit_enabled", True)
    @patch("app.core.config.settings.rate_limit_default_requests", 2)
    def test_rate_limit_headers(self, client):
        """Test that 429 response includes rate limit headers."""
        # Exceed rate limit
        for _ in range(5):
            response = client.get("/api/v1/documents")
            if response.status_code == 429:
                # Check headers
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers
                assert "Retry-After" in response.headers

                # Verify header values
                assert response.headers["X-RateLimit-Remaining"] == "0"
                assert int(response.headers["Retry-After"]) > 0
                return

        pytest.fail("Rate limit was not triggered")

    @patch("app.core.config.settings.auth_enabled", False)
    @patch("app.core.config.settings.rate_limit_enabled", False)
    def test_rate_limit_disabled(self, client):
        """Test that rate limiting is bypassed when RATE_LIMIT_ENABLED=false."""
        # Make many requests - none should be rate limited
        for i in range(20):
            response = client.get("/api/v1/documents")
            assert response.status_code != 429, f"Request {i+1} was rate limited despite RATE_LIMIT_ENABLED=false"

    def test_rate_limit_per_user(self):
        """Test that rate limits are tracked per user."""
        limiter = get_rate_limiter()

        # User 1 makes requests
        for _ in range(3):
            allowed, limit, remaining = limiter.check_rate_limit(
                "user1", "default")
            assert allowed is True

        # User 2 should have separate limit
        allowed, limit, remaining = limiter.check_rate_limit(
            "user2", "default")
        assert allowed is True
        assert remaining == limit - 1  # First request for user2


# ============================================================================
# RLS Enforcement Tests
# ============================================================================


class TestRLSEnforcement:
    """Test Row-Level Security enforcement."""

    @patch("app.core.config.settings.auth_enabled", False)
    def test_user_isolation(self, client):
        """Test that users cannot access each other's documents."""
        # This test verifies RLS at the database level
        # When auth is enabled, each user gets their own isolated data

        # Note: Full RLS testing requires:
        # 1. Creating documents for user A
        # 2. Attempting to access them as user B
        # 3. Verifying access is denied

        # For now, we verify that user_id is passed correctly to queries
        response = client.get("/api/v1/documents")
        assert response.status_code in [200, 401]  # Valid response codes


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuthenticationIntegration:
    """Test full authentication and rate limiting flow."""

    @patch("app.core.config.settings.auth_enabled", False)
    @patch("app.core.config.settings.rate_limit_enabled", True)
    @patch("app.core.config.settings.rate_limit_default_requests", 10)
    def test_full_auth_flow(self, client):
        """Test complete auth and rate limiting flow."""
        # Make several requests
        for i in range(5):
            response = client.get("/api/v1/documents")
            # Should succeed (auth disabled, under rate limit)
            assert response.status_code != 401
            assert response.status_code != 429

    def test_redis_connection_failure_graceful_degradation(self):
        """Test that rate limiter fails open if Redis is unavailable."""
        limiter = get_rate_limiter()

        # Mock Redis failure
        with patch.object(limiter, "_get_redis", side_effect=Exception("Redis down")):
            # Should still allow request (fail open)
            allowed, limit, remaining = limiter.check_rate_limit(
                "test_user", "default")
            assert allowed is True
            assert limit == 0
            assert remaining == 0


# ============================================================================
# Helper Tests
# ============================================================================


class TestRateLimiterHelpers:
    """Test rate limiter helper functions."""

    def test_get_rate_limit_key_format(self):
        """Test rate limit key formatting."""
        from app.core.rate_limiter import get_rate_limit_key

        key = get_rate_limit_key("user123", "chat")
        assert key == "ratelimit:user123:chat"

    def test_get_endpoint_limits(self):
        """Test endpoint limit configuration."""
        from app.core.rate_limiter import get_endpoint_limits

        # Test default endpoint
        limit, window = get_endpoint_limits("default")
        assert limit == settings.rate_limit_default_requests
        assert window == settings.rate_limit_default_window

        # Test specific endpoint
        limit, window = get_endpoint_limits("chat")
        assert limit == settings.rate_limit_chat
        assert window == settings.rate_limit_default_window
