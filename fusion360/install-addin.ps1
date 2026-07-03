# Installs EccentricLobeGearGenerator into the Fusion 360 Add-Ins folder.
# Run in PowerShell:  .\install-addin.ps1

$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'EccentricLobeGearGenerator'
$destRoot = Join-Path $env:APPDATA 'Autodesk\Autodesk Fusion 360\API\AddIns'
$dest = Join-Path $destRoot 'EccentricLobeGearGenerator'

if (-not (Test-Path $source)) {
    Write-Error "Source folder not found: $source"
}

# Generate toolbar icons required by Fusion addButtonDefinition
$iconScript = Join-Path $source 'make_icons.py'
if (Test-Path $iconScript) {
    python $iconScript
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Icon generation failed; add-in may still need resources/16x16.png and 32x32.png"
    }
}

if (-not (Test-Path $destRoot)) {
    New-Item -ItemType Directory -Path $destRoot -Force | Out-Null
}

if (Test-Path $dest) {
    Remove-Item -Path $dest -Recurse -Force
}

Copy-Item -Path $source -Destination $dest -Recurse -Force

Write-Host ''
Write-Host 'Installed to:' $dest
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1. Open Fusion 360'
Write-Host '  2. UTILITIES -> Scripts and Add-Ins'
Write-Host '  3. Add-Ins tab -> find EccentricLobeGearGenerator'
Write-Host '  4. Check "Run on Startup" (or click Run once)'
Write-Host '  5. SOLID workspace -> ADD-INS panel -> "Eccentric Lobe Gears"'
Write-Host ''
