# Scripts

Utility scripts are grouped by responsibility to keep the repository root flatter.

## Layout

- `scripts/docker/`: build, image scan and container size helpers.
- `scripts/ops/`: local environment setup, service management, health checks and PC2 reference material.
- `scripts/backup.sh`: backup routine for the PC1 stack.
- `scripts/security-scan.sh`: repository and container security checks.
- `scripts/docs-check.sh`: lightweight documentation verification helper.

## Common Entry Points

```bash
./scripts/ops/manage.sh status pc1
./scripts/ops/health-check.sh
./scripts/docker/build-multiplatform.sh
./scripts/docker/scan-image.sh janus-api:latest
```
