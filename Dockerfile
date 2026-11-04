# Stage 1: build-only. Node compiles Tailwind and vendors marked/DOMPurify into
# static/. This stage never reaches the runtime image, so the container that runs
# the app does not need Node or network access at start-up.
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

# Stage 2: runtime. Python only; no Node, no build tools.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/serve_static.py ./scripts/serve_static.py
COPY --from=ui-builder /build/static ./static

# Run as an unprivileged user; the app only needs to read static files.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2).status == 200 else 1)"

CMD ["python", "scripts/serve_static.py", "--host", "0.0.0.0", "--port", "8000"]
