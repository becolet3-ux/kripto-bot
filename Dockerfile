# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app
ENV TMPDIR=/var/tmp

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    git \
    libssl-dev \
    openssl \
    libgomp1 \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Create venv and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Install runtime dependencies
# libgomp1 is needed for some ML libraries
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib shared libraries from builder
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy the rest of the application
COPY . .

# Create directories for data and logs
RUN mkdir -p data logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "src/main.py"]
