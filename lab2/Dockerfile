FROM python:3.12-slim

WORKDIR /app
COPY server_single.py server_threaded.py index.py rate_limit_test.py ./

RUN pip install --no-cache-dir requests

WORKDIR /app/data

CMD ["python", "-m", "http.server", "8000"]
