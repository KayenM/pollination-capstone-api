# Dockerfile for Render.com deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory (for temporary processing)
RUN mkdir -p uploads/images

# Expose port (Render sets PORT environment variable)
EXPOSE 8000

# Run the application
# PORT is set automatically by Render
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

