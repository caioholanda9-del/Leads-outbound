FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e .

COPY leads/ leads/
COPY alembic/ alembic/
COPY alembic.ini .

RUN mkdir -p /app/data

CMD ["sh", "-c", "alembic upgrade head && uvicorn leads.api.main:app --host 0.0.0.0 --port 8000"]
