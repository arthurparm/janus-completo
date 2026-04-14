#!/usr/bin/env bash
# Security scanning and hardening checks for the current JANUS workspace

set -euo pipefail

KNOWN_CONTAINERS=(
  janus_api_pc1
  janus_api
  janus_frontend_pc1
  janus_frontend
  janus_postgres_pc1
  janus_postgres
  janus_redis_pc1
  janus_redis
  janus_rabbitmq_pc1
  janus_rabbitmq
  janus_prometheus
  janus_grafana
  janus_loki
)

scan_image_with_tool() {
  local image="$1"

  if command -v trivy >/dev/null 2>&1; then
    trivy image --severity HIGH,CRITICAL --ignore-unfixed "$image" || true
  elif command -v docker-scout >/dev/null 2>&1; then
    docker-scout cves "$image" --only-severity high,critical || true
  else
    echo "  ⚠️  Neither trivy nor docker-scout is installed; skipping image scan for $image"
  fi
}

echo "🔒 JANUS SECURITY SCAN"
echo "═════════════════════════════════════════════════════════════════════"
echo ""

echo "🔍 Scanning Docker images for vulnerabilities..."
echo ""

for container in "${KNOWN_CONTAINERS[@]}"; do
  if docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
    IMAGE="$(docker inspect "$container" --format='{{.Config.Image}}')"
    echo "Scanning image used by $container: $IMAGE"
    scan_image_with_tool "$IMAGE"
  fi
done

echo ""
echo "🔐 Checking container security..."
echo ""

echo "✓ Non-root user check:"
for container in "${KNOWN_CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
        USER=$(docker inspect "$container" --format='{{.Config.User}}')
        if [ -z "$USER" ] || [ "$USER" = "root" ]; then
            echo "  ⚠️  $container running as root (or default image user)"
        else
            echo "  ✅ $container running as: $USER"
        fi
    fi
done

echo ""
echo "✓ Container hardening check:"
for container in "${KNOWN_CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -qx "$container"; then
        PRIVILEGED=$(docker inspect "$container" --format='{{.HostConfig.Privileged}}')
        READONLY_ROOTFS=$(docker inspect "$container" --format='{{.HostConfig.ReadonlyRootfs}}')
        echo "  • $container privileged=$PRIVILEGED readonly_rootfs=$READONLY_ROOTFS"
    fi
done

echo ""
echo "✓ Network isolation check:"
for network in janus-pc1-net janus-pc2-net; do
    if docker network inspect "$network" >/dev/null 2>&1; then
        echo "  ✅ $network exists"
    else
        echo "  ⚠️  $network not found"
    fi
done

echo ""
echo "✓ Secret management check:"
if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --no-banner --source . || true
elif command -v trivy >/dev/null 2>&1; then
    trivy fs --scanners secret,config --severity HIGH,CRITICAL . || true
else
    echo "  ⚠️  Install gitleaks or trivy for repository secret scanning"
fi

echo ""
echo "✓ Dockerfile security checks:"
echo "  - Multi-stage builds: $(grep -c "^FROM" backend/docker/Dockerfile) stages"
echo "  - Alpine base: $(grep -c "alpine" backend/docker/Dockerfile) matches"
echo "  - Non-root user configured: $(grep -c "^USER " backend/docker/Dockerfile) matches"
echo "  - No sudo usage: $(grep -c "sudo\\|SUDO" backend/docker/Dockerfile) matches"
echo "  - No Dockerfile secret envs: $(grep -c "ENV.*PASSWORD\\|ENV.*SECRET" backend/docker/Dockerfile) matches"

echo ""
echo "✓ Dependency scanning:"
if [ -f "backend/pyproject.toml" ]; then
    echo "  Python dependencies found"
    if command -v pip-audit >/dev/null 2>&1; then
        pip-audit || true
    else
        echo "  Install pip-audit to scan Python dependencies"
    fi
fi

if [ -f "frontend/package.json" ]; then
    echo "  Node dependencies found"
    if command -v npm >/dev/null 2>&1; then
        npm audit --prefix frontend --omit=dev || true
    fi
fi

echo ""
echo "═════════════════════════════════════════════════════════════════════"
echo "✅ Security scan complete!"
echo ""
echo "Recommendations:"
echo "  1. Keep Docker images updated: docker pull <image>"
echo "  2. Run 'docker scan' for vulnerability detection"
echo "  3. Use Snyk for continuous dependency scanning"
echo "  4. Enable Docker security options (--cap-drop, --read-only)"
echo "  5. Use image signing for production deployments"
