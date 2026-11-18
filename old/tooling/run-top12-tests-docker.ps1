param(
    [string]$ImageTag = "janus-completo-janus-api:test",
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Dockerfile = Join-Path $RepoRoot "backend/docker/Dockerfile"
$BuildContext = Join-Path $RepoRoot "janus"
$EnvFile = Join-Path $RepoRoot "backend/app/.env"

$Tests = @(
    "qa/test_api_visibility_endpoints.py",
    "qa/test_tool_executor_policy_guards.py",
    "qa/test_chat_agent_loop_content_safety.py",
    "qa/test_memory_quota_enforcement.py",
    "qa/test_generative_memory_llm_role_priority.py",
    "qa/test_chat_endpoint_contract.py",
    "qa/test_observability_request_dashboard.py",
    "qa/test_db_migration_service_contract.py",
    "qa/test_knowledge_code_query_contract.py",
    "backend/tests/unit/test_code_analysis_service_calls.py",
    "backend/tests/unit/test_knowledge_repository_code_indexing.py",
    "backend/tests/unit/test_technical_qa_eval_service.py"
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
