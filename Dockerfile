# --- Stage 1: build the virtual env ----------
FROM ghcr.io/astral-sh/uv:0.12.13-python3.13-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies alone, in their own layer.
RUN --mount=type=cache,target=/root/.cache/uv.lock \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Code
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# ---- Stage 2: the image shipped -------------
FROM python:3.13-slim-trixie

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER nonroot
WORKDIR /app

CMD ["kansei"]