param(
    [switch]$ForceRecreate,
    [switch]$SkipPipUpgrade,
    [switch]$CopyPassageEnvExample
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$rootVenvDir = Join-Path $root ".venv"
$passageVenvDir = Join-Path $root "passage_service\.venv"
$rootPython = Join-Path $rootVenvDir "Scripts\python.exe"
$rootPip = Join-Path $rootVenvDir "Scripts\pip.exe"
$passagePython = Join-Path $passageVenvDir "Scripts\python.exe"
$passagePip = Join-Path $passageVenvDir "Scripts\pip.exe"

function Get-BootstrapPythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, "-3")
    }

    throw "Python was not found in PATH. Install Python 3.11+ first."
}

function Invoke-BootstrapPython {
    param(
        [string[]]$Args,
        [string]$WorkingDirectory = $root
    )

    $command = Get-BootstrapPythonCommand
    Push-Location $WorkingDirectory
    try {
        if ($command.Count -eq 1) {
            & $command[0] @Args
        } else {
            & $command[0] $command[1] @Args
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Bootstrap Python command failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Ensure-Venv {
    param(
        [string]$VenvDir,
        [string]$Name
    )

    if ($ForceRecreate -and (Test-Path -LiteralPath $VenvDir)) {
        Write-Host "Removing existing $Name virtual environment at $VenvDir" -ForegroundColor DarkYellow
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }

    if (Test-Path -LiteralPath $VenvDir) {
        Write-Host "$Name virtual environment already exists: $VenvDir" -ForegroundColor DarkGray
        return
    }

    Write-Host "Creating $Name virtual environment..." -ForegroundColor Cyan
    Invoke-BootstrapPython -Args @("-m", "venv", $VenvDir)
}

function Install-PackageSet {
    param(
        [string]$PythonPath,
        [string]$PipPath,
        [string]$PackagePath,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $PythonPath)) {
        throw "$Name python runtime not found at $PythonPath"
    }

    if (-not $SkipPipUpgrade) {
        Write-Host "Upgrading pip/setuptools/wheel for $Name..." -ForegroundColor Cyan
        & $PythonPath -m pip install --upgrade pip setuptools wheel
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to upgrade pip toolchain for $Name"
        }
    }

    Write-Host "Installing editable package for $Name from $PackagePath" -ForegroundColor Cyan
    & $PipPath install -e $PackagePath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install package for $Name"
    }
}

function Maybe-CopyPassageEnvExample {
    $examplePath = Join-Path $root "passage_service\.env.example"
    $targetPath = Join-Path $root "passage_service\.env"

    if (-not $CopyPassageEnvExample) {
        return
    }

    if (-not (Test-Path -LiteralPath $examplePath)) {
        Write-Host "passage_service/.env.example not found, skipping env bootstrap." -ForegroundColor DarkYellow
        return
    }

    if (Test-Path -LiteralPath $targetPath) {
        Write-Host "passage_service/.env already exists, leaving it untouched." -ForegroundColor DarkGray
        return
    }

    Copy-Item -LiteralPath $examplePath -Destination $targetPath
    Write-Host "Created passage_service/.env from .env.example" -ForegroundColor Green
}

Ensure-Venv -VenvDir $rootVenvDir -Name "prompt/root"
Ensure-Venv -VenvDir $passageVenvDir -Name "passage_service"

Install-PackageSet -PythonPath $rootPython -PipPath $rootPip -PackagePath (Join-Path $root "prompt_skeleton_service") -Name "prompt/root"
Install-PackageSet -PythonPath $passagePython -PipPath $passagePip -PackagePath (Join-Path $root "passage_service") -Name "passage_service"
Maybe-CopyPassageEnvExample

Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Set GENERATION_LLM_API_KEY and MATERIAL_LLM_API_KEY in your shell or profile." -ForegroundColor Green
Write-Host "2. Start services with one command:" -ForegroundColor Green
Write-Host "   powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload" -ForegroundColor Yellow
