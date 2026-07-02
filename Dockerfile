# Dockerfile — FastAPI Backend
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for compiling some python packages if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Pre-create folders for uploads, outputs, and static Gantt charts
RUN mkdir -p uploads output static

# Expose FastAPI default port
EXPOSE 8000

# Launch uvicorn server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
