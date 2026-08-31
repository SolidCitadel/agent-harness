[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$UserHome = $HOME
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$UserHome = [IO.Path]::GetFullPath($UserHome)
$claudeHome = Join-Path $UserHome '.claude'
$codexHome = Join-Path $UserHome '.codex'
$agentsSkills = Join-Path $UserHome '.agents\skills'

& python (Join-Path $RepoRoot 'scripts\render_global_instructions.py')
if ($LASTEXITCODE -ne 0) { throw '공통 전역 지침 생성 실패' }

foreach ($path in @($claudeHome, $codexHome, $agentsSkills)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

function Test-LinkTarget {
    param([string]$Path, [string]$Expected)

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
        if (-not [IO.Path]::IsPathRooted($target)) {
            $target = Join-Path (Split-Path -Parent $Path) $target
        }
        if ([IO.Path]::GetFullPath($target).Equals([IO.Path]::GetFullPath($Expected), [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Install-Link {
    param(
        [string]$Source,
        [string]$Destination,
        [ValidateSet('File', 'Directory')][string]$Kind
    )

    $sourceFull = [IO.Path]::GetFullPath($Source)
    if (-not (Test-Path -LiteralPath $sourceFull)) {
        throw "링크 원본이 없습니다: $sourceFull"
    }
    $existing = Get-Item -Force -LiteralPath $Destination -ErrorAction SilentlyContinue
    if (Test-LinkTarget -Path $Destination -Expected $sourceFull) {
        Write-Host "유지: $Destination"
        return
    } elseif ($existing) {
        throw "기존 경로가 관리 링크와 다릅니다: $Destination"
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

$fileLinks = @(
    @{ S = 'claude\CLAUDE.md'; D = (Join-Path $claudeHome 'CLAUDE.md') },
    @{ S = 'shared\harness-authoring.md'; D = (Join-Path $claudeHome 'harness-authoring.md') },
    @{ S = 'shared\skill-authoring.md'; D = (Join-Path $claudeHome 'skill-authoring.md') },
    @{ S = 'shared\agent-authoring.md'; D = (Join-Path $claudeHome 'agent-authoring.md') },
    @{ S = 'shared\self-harness-architecture.md'; D = (Join-Path $claudeHome 'self-harness-architecture.md') },
    @{ S = 'shared\meta-doc-critic.md'; D = (Join-Path $claudeHome 'meta-doc-critic.md') },
    @{ S = 'claude\commands\frontend-design.md'; D = (Join-Path $claudeHome 'commands\frontend-design.md') },
    @{ S = 'shared\vendor\anthropics\frontend-design\LICENSE.txt'; D = (Join-Path $claudeHome 'commands\frontend-design.LICENSE.txt') },
    @{ S = 'codex\AGENTS.md'; D = (Join-Path $codexHome 'AGENTS.md') },
    @{ S = 'shared\harness-authoring.md'; D = (Join-Path $codexHome 'harness-authoring.md') },
    @{ S = 'shared\skill-authoring.md'; D = (Join-Path $codexHome 'skill-authoring.md') },
    @{ S = 'shared\agent-authoring.md'; D = (Join-Path $codexHome 'agent-authoring.md') },
    @{ S = 'shared\self-harness-architecture.md'; D = (Join-Path $codexHome 'self-harness-architecture.md') },
    @{ S = 'shared\meta-doc-critic.md'; D = (Join-Path $codexHome 'meta-doc-critic.md') },
    @{ S = 'codex\harness-components.md'; D = (Join-Path $codexHome 'harness-components.md') },
    @{ S = 'codex\agents\meta-doc-critic.toml'; D = (Join-Path $codexHome 'agents\meta-doc-critic.toml') }
)

foreach ($link in $fileLinks) {
    $existing = Get-Item -Force -LiteralPath $link.D -ErrorAction SilentlyContinue
    if ($existing -and $existing.LinkType -eq 'HardLink') {
        Remove-Item -LiteralPath $link.D
        Write-Host "hard link 교체: $($link.D)"
    }
}

foreach ($link in $fileLinks) {
    Install-Link -Source (Join-Path $RepoRoot $link.S) -Destination $link.D -Kind File
}

$directoryLinks = @(
    @{ S = 'claude\rules'; D = (Join-Path $claudeHome 'rules') },
    @{ S = 'claude\agents'; D = (Join-Path $claudeHome 'agents') },
    @{ S = 'claude\hooks'; D = (Join-Path $claudeHome 'hooks') }
)

$sharedSkills = @('brain-storming', 'grill-me', 'improve-code-base-architecture', 'interface-design', 'review-pull-request', 'structure-documentation', 'ubuiquitous-language', 'port-harness-change')
foreach ($name in $sharedSkills) {
    $directoryLinks += @{ S = "shared\skills\$name"; D = Join-Path $claudeHome "skills\$name" }
    $directoryLinks += @{ S = "shared\skills\$name"; D = Join-Path $agentsSkills $name }
}

$directoryLinks += @{ S = 'codex\skills\frontend-design'; D = Join-Path $agentsSkills 'frontend-design' }
$directoryLinks += @{ S = 'claude\skills\refine-harness'; D = Join-Path $claudeHome 'skills\refine-harness' }
$directoryLinks += @{ S = 'shared\skills\refine-harness'; D = Join-Path $agentsSkills 'refine-harness' }
$directoryLinks += @{ S = 'claude\skills\self-improve'; D = Join-Path $claudeHome 'skills\self-improve' }
$directoryLinks += @{ S = 'codex\skills\self-improve'; D = Join-Path $agentsSkills 'self-improve' }

foreach ($link in $directoryLinks) {
    Install-Link -Source (Join-Path $RepoRoot $link.S) -Destination $link.D -Kind Directory
}

Write-Host "설치 완료: $RepoRoot"
