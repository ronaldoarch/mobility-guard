FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN pip install .

RUN mkdir -p /app/data && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"

CMD ["uvicorn", "mobility_guard.main:app", "--host", "0.0.0.0", "--port", "8000"]
