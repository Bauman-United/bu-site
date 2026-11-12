# bu-browser: headed Chromium под Xvfb для страниц Join.Football за SafeLine.
# Порт fantasy-back (Dockerfile.browser-worker). Chromium запускается как обычный браузер,
# без Playwright/CDP; страницы возвращает локальное расширение (bu_worker/browser/extension).
# noVNC нужен только чтобы вручную нажать «Confirm You Are Human» после смены IP/профиля.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium fonts-dejavu-core novnc websockify x11vnc xvfb \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn>=0.30" "httpx>=0.27" "pydantic>=2"
WORKDIR /app
# Только пакет воркера: браузеру нужны bu_worker.waf и bu_worker.browser (без bu_core/БД).
COPY worker/bu_worker bu_worker
COPY deploy/browser-entrypoint.sh /usr/local/bin/browser-entrypoint
RUN chmod +x /usr/local/bin/browser-entrypoint
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 BROWSER_PROFILE_DIR=/data/browser/profile
EXPOSE 8090
CMD ["browser-entrypoint"]
