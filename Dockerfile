FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY astrodaily ./astrodaily
COPY alembic ./alembic
RUN pip install --no-cache-dir .
ENV PORT=8000
# Apply database migrations when DATABASE_URL is set, then start the API.
CMD ["sh", "-c", "if [ -n \"$DATABASE_URL\" ]; then alembic upgrade head; fi; exec uvicorn astrodaily.main:app --host 0.0.0.0 --port ${PORT}"]
