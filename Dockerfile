# Multi-stage Docker build for CBS Research Application
# Stage 1: Base image with Python and system dependencies
FROM python:3.10-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpcap-dev \
    tcpdump \
    iperf3 \
    iproute2 \
    net-tools \
    iputils-ping \
    traceroute \
    vim \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Development image with additional tools
FROM base as development

# Install development dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Install Jupyter for interactive development
RUN pip install --no-cache-dir jupyter jupyterlab

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/
COPY config/ ./config/
COPY experimental_data.json .

# Set environment variables
ENV PYTHONPATH=/app:$PYTHONPATH
ENV CBS_ENV=development

# Expose ports
EXPOSE 5000 8888 6006

# Development entrypoint
CMD ["python", "-m", "src.dashboard"]

# Stage 3: Production image (optimized)
FROM base as production

# Copy only necessary files
COPY src/ ./src/
COPY config/ ./config/
COPY experimental_data.json .
COPY static/ ./static/
COPY templates/ ./templates/

# Create non-root user
RUN useradd -m -u 1000 cbsuser && \
    chown -R cbsuser:cbsuser /app

USER cbsuser

# Set environment variables
ENV PYTHONPATH=/app:$PYTHONPATH
ENV CBS_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose application port
EXPOSE 5000

# Production entrypoint
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "--timeout=120", "src.dashboard:app"]

# Stage 4: Testing image
FROM development as testing

# Copy test files
COPY pytest.ini .
COPY .coveragerc .

# Run tests by default
CMD ["pytest", "tests/", "-v", "--cov=src", "--cov-report=html", "--cov-report=term"]

# Stage 5: Documentation builder
FROM base as docs

# Install documentation tools
RUN pip install --no-cache-dir \
    sphinx \
    sphinx-rtd-theme \
    sphinx-autodoc-typehints \
    myst-parser

# Copy documentation source
COPY docs/ ./docs/
COPY src/ ./src/
COPY README.md .

WORKDIR /app/docs

# Build documentation
RUN sphinx-build -b html . _build/html

# Serve documentation
FROM nginx:alpine as docs-server
COPY --from=docs /app/docs/_build/html /usr/share/nginx/html
EXPOSE 80

# Stage 6: Performance testing image
FROM base as performance

# Install performance testing tools
RUN apt-get update && apt-get install -y \
    iperf3 \
    netperf \
    nuttcp \
    mtr \
    && rm -rf /var/lib/apt/lists/*

# Copy performance scripts
COPY src/performance_benchmark.py ./src/
COPY src/cbs_calculator.py ./src/
COPY experimental_data.json .

# Run performance benchmarks
CMD ["python", "-m", "src.performance_benchmark", "--duration", "300", "--output", "/results"]

# Stage 7: Network simulator image
FROM base as simulator

# Install additional networking tools
RUN apt-get update && apt-get install -y \
    mininet \
    openvswitch-switch \
    && rm -rf /var/lib/apt/lists/*

# Copy simulator code
COPY src/network_simulator.py ./src/
COPY src/cbs_calculator.py ./src/
COPY config/ ./config/

# Set up OVS
RUN ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema

# Run network simulator
CMD ["python", "-m", "src.network_simulator"]

# Stage 8: ML training image
FROM base as ml-training

# Install ML dependencies
RUN pip install --no-cache-dir \
    torch==2.0.1 \
    tensorflow==2.13.0 \
    scikit-learn==1.3.0 \
    xgboost==1.7.6 \
    lightgbm==4.0.0

# Copy ML code and data
COPY src/ml_optimizer.py ./src/
COPY src/cbs_calculator.py ./src/
COPY experimental_data.json .
COPY ml_models/ ./ml_models/

# Train ML models
CMD ["python", "-m", "src.ml_optimizer", "--train", "--save-models"]

# Stage 9: Demo image with everything
FROM development as demo

# Install additional demo dependencies
RUN pip install --no-cache-dir streamlit gradio

# Copy all demo materials
COPY . .

# Expose all ports
EXPOSE 5000 5001 6006 8501 8888

# Start script for demo
COPY <<EOF /app/start_demo.sh
#!/bin/bash
echo "Starting CBS Research Demo Environment..."
echo "=================================="
echo "Dashboard: http://localhost:5000"
echo "Jupyter: http://localhost:8888"
echo "TensorBoard: http://localhost:6006"
echo "Streamlit: http://localhost:8501"
echo "=================================="

# Start services in background
jupyter lab --ip=0.0.0.0 --allow-root --no-browser &
tensorboard --logdir=./logs --host=0.0.0.0 &
python -m src.dashboard &

# Keep container running
tail -f /dev/null
EOF

RUN chmod +x /app/start_demo.sh

CMD ["/app/start_demo.sh"]