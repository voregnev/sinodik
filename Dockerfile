# ── Build stage: install Python deps ─────────────────────
FROM python:3.14-slim-trixie AS builder

WORKDIR /build

RUN sed -i 's/deb.debian.org/ftp.ru.debian.org/g' /etc/apt/sources.list.d/*.sources 2>/dev/null; \
    sed -i 's/deb.debian.org/ftp.ru.debian.org/g' /etc/apt/sources.list 2>/dev/null; \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ────────────────────────────────────────
FROM python:3.14-slim-trixie

WORKDIR /app

RUN sed -i 's/deb.debian.org/ftp.ru.debian.org/g' /etc/apt/sources.list.d/*.sources 2>/dev/null; \
    sed -i 's/deb.debian.org/ftp.ru.debian.org/g' /etc/apt/sources.list 2>/dev/null; \
    apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /install /usr/local

COPY requirements.txt .
COPY app/ .
COPY alembic/ ./alembic
COPY alembic.ini .
COPY tests/ ./tests
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh

RUN chmod +x /app/scripts/entrypoint.sh && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
