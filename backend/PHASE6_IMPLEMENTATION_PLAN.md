# Phase 6: Authentication & Security - Implementation Plan

**Date:** January 25, 2026  
**Branch:** `feat/auth-security`  
**Status:** Planning Complete - Awaiting Approval

---

## 📋 Executive Summary

This plan implements production-ready authentication (Clerk JWT) and rate limiting (Redis) for all API endpoints. The implementation replaces hardcoded `user_id = "test_user_phase5"` with real JWT validation and adds Redis-based rate limiting to prevent abuse.

**Key Objectives:**

- ✅ Secure all endpoints with Clerk JWT authentication
- ✅ Implement Redis-based sliding window rate limiter
- ✅ Maintain backward compatibility with development toggle
- ✅ Enable curl-based testing with real/mock JWT tokens
- ✅ Ensure RLS policies are enforced with real user context

---

## 🔍 Current State Analysis

### Existing Infrastructure (Ready for Enhancement)

**✅ Schemas & Models:**

- All schemas use `user_id: str` (Clerk-compatible)
- Response models properly hide sensitive fields
- Error schemas include proper 401/403/429 responses
- No schema changes required

**✅ Database & Repositories:**

- All models use `user_id: str` (not UUID)
- RLS policies exist in Supabase
- Repositories ready for authenticated user context
- No database migrations required

**✅ API Endpoints:**

- `/api/v1/ingest` - Upload documents
- `/api/v1/documents` - List/delete documents
- `/api/v1/chat` - Chat with streaming
- All use `UserID` dependency (ready for JWT swap)

**✅ Dependencies (`app/api/deps.py`):**

- `get_current_user_id()` - Returns hardcoded user (Phase 5)
- `check_user_rate_limit()` - No-op placeholder (Phase 5)
- Type aliases ready: `UserID`, `RateLimitCheck`

**✅ Core Infrastructure:**

- `app/core/auth.py` - Empty file, ready for implementation
- `app/core/rate_limiter.py` - Placeholder with structure
- `app/core/config.py` - Settings manager with validators
- Error handlers for 401/403/429 already exist

---

## 📦 Dependencies to Install

### Required Packages

```toml
# JWT validation
"python-jose[cryptography]>=3.3.0"  # JWT decoding with RS256 support

# Rate limiting
"redis>=5.0.0"                       # Redis client for rate limiting
"hiredis>=2.3.0"                     # C parser for Redis (performance)

# Testing
"httpx>=0.28.0"                      # Already installed, used for auth tests
```

**Installation:**

```bash
cd backend
uv add python-jose[cryptography] redis hiredis
```

---

## 🏗️ Implementation Tasks

### Task 1: Update Environment Configuration

**File:** `backend/.env`

**Add Redis Configuration:**

```bash
# Redis Configuration (Rate Limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=                      # Empty for local dev
REDIS_SSL=false

# Authentication Configuration
AUTH_ENABLED=true                    # Toggle for dev/testing
CLERK_JWKS_CACHE_TTL=3600           # Cache JWKS for 1 hour
```

**File:** `backend/.env.example`

Update with same Redis and Auth configs (with placeholder values).

**Checklist:**

- [ ] Add Redis settings to `.env`
- [ ] Add Auth toggle to `.env`
- [ ] Update `.env.example` with documentation
- [ ] Verify Clerk keys already present (✅ confirmed)

---

### Task 2: Update Settings Configuration

**File:** `app/core/config.py`

**Add to Settings class:**

```python
# Clerk Authentication Settings
clerk_secret_key: str = Field(..., description="Clerk secret key", repr=False)
clerk_publishable_key: str = Field(..., description="Clerk publishable key")
clerk_issuer_url: str = Field(..., description="Clerk issuer URL")
clerk_jwks_cache_ttl: int = Field(default=3600, description="JWKS cache TTL in seconds")
auth_enabled: bool = Field(default=True, description="Enable JWT authentication")

# Redis Configuration
redis_host: str = Field(default="localhost", description="Redis host")
redis_port: int = Field(default=6379, description="Redis port")
redis_db: int = Field(default=0, description="Redis database number")
redis_password: str | None = Field(default=None, description="Redis password", repr=False)
redis_ssl: bool = Field(default=False, description="Use SSL for Redis connection")
redis_connection_pool_size: int = Field(default=10, description="Redis connection pool size")

# Rate Limiting Configuration
rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
rate_limit_default_requests: int = Field(default=100, description="Default requests per hour")
rate_limit_default_window: int = Field(default=3600, description="Rate limit window in seconds")
rate_limit_burst_multiplier: float = Field(default=1.5, description="Burst multiplier")

# Per-endpoint rate limits (requests per hour)
rate_limit_ingest: int = Field(default=20, description="Ingestion endpoint limit")
rate_limit_chat: int = Field(default=100, description="Chat endpoint limit")
rate_limit_documents: int = Field(default=200, description="Document listing limit")
```

**Add property:**

```python
@property
def redis_url(self) -> str:
    """Build Redis connection URL."""
    protocol = "rediss" if self.redis_ssl else "redis"
    auth = f":{self.redis_password}@" if self.redis_password else ""
    return f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
```

**Checklist:**

- [ ] Add Clerk settings fields
- [ ] Add Redis settings fields
- [ ] Add rate limiting config fields
- [ ] Add `redis_url` property
- [ ] Test settings loading with `pytest` or manual check

---

### Task 3: Implement JWT Authentication

**File:** `app/core/auth.py`

**Implementation Overview:**

```python
# 1. JWKS Fetching & Caching
class JWKSClient:
    """Fetches and caches Clerk's JWKS (public keys)."""
    - fetch_jwks() -> dict
    - get_signing_key(token: str) -> dict
    - Cache using TTL from settings

# 2. JWT Token Validation
def verify_jwt_token(token: str) -> dict:
    """
    Validates JWT token from Authorization header.

    Steps:
    1. Decode JWT header to get 'kid' (key ID)
    2. Fetch matching public key from JWKS
    3. Verify signature using RS256
    4. Validate claims (iss, exp, aud)
    5. Return decoded payload

    Raises:
    - AuthenticationError: Invalid/expired token
    """

# 3. User ID Extraction
def extract_user_id(payload: dict) -> str:
    """
    Extracts user_id from JWT 'sub' claim.

    Clerk format: "user_2bXYZ123"
    """

# 4. FastAPI Dependency
async def get_current_user(
    authorization: str = Header(None)
) -> str:
    """
    FastAPI dependency for JWT authentication.

    Flow:
    1. Check AUTH_ENABLED flag
    2. If disabled: return "test_user_dev"
    3. If enabled: validate JWT and extract user_id

    Usage:
        @router.get("/documents")
        def list_docs(user_id: Annotated[str, Depends(get_current_user)]):
            ...
    """
```

**Key Implementation Details:**

- **JWKS URL:** `{CLERK_ISSUER_URL}/.well-known/jwks.json`
- **Algorithm:** RS256 (asymmetric signing)
- **Required Claims:** `iss`, `sub`, `exp`, `iat`
- **Issuer Validation:** Must match `CLERK_ISSUER_URL`
- **Caching:** In-memory cache with TTL (no Redis needed)
- **Error Handling:** Raise `AuthenticationError` for all failures

**Checklist:**

- [ ] Implement `JWKSClient` class
- [ ] Implement `verify_jwt_token()` function
- [ ] Implement `extract_user_id()` function
- [ ] Implement `get_current_user()` FastAPI dependency
- [ ] Add comprehensive error messages
- [ ] Add logging for auth failures
- [ ] Test with mock JWT tokens

---

### Task 4: Implement Redis Rate Limiter

**File:** `app/core/rate_limiter.py`

**Implementation Overview:**

```python
# 1. Redis Client Singleton
class RedisRateLimiter:
    """
    Redis-based sliding window rate limiter.

    Uses Redis ZSET with timestamps for efficient sliding window:
    - Key: "ratelimit:{user_id}:{endpoint}"
    - Value: Sorted set of request timestamps
    - Score: Unix timestamp
    """

    def __init__(self):
        self.client = redis.from_url(settings.redis_url)
        self.pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_connection_pool_size
        )

    def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, dict]:
        """
        Check if user has exceeded rate limit.

        Algorithm (Sliding Window):
        1. Current time: now = time.time()
        2. Window start: now - window_seconds
        3. Remove old entries: ZREMRANGEBYSCORE key -inf window_start
        4. Count requests: ZCARD key
        5. If count < max: ZADD key now now (add this request)
        6. Set expiry: EXPIRE key window_seconds
        7. Return (allowed, metadata)

        Returns:
            (allowed: bool, metadata: dict)
            - allowed: True if within limit
            - metadata: {
                "requests_made": int,
                "requests_remaining": int,
                "reset_at": int (Unix timestamp),
                "retry_after": int (seconds until reset)
              }
        """

# 2. Helper Functions
def get_rate_limit_key(user_id: str, endpoint: str) -> str:
    """Build Redis key: ratelimit:user_123:chat"""

def get_endpoint_limits(endpoint: str) -> tuple[int, int]:
    """
    Get limit config for endpoint.

    Returns: (max_requests, window_seconds)

    Mapping:
    - /api/v1/ingest -> (20, 3600)
    - /api/v1/chat -> (100, 3600)
    - /api/v1/documents -> (200, 3600)
    - default -> (100, 3600)
    """

# 3. Singleton Instance
_rate_limiter: RedisRateLimiter | None = None

def get_rate_limiter() -> RedisRateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter()
    return _rate_limiter
```

**Checklist:**

- [ ] Implement `RedisRateLimiter` class
- [ ] Implement sliding window algorithm with ZSET
- [ ] Add connection pooling
- [ ] Add error handling for Redis failures
- [ ] Add logging for rate limit events
- [ ] Add metrics (requests remaining, reset time)
- [ ] Test with local Redis instance

---

### Task 5: Update API Dependencies

**File:** `app/api/deps.py`

**Changes:**

```python
# OLD (Phase 5):
def get_current_user_id() -> str:
    return "test_user_phase5"

# NEW (Phase 6):
async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None
) -> str:
    """
    Extract user ID from JWT token.

    If AUTH_ENABLED=false: Returns "test_user_dev"
    If AUTH_ENABLED=true: Validates JWT and returns user_id
    """
    from app.core.auth import get_current_user
    from app.core.config import settings

    if not settings.auth_enabled:
        return "test_user_dev"

    # Validate JWT and extract user_id
    return await get_current_user(authorization)


# OLD (Phase 5):
async def check_user_rate_limit(user_id: UserID) -> None:
    pass  # No-op

# NEW (Phase 6):
async def check_user_rate_limit(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> None:
    """
    Check rate limit for current user and endpoint.

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    from app.core.rate_limiter import get_rate_limiter, get_endpoint_limits
    from app.core.config import settings

    if not settings.rate_limit_enabled:
        return

    # Get endpoint from request path
    endpoint = request.url.path
    max_requests, window = get_endpoint_limits(endpoint)

    # Check rate limit
    rate_limiter = get_rate_limiter()
    allowed, metadata = rate_limiter.check_rate_limit(
        user_id, endpoint, max_requests, window
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(metadata["reset_at"]),
                "Retry-After": str(metadata["retry_after"])
            }
        )
```

**Checklist:**

- [ ] Update `get_current_user_id()` to use JWT auth
- [ ] Update `check_user_rate_limit()` to use Redis
- [ ] Add proper error handling
- [ ] Add rate limit headers to responses
- [ ] Test with AUTH_ENABLED toggle

---

### Task 6: Protect All API Endpoints

**Files to Update:**

- `app/api/v1/ingest.py`
- `app/api/v1/documents.py`
- `app/api/v1/chat.py`

**Changes Required:**

All endpoints already use `UserID` dependency - **NO CHANGES NEEDED** to endpoint signatures!

**Example (already correct):**

```python
@router.post("/ingest")
async def ingest_document(
    user_id: UserID,  # ✅ Already using dependency
    file: UploadFile = File(...)
):
    # user_id is now extracted from JWT automatically
    ...
```

**What Happens Automatically:**

1. `UserID` = `Annotated[str, Depends(get_current_user_id)]`
2. `get_current_user_id()` now validates JWT
3. If invalid: Raises `AuthenticationError` → 401 response
4. If valid: Extracts `user_id` from token
5. RLS policies automatically enforced in Supabase

**Optional Enhancement:**
Add rate limit dependency to endpoints that need stricter limits:

```python
@router.post("/ingest")
async def ingest_document(
    _: RateLimitCheck,  # Add this line
    user_id: UserID,
    file: UploadFile = File(...)
):
    ...
```

**Checklist:**

- [ ] Verify all endpoints use `UserID` dependency (already done)
- [ ] Optionally add `RateLimitCheck` to high-cost endpoints
- [ ] Test 401 responses for missing/invalid JWT
- [ ] Test 403 for RLS violations (user trying to access other's data)
- [ ] Test 429 for rate limit exceeded

---

### Task 7: Docker Compose for Redis

**File:** `backend/docker-compose.yml` (new file)

**Contents:**

```yaml
version: "3.8"

services:
  redis:
    image: redis:7-alpine
    container_name: integration-forge-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  redis_data:
    driver: local
```

**Usage:**

```bash
cd backend
docker-compose up -d      # Start Redis
docker-compose down       # Stop Redis
docker-compose logs redis # View logs
```

**Checklist:**

- [ ] Create `docker-compose.yml`
- [ ] Test Redis startup: `docker-compose up -d`
- [ ] Verify connection: `redis-cli ping` → PONG
- [ ] Update `.gitignore` to exclude Redis data

---

### Task 8: Testing Tools & Scripts

#### 8.1 JWT Token Generator Script

**File:** `backend/scripts/generate_test_jwt.py` (new file)

**Purpose:** Generate valid JWT tokens for testing without Clerk UI

```python
"""
Generate test JWT tokens for local development.

Usage:
    python scripts/generate_test_jwt.py --user-id user_test_123
    python scripts/generate_test_jwt.py --user-id user_test_123 --expires-in 3600
"""

import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def generate_test_token(
    user_id: str = "user_test_dev",
    expires_in: int = 3600
) -> str:
    """
    Generate a test JWT token.

    Note: This uses HMAC (HS256) for simplicity in testing.
    Real Clerk tokens use RSA (RS256).
    """
    payload = {
        "sub": user_id,
        "iss": settings.clerk_issuer_url,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=expires_in)
    }

    return jwt.encode(
        payload,
        settings.clerk_secret_key,
        algorithm="HS256"
    )
```

**Checklist:**

- [ ] Create script
- [ ] Test token generation
- [ ] Document usage in README

#### 8.2 Curl Test Scripts

**File:** `backend/scripts/test_auth_curl.sh` (new file)

**Purpose:** Test authentication with curl

```bash
#!/bin/bash
# Test authentication with curl

BASE_URL="http://localhost:8000"

# 1. Get test JWT token
echo "Generating test JWT token..."
TOKEN=$(python scripts/generate_test_jwt.py --user-id user_test_123)

# 2. Test authenticated request
echo -e "\n✅ Testing authenticated request..."
curl -X GET "$BASE_URL/api/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# 3. Test missing token (should return 401)
echo -e "\n❌ Testing missing token..."
curl -X GET "$BASE_URL/api/v1/documents" \
  -H "Content-Type: application/json"

# 4. Test invalid token (should return 401)
echo -e "\n❌ Testing invalid token..."
curl -X GET "$BASE_URL/api/v1/documents" \
  -H "Authorization: Bearer invalid_token_here" \
  -H "Content-Type: application/json"
```

**Checklist:**

- [ ] Create auth test script
- [ ] Create rate limit test script
- [ ] Test all scenarios (valid, invalid, expired, missing)
- [ ] Document curl examples

#### 8.3 Integration Tests

**File:** `backend/tests/test_authentication.py` (new file)

**Test Cases:**

```python
class TestJWTAuthentication:
    - test_valid_jwt_token()
    - test_expired_jwt_token()
    - test_invalid_signature()
    - test_missing_authorization_header()
    - test_malformed_jwt_token()
    - test_wrong_issuer()
    - test_user_id_extraction()
    - test_auth_disabled_fallback()

class TestRateLimiting:
    - test_rate_limit_not_exceeded()
    - test_rate_limit_exceeded()
    - test_rate_limit_reset()
    - test_rate_limit_headers()
    - test_different_endpoints_separate_limits()
    - test_redis_connection_failure()
    - test_rate_limit_disabled()

class TestEndpointSecurity:
    - test_document_list_requires_auth()
    - test_document_delete_requires_auth()
    - test_chat_requires_auth()
    - test_ingest_requires_auth()
    - test_rls_enforcement()  # User A can't see User B's docs
```

**Checklist:**

- [ ] Create test file
- [ ] Implement all test cases
- [ ] Mock Redis for unit tests
- [ ] Use real Redis for integration tests
- [ ] Test RLS enforcement with multiple users

---

### Task 9: Documentation & Error Messages

#### 9.1 Error Response Examples

**File:** `app/schemas/responses.py` (update)

Add examples for auth errors:

```python
# 401 Unauthorized Example
{
    "error": "AuthenticationError",
    "message": "Invalid or expired JWT token",
    "status_code": 401,
    "details": {
        "hint": "Obtain a new token from Clerk authentication"
    }
}

# 429 Rate Limit Example
{
    "error": "RateLimitError",
    "message": "Rate limit exceeded. Please try again later.",
    "status_code": 429,
    "details": {
        "limit": 100,
        "window": "1 hour",
        "reset_at": 1706198400,
        "retry_after": 3456
    }
}
```

#### 9.2 Setup Guide

**File:** `backend/docs/PHASE6_AUTH_SETUP.md` (new file)

**Contents:**

- How to obtain Clerk keys
- How to start Redis
- How to generate test JWT tokens
- How to test with curl
- How to disable auth for development
- Troubleshooting guide

**Checklist:**

- [ ] Update error response examples
- [ ] Create setup guide
- [ ] Update main README.md
- [ ] Add inline code comments
- [ ] Update `.env.example`

---

### Task 10: Update Session Log & Roadmap

**File:** `backend/CONTEXT.md`

Add Session 8 summary with:

- What was implemented
- Key decisions made
- Testing results
- Next steps

**File:** `backend/TODOS.md`

Mark Phase 6 as complete:

- ✅ Checkpoint 6: Authentication & Security

**Checklist:**

- [ ] Update CONTEXT.md
- [ ] Update TODOS.md
- [ ] Document any deviations from plan
- [ ] Note any tech debt for Phase 7

---

## 🧪 Testing Strategy

### Unit Tests (Mock Dependencies)

1. **JWT Validation:**
   - Mock JWKS responses
   - Test all error cases
   - Test claim validation

2. **Rate Limiting:**
   - Mock Redis client
   - Test sliding window algorithm
   - Test limit calculations

### Integration Tests (Real Services)

1. **End-to-End Auth:**
   - Real Clerk test tokens
   - Real Supabase RLS enforcement
   - Multi-user scenarios

2. **End-to-End Rate Limiting:**
   - Real Redis instance
   - Concurrent request testing
   - Window reset verification

### Manual Testing Checklist

- [ ] Generate test JWT with script
- [ ] Test valid token with curl
- [ ] Test expired token (401)
- [ ] Test invalid signature (401)
- [ ] Test missing token (401)
- [ ] Test rate limit exceeded (429)
- [ ] Test RLS (user A cannot access user B's docs)
- [ ] Test auth disabled mode (AUTH_ENABLED=false)
- [ ] Test rate limit disabled mode (RATE_LIMIT_ENABLED=false)

---

## 🚨 Important Notes & Gotchas

### 1. JWT Algorithm: RS256 vs HS256

**Clerk uses RS256 (asymmetric):**

- Public key from JWKS verifies signature
- Private key stays with Clerk (secure)
- Must fetch JWKS from Clerk endpoint

**Test tokens use HS256 (symmetric):**

- Single secret key for sign + verify
- Simpler for local development
- Not compatible with real Clerk tokens

**Solution:** Support both algorithms, detect from JWT header.

### 2. Redis Connection Handling

**Important:** Redis connections must be:

- Pooled (don't create new connection per request)
- Reused (singleton pattern)
- Gracefully closed on shutdown

**Wrong:**

```python
def check_limit(user_id):
    redis = redis.Redis()  # ❌ New connection every request
```

**Right:**

```python
_client = redis.ConnectionPool(...)  # ✅ Pool created once
def check_limit(user_id):
    redis = redis.Redis(connection_pool=_client)
```

### 3. RLS with Service Role Key

**Problem:** Backend uses `SUPABASE_SERVICE_ROLE_KEY` which **bypasses RLS**.

**Solution:** For auth to work with RLS:

- Option A: Use Supabase Auth (not compatible with Clerk)
- Option B: Use `user_id` in WHERE clauses explicitly
- Option C: Use Supabase REST API with anon key + JWT

**Current Implementation:** Option B (manual user_id filtering)

- All repository methods already filter by `user_id`
- Service role key still used, but user_id enforced in app layer

### 4. AUTH_ENABLED Toggle

**Purpose:** Allow testing without JWT validation

**When to disable:**

- Local development
- Integration tests
- Debugging

**When to enable:**

- Production (always)
- Staging
- Manual auth testing

**Default:** `AUTH_ENABLED=true` (secure by default)

### 5. Rate Limit Granularity

**Per-User vs Per-Endpoint:**

Current implementation: **Per-user AND per-endpoint**

- Key format: `ratelimit:user_123:chat`
- Different limits for different endpoints
- User can make 20 ingestions + 100 chats per hour

**Alternative:** Global per-user

- Key format: `ratelimit:user_123`
- Single limit across all endpoints
- Simpler but less flexible

**Decision:** Per-endpoint for better UX.

---

## 📊 Success Criteria

Phase 6 is complete when:

- [ ] All dependencies installed
- [ ] All configuration added to `.env`
- [ ] JWT authentication implemented and tested
- [ ] Redis rate limiter implemented and tested
- [ ] All endpoints protected with auth
- [ ] Docker Compose for Redis working
- [ ] Test scripts (JWT generator, curl examples) created
- [ ] Integration tests passing (auth + rate limiting)
- [ ] Manual testing completed (curl + browser)
- [ ] Documentation updated (CONTEXT.md, TODOS.md, setup guide)
- [ ] RLS enforcement verified with multiple users
- [ ] Error messages clear and helpful
- [ ] Code committed to `feat/auth-security` branch
- [ ] Ready for PR review

---

## 🔄 Rollback Plan

If issues arise during implementation:

1. **Auth Breaking Endpoints:**
   - Set `AUTH_ENABLED=false` in `.env`
   - Revert to hardcoded user_id

2. **Redis Connection Issues:**
   - Set `RATE_LIMIT_ENABLED=false` in `.env`
   - Rate limiting becomes no-op

3. **Critical Bugs:**
   - Revert branch to main
   - Create hotfix for blocking issues
   - Resume Phase 6 after fix

---

## 📝 Implementation Order (Recommended)

1. **Setup (30 min):**
   - Install dependencies
   - Add Redis config to `.env`
   - Start Redis with Docker Compose

2. **Config (15 min):**
   - Update `app/core/config.py`
   - Test settings loading

3. **JWT Auth (2 hours):**
   - Implement `app/core/auth.py`
   - Test JWT validation
   - Test user_id extraction

4. **Rate Limiting (1.5 hours):**
   - Implement `app/core/rate_limiter.py`
   - Test Redis connection
   - Test sliding window algorithm

5. **API Integration (30 min):**
   - Update `app/api/deps.py`
   - Test endpoints with auth
   - Test rate limiting

6. **Testing Tools (1 hour):**
   - Create JWT generator script
   - Create curl test scripts
   - Test manually

7. **Integration Tests (2 hours):**
   - Write auth tests
   - Write rate limit tests
   - Write RLS tests

8. **Documentation (30 min):**
   - Update CONTEXT.md
   - Update TODOS.md
   - Create setup guide

**Total Estimated Time:** 8-10 hours

---

## 🎯 Next Steps After Approval

1. **Confirm this plan** - Review and approve
2. **Start implementation** - Follow task order above
3. **Incremental commits** - Commit after each task
4. **Test continuously** - Run tests after each task
5. **Update this doc** - Check off completed tasks
6. **Request code review** - After all tasks complete

---

**End of Implementation Plan**

**Status:** ⏳ Awaiting approval to begin implementation  
**Questions/Concerns:** Please review and provide feedback before starting.
