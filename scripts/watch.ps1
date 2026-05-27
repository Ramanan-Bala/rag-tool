param(
    [string]$RepoId = "raptor-forms-render",
    [int]$IntervalSec = 30,
    [int]$TotalFiles = 0,
    [string]$RepoPath = ""
)

$db = Join-Path $env:USERPROFILE ".droid-index\$RepoId\metadata.sqlite"
$py = "C:\Raptor\rag tool\.venv\Scripts\python.exe"
$rag = "C:\Raptor\rag tool\.venv\Scripts\rag.exe"

if (-not (Test-Path $db)) {
    Write-Error "Index DB not found: $db"
    exit 1
}

if ($TotalFiles -le 0) {
    if (-not $RepoPath) {
        $RepoPath = & $py -c "import json; from pathlib import Path; p=Path(r'$env:USERPROFILE') / '.droid-index' / '$RepoId' / 'meta.json'; print(json.loads(p.read_text())['repo_root'] if p.exists() else '')"
    }
    if ($RepoPath -and (Test-Path $RepoPath)) {
        Write-Host "Discovering expected file count from $RepoPath ..." -ForegroundColor DarkGray
        $TotalFiles = & $py -c @"
import sys
sys.path.insert(0, r'C:\Raptor\rag tool\src')
from pathlib import Path
from repo_rag.config import load_global_config
from repo_rag.fileutils import iter_repo_files
cfg = load_global_config()
n = sum(1 for _ in iter_repo_files(Path(r'$RepoPath'), cfg.include_globs, cfg.exclude_globs, cfg.chunking.max_file_bytes))
print(n)
"@
        $TotalFiles = [int]$TotalFiles
    }
}

if ($TotalFiles -gt 0) {
    Write-Host "Watching $RepoId every ${IntervalSec}s, expected total = $TotalFiles files (Ctrl+C to stop)" -ForegroundColor Cyan
} else {
    Write-Host "Watching $RepoId every ${IntervalSec}s (no total - ETA unavailable; pass -TotalFiles N)" -ForegroundColor Cyan
}

$prevFiles = 0
$prevChunks = 0
$prevTime = Get-Date
$first = $true
$rateHistory = @()

while ($true) {
    $ts = Get-Date -Format "HH:mm:ss"
    $raw = & $py -c "import sqlite3; c=sqlite3.connect(r'$db'); print(c.execute('select count(*) from files').fetchone()[0], c.execute('select count(*) from chunks').fetchone()[0], c.execute('select count(*) from embedding_cache').fetchone()[0])"
    $parts = $raw -split ' '
    $files = [int]$parts[0]
    $chunks = [int]$parts[1]
    $cached = [int]$parts[2]

    $now = Get-Date
    $elapsed = ($now - $prevTime).TotalSeconds
    if ($first -or $elapsed -le 0) {
        $rate = 0.0
        $chunkRate = 0.0
        $first = $false
    } else {
        $rate = ($files - $prevFiles) / $elapsed
        $chunkRate = ($chunks - $prevChunks) / $elapsed
    }

    $rateHistory += $rate
    if ($rateHistory.Count -gt 6) { $rateHistory = $rateHistory[-6..-1] }
    $smoothRate = ($rateHistory | Where-Object { $_ -gt 0 } | Measure-Object -Average).Average
    if (-not $smoothRate) { $smoothRate = 0 }

    $line = "[$ts] files=$files chunks=$chunks cached=$cached"
    if ($rate -gt 0) {
        $line += "  pace=$([Math]::Round($rate,1)) f/s, $([Math]::Round($chunkRate,1)) c/s"
    }
    if ($TotalFiles -gt 0 -and $smoothRate -gt 0 -and $files -lt $TotalFiles) {
        $remaining = $TotalFiles - $files
        $etaSec = [int]($remaining / $smoothRate)
        $etaH = [int][Math]::Floor($etaSec / 3600)
        $etaM = [int][Math]::Floor(($etaSec % 3600) / 60)
        $etaS = [int]($etaSec % 60)
        $eta = if ($etaH -gt 0) { "{0}h{1:D2}m{2:D2}s" -f $etaH, $etaM, $etaS } else { "{0:D2}m{1:D2}s" -f $etaM, $etaS }
        $pct = [Math]::Round(100.0 * $files / $TotalFiles, 1)
        $line += "  $pct% done  ETA=$eta"
    } elseif ($TotalFiles -gt 0 -and $files -ge $TotalFiles) {
        $line += "  DONE"
    }

    Write-Host $line

    $prevFiles = $files
    $prevChunks = $chunks
    $prevTime = $now
    if ($TotalFiles -gt 0 -and $files -ge $TotalFiles) { break }
    Start-Sleep -Seconds $IntervalSec
}
