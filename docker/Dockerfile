# Multi-stage build for optimal size
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies for PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies in builder stage
COPY requirements-core.txt ./

# Install setuptools first, then other dependencies
RUN pip install --user --no-cache-dir setuptools wheel
RUN pip install --user --no-cache-dir -r requirements-core.txt

# Production stage
FROM python:3.12-slim

WORKDIR /src

# Install system packages needed for PaddleOCR runtime
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  libgl1-mesa-glx \
  libglib2.0-0 \
  libgomp1 \
  libgstreamer1.0-0 \
  libgstreamer-plugins-base1.0-0 \
  libgtk-3-0 \
  libavcodec-dev \
  libavformat-dev \
  libswscale-dev \
  libjpeg-dev \
  libpng-dev \
  libtiff-dev \
  libdc1394-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . /src/

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8888

# Use specific command for API
# CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "1"]
