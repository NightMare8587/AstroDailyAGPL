FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY astrodaily ./astrodaily
COPY alembic ./alembic
# pyswisseph has no prebuilt wheel for this platform, so it compiles from source: gcc is needed
# at build time only and is removed again to keep the image small.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev \
 && pip install --no-cache-dir . \
 && apt-get purge -y --auto-remove gcc libc6-dev \
 && rm -rf /var/lib/apt/lists/*
ENV PORT=8000
# Apply database migrations when DATABASE_URL is set, then start the API.
CMD ["sh", "-c", "if [ -n \"$DATABASE_URL\" ]; then alembic upgrade head; fi; exec uvicorn astrodaily.main:app --host 0.0.0.0 --port ${PORT}"]
