# health-os MCP server image (stdio). Used by docker-compose.demo.yml; also usable on its own
# with DATABASE_URL pointing at your Postgres.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .

# MCP over stdio: the client starts the container and talks through stdin/stdout
CMD ["python", "-m", "mcp_server.server"]
