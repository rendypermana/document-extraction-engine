# Stage 1: build-only. Node compiles Tailwind and vendors marked/DOMPurify into
# static/. Node never reaches the runtime image.
FROM node:22-alpine AS ui-builder

WORKDIR /build

# `npm ci` needs the lockfile and installs exactly the pinned versions.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY scripts/vendor-ui-libs.mjs ./scripts/
COPY static ./static
RUN node ./scripts/vendor-ui-libs.mjs \
    && npx --no-install tailwindcss -i ./static/css/input.css -o ./static/css/app.css --minify \
    && test -s ./static/css/app.css

# Stage 2: runtime. Python only; no Node or frontend build tools.
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-ind \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OCR_ENABLED=true

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY --from=ui-builder /build/static ./static

# Run as an unprivileged user; uploads use the system temporary directory.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT','8000') + '/api/health', timeout=2).status == 200 else 1)"

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
