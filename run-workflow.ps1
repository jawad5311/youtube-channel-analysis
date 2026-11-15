param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Channel,
    [int]$Timeout = 30
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonCandidates = @(
    (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    'C:\Program Files\LibreOffice\program\python.exe'
)
$python = $null
foreach ($candidate in $pythonCandidates) {
    if (-not $candidate -or -not (Test-Path -LiteralPath $candidate)) {
        continue
    }
    try {
        & $candidate -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate
            break
        }
    } catch {
        continue
    }
}
if (-not $python) {
    throw 'No usable Python 3.10 or newer interpreter was found. Install Python or LibreOffice.'
}

Push-Location -LiteralPath $projectRoot
try {
    & $python (Join-Path $projectRoot 'orchestrator.py') $Channel '--timeout' $Timeout
    if ($LASTEXITCODE -ne 0) {
        throw "The collection phase failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
