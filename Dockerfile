# Build frontend bundle so Flask can serve the Vite SPA from /smartfridge_frontend/dist
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY smartfridge_frontend ./smartfridge_frontend
RUN cd smartfridge_frontend \
    && npm install \
    && npm run build

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .
COPY --from=frontend-build /app/smartfridge_frontend/dist ./smartfridge_frontend/dist
RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:app"]
