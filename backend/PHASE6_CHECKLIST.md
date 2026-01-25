# Phase 6: Authentication & Security - Progress Checklist

**Track implementation progress - check off as you complete each task**

---

## 📦 Setup (30 min)

- [x] Install dependencies: `uv add python-jose[cryptography] redis hiredis`
- [x] Add Redis config to `.env` (see implementation plan Task 1)
- [x] Add Auth config to `.env` (AUTH_ENABLED, CLERK_JWKS_CACHE_TTL)
- [x] Update `.env.example` with new settings
- [x] Create `docker-compose.yml` for Redis
- [x] Start Redis: `docker-compose up -d`
- [x] Verify Redis: `docker exec -it integration-forge-redis redis-cli ping`

---

## 🔧 Configuration (15 min)

- [x] Update `app/core/config.py` - Add Clerk settings (secret, publishable, issuer, cache TTL)
- [x] Update `app/core/config.py` - Add Redis settings (host, port, db, password, SSL, pool size)
- [x] Update `app/core/config.py` - Add rate limit settings (enabled, default limits, per-endpoint limits)
- [x] Update `app/core/config.py` - Add `redis_url` property
- [x] Test settings load without errors: `python -c "from app.core.config import settings; print(settings.redis_url)"`

---

## 🔐 JWT Authentication (2 hours)

- [x] Implement `app/core/auth.py` - `JWKSClient` class (fetch and cache JWKS)
- [x] Implement `app/core/auth.py` - `verify_jwt_token()` (validate signature, claims, expiry)
- [x] Implement `app/core/auth.py` - `extract_user_id()` (get user_id from 'sub' claim)
- [x] Implement `app/core/auth.py` - `get_current_user()` FastAPI dependency (with AUTH_ENABLED toggle)
- [x] Add error handling (AuthenticationError for all failure cases)
- [x] Add logging for auth failures
- [ ] Test: Generate mock JWT and verify it decodes correctly

---

## ⏱️ Rate Limiting (1.5 hours)

- [x] Implement `app/core/rate_limiter.py` - `RedisRateLimiter` class (singleton, connection pool)
- [x] Implement sliding window algorithm (ZSET with timestamps, ZREMRANGEBYSCORE, ZCARD, ZADD)
- [x] Implement `get_rate_limit_key()` helper (format: "ratelimit:{user_id}:{endpoint}")
- [x] Implement `get_endpoint_limits()` helper (map endpoints to limits)
- [x] Implement `get_rate_limiter()` singleton getter
- [x] Add error handling for Redis connection failures
- [x] Add logging for rate limit events
- [x] Test: Manually call rate limiter and verify Redis keys created

---

## 🔌 API Integration (30 min)

- [x] Update `app/api/deps.py` - Replace `get_current_user_id()` body with JWT validation call
- [x] Update `app/api/deps.py` - Replace `check_user_rate_limit()` body with Redis rate limiter call
- [x] Add rate limit headers to 429 responses (X-RateLimit-Limit, X-RateLimit-Remaining, etc.)
- [x] Verify all endpoints already use `UserID` dependency (no changes needed to routes)
- [ ] Test: Start server, verify endpoints now require auth

---

## 🧪 Testing Tools (1 hour)

- [x] Create `scripts/generate_test_jwt.py` - Generate test JWT tokens with configurable user_id/expiry
- [x] Create `scripts/test_auth_curl.sh` - Test valid token, invalid token, missing token, expired token
- [x] Test scripts work: `python scripts/generate_test_jwt.py --user-id test123`
- [ ] Test curl script works: `bash scripts/test_auth_curl.sh`

---

## ✅ Integration Tests (2 hours)

- [x] Create `tests/test_authentication.py` - JWT validation tests (valid, expired, invalid, missing)
- [x] Add test for AUTH_ENABLED=false fallback
- [x] Add test for user_id extraction
- [x] Create rate limiting tests (not exceeded, exceeded, headers, reset)
- [x] Add test for RATE_LIMIT_ENABLED=false fallback
- [x] Add test for RLS enforcement (user A cannot access user B's docs)
- [x] Run tests: `pytest tests/test_authentication.py -v`
- [ ] All tests passing (15/17 passing - 2 rate limit tests need route updates)

---

## 🧑‍💻 Manual Testing (30 min)

- [ ] Generate test JWT: `python scripts/generate_test_jwt.py`
- [ ] Test valid token → 200 OK
- [ ] Test missing token → 401 Unauthorized
- [ ] Test invalid token → 401 Unauthorized
- [ ] Test expired token → 401 Unauthorized (may need to generate with --expires-in 1)
- [ ] Test rate limit: Make 101 rapid requests → 429 Too Many Requests
- [ ] Test RLS: Create two users, verify isolation
- [ ] Test toggles: AUTH_ENABLED=false, RATE_LIMIT_ENABLED=false

---

## 📝 Final Steps (30 min)

- [ ] Code review fixes (Code Rabbit feedback)
  - [x] Fix rate limiting config conflict (deprecated rate_limit_per_minute)
  - [x] Fix Redis URL password encoding (URL-encode special characters)
- [ ] Update `CONTEXT.md` - Add Session 8 summary
- [ ] Update `TODOS.md` - Mark Phase 6 as complete
- [ ] Commit all changes: `git add . && git commit -m "feat: implement Phase 6 - JWT auth and Redis rate limiting"`
- [ ] Push branch: `git push origin feat/auth-security`
- [ ] Create PR for review

---

## ✅ Definition of Done

Phase 6 is complete when ALL of the following are true:

- [ ] All code tasks completed above
- [ ] All tests passing (`pytest -v`)
- [ ] Manual testing verified (curl tests working)
- [ ] Redis running and connected
- [ ] JWT validation working (401 on invalid tokens)
- [ ] Rate limiting enforced (429 on exceeded limits)
- [ ] RLS verified (users cannot access each other's data)
- [ ] Code committed and pushed
- [ ] Ready for PR review

---

**Branch:** `feat/auth-security`  
**Time Invested:** ~8 hours (implementation + Code Rabbit fixes)  
**Status:** Implementation complete - Manual testing, documentation, and final PR pending  
**Progress:** Core auth + rate limiting implemented (31/49 tasks) | Code review fixes applied | Integration tests 15/17 passing
