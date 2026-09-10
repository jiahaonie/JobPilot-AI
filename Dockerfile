# syntax=docker/dockerfile:1.7

FROM python:3.13-slim-bookworm AS builder

# 固定 uv 版本，确保不同机器上的依赖安装行为一致。
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 依赖文件先于源码复制，使源码变更时可以复用依赖安装缓存。
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable


FROM python:3.13-slim-bookworm AS runtime

# FastEmbed 使用的 ONNX Runtime 在精简 Debian 镜像中需要 libgomp。
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system jobpilot \
    && useradd --system --gid jobpilot --home-dir /app jobpilot

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DATABASE_URL=sqlite:////app/data/jobpilot.db \
    RAG_CHROMA_PATH=/app/data/chroma

WORKDIR /app

COPY --from=builder --chown=jobpilot:jobpilot /app/.venv /app/.venv
COPY --chown=jobpilot:jobpilot alembic.ini ./
COPY --chown=jobpilot:jobpilot migrations ./migrations
COPY --chown=jobpilot:jobpilot scripts ./scripts

# SQLite 与 Chroma 共用该目录，后续由 Compose 挂载持久化数据卷。
RUN mkdir -p /app/data \
    && chown -R jobpilot:jobpilot /app/data

USER jobpilot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
