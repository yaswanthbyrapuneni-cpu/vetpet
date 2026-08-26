FROM python:3.11-slim
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
RUN pip install --no-cache-dir ".[postgres]"

EXPOSE 8000

# Single worker only: chat/call/notification delivery lives in an in-process
# EventHub (see app/services/realtime.py). A second worker or container
# replica would silently miss pushes to sockets held by the other process —
# scaling this out needs a shared pub/sub (e.g. Redis) behind EventHub first.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
