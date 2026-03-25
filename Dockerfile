FROM python:3.11-slim

# Install system dependencies including Opus
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    opus-tools \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the bot
CMD ["python", "main.py"]
