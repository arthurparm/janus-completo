# syntax=docker/dockerfile:1.7
# Multi-stage build: separates build-time deps from runtime

# --- Stage 1: Dependencies ---
FROM node:20-alpine AS dependencies

WORKDIR /app

COPY package*.json ./

# Use npm install with --legacy-peer-deps (more forgiving than npm ci)
RUN npm install --legacy-peer-deps --no-audit --no-fund


# --- Stage 2: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY package*.json ./
COPY . .

# Pre-build Angular app for production
RUN npm run build --prod 2>/dev/null || npm run build


# --- Stage 3: Runtime (production) ---
FROM node:20-alpine

WORKDIR /app

ARG JANUS_BUILD_REF=local-dev
ARG JANUS_BUILD_DATE
ARG JANUS_VERSION=0.5.44

# Copy only built artifacts from builder
COPY --from=builder /app/dist ./dist
COPY docker/server.mjs ./server.mjs

ENV JANUS_BUILD_REF=${JANUS_BUILD_REF}
ENV JANUS_BUILD_DATE=${JANUS_BUILD_DATE}
ENV JANUS_VERSION=${JANUS_VERSION}
ENV JANUS_API_URL=http://janus-api:8000
ENV JANUS_PUBLIC_API_URL=http://janus-public-api:8000
ENV PORT=4300

LABEL org.opencontainers.image.revision=${JANUS_BUILD_REF} \
      org.opencontainers.image.created=${JANUS_BUILD_DATE} \
      org.opencontainers.image.version=${JANUS_VERSION}

EXPOSE 4300

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:4300/ | grep -q "<app-root" || exit 1

# Serve the Angular browser bundle and proxy backend API calls inside the PC1 network.
CMD ["node", "server.mjs"]
