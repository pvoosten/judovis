<#
.SYNOPSIS
    Builds, tests and optionally exports the Judo Technique Visualizer.

.DESCRIPTION
    Steps, each stopping the build on failure:
      1. dotnet build of the Godot C# project
      2. unit tests (tests/JudoVisualizer.Tests)
      3. Godot asset import (headless)
      4. smoke run of the main scene (headless): fails on Godot errors or when no technique loads
      5. with -Export: Windows export to build\windows\JudoVisualizer.exe (preset "Windows Desktop")
    Godot exits with 0 even after reporting errors, so its output is scanned for error lines.

.EXAMPLE
    .\build.ps1
    Build, test, import and smoke-run (Debug).

.EXAMPLE
    .\build.ps1 -Configuration Release -Export
    Full release build including the Windows executable.

.EXAMPLE
    .\build.ps1 -SkipTests -SkipSmokeRun
    Quick compile + import only.
#>
[CmdletBinding()]
param(
    [ValidateSet('Debug', 'Release')]
    [string] $Configuration = 'Debug',

    [switch] $SkipTests,

    [switch] $SkipSmokeRun,

    # Export a Windows build (debug or release template, following -Configuration).
    [switch] $Export,

    # Remove the export output and Godot's C# build cache first.
    [switch] $Clean,

    # Godot .NET console executable; defaults to $env:GODOT or the version in C:\tools\godot.
    [string] $Godot = $(if ($env:GODOT) { $env:GODOT } else { 'C:\tools\godot\Godot_v4.7.2-stable_mono_win64_console.exe' }),

    [string] $OutputDir = (Join-Path $PSScriptRoot 'build\windows')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = $PSScriptRoot

function Invoke-Step([string] $Name, [scriptblock] $Action) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed (exit code $LASTEXITCODE)."
    }
    Write-Host ('    ok ({0:0.0} s)' -f $timer.Elapsed.TotalSeconds) -ForegroundColor DarkGray
}

# Runs Godot and returns its output lines; throws on a non-zero exit code or on error lines.
function Invoke-Godot([string[]] $Arguments) {
    # Godot writes to stderr; in Windows PowerShell 5.1 that would trip $ErrorActionPreference = 'Stop'.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = @(& $Godot --path $root @Arguments 2>&1 | ForEach-Object { "$_" })
    }
    finally {
        $ErrorActionPreference = $previous
    }
    $code = $LASTEXITCODE
    $errors = @($output | Where-Object { $_ -match '(^|\s)(USER |SCRIPT )?ERROR:' })
    if ($code -ne 0 -or $errors.Count -gt 0) {
        $output | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        throw "Godot $($Arguments -join ' ') failed (exit code $code, $($errors.Count) error line(s))."
    }
    $global:LASTEXITCODE = 0
    return $output
}

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw 'dotnet was not found on PATH (needs the .NET 8 SDK).'
}
if (-not (Test-Path $Godot)) {
    throw "Godot not found at '$Godot'. Pass -Godot <path> or set `$env:GODOT."
}

Push-Location $root
try {
    if ($Clean) {
        Invoke-Step 'Clean' {
            foreach ($path in @($OutputDir, (Join-Path $root '.godot\mono'))) {
                if (Test-Path $path) {
                    Remove-Item -Recurse -Force $path
                }
            }
        }
    }

    Invoke-Step "Build ($Configuration)" {
        dotnet build JudoVisualizer.csproj -c $Configuration --nologo -v quiet
    }

    if (-not $SkipTests) {
        Invoke-Step 'Unit tests' {
            dotnet test JudoVisualizer.sln -c $Configuration --nologo -v quiet
        }
    }

    Invoke-Step 'Import assets' {
        Invoke-Godot @('--headless', '--import') | Out-Null
    }

    if (-not $SkipSmokeRun) {
        Invoke-Step 'Smoke run' {
            $output = Invoke-Godot @('--headless', '--quit-after', '60')
            # Main logs "Loaded <n> techniques, <m> animated:" followed by one line per animated technique.
            $summary = $output | Where-Object { $_ -match '^Loaded (\d+) techniques, (\d+) animated' } | Select-Object -First 1
            if (-not $summary) {
                throw 'Smoke run: no techniques were loaded.'
            }
            if ([int]$Matches[2] -eq 0) {
                throw "Smoke run: no animated technique was loaded ($summary)."
            }
            Write-Host "    $summary"
            $output | Where-Object { $_ -match '^\s+\S+ ''.+'' \(' } | ForEach-Object { Write-Host "    $_" }
        }
    }

    if ($Export) {
        Invoke-Step "Export Windows ($Configuration)" {
            New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
            $exe = Join-Path $OutputDir 'JudoVisualizer.exe'
            $mode = if ($Configuration -eq 'Release') { '--export-release' } else { '--export-debug' }
            Invoke-Godot @('--headless', $mode, 'Windows Desktop', $exe) | Out-Null
            if (-not (Test-Path $exe)) {
                throw "Export did not produce $exe."
            }
            Write-Host "    $exe"
        }
    }

    Write-Host 'Build succeeded.' -ForegroundColor Green
}
finally {
    Pop-Location
}
