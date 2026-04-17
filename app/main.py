"""
Production AI Agent — Kết hợp tất cả Day 12 concepts
"""
import time
import signal
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import redis

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, check_and_record_cost, get_monthly_cost

# Mock LLM
from utils.mock_llm import ask as llm_ask

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# Redis for State (Conversation History)
r = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    
    # Simulate initialization and check Redis
    if r:
        try:
            r.ping()
            logger.info(json.dumps({"event": "redis_connected"}))
        except redis.RedisError as e:
            logger.error(json.dumps({"event": "redis_connection_failed", "error": str(e)}))
    
    time.sleep(0.1)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


def _to_user_id(api_key: str) -> str:
    return api_key[:8]


def rate_limit_dependency(api_key: str = Depends(verify_api_key)) -> None:
    check_rate_limit(_to_user_id(api_key))


def budget_dependency(api_key: str = Depends(verify_api_key)) -> None:
    # Pre-flight budget check; actual request cost is recorded after response generation.
    check_budget(_to_user_id(api_key), estimated_cost=0.0)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        logger.error(json.dumps({"event": "request_failed", "error": str(e)}))
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")

class AskResponse(BaseModel):
    question: str
    answer: str
    history_count: int
    model: str
    timestamp: str

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }

@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    _request: Request,
    _rate_limit: None = Depends(rate_limit_dependency),
    _budget: None = Depends(budget_dependency),
    api_key: str = Depends(verify_api_key),
):
    user_id = _to_user_id(api_key)

    # State: Get conversation history from Redis
    history = []
    if r:
        history = r.lrange(f"history:{user_id}", -10, -1) # Last 5 turns (q+a)

    logger.info(json.dumps({
        "event": "agent_call",
        "user": user_id,
        "q_len": len(body.question),
        "history_len": len(history),
    }))

    # Call LLM
    answer = llm_ask(body.question)

    # State: Save to Redis
    if r:
        r.rpush(f"history:{user_id}", body.question, answer)
        r.ltrim(f"history:{user_id}", -20, -1) # Keep last 10 turns
        r.expire(f"history:{user_id}", 3600)   # 1 hour TTL

    input_tokens = len(body.question.split()) * 2
    output_tokens = len(answer.split()) * 2
    check_and_record_cost(user_id, input_tokens, output_tokens)

    return AskResponse(
        question=body.question,
        answer=answer,
        history_count=len(history) // 2,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Checks Redis connection."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    
    if r:
        try:
            r.ping()
        except Exception:
            raise HTTPException(503, "Redis connection failed")
            
    return {"ready": True}

@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    user_id = _to_user_id(_key)
    monthly_cost = get_monthly_cost(user_id)
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "monthly_cost_usd": round(monthly_cost, 4),
        "monthly_budget_usd": settings.monthly_budget_usd,
        "budget_used_pct": round(monthly_cost / settings.monthly_budget_usd * 100, 1) if settings.monthly_budget_usd > 0 else 0,
    }

# ─────────────────────────────────────────────────────────
# Signal handling for Graceful Shutdown handled by Uvicorn
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )