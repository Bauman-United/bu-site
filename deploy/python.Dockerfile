FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY core/pyproject.toml core/pyproject.toml
COPY worker/pyproject.toml worker/pyproject.toml
COPY api/pyproject.toml api/pyproject.toml
COPY core/bu_core core/bu_core
COPY worker/bu_worker worker/bu_worker
COPY api/bu_api api/bu_api
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 bu
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY core/alembic.ini core/alembic.ini
COPY core/migrations core/migrations
COPY content content
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 BU_CONTENT_DIR=/app/content BU_SNAPSHOT_DIR=/data/snapshots
RUN mkdir -p /data/snapshots /data/media && chown -R bu /data
USER bu
EXPOSE 8000
CMD ["uvicorn", "bu_api.app:build", "--factory", "--host", "0.0.0.0", "--port", "8000"]
