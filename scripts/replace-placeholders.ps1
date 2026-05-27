<#
.SYNOPSIS
    Replace repo-rag placeholders with real identity values.

.DESCRIPTION
    Walks the repository tree and swaps every occurrence of:

      <YOUR_GITHUB_USERNAME>  ->  -GitHubUsername
      <YOUR_NAME>             ->  -FullName
      <your.email@example.com> ->  -Email
      noreply@example.com     ->  -Email (the pyproject.toml needs a parseable address)
      <YEAR>                  ->  -Year

    Skips .git, .venv, dist, build, .pytest_cache, .ruff_cache, .mypy_cache,
    node_modules, .repo-rag, and any binary file.

.EXAMPLE
    .\scripts\replace-placeholders.ps1 -GitHubUsername "octocat" -FullName "Octo Cat" -Email "octo@example.com" -Year "2026"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)] [string] $GitHubUsername,
    [Parameter(Mandatory=$true)] [string] $FullName,
    [Parameter(Mandatory=$true)] [string] $Email,
    [Parameter(Mandatory=$false)] [string] $Year = (Get-Date).Year.ToString()
)

$ErrorActionPreference = 'Stop'

$skipDirs = @('.git', '.venv', 'venv', 'env', 'dist', 'build', '.pytest_cache',
              '.ruff_cache', '.mypy_cache', 'node_modules', '.repo-rag',
              '__pycache__', '.tox', '.nox', 'htmlcov', '.idea')

$textExtensions = @('.py','.md','.toml','.yml','.yaml','.json','.cfg','.ini',
                    '.txt','.ps1','.sh','.dockerfile','.dockerignore','.gitignore',
                    '.mdc','.rules','.conf')

function Test-IsTextFile {
    param([string] $Path)
    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($textExtensions -contains $ext) { return $true }
    $name = [System.IO.Path]::GetFileName($Path)
    if ($name -in @('Dockerfile','LICENSE','CHANGELOG','CONTRIBUTING','SECURITY','CODE_OF_CONDUCT')) {
        return $true
    }
    return $false
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$files = Get-ChildItem -Path $root -Recurse -File -Force | Where-Object {
    $rel = $_.FullName.Substring($root.Length).TrimStart('\','/')
    $parts = $rel -split '[\\/]'
    -not ($parts | Where-Object { $skipDirs -contains $_ })
} | Where-Object { Test-IsTextFile $_.FullName }

$replacements = @{
    '<YOUR_GITHUB_USERNAME>'       = $GitHubUsername
    '<YOUR_NAME>'                  = $FullName
    '<your.email@example.com>'     = $Email
    'noreply@example.com'          = $Email
    '<YEAR>'                       = $Year
}

$changed = 0
foreach ($file in $files) {
    $content = Get-Content -Raw -LiteralPath $file.FullName -Encoding UTF8
    if ($null -eq $content) { continue }
    $original = $content
    foreach ($key in $replacements.Keys) {
        $content = $content.Replace($key, $replacements[$key])
    }
    if ($content -ne $original) {
        Set-Content -LiteralPath $file.FullName -Value $content -Encoding UTF8 -NoNewline
        $changed += 1
        Write-Host "patched: $($file.FullName.Substring($root.Length).TrimStart('\','/'))"
    }
}

Write-Host ""
Write-Host "Done. Updated $changed files."
