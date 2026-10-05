# Backend image for the Community platform.
# The api and worker services share this image with different commands
# (technical-design.md §12). Worker runtime behavior is introduced in M1-11.

FROM python:3.13-slim

# uv is copied from the official pinned image.
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

# The virtual environment lives outside the source tree so a development bind
# mount of ./backend onto /app does not shadow installed dependencies.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (reproducible, cache-friendly). Source is copied
# afterwards so editing code does not invalidate the dependency layer.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app

# Install the project itself (no dev dependencies) against the frozen lock.
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
