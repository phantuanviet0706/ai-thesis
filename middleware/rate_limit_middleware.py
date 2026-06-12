import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from constants.constants import RATE_LIMIT_RPM
from core.logger import custom_logger

_SKIP_PREFIXES = ("/health", "/docs", "/openapi", "/redoc", "/favicon")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter: RATE_LIMIT_RPM requests per minute per client IP.

    Uses an in-memory deque per IP — suitable for single-instance deployments.
    For multi-instance setups, swap the store for a Redis ZSET.
    """

    def __init__(self, app):
        """
        @desc Khởi tạo middleware giới hạn tốc độ với cửa sổ trượt theo phút. Tạo bộ lưu trữ in-memory theo dạng dict ánh xạ IP đến danh sách timestamp các yêu cầu.
        @params app (ASGIApp): Ứng dụng ASGI được bọc bởi middleware này
        """
        super().__init__(app)
        self._window: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """
        @desc Xử lý từng yêu cầu HTTP đến, kiểm tra giới hạn tốc độ theo IP theo thuật toán cửa sổ trượt. Bỏ qua các đường dẫn hệ thống như /health, /docs. Trả về 429 nếu vượt quá RATE_LIMIT_RPM yêu cầu/phút.
        @params request (Request): Đối tượng yêu cầu HTTP đến từ client
        @params call_next (Callable): Hàm gọi tiếp theo trong chuỗi middleware
        @return Response: Phản hồi HTTP từ handler tiếp theo hoặc JSONResponse 429 nếu bị giới hạn
        """
        path = request.url.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - 60.0

        timestamps = self._window[client_ip]
        # Evict expired entries
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= RATE_LIMIT_RPM:
            retry_after = int(60 - (now - timestamps[0])) + 1
            custom_logger.warning(
                f"[RateLimit] 429 | ip={client_ip} | path={path} | "
                f"count={len(timestamps)}/{RATE_LIMIT_RPM} | retry_after={retry_after}s"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": f"Rate limit exceeded: {RATE_LIMIT_RPM} requests/minute. "
                               f"Retry after {retry_after}s.",
                    "result": None,
                },
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        return await call_next(request)
