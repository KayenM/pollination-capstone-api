# Dockerfile for Render.com deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Update package lists and install system dependencies
# Using separate RUN commands for better error tracking
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgl1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create uploads directory (for temporary processing)
RUN mkdir -p uploads/images

# Expose port (Render sets PORT environment variable)
EXPOSE 8000

# Run the application
# PORT is set automatically by Render
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

