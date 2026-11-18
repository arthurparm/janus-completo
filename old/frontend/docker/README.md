# Docker Build Configuration for Frontend

## Multi-Platform Build

```bash
# Build for AMD64 and ARM64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg JANUS_BUILD_REF="$(git rev-parse --short HEAD)" \
  --build-arg JANUS_BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg JANUS_VERSION="0.5.44" \
  --tag your-registry/janus-frontend:latest \
  --push \
  .
```

## Stages

- **dependencies**: Installs npm packages
- **builder**: Compiles Angular app with `npm run build`
- **final**: Runs compiled app with `serve` (lightweight HTTP server)

## Build Arguments

- `JANUS_BUILD_REF`: Git commit SHA
- `JANUS_BUILD_DATE`: Build timestamp
- `JANUS_VERSION`: Semantic version

## Image Size

- **Before**: ~400MB (with ng serve)
- **After**: ~150-200MB (pre-compiled dist + serve)
- **Reduction**: ~60% smaller
