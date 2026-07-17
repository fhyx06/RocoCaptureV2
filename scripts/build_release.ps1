param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$Version = (& $Python -c "from src.__about__ import APP_VERSION; print(APP_VERSION)").Trim()
$AppDirName = "RocoCaptureV2-v$Version-win-x64"
$DistAppDir = Join-Path $Root "dist\$AppDirName"
$ReleaseDir = Join-Path $Root "release"
$ZipPath = Join-Path $ReleaseDir "$AppDirName-portable.zip"
$LatestJsonPath = Join-Path $ReleaseDir "latest.json"
$ContentPackVersion = 1
$ContentSourceDir = Join-Path $Root "content_sources\S3"
$ContentSeasonFile = Join-Path $ContentSourceDir "season.json"
$ContentSpiritsDir = Join-Path $ContentSourceDir "spirits"
$ContentPackDir = Join-Path $ReleaseDir "content"
$ContentPackPath = Join-Path $ContentPackDir "S3-v$ContentPackVersion.zip"

foreach ($RequiredPath in @($ContentSeasonFile, $ContentSpiritsDir)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "S3 content source was not found: $RequiredPath"
    }
}

if ($Clean) {
    foreach ($Path in @("build", "dist", "release")) {
        $FullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $Path))
        if ((Split-Path -Parent $FullPath) -ne $Root) {
            throw "Refusing to clean a path outside the project root: $FullPath"
        }
        if (Test-Path $FullPath) {
            Remove-Item -LiteralPath $FullPath -Recurse -Force
        }
    }
}

$PyInstaller = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstaller)) {
    $PyInstaller = "pyinstaller"
}

& $PyInstaller --noconfirm "RocoCaptureV2.spec"

if (-not (Test-Path $DistAppDir)) {
    throw "Build output directory was not found: $DistAppDir"
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $ContentPackDir | Out-Null

& $Python "scripts\build_content_pack.py" `
    --season-file $ContentSeasonFile `
    --spirits-dir $ContentSpiritsDir `
    --version $ContentPackVersion `
    --output $ContentPackPath
if ($LASTEXITCODE -ne 0) {
    throw "S3 content pack build failed."
}

$BundledContentRoot = Join-Path $DistAppDir "data\content"
$InstallContentScript = @"
import sys
from pathlib import Path
from src.content.repository import BUILTIN_CONTENT_ROOT, ContentRepository
from src.services.content_pack_service import ContentPackService

archive = Path(sys.argv[1])
content_root = Path(sys.argv[2])
repository = ContentRepository(BUILTIN_CONTENT_ROOT, content_root)
ContentPackService(repository, content_root).install_pack(archive)
"@
& $Python -c $InstallContentScript $ContentPackPath $BundledContentRoot
if ($LASTEXITCODE -ne 0) {
    throw "Bundling S3 content pack failed."
}

Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination (Join-Path $DistAppDir "README.md") -Force

$VersionText = @(
    "RocoCaptureV2 v$Version",
    "Build: Windows x64 portable",
    "Entry: RocoCaptureV2-v$Version.exe",
    "Content: built-in S1/S2 + bundled S3 v$ContentPackVersion"
)
Set-Content -LiteralPath (Join-Path $DistAppDir "VERSION.txt") -Value $VersionText -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path $DistAppDir -DestinationPath $ZipPath -Force

$LatestManifest = [ordered]@{
    version = $Version
    tag_name = "v$Version"
    release_url = "https://github.com/fhyx06/RocoCaptureV2/releases/tag/v$Version"
    download_url = "https://github.com/fhyx06/RocoCaptureV2/releases/download/v$Version/$AppDirName-portable.zip"
    notes = "v$Version"
}
$LatestJson = $LatestManifest | ConvertTo-Json -Depth 4
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($LatestJsonPath, ($LatestJson + [Environment]::NewLine), $Utf8NoBom)

Write-Host "Release package created:"
Write-Host $ZipPath
Write-Host "Update manifest created:"
Write-Host $LatestJsonPath
Write-Host "Standalone S3 content pack created:"
Write-Host $ContentPackPath
