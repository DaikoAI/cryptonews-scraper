# Python Railway Template - uv optimized Docker build
# Based on https://docs.astral.sh/uv/guides/integration/docker/

FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory to the `app` directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-install-project --no-dev

# Copy the project into the intermediate image
COPY . /app

# Sync the project (non-editable install)
RUN uv sync --no-editable --no-dev

# Production stage
FROM python:3.12-slim

# Install uv in production stage
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the environment and source code
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src
COPY --from=builder --chown=app:app /app/pyproject.toml /app/pyproject.toml
COPY --from=builder --chown=app:app /app/uv.lock /app/uv.lock
COPY --from=builder --chown=app:app /app/README.md /app/README.md

# Make sure scripts in .venv are usable
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Create reports directory for outputs
RUN mkdir -p /app/reports && chown -R app:app /app/reports

# Change to non-root user
USER app

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (if needed for web apps)
EXPOSE 8000

# Run the application using the entry point from pyproject.toml
CMD ["python", "-m", "src.main"]
