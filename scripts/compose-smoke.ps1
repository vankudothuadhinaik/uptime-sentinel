$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is required for the Compose smoke test."
}
if (-not (Test-Path -LiteralPath ".env")) {
    throw "Create a test-only .env from .env.example before running this smoke test."
}

docker compose config --quiet
docker compose up --build --detach
try {
    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health/live"
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    docker compose ps
    if (-not $ready) {
        throw "API healthcheck did not become ready within 60 seconds."
    }
    py scripts/compose-e2e.py
    if ($LASTEXITCODE -ne 0) {
        throw "Compose end-to-end smoke test failed."
    }
    Write-Output "Compose smoke test passed: API health and registration-to-worker workflow succeeded."
} finally {
    docker compose logs --no-color
    docker compose down
}
