# Stage 0: Go binary builder
FROM golang:1.27-alpine AS go-builder

WORKDIR /build
COPY tools/sdd-compile/ .
RUN go mod download && go build -o sdd-compile .

# Stage 1: Builder
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=$SETUPTOOLS_SCM_PRETEND_VERSION

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
ENV PATH="/usr/local/bin:${PATH}"

# Install all workspace packages + test extras into /app/.venv in a single locked pass.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --clear /app/.venv && \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    uv sync --frozen --no-group docs --all-packages --extra test && \
    uv pip install --python /app/.venv/bin/python --reinstall \
    msgpack==1.2.1 setuptools==84.0.0 && \
    grep -R -H -E '^Version: 1\.2\.1$' \
    /app/.venv/lib/python*/site-packages/msgpack-*.dist-info/METADATA && \
    grep -R -H -E '^Version: 84\.0\.0$' \
    /app/.venv/lib/python*/site-packages/setuptools-*.dist-info/METADATA && \
    ! grep -R -H -E '^Version: (1\.1\.2|70\.3\.0|83\.0\.0)$' \
    /app/.venv/lib/python*/site-packages/msgpack-*.dist-info/METADATA \
    /app/.venv/lib/python*/site-packages/setuptools-*.dist-info/METADATA

# Install sdd-compile Go binary into builder PATH
COPY --from=go-builder /build/sdd-compile /usr/local/bin/sdd-compile

# Pre-compile governance artifacts so tests don't rebuild from a different source path
ENV PATH="/app/.venv/bin:${PATH}"
RUN providence governance compile

# Stage 2: Runtime
FROM python:3.14-slim

LABEL org.opencontainers.image.title="Providence Agentic OS" \
      org.opencontainers.image.description="Professional AI-first Agentic Operating System Architecture" \
      org.opencontainers.image.vendor="providence" \
      org.opencontainers.image.version="1.0.0"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    tini \
    openssl \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy uv for the `uv run` fallback path in the Makefile.
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

# Trivy scans the full runtime filesystem, including the base image's system
# site-packages outside /app/.venv.
RUN uv pip install --system --break-system-packages --reinstall setuptools==84.0.0 && \
    grep -R -H -E '^Version: 84\.0\.0$' \
    /usr/local/lib/python*/site-packages/setuptools-*.dist-info/METADATA && \
    ! grep -R -H -E '^Version: (70\.3\.0|83\.0\.0)$' \
    /usr/local/lib/python*/site-packages/setuptools-*.dist-info/METADATA && \
    rm -rf /root/.cache/uv \
    /usr/local/lib/python*/site-packages/pip \
    /usr/local/lib/python*/site-packages/pip-*.dist-info

RUN groupadd -g 1000 sdd && \
    useradd -u 1000 -g sdd -m -s /bin/bash sdd

WORKDIR /app

COPY --chown=sdd:sdd . /app
RUN rm -rf /app/.venv
COPY --from=go-builder /build/sdd-compile /usr/local/bin/sdd-compile
COPY --from=builder /app/.venv /app/.venv

# Overlay pre-compiled governance artifacts from builder (not in git)
COPY --from=builder --chown=sdd:sdd /app/.providence/compiled /app/.providence/compiled

COPY --chown=sdd:sdd infrastructure/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chown sdd:sdd /app && \
    ln -s /app/.venv /venv

# Final image gate: Trivy scans the complete filesystem, so reject stale Python
# package metadata no matter which layer or path introduced it.
RUN find / -type d \( \
    -name 'msgpack-1.1.2.dist-info' -o \
    -name 'setuptools-70.3.0.dist-info' -o \
    -name 'setuptools-83.0.0.dist-info' \
    \) -prune -exec rm -rf {} + && \
    rm -rf /root/.cache/uv && \
    ! sh -c "find / -path '*dist-info/METADATA' -type f -print0 | \
    xargs -0 -r grep -H -E '^Version: (1\.1\.2|70\.3\.0|83\.0\.0)$'" && \
    ! grep -R -H -E 'pkg:pypi/(msgpack@1\.1\.2|setuptools@70\.3\.0|setuptools@83\.0\.0)|^(msgpack==1\.1\.2|setuptools==70\.3\.0|setuptools==83\.0\.0)$' \
    /usr/local/lib/python*/site-packages/pip/_vendor 2>/dev/null

# /app/.venv/bin first so Python and all tools resolve from the pre-built venv.
# VIRTUAL_ENV points to the project-local virtualenv used by the runtime container.
ENV PATH="/app/.venv/bin:/usr/local/bin:${PATH}" \
    VIRTUAL_ENV=/app/.venv

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

USER 1000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["sh", "-c", "providence --help || exit 1"]
