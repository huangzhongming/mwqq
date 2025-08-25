# Backend Dockerfile for MWQQ Passport Photo Application
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        pkg-config \
        libmariadb-dev \
        build-essential \
        curl \
        wget \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-cpu.txt /app/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements-cpu.txt \
    && pip install mysqlclient gunicorn

# Copy project files
COPY . /app/

# Create directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "ai_tools.wsgi:application"]