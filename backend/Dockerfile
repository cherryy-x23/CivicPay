FROM python:3.13-slim

# Prevent Python from creating .pyc files
# and ensure logs appear immediately.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Tesseract OCR
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Application directory
WORKDIR /app

# Install Python dependencies first
# so Docker can cache this layer.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy CivicPay backend
COPY . .

# Production server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]