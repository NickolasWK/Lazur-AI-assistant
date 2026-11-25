param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

try {
    $demoVenv = Join-Path $PSScriptRoot '.venv'
    $workspaceVenv = Join-Path (Split-Path $PSScriptRoot -Parent) '.venv'
    if (Test-Path -LiteralPath (Join-Path $workspaceVenv 'Scripts\python.exe')) {
        $demoVenv = $workspaceVenv
    }
    $demoPython = Join-Path $demoVenv 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $demoPython)) {
        $candidates = @()
        if (Get-Command py -ErrorAction SilentlyContinue) {
            $candidates += (& py -3 -c 'import sys; print(sys.executable)' 2>$null)
        }
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCommand -and $pythonCommand.Source -notlike '*\Microsoft\WindowsApps\*') {
            $candidates += $pythonCommand.Source
        }
        $basePython = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $basePython) { throw 'Python 3.10+ is required. Install Python, then run start_demo.cmd again.' }
        & $basePython -m venv $demoVenv
        if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python virtual environment.' }
    }
    $dependencies = @('requirements.txt', 'requirements-demo.txt') | ForEach-Object {
        $dependencyBytes = [System.IO.File]::ReadAllBytes((Join-Path $PSScriptRoot $_))
        $dependencyHash = [System.Security.Cryptography.SHA256]::Create()
        try { [BitConverter]::ToString($dependencyHash.ComputeHash($dependencyBytes)) }
        finally { $dependencyHash.Dispose() }
    }
    $signature = $dependencies -join ':'
    $marker = Join-Path $demoVenv 'lazur-demo-requirements.sha256'
    if (-not (Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne $signature) {
        & $demoPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-demo.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Cannot install dependencies. Check the network connection.' }
        Set-Content -LiteralPath $marker -Value $signature -Encoding ASCII
    }
    Write-Host "Open http://127.0.0.1:$Port in your browser. Stop: Ctrl+C."
    & $demoPython -m uvicorn skeleton.main:app --app-dir $PSScriptRoot --host 127.0.0.1 --port $Port
    exit $LASTEXITCODE
}
catch {
    Write-Host $_ -ForegroundColor Red
    exit 1
}
