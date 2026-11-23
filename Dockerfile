# Multi-stage Dockerfile for Autonomous Incident Triage Agent

# ---------------------------------------------------------------------------
# Stage 1: Build Rust MCP Server
# ---------------------------------------------------------------------------
FROM rust:1.80-slim AS rust-builder
WORKDIR /build

COPY mcp-server ./mcp-server
RUN cd mcp-server && cargo build --release

# ---------------------------------------------------------------------------
# Stage 2: Build React Web UI Production Assets
# ---------------------------------------------------------------------------
FROM node:24-slim AS ui-builder
WORKDIR /build

COPY web-ui ./web-ui
RUN cd web-ui && npm ci && npm run build

# ---------------------------------------------------------------------------
# Stage 3: Python Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim
WORKDIR /app

# Install Node.js 24 runtime for @modelcontextprotocol/server-filesystem
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy package descriptors and source code
COPY agent-client ./agent-client
COPY web-backend ./web-backend

# Install filesystem MCP server dependencies
RUN cd agent-client && npm ci

# Install Python packages (core and web backend)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e ./agent-client -e ./web-backend

# Copy Rust MCP Server binary from rust-builder
COPY --from=rust-builder /build/mcp-server/target/release/ops-telemetry-mcp ./mcp-server/target/release/ops-telemetry-mcp
RUN chmod +x ./mcp-server/target/release/ops-telemetry-mcp

# Copy built frontend UI from ui-builder
COPY --from=ui-builder /build/web-ui/dist ./web-ui/dist

# Copy mock data, workspace, and configuration files
COPY mock_data ./mock_data
COPY pyrightconfig.json pytest.ini .env.example ./

# Expose FastAPI backend / static UI port
EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000
ENV OPS_DATA_DIR=/app/mock_data
ENV WORKSPACE_DIR=/app/mock_data/workspace

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
