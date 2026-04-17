import time
import redis
from fastapi import HTTPException
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

def check_and_record_cost(input_tokens: int, output_tokens: int):
    """
    Checks if the daily budget is exceeded and records the cost of the current request.
    Formula: (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    """
    if not r:
        return

    today = time.strftime("%Y-%m-%d")
    key = f"cost_guard:daily:{today}"
    
    try:
        current_cost = float(r.get(key) or 0.0)
        
        if current_cost >= settings.daily_budget_usd:
            raise HTTPException(
                status_code=503, 
                detail="Daily budget exhausted. Try tomorrow."
            )
        
        # Calculate cost for current request
        cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
        
        # Atomically increment
        r.incrbyfloat(key, cost)
        # Set expiry to 48h to be safe
        r.expire(key, 172800)
        
    except redis.RedisError:
        # Fallback: allow request if Redis is down
        pass

def get_daily_cost() -> float:
    """Returns the total cost for today."""
    if not r:
        return 0.0
    today = time.strftime("%Y-%m-%d")
    key = f"cost_guard:daily:{today}"
    try:
        return float(r.get(key) or 0.0)
    except:
        return 0.0
