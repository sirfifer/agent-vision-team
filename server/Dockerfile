FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    sqlite3 \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 (for Claude Code CLI and frontend build)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install uv --no-cache-dir

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Set up workspace
WORKDIR /workspace
COPY . .

# Install Python dependencies for all MCP servers and Gateway
RUN cd mcp-servers/knowledge-graph && uv sync && cd ../.. \
    && cd mcp-servers/quality && uv sync && cd ../.. \
    && cd mcp-servers/governance && uv sync && cd ../.. \
    && cd server && uv sync && cd ..

# Build web dashboard
RUN cd extension/webview-dashboard && npm ci && npm run build -- --mode web

# Configure nginx
COPY server/nginx.conf /etc/nginx/sites-available/default

# Make entrypoint executable
COPY server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 443 8080

ENTRYPOINT ["/entrypoint.sh"]
