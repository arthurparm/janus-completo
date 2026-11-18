# Docker Buildx Configuration for Multi-Platform Builds

This directory contains optimized Dockerfiles for production use with multi-platform support (linux/amd64, linux/arm64).

## Files

- **Dockerfile** - Optimized backend (FastAPI) with Alpine base
- **.dockerignore** - Reduces build context size

## Building

### Local Build (Single Platform)

```bash
# Backend (Final stage)
docker build -t janus-api:latest -f docker/Dockerfile --target final .

# Backend (Test stage)
docker build -t janus-api:test -f docker/Dockerfile --target test .
```

### Multi-Platform Build (Buildx)

```bash
# Build and push to registry (requires Docker Buildx)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag your-registry/janus-api:latest \
  --push \
  -f docker/Dockerfile .

# Or use the provided script:
./scripts/docker/build-multiplatform.sh
```

## Key Optimizations

1. **Alpine Linux**: Reduces base image from 200MB (Debian slim) to 80MB
2. **Multi-stage builds**: Separates builder from runtime, removes build dependencies
3. **Layer caching**: Optimized COPY order for faster rebuilds
4. **Non-root user**: Security hardened (UID 1000)
5. **Cache mounts**: Speeds up dependency installation
6. **Health checks**: Built-in readiness probes

## Size Comparison

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Base Image | 200 MB | 80 MB | -60% |
| Final Image | 650-750 MB | 350-450 MB | -45% |

## Security Scanning

```bash
# Run Docker Scout scan
./scripts/docker/scan-image.sh janus-api:latest

# Or with docker-scout CLI
docker-scout cves janus-api:latest --only-severity high,critical
docker-scout recommendations janus-api:latest
```

## Build Arguments

```dockerfile
ARG JANUS_BUILD_REF=local-dev      # Git commit SHA or custom ref
ARG JANUS_BUILD_DATE               # Build timestamp
ARG JANUS_VERSION=0.5.44           # Semantic version
```

Example:

```bash
docker build \
  --build-arg JANUS_BUILD_REF="$(git rev-parse --short HEAD)" \
  --build-arg JANUS_BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg JANUS_VERSION="0.5.44" \
  .
```

## Platform-Specific Notes

### ARM64 (Apple Silicon, EC2 Graviton)

Alpine on ARM64 may require additional compile flags for some ML packages:

```bash
# If sentence-transformers fails on ARM64:
LDFLAGS="-lm" ARCHFLAGS="-arch arm64" docker build .
```

### amd64 (Intel/AMD)

Standard build process, no special considerations.

## Labels

Images include OCI-compliant metadata:

```dockerfile
LABEL org.opencontainers.image.revision=${JANUS_BUILD_REF}
LABEL org.opencontainers.image.created=${JANUS_BUILD_DATE}
LABEL org.opencontainers.image.version=${JANUS_VERSION}
```

Inspect with:

```bash
docker inspect janus-api:latest | grep -A 5 Labels
```

## Troubleshooting

### Build Fails on Alpine

Alpine requires build tools for native extensions. Ensure Stage 1 has:
```dockerfile
RUN apk add --no-cache gcc musl-dev linux-headers g++ make
```

### Docker CLI Not Found in Container

Alpine doesn't have docker-ce-cli in the stable repo. Use edge:
```dockerfile
RUN apk add --no-cache docker-cli --repository https://dl-cdn.alpinelinux.org/alpine/edge/community
```

### Scout CLI Missing

Install docker-scout:
```bash
npm install -g @docker/scout-cli
# or
brew install docker/scout-cli/scout
```
