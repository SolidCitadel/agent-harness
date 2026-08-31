[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$UserHome = $HOME
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$UserHome = [IO.Path]::GetFullPath($UserHome)
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$claudeHome = Join-Path $UserHome '.claude'
$codexHome = Join-Path $UserHome '.codex'
$agentsSkills = Join-Path $UserHome '.agents\skills'

foreach ($path in @($claudeHome, $codexHome, $agentsSkills)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

function Test-LinkTarget {
    param([string]$Path)
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $item -or -not $item.LinkType) { return $false }

    $targets = @($item.Target)
    if ($item.LinkType -eq 'HardLink') {
        $volumeRoot = [IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path))
        $targets = @(& fsutil hardlink list $Path 2>$null | ForEach-Object {
            if ($_.StartsWith([IO.Path]::DirectorySeparatorChar)) {
                Join-Path $volumeRoot $_.TrimStart([IO.Path]::DirectorySeparatorChar)
            } else {
                $_
            }
        })
    }

    foreach ($target in $targets) {
        if (-not [IO.Path]::IsPathRooted($target)) { $target = Join-Path (Split-Path -Parent $Path) $target }
        if ([IO.Path]::GetFullPath($target).Equals([IO.Path]::GetFullPath($script:ExpectedLinkSource), [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Install-Link {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$BackupRoot,
        [string]$BackupRelative,
        [ValidateSet('File', 'Directory')][string]$Kind
    )

    $sourceFull = [IO.Path]::GetFullPath($Source)
    if (-not (Test-Path -LiteralPath $sourceFull)) {
        throw "링크 원본이 없습니다: $sourceFull"
    }

    $script:ExpectedLinkSource = $sourceFull
    if (Test-LinkTarget -Path $Destination) {
        Write-Host "유지: $Destination"
        return
    }

    $existing = Get-Item -Force -LiteralPath $Destination -ErrorAction SilentlyContinue
    if ($existing) {
        $backupPath = Join-Path $BackupRoot $BackupRelative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupPath) | Out-Null
        Move-Item -LiteralPath $Destination -Destination $backupPath
        Write-Host "백업: $Destination -> $backupPath"
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    if ($Kind -eq 'Directory') {
        New-Item -ItemType Junction -Path $Destination -Target $sourceFull | Out-Null
    } else {
        try {
            New-Item -ItemType SymbolicLink -Path $Destination -Target $sourceFull -ErrorAction Stop | Out-Null
        } catch [System.UnauthorizedAccessException] {
            New-Item -ItemType HardLink -Path $Destination -Target $sourceFull | Out-Null
        }
    }
    Write-Host "연결: $Destination -> $sourceFull"
}

$snapshotRoot = Join-Path $RepoRoot ".migration-snapshots\$stamp"
$claudeBackup = Join-Path $snapshotRoot 'claude'
$codexBackup = Join-Path $snapshotRoot 'codex'
$agentsBackup = Join-Path $snapshotRoot 'agents'

$legacyGit = Join-Path $claudeHome '.git'
if (Test-Path -LiteralPath $legacyGit) {
    $legacyRepoBackup = Join-Path $claudeBackup 'legacy-repository'
    New-Item -ItemType Directory -Force -Path $legacyRepoBackup | Out-Null
    Move-Item -LiteralPath $legacyGit -Destination (Join-Path $legacyRepoBackup '.git')
    $legacyIgnore = Join-Path $claudeHome '.gitignore'
    if (Test-Path -LiteralPath $legacyIgnore) {
        Move-Item -LiteralPath $legacyIgnore -Destination (Join-Path $legacyRepoBackup '.gitignore')
    }
    Write-Host "기존 ~/.claude Git 메타데이터 백업: $legacyRepoBackup"
}

$fileLinks = @(
    @{ S = 'claude\CLAUDE.md'; D = (Join-Path $claudeHome 'CLAUDE.md'); B = $claudeBackup; R = 'CLAUDE.md' },
    @{ S = 'claude\self-harness-engineering.md'; D = (Join-Path $claudeHome 'self-harness-engineering.md'); B = $claudeBackup; R = 'self-harness-engineering.md' },
    @{ S = 'codex\AGENTS.md'; D = (Join-Path $codexHome 'AGENTS.md'); B = $codexBackup; R = 'AGENTS.md' },
    @{ S = 'codex\agents\meta-doc-critic.toml'; D = (Join-Path $codexHome 'agents\meta-doc-critic.toml'); B = $codexBackup; R = 'agents\meta-doc-critic.toml' }
)

foreach ($link in $fileLinks) {
    Install-Link -Source (Join-Path $RepoRoot $link.S) -Destination $link.D -BackupRoot $link.B -BackupRelative $link.R -Kind File
}

$directoryLinks = @(
    @{ S = 'claude\rules'; D = (Join-Path $claudeHome 'rules'); B = $claudeBackup; R = 'rules' },
    @{ S = 'claude\agents'; D = (Join-Path $claudeHome 'agents'); B = $claudeBackup; R = 'agents' },
    @{ S = 'claude\hooks'; D = (Join-Path $claudeHome 'hooks'); B = $claudeBackup; R = 'hooks' }
)

$sharedSkills = @('brain-storming', 'frontend-design', 'grill-me', 'improve-code-base-architecture', 'ubuiquitous-language', 'port-harness-change')
foreach ($name in $sharedSkills) {
    $directoryLinks += @{
        S = "shared\skills\$name"
        D = Join-Path $claudeHome "skills\$name"
        B = $claudeBackup
        R = "skills\$name"
    }
    $directoryLinks += @{
        S = "shared\skills\$name"
        D = Join-Path $agentsSkills $name
        B = $agentsBackup
        R = "skills\$name"
    }
}

$directoryLinks += @{
    S = 'claude\skills\self-improve'
    D = Join-Path $claudeHome 'skills\self-improve'
    B = $claudeBackup
    R = 'skills\self-improve'
}
$directoryLinks += @{
    S = 'codex\skills\self-improve'
    D = Join-Path $agentsSkills 'self-improve'
    B = $agentsBackup
    R = 'skills\self-improve'
}

foreach ($link in $directoryLinks) {
    Install-Link -Source (Join-Path $RepoRoot $link.S) -Destination $link.D -BackupRoot $link.B -BackupRelative $link.R -Kind Directory
}

Write-Host "설치 완료: $RepoRoot"
