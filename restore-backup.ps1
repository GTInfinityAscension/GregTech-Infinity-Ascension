# Restores a world from an FTB Backups 2 backup. Run restore-backup.bat (or: powershell -File restore-backup.ps1 [FILE.zip]).
param([string]$argZip)
Set-Location -LiteralPath $PSScriptRoot
$ErrorActionPreference = 'Stop'
function Die($msg) { Write-Host "Error: $msg" -ForegroundColor Red; exit 1 }
$backups = 'backups'
if (-not (Test-Path $backups -PathType Container)) {
    Die "no '$backups' folder here. Run this script from the instance (.minecraft) or server folder."
}

if ($argZip) {
    $zip = Get-Item -LiteralPath $argZip
} else {
    $zips = @(Get-ChildItem -LiteralPath $backups -Filter *.zip | Sort-Object LastWriteTime -Descending)
    if ($zips.Count -eq 0) { Die "no backups (.zip) in '$backups'." }
    Write-Host 'Backups, newest first:'
    for ($n = 0; $n -lt $zips.Count; $n++) {
        Write-Host ('  {0,2}) {1}  ({2:N1} MB)' -f ($n + 1), $zips[$n].Name, ($zips[$n].Length / 1MB))
    }
    $pick = Read-Host 'Number of the backup to restore (empty to cancel)'
    if (-not $pick) { exit 0 }
    $k = 0
    if (-not [int]::TryParse($pick, [ref]$k) -or $k -lt 1 -or $k -gt $zips.Count) { Die 'invalid choice.' }
    $zip = $zips[$k - 1]
}

# Expected SHA-1 recorded by FTB Backups in backups.json.
$index = Join-Path $backups 'backups.json'
if (Test-Path $index) {
    $entry = (Get-Content $index -Raw | ConvertFrom-Json).backups |
        Where-Object { [IO.Path]::GetFileName($_.backupLocation) -eq $zip.Name } | Select-Object -First 1
    if ($entry -and $entry.sha1) {
        $actual = (Get-FileHash -LiteralPath $zip.FullName -Algorithm SHA1).Hash.ToLower()
        if ($actual -ne $entry.sha1.ToLower()) { Die 'the backup is damaged (SHA-1 differs from backups.json).' }
    }
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ('gtia-restore-' + [guid]::NewGuid())
try {
    Expand-Archive -LiteralPath $zip.FullName -DestinationPath $tmp
    # Client backups contain saves\<world>\, server backups contain <world>\.
    $level = Get-ChildItem -LiteralPath $tmp -Recurse -Depth 2 -Filter level.dat | Select-Object -First 1
    if (-not $level) { Die 'this backup has no level.dat; it is not a world backup.' }
    $src = $level.Directory
    $world = $src.Name
    if ($src.Parent.Name -eq 'saves' -or (Test-Path 'saves')) { $dest = Join-Path 'saves' $world } else { $dest = $world }

    Write-Host ''
    Write-Host "Backup: $($zip.Name)"
    Write-Host "World:  $dest"
    Write-Host 'Make sure Minecraft (or the server) is closed.'
    $ok = Read-Host 'Restore? The current world will be kept as a renamed copy. [y/N]'
    if ($ok -notmatch '^[yYsS]') { exit 0 }

    if (Test-Path -LiteralPath $dest) {
        $keep = "$dest.before-restore-$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
        Move-Item -LiteralPath $dest -Destination $keep
        Write-Host "Current world kept as: $keep"
    }
    $parent = Split-Path $dest -Parent
    if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory $parent | Out-Null }
    Move-Item -LiteralPath $src.FullName -Destination $dest
    Write-Host "Done. '$world' was restored from $($zip.Name)."
} finally {
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
}
