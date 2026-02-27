FROM python:3.11-slim

WORKDIR /app

# Install git (needed by updater to run git pull/reset on the mounted volume)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire watchdog package (all sub-packages + config + entry point)
COPY . .

CMD ["python", "watchdog.py"]
