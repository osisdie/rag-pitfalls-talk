FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: build tools for asyncpg/redis wheels, curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Ensure the live rag.py starts from the default. This file is volume-mounted
# writable so apply_fix can swap it at runtime.
RUN cp app/core/rag.py.default app/core/rag.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
