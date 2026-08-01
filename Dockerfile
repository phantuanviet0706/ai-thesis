# syntax=docker/dockerfile:1
#
# Multi-stage build tối ưu cho VPS CPU-only (6 vCPU E5 v2 / 8GB RAM / 60GB SSD):
#   - torch cài từ index CPU-only của PyTorch (~200MB) thay vì wheel mặc định kèm CUDA
#     (~2.5-3GB) — đây là khoản tiết kiệm disk/RAM lớn nhất trong toàn bộ image.
#   - Build stage tách riêng runtime stage — toolchain biên dịch (gcc, headers) không lọt
#     vào image cuối, chỉ có --user site-packages đã build sẵn được copy sang.
#   - Model embedding (all-MiniLM-L6-v2) được tải sẵn ở build time để container không cần
#     internet lúc cold-start và không tốn ~1-2 phút tải model mỗi lần container khởi động lại.

ARG PYTHON_VERSION=3.13

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# torch (CPU-only wheel) cài riêng trước bằng --extra-index-url — nếu để chung trong
# requirements.txt, pip có thể resolve nhầm sang wheel CUDA mặc định trên PyPI.
RUN pip install --user --no-cache-dir torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu \
    && grep -v '^torch==' requirements.txt > requirements.notorch.txt \
    && pip install --user --no-cache-dir -r requirements.notorch.txt

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/root/.local/lib/python3.13/site-packages

# Pre-warm embedding model vào cache HuggingFace ngay trong image — tránh phải tải lúc
# container start lần đầu trên VPS (mạng VPS có thể chậm/không ổn định).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/home/appuser/.local/lib/python3.13/site-packages \
    HF_HOME=/home/appuser/.cache/huggingface \
    # Giới hạn số thread torch/OpenMP dùng cho mỗi request encode — tránh 1 process
    # torch chiếm hết 6 vCPU và làm đói MySQL/Redis chạy chung trên cùng VPS.
    OMP_NUM_THREADS=3 \
    TORCH_NUM_THREADS=3 \
    TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --from=builder --chown=appuser:appuser /root/.cache/huggingface /home/appuser/.cache/huggingface

COPY --chown=appuser:appuser . .

# logs/, data/ (checkpoints), chroma_db/ được mount làm volume ở docker-compose.yml —
# tạo trước ở đây để đúng owner (appuser), tránh lỗi permission khi volume rỗng lần đầu.
RUN mkdir -p logs logs/errors data chroma_db && chown -R appuser:appuser logs data chroma_db

USER appuser

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8088/health || exit 1

# --workers 1: RateLimitMiddleware (middleware/rate_limit_middleware.py) và checkpointer
# SQLite fallback (graph/graph.py) đều giữ state in-memory/per-process — nhiều worker sẽ
# nhân bản state đó (rate limit thực tế = N x ngưỡng cấu hình) thay vì chia sẻ đúng. Với
# 1 process, độ trễ mỗi request chủ yếu là I/O chờ Anthropic/Gemini API (không phải CPU-
# bound), nên asyncio của FastAPI đã đủ xử lý concurrency mà không cần thêm worker. Chỉ
# tăng --workers sau khi đã chuyển rate limiter sang Redis (xem ghi chú trong file đó).
#
# --proxy-headers + --forwarded-allow-ips: bắt buộc để request.client.host lấy đúng IP
# thật của client (qua header X-Forwarded-For) thay vì luôn là IP của Nginx reverse proxy
# — nếu thiếu, rate limit coi mọi client là cùng 1 IP. Xem resources/setup/8_security-hardening.md.
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8088", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
