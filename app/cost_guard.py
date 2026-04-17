import time
import redis
from fastapi import HTTPException
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

def _month_key() -> str:
    return time.strftime("%Y-%m")


def _user_budget_key(user_id: str) -> str:
    return f"budget:{user_id}:{_month_key()}"


def _calculate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006


def check_budget(user_id: str, estimated_cost: float = 0.0) -> None:
    """
    Enforces per-user monthly budget and raises 402 if exceeded.
    """
    if not r:
        return

    key = _user_budget_key(user_id)
    try:
        current_cost = float(r.get(key) or 0.0)
        if current_cost + estimated_cost > settings.monthly_budget_usd:
            raise HTTPException(
                status_code=402,
                detail="Monthly budget exceeded.",
            )
    except redis.RedisError:
        # Keep service available if Redis has temporary issues.
        return


def check_and_record_cost(user_id: str, input_tokens: int, output_tokens: int):
    """
    Checks monthly budget and records the cost of the current request.
    Formula: (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    """
    if not r:
        return

    key = _user_budget_key(user_id)
    cost = _calculate_cost(input_tokens, output_tokens)
    
    try:
        check_budget(user_id, estimated_cost=cost)

        # Atomically increment
        r.incrbyfloat(key, cost)
        # Keep keys for slightly more than one month.
        r.expire(key, 32 * 24 * 3600)

    except redis.RedisError:
        # Fallback: allow request if Redis is down.
        pass


def get_monthly_cost(user_id: str) -> float:
    """Returns total cost for the user in the current month."""
    if not r:
        return 0.0
    key = _user_budget_key(user_id)
    try:
        return float(r.get(key) or 0.0)
    except redis.RedisError:
        return 0.0
