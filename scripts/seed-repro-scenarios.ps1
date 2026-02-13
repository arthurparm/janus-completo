param(
    [string]$ContainerName = "janus_api",
    [string]$UserId = "seed-admin",
    [switch]$NoReset
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$resetArg = ""
if ($NoReset) {
    $resetArg = "--no-reset"
}

Write-Host "Seeding reproducible scenarios in container '$ContainerName' for user '$UserId'..."
docker exec $ContainerName sh -lc "cd /app && PYTHONPATH=/app python /app/scripts/seed_repro_scenarios.py --user-id '$UserId' $resetArg"
