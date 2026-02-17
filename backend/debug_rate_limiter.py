
import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.rate_limiter import RedisRateLimiter

print(f"RATE_LIMIT_ENABLED: {settings.rate_limit_enabled}")
print(f"Redis URL: {settings.redis_url}")

limiter = RedisRateLimiter()
try:
    result = limiter.check_rate_limit("test_user", "default")
    print(f"check_rate_limit result: {result}")
except Exception as e:
    print(f"Error checking rate limit: {e}")
