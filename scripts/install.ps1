[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$UserHome = $HOME
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$UserHome = [IO.Path]::GetFullPath($UserHome)
$claudeHome = Join-Path $UserHome '.claude'
$codexHome = Join-Path $UserHome '.codex'
$agentsSkills = Join-Path $UserHome '.agents\skills'

& python (Join-Path $RepoRoot 'scripts\render_platform_files.py')
if ($LASTEXITCODE -ne 0) { throw '플랫폼 생성물 렌더링 실패' }

# 저장소의 커밋 전 검사를 쓰도록 이 저장소의 git hook 경로만 설정한다. 다른 값이 있으면 보존하고 중단한다.
$gitTop = $null
if (Get-Command git -ErrorAction SilentlyContinue) {
    # Windows PowerShell 5.1은 Stop 상태에서 네이티브 명령의 stderr를 종료 오류로 바꾸므로 잠시 완화한다.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $gitTop = & git -C $RepoRoot rev-parse --show-toplevel 2>$null
    $ErrorActionPreference = $previousPreference
}
$isRepoRoot = $gitTop -and ([IO.Path]::GetFullPath($gitTop).TrimEnd('\') -eq $RepoRoot.TrimEnd('\'))
if ($isRepoRoot) {
    $hooksPath = & git -C $RepoRoot config --local --get core.hooksPath
    if (-not $hooksPath) {
        # 전역 hook 경로나 .git/hooks의 사용자 hook이 있으면 설정이 그것을 끄게 되므로 보존하고 중단한다.
        $inherited = & git -C $RepoRoot config --get core.hooksPath
        $defaultHooks = & git -C $RepoRoot rev-parse --git-path hooks
        if (-not [IO.Path]::IsPathRooted($defaultHooks)) { $defaultHooks = Join-Path $RepoRoot $defaultHooks }
        $customHooks = @(Get-ChildItem -File -LiteralPath $defaultHooks -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -ne '.sample' } | ForEach-Object { $_.FullName })
        if ($inherited -or $customHooks) {
            throw ("기존 git hook이 있어 설치를 중단했습니다: " + ((@($inherited) + $customHooks | Where-Object { $_ }) -join ', ') +
                ". 기존 hook을 .githooks로 옮기거나 연결한 뒤 git config --local core.hooksPath .githooks를 설정하고 설치기를 다시 실행하세요.")
        }
        & git -C $RepoRoot config --local core.hooksPath .githooks
        if ($LASTEXITCODE -ne 0) { throw 'core.hooksPath 설정 실패' }
        Write-Host '연결: core.hooksPath -> .githooks'
    } elseif ($hooksPath -ne '.githooks') {
        throw "기존 core.hooksPath가 관리 값과 다릅니다: $hooksPath"
    }
} else {
    Write-Host 'git을 찾지 못했거나 저장소 루트가 git 작업 트리가 아니어서 core.hooksPath를 설정하지 않았습니다.'
}

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
    @{ S = 'shared\harness-review.md'; D = (Join-Path $claudeHome 'harness-review.md') },
    @{ S = 'claude\harness-components.md'; D = (Join-Path $claudeHome 'harness-components.md') },
    @{ S = 'claude\self-diagnosis.md'; D = (Join-Path $claudeHome 'self-diagnosis.md'); O = 'shared\self-diagnosis.md' },
    @{ S = 'claude\commands\frontend-design.md'; D = (Join-Path $claudeHome 'commands\frontend-design.md') },
    @{ S = 'shared\vendor\anthropics\frontend-design\LICENSE.txt'; D = (Join-Path $claudeHome 'commands\frontend-design.LICENSE.txt') },
    @{ S = 'codex\AGENTS.md'; D = (Join-Path $codexHome 'AGENTS.md') },
    @{ S = 'shared\harness-authoring.md'; D = (Join-Path $codexHome 'harness-authoring.md') },
    @{ S = 'shared\skill-authoring.md'; D = (Join-Path $codexHome 'skill-authoring.md') },
    @{ S = 'shared\agent-authoring.md'; D = (Join-Path $codexHome 'agent-authoring.md') },
    @{ S = 'shared\self-harness-architecture.md'; D = (Join-Path $codexHome 'self-harness-architecture.md') },
    @{ S = 'shared\harness-review.md'; D = (Join-Path $codexHome 'harness-review.md') },
    @{ S = 'codex\self-diagnosis.md'; D = (Join-Path $codexHome 'self-diagnosis.md'); O = 'shared\self-diagnosis.md' },
    @{ S = 'codex\harness-components.md'; D = (Join-Path $codexHome 'harness-components.md') },
    @{ S = 'codex\agents\harness-reviewer.toml'; D = (Join-Path $codexHome 'agents\harness-reviewer.toml') }
)

$fileRequest = @{ repo = $RepoRoot; home = $UserHome; links = @($fileLinks) } | ConvertTo-Json -Depth 5
$requestPath = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($requestPath, $fileRequest, [Text.UTF8Encoding]::new($false))
    & python (Join-Path $RepoRoot 'scripts/windows_file_links.py') --request $requestPath
    if ($LASTEXITCODE -ne 0) { throw '파일 링크 또는 설치 상태 처리 실패' }
} finally {
    Remove-Item -LiteralPath $requestPath
}

$directoryLinks = @(
    @{ S = 'claude\rules'; D = (Join-Path $claudeHome 'rules') },
    @{ S = 'claude\agents'; D = (Join-Path $claudeHome 'agents') },
    @{ S = 'claude\hooks'; D = (Join-Path $claudeHome 'hooks') }
)

$sharedSkills = @('brain-storming', 'create-pull-request', 'grill-me', 'improve-code-base-architecture', 'interface-design', 'review-pull-request', 'structure-documentation', 'ubiquitous-language')
foreach ($name in $sharedSkills) {
    $directoryLinks += @{ S = "shared\skills\$name"; D = Join-Path $claudeHome "skills\$name" }
    $directoryLinks += @{ S = "shared\skills\$name"; D = Join-Path $agentsSkills $name }
}

$directoryLinks += @{ S = 'codex\skills\frontend-design'; D = Join-Path $agentsSkills 'frontend-design' }

# 같은 이름의 플랫폼별 skill로 바뀐 이전 shared skill 링크만 먼저 제거한다.
foreach ($name in @('self-diagnose', 'integrate-context', 'refine-harness')) {
    foreach ($destination in @((Join-Path $claudeHome "skills\$name"), (Join-Path $agentsSkills $name))) {
        $existing = Get-Item -Force -LiteralPath $destination -ErrorAction SilentlyContinue
        if ($existing -and $existing.LinkType -in @('Junction', 'SymbolicLink') -and
            (Test-LinkTarget $destination (Join-Path $RepoRoot "shared\skills\$name"))) {
            [IO.Directory]::Delete($destination)
            Write-Host "이전 관리 skill 링크 제거: $destination"
        }
    }
    Install-Link -Source (Join-Path $RepoRoot "claude\skills\$name") -Destination (Join-Path $claudeHome "skills\$name") -Kind Directory
    Install-Link -Source (Join-Path $RepoRoot "codex\skills\$name") -Destination (Join-Path $agentsSkills $name) -Kind Directory
}

foreach ($link in $directoryLinks) {
    Install-Link -Source (Join-Path $RepoRoot $link.S) -Destination $link.D -Kind Directory
}

# 새 경로를 검증한 뒤 이 저장소의 이전 관리 링크만 정리한다.
$migrations = @(
    @{ D = (Join-Path $claudeHome 'meta-doc-critic.md'); Old = 'shared\meta-doc-critic.md'; New = 'shared\harness-review.md'; Installed = (Join-Path $claudeHome 'harness-review.md') },
    @{ D = (Join-Path $codexHome 'meta-doc-critic.md'); Old = 'shared\meta-doc-critic.md'; New = 'shared\harness-review.md'; Installed = (Join-Path $codexHome 'harness-review.md') },
    @{ D = (Join-Path $codexHome 'agents\meta-doc-critic.toml'); Old = 'codex\agents\meta-doc-critic.toml'; New = 'codex\agents\harness-reviewer.toml'; Installed = (Join-Path $codexHome 'agents\harness-reviewer.toml') }
)
foreach ($migration in $migrations) {
    if (-not (Test-LinkTarget $migration.Installed (Join-Path $RepoRoot $migration.New))) {
        throw "새 관리 링크 검증 실패: $($migration.Installed)"
    }
}
foreach ($migration in $migrations) {
    $existing = Get-Item -Force -LiteralPath $migration.D -ErrorAction SilentlyContinue
    if (-not $existing) { continue }
    $managed = if ($existing.LinkType -eq 'HardLink') {
        Test-LinkTarget $migration.D (Join-Path $RepoRoot $migration.New)
    } elseif ($existing.LinkType -eq 'SymbolicLink') {
        (Test-LinkTarget $migration.D (Join-Path $RepoRoot $migration.Old)) -or
        (Test-LinkTarget $migration.D (Join-Path $RepoRoot $migration.New))
    } else { $false }
    if (-not $managed) { throw "이전 비관리 경로를 보존했습니다: $($migration.D)" }
    Remove-Item -LiteralPath $migration.D
    Write-Host "이전 관리 링크 제거: $($migration.D)"
}

# 새 skill 연결을 확인한 뒤 기존 디렉터리 링크만 제거한다.
$newSkillLinks = @(
    @{ D = (Join-Path $claudeHome 'skills\ubiquitous-language'); S = 'shared\skills\ubiquitous-language' },
    @{ D = (Join-Path $agentsSkills 'ubiquitous-language'); S = 'shared\skills\ubiquitous-language' },
    @{ D = (Join-Path $claudeHome 'skills\integrate-context'); S = 'claude\skills\integrate-context' },
    @{ D = (Join-Path $agentsSkills 'integrate-context'); S = 'codex\skills\integrate-context' }
)
foreach ($link in $newSkillLinks) {
    if (-not (Test-LinkTarget $link.D (Join-Path $RepoRoot $link.S))) {
        throw "새 skill 링크 검증 실패: $($link.D)"
    }
}
$previousSkills = @(
    @{ D = (Join-Path $claudeHome 'skills\ubuiquitous-language'); S = 'shared\skills\ubuiquitous-language' },
    @{ D = (Join-Path $agentsSkills 'ubuiquitous-language'); S = 'shared\skills\ubuiquitous-language' },
    @{ D = (Join-Path $claudeHome 'skills\self-improve'); S = 'claude\skills\self-improve' },
    @{ D = (Join-Path $agentsSkills 'self-improve'); S = 'codex\skills\self-improve' },
    @{ D = (Join-Path $claudeHome 'skills\port-harness-change'); S = 'shared\skills\port-harness-change' },
    @{ D = (Join-Path $agentsSkills 'port-harness-change'); S = 'shared\skills\port-harness-change' }
)
foreach ($previous in $previousSkills) {
    $existing = Get-Item -Force -LiteralPath $previous.D -ErrorAction SilentlyContinue
    if (-not $existing) { continue }
    if ($existing.LinkType -notin @('Junction', 'SymbolicLink') -or
        -not (Test-LinkTarget $previous.D (Join-Path $RepoRoot $previous.S))) {
        throw "이전 비관리 skill 경로를 보존했습니다: $($previous.D)"
    }
    # 재귀 삭제 없이 디렉터리 reparse point 자체만 제거한다.
    [IO.Directory]::Delete($previous.D)
    Write-Host "이전 관리 skill 링크 제거: $($previous.D)"
}

Write-Host "설치 완료: $RepoRoot"
