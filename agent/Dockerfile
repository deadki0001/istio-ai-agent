FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

RUN useradd -m -u 1000 agent
USER agent

ENV POLL_INTERVAL_SECONDS=30
ENV ERROR_RATE_THRESHOLD=0.05
ENV LATENCY_THRESHOLD_MS=500

CMD ["python", "main.py"]
