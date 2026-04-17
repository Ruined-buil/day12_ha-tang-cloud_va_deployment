"""
Redis-based Rate Limiter (Stateless)

Giới hạn số request mỗi user trong 1 khoảng thời gian.
Dùng Redis để lưu trữ state, cho phép scale nhiều instances.

Algorithm: Sliding Window Counter (Redis Sorted Set)
"""
import time
import os
import redis
from fastapi import HTTPException

# Initialize Redis client
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)

class RateLimiter:
    def __init__(self, name: str, max_requests: int = 10, window_seconds: int = 60):
        """
        Args:
            name: Tên của limiter (để phân biệt keys trong Redis)
            max_requests: Số request tối đa trong window
            window_seconds: Khoảng thời gian (giây)
        """
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, user_id: str) -> dict:
        """
        Kiểm tra user có vượt rate limit không bằng Redis Sorted Set.
        """
        now = time.time()
        key = f"rate_limit:{self.name}:{user_id}"
        window_start = now - self.window_seconds
        
        try:
            # Dùng pipeline để tối ưu performance
            pipeline = r.pipeline()
            
            # 1. Xóa các request cũ ngoài window
            pipeline.zremrangebyscore(key, 0, window_start)
            
            # 2. Đếm số request hiện tại trong window
            pipeline.zcard(key)
            
            # 3. Thêm request hiện tại vào (dùng timestamp làm score và member)
            # Member phải unique, nên dùng timestamp + random/unique id nếu cần cực kỳ chính xác,
            # nhưng cho lab này timestamp là đủ.
            pipeline.zadd(key, {str(now): now})
            
            # 4. Set expiration để tự động dọn dẹp Redis
            pipeline.expire(key, self.window_seconds + 10)
            
            # Thực thi pipeline
            results = pipeline.execute()
            current_count = results[1]  # Kết quả của zcard
            
            remaining = self.max_requests - current_count
            reset_at = int(now) + self.window_seconds

            if current_count >= self.max_requests:
                retry_after = self.window_seconds
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": self.max_requests,
                        "window_seconds": self.window_seconds,
                        "retry_after_seconds": retry_after,
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                        "Retry-After": str(retry_after),
                    },
                )

            return {
                "limit": self.max_requests,
                "remaining": remaining - 1,
                "reset_at": reset_at,
            }
            
        except redis.RedisError as e:
            # Fallback: Nếu Redis lỗi, log lại và cho phép request (fail-open)
            print(f"Redis RateLimiter error: {e}")
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "reset_at": int(now) + self.window_seconds,
            }

    def get_stats(self, user_id: str) -> dict:
        """Trả về stats của user từ Redis."""
        now = time.time()
        key = f"rate_limit:{self.name}:{user_id}"
        window_start = now - self.window_seconds
        
        try:
            active = r.zcount(key, window_start, "+inf")
            return {
                "requests_in_window": active,
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - active),
            }
        except:
            return {"error": "Could not fetch stats from Redis"}

# Singleton instances
rate_limiter_user = RateLimiter("user", max_requests=10, window_seconds=60)
rate_limiter_admin = RateLimiter("admin", max_requests=100, window_seconds=60)

