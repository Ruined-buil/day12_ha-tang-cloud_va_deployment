import time
import redis
from fastapi import HTTPException
from app.config import settings

# Initialize Redis client
# Note: In production, you might want to handle connection errors gracefully
r = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

def check_rate_limit(user_id: str):
    """
    Checks the rate limit for a user using a sliding window with Redis.
    Limit: settings.rate_limit_per_minute (default 20, lab suggests 10).
    """
    if not r:
        # Fallback to no limit if Redis is not configured (for development)
        return

    now = time.time()
    key = f"rate_limit:{user_id}"
    window_start = now - 60

    try:
        pipeline = r.pipeline()
        # Remove old requests
        pipeline.zremrangebyscore(key, 0, window_start)
        # Count current requests
        pipeline.zcard(key)
        # Add current request
        pipeline.zadd(key, {str(now): now})
        # Set expiration for the whole set to clean up
        pipeline.expire(key, 60)
        
        results = pipeline.execute()
        current_count = results[1]

        if current_count >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
    except redis.RedisError:
        # If Redis is down, we might want to allow the request to keep the service running
        # or log an error. For this lab, we'll just continue.
        pass
