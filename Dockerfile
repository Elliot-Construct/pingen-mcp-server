# Pingen MCP server — public streamable-HTTP deployment (PINGEN-02).
#
# Deliberately publishes NO port: the container is reachable only from
# containers on a shared Docker network (Traefik), never from the host LAN
# or the internet. See design D3 in openspec/changes/deploy-pingen-mcp-http.
FROM python:3.12-slim

WORKDIR /app

# Build metadata first so source edits do not invalidate the dependency layer.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Non-root: the server only reads its env file and calls out to the Pingen API.
RUN useradd --create-home --uid 10001 app
USER app

# Container-interface bind (no `ports:` in compose, so nothing is exposed).
# HTTP mode is selected by PINGEN_MCP_PUBLIC_URL in the environment; without
# it the entry point falls back to stdio.
ENV PINGEN_MCP_BIND=0.0.0.0 \
    PINGEN_MCP_PORT=8747

CMD ["pingen-mcp-server"]
