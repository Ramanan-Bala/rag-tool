FROM python:3.12-slim

LABEL org.opencontainers.image.title="repo-rag"
LABEL org.opencontainers.image.description="Local RAG indexer and MCP server for AI coding agents"
LABEL org.opencontainers.image.source="https://github.com/<YOUR_GITHUB_USERNAME>/repo-rag"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REPO_RAG_INDEX_DIR=/data/.repo-rag

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

VOLUME ["/data"]

ENTRYPOINT ["rag"]
CMD ["mcp-server"]
