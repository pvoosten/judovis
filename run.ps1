<#
.SYNOPSIS
    Runs the Judo Technique Visualizer.

.DESCRIPTION
    Builds the C# project (unless -NoBuild) and starts the main scene with Godot. By default the
    window runs detached; -Console runs Godot's console executable in this terminal so its log
    (loaded techniques, errors) is shown, and waits until the window is closed.
    -Exported runs the Windows export from build.ps1 -Export instead.

.EXAMPLE
    .\run.ps1
    Build (Debug) and start the app.

.EXAMPLE
    .\run.ps1 -Console
    Start the app and show Godot's log in this terminal.

.EXAMPLE
    .\run.ps1 -Exported
    Start build\windows\JudoVisualizer.exe.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [ValidateSet('Debug', 'Release')]
    [string] $Configuration = 'Debug',

    # Skip the dotnet build (Godot uses the last built assembly).
    [switch] $NoBuild,

    # Run in this terminal with Godot's log, and wait for the window to close.
    [switch] $Console,

    # Run the exported executable (build.ps1 -Export) instead of the project.
    [switch] $Exported,

    # Godot .NET directory; defaults to $env:GODOT's directory or C:\tools\godot.
    [string] $GodotDir = $(if ($env:GODOT) { Split-Path $env:GODOT } else { 'C:\tools\godot' }),

    [string] $OutputDir = (Join-Path $PSScriptRoot 'build\windows'),

    # Extra arguments passed on to Godot / the executable.
    [Parameter(ValueFromRemainingArguments)]
    [string[]] $ArgumentList = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = $PSScriptRoot

if ($Exported) {
    $exe = Join-Path $OutputDir 'JudoVisualizer.exe'
    if (-not (Test-Path $exe)) {
        throw "$exe not found; run .\build.ps1 -Export first."
    }
    $arguments = $ArgumentList
}
else {
    $name = if ($Console) { 'Godot_v4.7.2-stable_mono_win64_console.exe' } else { 'Godot_v4.7.2-stable_mono_win64.exe' }
    $exe = Join-Path $GodotDir $name
    if (-not (Test-Path $exe)) {
        throw "Godot not found at '$exe'. Pass -GodotDir <dir> or set `$env:GODOT."
    }
    if (-not $NoBuild) {
        Write-Host "==> Build ($Configuration)" -ForegroundColor Cyan
        dotnet build (Join-Path $root 'JudoVisualizer.csproj') -c $Configuration --nologo -v quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed (exit code $LASTEXITCODE)."
        }
    }
    $arguments = @('--path', $root) + $ArgumentList
}

Write-Host "==> $exe $($arguments -join ' ')" -ForegroundColor Cyan
if ($Console) {
    & $exe @arguments
}
else {
    # Start-Process joins the arguments with spaces: quote the ones that contain spaces.
    $quoted = @($arguments | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } })
    Start-Process -FilePath $exe -ArgumentList $quoted -WorkingDirectory $root | Out-Null
}
