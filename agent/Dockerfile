FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install kubectl
RUN apt-get update && apt-get install -y curl &&     curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" &&     chmod +x kubectl && mv kubectl /usr/local/bin/kubectl &&     apt-get clean && rm -rf /var/lib/apt/lists/*

COPY *.py .

RUN useradd -m -u 1000 agent
USER agent

ENV POLL_INTERVAL_SECONDS=30
ENV ERROR_RATE_THRESHOLD=0.05
ENV LATENCY_THRESHOLD_MS=500

CMD ["python", "main.py"]
