# health-os MCP server image (stdio). Used by demo/docker-compose.yml and published to
# ghcr.io/andronaft/health-os (MCP Registry: server.json); also usable on its own
# with DATABASE_URL pointing at your Postgres.
FROM python:3.13-slim

# MCP Registry ownership check + OCI metadata (GHCR links the package to the repo via source)
LABEL io.modelcontextprotocol.server.name="io.github.andronaft/health-os" \
      org.opencontainers.image.source="https://github.com/andronaft/health-os" \
      org.opencontainers.image.description="Local-first personal health record exposed over MCP" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .

# MCP over stdio: the client starts the container and talks through stdin/stdout
CMD ["python", "-m", "mcp_server.server"]
