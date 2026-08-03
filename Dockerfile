# xhaip v1.0 — Hospital AI Platform
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN pip install --no-cache-dir fastapi uvicorn pyyaml

# Copy packages
COPY packages/haip-core/ /app/packages/haip-core/
COPY packages/haip-hospital/ /app/packages/haip-hospital/
COPY config/ /app/config/

# Install haip-core
RUN pip install -e /app/packages/haip-core

# Pre-load and validate agents
ENV PYTHONPATH="/app/packages/haip-core:/app/packages/haip-hospital"
RUN python -c "import sys; sys.path.insert(0,'packages/haip-core'); sys.path.insert(0,'packages/haip-hospital'); from haip.agent import load_from_dir; load_from_dir('/app/packages/haip-hospital/agents/definitions'); print(f'Agents loaded: {len(haip.agent.list_all())}')"

EXPOSE 8769

# Run as non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8769/api/health')" || exit 1

CMD ["python", "-m", "uvicorn", "haip.web_server:app", "--host", "0.0.0.0", "--port", "8769"]
