# Use Python slim as the base image
FROM python:3.10-slim

# Set environment variables to prevent Python from buffering output
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for OpenCV and other libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
    libboost-python-dev \
    libboost-thread-dev \
    libx11-dev \
    libopenblas-dev \
    liblapack-dev \
    python3-dev \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    libjpeg-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy project files into the container
COPY . /app

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies from requirements.txt
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Expose port 8000 for FastAPI
EXPOSE 8000

# Set the default command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

