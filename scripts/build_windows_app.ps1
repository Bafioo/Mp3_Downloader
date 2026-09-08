param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$AppName = "MP3 Downloader"
$EntryPoint = "mp3_downloader_gui.py"
$IconPng = "Images\icon.png"
$IconIco = "Images\icon.ico"

if (-not $env:PYINSTALLER_CONFIG_DIR) {
    $env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) "build\pyinstaller-config"
}

function Test-PythonImport {
    param([string]$ImportStatement)

    & $Python -c $ImportStatement > $null 2> $null
    return $LASTEXITCODE -eq 0
}

function Test-BinaryPath {
    param(
        [string]$Path,
        [string]$VersionArgument = "-version"
    )

    if (-not $Path) {
        return $false
    }

    try {
        & $Path $VersionArgument > $null 2> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Get-ApplicationPath {
    param([string[]]$Names)

    foreach ($Name in $Names) {
        $Command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($Command) {
            return $Command.Source
        }
    }

    return $null
}

function Find-WingetFfmpegBinary {
    param([string]$ExecutableName)

    if (-not $env:LOCALAPPDATA) {
        return $null
    }

    $PackageRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (-not (Test-Path -LiteralPath $PackageRoot)) {
        return $null
    }

    $Packages = Get-ChildItem -LiteralPath $PackageRoot -Directory -Filter "Gyan.FFmpeg_*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($Package in $Packages) {
        $Builds = Get-ChildItem -LiteralPath $Package.FullName -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($Build in $Builds) {
            $Candidate = Join-Path $Build.FullName "bin\$ExecutableName"
            if (Test-BinaryPath -Path $Candidate) {
                return $Candidate
            }
            if (Test-Path -LiteralPath $Candidate -ErrorAction SilentlyContinue) {
                return $Candidate
            }
        }
    }

    return $null
}

function Find-PythonDetectedBinary {
    param([string]$FunctionName)

    try {
        $Detected = & $Python -c "import mp3_download; path = mp3_download.$FunctionName(); print(path or '')"
        if ($LASTEXITCODE -eq 0 -and $Detected) {
            $DetectedPath = ($Detected | Select-Object -Last 1).Trim()
            if (Test-Path -LiteralPath $DetectedPath) {
                return $DetectedPath
            }
        }
    }
    catch {
        return $null
    }

    return $null
}

function Find-JavascriptRuntime {
    $Candidates = @(
        @{ Name = "deno"; Argument = "--version" },
        @{ Name = "node"; Argument = "--version" },
        @{ Name = "qjs"; Argument = "--version" },
        @{ Name = "quickjs"; Argument = "--version" }
    )

    foreach ($Candidate in $Candidates) {
        $Executable = Get-ApplicationPath -Names @("$($Candidate.Name).exe", $Candidate.Name)
        if ($Executable -and (Test-BinaryPath -Path $Executable -VersionArgument $Candidate.Argument)) {
            return $Executable
        }
    }

    return $null
}

if (-not (Test-PythonImport -ImportStatement "import PyInstaller")) {
    Write-Error "PyInstaller is not installed. Run: $Python -m pip install -r requirements-build.txt"
}

if (-not (Test-PythonImport -ImportStatement "import yt_dlp, yt_dlp_ejs")) {
    Write-Error "yt-dlp with EJS support is not installed. Run: $Python -m pip install -U -r requirements.txt"
}

if (-not (Test-Path -LiteralPath $IconPng)) {
    Write-Error "Missing app icon: $IconPng"
}

$PyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", $AppName,
    "--add-data", "$IconPng;Images",
    "--collect-all", "yt_dlp_ejs",
    "--hidden-import", "yt_dlp_ejs",
    "--hidden-import", "yt_dlp_ejs.yt",
    "--hidden-import", "yt_dlp_ejs.yt.solver"
)

if (Test-Path -LiteralPath $IconIco) {
    $PyInstallerArgs += @("--icon", $IconIco)
}

$FfmpegPath = Get-ApplicationPath -Names @("ffmpeg.exe", "ffmpeg")
if (-not $FfmpegPath) {
    $FfmpegPath = Find-WingetFfmpegBinary -ExecutableName "ffmpeg.exe"
}
if (-not $FfmpegPath) {
    $FfmpegPath = Find-PythonDetectedBinary -FunctionName "find_ffmpeg"
}
if ($FfmpegPath) {
    $PyInstallerArgs += @("--add-binary", "$FfmpegPath;.")
}
else {
    Write-Warning "ffmpeg was not found, so it will not be bundled."
}

$FfprobePath = Get-ApplicationPath -Names @("ffprobe.exe", "ffprobe")
if (-not $FfprobePath) {
    $FfprobePath = Find-WingetFfmpegBinary -ExecutableName "ffprobe.exe"
}
if (-not $FfprobePath) {
    $FfprobePath = Find-PythonDetectedBinary -FunctionName "find_ffprobe"
}
if ($FfprobePath) {
    $PyInstallerArgs += @("--add-binary", "$FfprobePath;.")
}
else {
    Write-Warning "ffprobe was not found, so it will not be bundled."
}

$JavascriptRuntimePath = Find-JavascriptRuntime
if ($JavascriptRuntimePath) {
    $PyInstallerArgs += @("--add-binary", "$JavascriptRuntimePath;.")
}
else {
    Write-Warning "No JavaScript runtime was found, so none will be bundled."
    Write-Warning "The built app will require Deno 2.3+ or Node.js 22+ separately."
}

& $Python -m PyInstaller @PyInstallerArgs $EntryPoint
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Built: dist\$AppName\$AppName.exe"
