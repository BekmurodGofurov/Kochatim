FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9000

# geventwebsocket's gunicorn worker monkey-patches the process before the
# app module is imported, so this avoids the blocking-call issue that
# `socketio.run(..., async_mode="gevent")` has when run directly.
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "-b", "0.0.0.0:9000", "app:app"]
