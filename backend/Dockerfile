FROM python:3.11-slim AS base

WORKDIR /app

# System deps for asyncpg, pdfplumber, tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the FastAPI app
CMD ["uvicorn", "agentcore.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
