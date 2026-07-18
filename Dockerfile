FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing and browser-based capture
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Create a directory for persistent image storage
RUN mkdir -p /app/images /app/images/check-done

# Expose port (Flask default + capture app if needed)
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001').read()" || exit 1

# Default command: start the main Flask app
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV OCR_LANG=en

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5001"]

