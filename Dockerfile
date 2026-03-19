FROM python:3.12-slim AS base

WORKDIR /app

# Install only production dependencies
COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/ data/

RUN pip install --no-cache-dir .

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

ENV DATABRIDGE_DB_PATH=/app/data/titanic.db
ENV DATABRIDGE_TRANSPORT=stdio
ENV DATABRIDGE_LOG_LEVEL=INFO

ENTRYPOINT ["python", "-m", "mcp_databridge"]
