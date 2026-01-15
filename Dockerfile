# Use Python 3.11 slim image as base (Debian Bookworm)
FROM python:3.11-slim-bookworm AS builder

ARG APP_UID=1000
ARG APP_GID=1000

# Set working directory for build stage
WORKDIR /build

# Copy git repo and version generation script
COPY .git/ ./.git/
COPY generate_version.sh ./

# Generate VERSION JSON file using the same script as semantic-release
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    chmod +x generate_version.sh && \
    ./generate_version.sh && \
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

# Copy generated VERSION JSON file from builder stage
COPY --from=builder /build/VERSION ./VERSION

# Copy application code
COPY app/ ./app/

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Set the entrypoint
WORKDIR /app/app
CMD ["python", "main.py"]