#!/usr/bin/env bash
# Quick security scan with Docker Scout

IMAGE="${1:?Usage: $0 <image-name:tag>}"

echo "🔍 Docker Scout Security Scan"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Image: ${IMAGE}"
echo ""

if ! command -v docker-scout &>/dev/null; then
    echo "⚠️  docker-scout not found."
    echo ""
    echo "Install options:"
    echo "  1. npm install -g @docker/scout-cli"
    echo "  2. brew install docker/scout-cli/scout"
    echo "  3. Download from: https://github.com/docker/scout-cli/releases"
    exit 1
fi

echo "📋 Critical & High Vulnerabilities:"
docker-scout cves "${IMAGE}" --only-severity critical,high || true

echo ""
echo "💡 Recommendations:"
docker-scout recommendations "${IMAGE}" || true

echo ""
echo "📊 Full Report:"
docker-scout compare "${IMAGE}" --to-latest || true
