# CloudTech v2.1 — Production Docker Image
FROM python:3.12-slim

LABEL app="CloudTech" version="2.1.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs /app/backups
VOLUME ["/app/data", "/app/logs", "/app/backups"]

ENV CLOUDTECH_HOST=0.0.0.0
ENV CLOUDTECH_PORT=5099
ENV CLOUDTECH_WORKERS=4
ENV PYTHONUNBUFFERED=1

EXPOSE 5099

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5099/health || exit 1

CMD ["python", "run_prod.py"]
