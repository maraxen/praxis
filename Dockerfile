# STAGE 1: Builder
# Use a larger base image to compile dependencies
FROM python:3.12-slim as builder

WORKDIR /app

# Install system build dependencies
# git is required for installing dependencies from git repositories
# curl and ca-certificates are required for installing uv
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure uv is in PATH
ENV PATH="/root/.local/bin:${PATH}"

# Copy pyproject.toml to cache dependencies
COPY pyproject.toml .

# Generate requirements.txt using uv
# We include 'dev' extras to support running tests in the container (for development/CI)
# The workspace member plr-sema is not on PyPI and its source is not copied yet:
# compile from a copy of pyproject.toml without it, and install it from source
# below (spec 261002 R1). The copy must itself be named pyproject.toml: uv picks
# the input format from the filename.
RUN mkdir -p /tmp/deps \
 && grep -v -e '"plr-sema\[extract\]",' -e '^plr-sema = { workspace = true }' pyproject.toml > /tmp/deps/pyproject.toml \
 && uv pip compile /tmp/deps/pyproject.toml --extra dev -o requirements.txt

# Install dependencies into /install prefix
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy application code
COPY . .

# Install the workspace member, then the application itself, into /install
# We use --no-deps because we already installed dependencies
RUN pip install --no-cache-dir --prefix=/install --no-deps ./plr-sema
RUN pip install --no-cache-dir --prefix=/install --no-deps .

# STAGE 2: Runtime
# Use a slim image for the final container
FROM python:3.12-slim

WORKDIR /app

# Create a non-root user for security
RUN groupadd -r praxis && useradd -r -g praxis praxis

# Install runtime dependencies
# libpq-dev is often required for PostgreSQL adapters (psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R praxis:praxis /app

# Switch to non-root user
USER praxis

# Expose the port defined in your app
EXPOSE 8000

# Use array syntax for CMD
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
