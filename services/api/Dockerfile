FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --uid 10001 appuser

COPY pyproject.toml .
COPY src ./src

RUN pip install --no-cache-dir . \
    && chown -R appuser:appgroup /app

ENV PYTHONPATH=/app/src

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "interfaces.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
