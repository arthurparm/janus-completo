#!/usr/bin/env bash
# Multi-platform build and push script with Docker Scout scanning

set -e

# Configuration
REGISTRY="${REGISTRY:-docker.io}"
NAMESPACE="${NAMESPACE:-arthurparaiso}"
VERSION="${VERSION:-0.5.44}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
BUILD_REF="${BUILD_REF:-$(git rev-parse --short HEAD 2>/dev/null || echo 'local-dev')}"

FRONTEND_IMAGE="${REGISTRY}/${NAMESPACE}/janus-frontend:${VERSION}"
BACKEND_IMAGE="${REGISTRY}/${NAMESPACE}/janus-api:${VERSION}"

echo "🚀 Building Janus Multi-Platform Images"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Frontend: ${FRONTEND_IMAGE}"
echo "Backend:  ${BACKEND_IMAGE}"
echo "Platforms: linux/amd64,linux/arm64"
echo "Build Date: ${BUILD_DATE}"
echo "Build Ref: ${BUILD_REF}"
echo ""

# Check if buildx is available
if ! docker buildx version &>/dev/null; then
    echo "⚠️  Docker Buildx not found. Installing..."
    docker run --privileged --rm tonistiigi/binfmt --install all
fi

# Build Frontend
echo "📦 Building Frontend..."
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg JANUS_BUILD_REF="${BUILD_REF}" \
    --build-arg JANUS_BUILD_DATE="${BUILD_DATE}" \
    --tag "${FRONTEND_IMAGE}" \
    --tag "${REGISTRY}/${NAMESPACE}/janus-frontend:latest" \
    --load \
    --progress=plain \
    ./frontend \
    -f ./frontend/docker/Dockerfile

echo "✅ Frontend built: ${FRONTEND_IMAGE}"
echo ""

# Build Backend
echo "📦 Building Backend..."
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg JANUS_BUILD_REF="${BUILD_REF}" \
    --build-arg JANUS_BUILD_DATE="${BUILD_DATE}" \
    --build-arg JANUS_VERSION="${VERSION}" \
    --target final \
    --tag "${BACKEND_IMAGE}" \
    --tag "${REGISTRY}/${NAMESPACE}/janus-api:latest" \
    --load \
    --progress=plain \
    ./backend \
    -f ./backend/docker/Dockerfile

echo "✅ Backend built: ${BACKEND_IMAGE}"
echo ""

# Scan with Docker Scout (requires Docker Desktop or Scout CLI)
echo "🔍 Running Docker Scout security scan..."
echo ""

if command -v docker-scout &>/dev/null; then
    # Using Scout CLI
    echo "Frontend Security Report:"
    docker-scout cves "${FRONTEND_IMAGE}" --only-severity high,critical || true
    echo ""
    echo "Backend Security Report:"
    docker-scout cves "${BACKEND_IMAGE}" --only-severity high,critical || true
    echo ""
    
    echo "Frontend Recommendations:"
    docker-scout recommendations "${FRONTEND_IMAGE}" || true
    echo ""
    echo "Backend Recommendations:"
    docker-scout recommendations "${BACKEND_IMAGE}" || true
else
    echo "⚠️  docker-scout CLI not installed. Install with: npm install -g @docker/scout-cli"
    echo "Skipping Scout scan."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Build complete!"
echo ""
echo "To push to registry:"
echo "  docker buildx build --push --platform linux/amd64,linux/arm64 \\"
echo "    --tag ${FRONTEND_IMAGE} ./frontend -f ./frontend/docker/Dockerfile"
echo "  docker buildx build --push --platform linux/amd64,linux/arm64 \\"
echo "    --tag ${BACKEND_IMAGE} ./backend -f ./backend/docker/Dockerfile"
echo ""
echo "To inspect images:"
echo "  docker inspect ${FRONTEND_IMAGE}"
echo "  docker inspect ${BACKEND_IMAGE}"
