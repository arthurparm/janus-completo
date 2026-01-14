# Development Dockerfile for Janus Frontend
# Optimized for caching node_modules and fast startup

FROM node:20-alpine

WORKDIR /app

# Install dependencies in a separate layer for caching
# We use package*.json to match both package.json and package-lock.json (if it exists)
COPY package*.json ./

# Clean install of dependencies
# We use --legacy-peer-deps as it was used in the original command
RUN npm install --legacy-peer-deps

# Copy the rest of the application source
# (Note: In dev, this is often shadowed by a bind mount, but good for completeness)
COPY . .

# Expose the Angular default port
EXPOSE 4300

# Default command matches the one used in docker-compose originally
# We added --poll 2000 to help with file watching on Windows/WSL
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4300", "--poll", "2000", "--proxy-config", "proxy.docker.conf.json"]
