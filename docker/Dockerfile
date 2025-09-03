# CBS Research Project Docker Image
# Multi-stage build for optimized production image

# Build stage
FROM python:3.9-slim as builder

LABEL maintainer="CBS Research Team"
LABEL description="Credit-Based Shaper Research and Implementation"
LABEL version="2.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip wheel setuptools
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.9-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    tcpdump \
    iperf3 \
    iproute2 \
    ethtool \
    net-tools \
    iputils-ping \
    curl \
    vim \
    less \
    procps \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN groupadd -r cbsuser && useradd -r -g cbsuser cbsuser
RUN mkdir -p /app && chown cbsuser:cbsuser /app
RUN mkdir -p /data && chown cbsuser:cbsuser /data
RUN mkdir -p /results && chown cbsuser:cbsuser /results

# Set working directory
WORKDIR /app

# Copy project files
COPY --chown=cbsuser:cbsuser src/ ./src/
COPY --chown=cbsuser:cbsuser tests/ ./tests/
COPY --chown=cbsuser:cbsuser scripts/ ./scripts/
COPY --chown=cbsuser:cbsuser config/ ./config/
COPY --chown=cbsuser:cbsuser results/ ./results/
COPY --chown=cbsuser:cbsuser requirements.txt ./
COPY --chown=cbsuser:cbsuser README.md ./
COPY --chown=cbsuser:cbsuser PROJECT_STRUCTURE.md ./

# Create entrypoint script
RUN cat > /app/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "🚗 CBS Research Container Starting..."
echo "📊 Python Version: $(python --version)"
echo "🔧 Available Tools:"
echo "  - CBS Calculator: python src/cbs_calculator.py"
echo "  - Data Analyzer: python src/data_analyzer.py"
echo "  - Traffic Generator: python src/traffic_generator.py"
echo "  - Performance Benchmark: python src/performance_benchmark.py"
echo "  - Run Tests: pytest tests/"
echo ""

# Execute the command passed to the container
if [ $# -eq 0 ]; then
    echo "🔍 Interactive mode - starting bash shell"
    echo "Use 'python src/cbs_calculator.py' to run the example"
    exec /bin/bash
else
    echo "🚀 Executing: $@"
    exec "$@"
fi
EOF

RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER cbsuser

# Add useful aliases for container usage
RUN echo 'alias ll="ls -la"' >> ~/.bashrc
RUN echo 'alias cbs="python src/cbs_calculator.py"' >> ~/.bashrc
RUN echo 'alias analyze="python src/data_analyzer.py"' >> ~/.bashrc
RUN echo 'alias traffic="python src/traffic_generator.py"' >> ~/.bashrc
RUN echo 'alias benchmark="python src/performance_benchmark.py"' >> ~/.bashrc
RUN echo 'alias test="pytest tests/"' >> ~/.bashrc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.cbs_calculator import CBSCalculator; CBSCalculator()" || exit 1

# Expose ports for network testing (if needed)
EXPOSE 5000-5010
EXPOSE 8000-8010

# Set default volumes
VOLUME ["/data", "/results"]

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD []