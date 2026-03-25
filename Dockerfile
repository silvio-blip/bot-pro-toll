FROM python:3.11-slim

# Install system dependencies including Opus and its deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    libopusfile0 \
    opus-tools \
    cffi \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for libraries
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/lib:$LD_LIBRARY_PATH

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with specific versions for voice
RUN pip install --no-cache-dir \
    PyNaCl==1.5.0 \
    discord.py==2.7.1 \
    aiohttp \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the bot
CMD ["python", "main.py"]
