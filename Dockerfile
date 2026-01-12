# Use Python 3.11 slim image as base (Debian Bookworm)
FROM python:3.11-slim-bookworm AS builder

ARG APP_UID=1000
ARG APP_GID=1000

# Set working directory for build stage
WORKDIR /build

# Copy only what's needed to extract version
COPY .git/ ./.git/

# Extract version information from git and generate version file
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "0.0.0-unknown") && \
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") && \
    echo "Extracted version: ${VERSION}, commit: ${COMMIT}" && \
    echo "${VERSION}" | grep -qE '^v?[0-9]+\.[0-9]+\.[0-9]+-beta\.' && IS_BETA=true || IS_BETA=false && \
    if [ "${IS_BETA}" = "true" ]; then \
        BASE_VERSION=$(echo "${VERSION}" | sed -E 's/^v?([0-9]+\.[0-9]+\.[0-9]+)-.*/\1/'); \
        PRERELEASE=$(echo "${VERSION}" | sed -E 's/^v?[0-9]+\.[0-9]+\.[0-9]+-([^-]+).*/\1/'); \
        BUILD="${PRERELEASE}"; \
    else \
        BASE_VERSION=$(echo "${VERSION}" | sed -E 's/^v?([0-9]+\.[0-9]+\.[0-9]+).*/\1/'); \
        BUILD="release"; \
    fi && \
    echo "${VERSION}" | grep -q dirty && BUILD="${BUILD}.dirty" || true && \
    mkdir -p /build/app && \
    echo "# Auto-generated version file - DO NOT EDIT" > /build/app/_version_info.py && \
    echo "# Generated at build time from git tags" >> /build/app/_version_info.py && \
    echo "__version__ = \"${BASE_VERSION}\"" >> /build/app/_version_info.py && \
    echo "__build__ = \"${BUILD}\"" >> /build/app/_version_info.py && \
    echo "__commit__ = \"${COMMIT}\"" >> /build/app/_version_info.py && \
    cat /build/app/_version_info.py && \
    apt-get remove -y git && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Final stage - minimal runtime image
FROM python:3.11-slim-bookworm

ARG APP_UID=1000
ARG APP_GID=1000

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        build-essential \
        iproute2 \
        wireless-tools \
        net-tools \
        iputils-ping \
        procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get remove -y gcc python3-dev build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy generated version file from builder stage
COPY --from=builder /build/app/_version_info.py ./app/_version_info.py

# Copy application code
COPY app/ ./app/

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (adjust if your app uses a specific port)
# EXPOSE 8000

# Set the entrypoint
WORKDIR /app/app
CMD ["python", "main.py"]