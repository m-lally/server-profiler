FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY config.yaml .

# Create output directory
RUN mkdir -p /app/output

# Make profiler executable
RUN chmod +x profiler.py

ENTRYPOINT ["python", "profiler.py"]
CMD ["--help"]
