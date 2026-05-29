# PicoWatch — Multi-stage Dockerfile
# Build stage: install dependencies
# Runtime stage: minimal image with only what's needed

FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY rules/ rules/

# Build wheel
RUN pip install --no-cache-dir --upgrade pip build && \
    python -m build --wheel

# Runtime stage
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="PicoWatch"
LABEL org.opencontainers.image.description="LLM defender with telemetry — prompt injection detection, output validation, and observability"
ARG PICOWATCH_VERSION=0.5.0
LABEL org.opencontainers.image.version="${PICOWATCH_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/KirkForge/PicoWatch"
LABEL org.opencontainers.image.vendor="KirkForge"

# Create non-root user
RUN groupadd -r picowatch && \
    useradd -r -g picowatch -d /home/picowatch -s /sbin/nologin picowatch

# Install runtime dependencies only
COPY --from=builder /build/dist/picowatch-*.whl /tmp/
RUN pip install --no-cache-dir /tmp/picowatch-*.whl[server] && \
    rm -f /tmp/picowatch-*.whl

# Copy rules (bundled in wheel, but also available as volume mount)
COPY rules/ /app/rules/

# Create audit DB directory
RUN mkdir -p /app/data && chown -R picowatch:picowatch /app

WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -m picowatch health || exit 1

# Expose ports
EXPOSE 8766

# Run as non-root user
USER picowatch

# Default environment
ENV PICOWATCH_HOST=0.0.0.0
ENV PICOWATCH_PORT=8766

# Entry point
ENTRYPOINT ["picowatch"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8766"]