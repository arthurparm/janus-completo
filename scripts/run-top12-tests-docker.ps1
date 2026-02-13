param(
    [string]$ImageTag = "janus-completo-janus-api:test",
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Dockerfile = Join-Path $RepoRoot "janus/docker/Dockerfile"
$BuildContext = Join-Path $RepoRoot "janus"
$EnvFile = Join-Path $RepoRoot "janus/app/.env"

$Tests = @(
    "tests/test_api_visibility_endpoints.py",
    "tests/test_tool_executor_policy_guards.py",
    "tests/test_chat_agent_loop_content_safety.py",
    "tests/test_memory_quota_enforcement.py",
    "tests/test_generative_memory_llm_role_priority.py",
    "tests/test_chat_endpoint_contract.py",
    "tests/test_observability_request_dashboard.py",
    "tests/test_db_migration_service_contract.py",
    "tests/test_knowledge_code_query_contract.py",
    "janus/tests/unit/test_code_analysis_service_calls.py",
    "janus/tests/unit/test_knowledge_repository_code_indexing.py",
    "janus/tests/unit/test_technical_qa_eval_service.py"
)

$PytestArgs = $Tests -join " "

if (-not $SkipBuild) {
    Write-Host "Building Docker test image: $ImageTag"
    docker build --target test -f $Dockerfile -t $ImageTag $BuildContext
} else {
    Write-Host "Skipping image build (-SkipBuild). Using existing image: $ImageTag"
}

Write-Host "Running Top-12 validation tests in Docker..."
docker run --rm `
    -v "${RepoRoot}:/repo" `
    -w /repo `
    --env-file $EnvFile `
    -e PYTHONPATH=/repo/janus `
    $ImageTag `
    /bin/sh -lc "/opt/venv/bin/python -m pytest -q $PytestArgs"
