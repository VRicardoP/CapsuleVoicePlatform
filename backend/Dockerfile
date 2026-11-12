# =============================================================================
# CapsuleCorp Backend - Dockerfile
# =============================================================================
# Simplified build for production
# =============================================================================

FROM python:3.12-slim

# Create non-root user
RUN groupadd -r capsulecorp && useradd -r -g capsulecorp capsulecorp

WORKDIR /app

# Install runtime dependencies (including WeasyPrint requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ffmpeg \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY pyproject.toml ./

# Install dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi uvicorn[standard] pydantic[email] pydantic-settings \
    sqlalchemy[asyncio] asyncpg python-jose[cryptography] \
    passlib[bcrypt] python-multipart httpx tenacity structlog aiosmtplib \
    weasyprint jinja2 openpyxl arq redis[hiredis] boto3 \
    playwright alembic

# Install Playwright Chromium (for Habitaclia scraper in captacion module)
# Install as root, then set PLAYWRIGHT_BROWSERS_PATH so all users can access it
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN playwright install --with-deps chromium

# Copy application code
COPY --chown=capsulecorp:capsulecorp app ./app
COPY --chown=capsulecorp:capsulecorp scripts ./scripts
COPY --chown=capsulecorp:capsulecorp alembic ./alembic
COPY --chown=capsulecorp:capsulecorp alembic.ini ./alembic.ini

# Switch to non-root user
USER capsulecorp

# Expose port
EXPOSE 8000

# NOTE: NO HEALTHCHECK directive on purpose. The image is shared between the
# uvicorn `backend` container (which DOES expose HTTP on :8000) and the ARQ
# `worker` container (which does NOT). A blanket HEALTHCHECK in the image
# made the worker permanently `unhealthy` because curl localhost:8000 always
# failed there. Each docker-compose.yml is responsible for declaring an
# appropriate healthcheck per service:
#   - backend:  test: curl -f http://localhost:8000/health
#   - worker:   healthcheck: { disable: true }   (or a real arq probe)

# Default command — overridden by the worker service in compose.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
