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

$fileStateChecks = [System.Collections.Generic.List[object]]::new()

function Assert-Link {
    param([string]$Path, [string]$Expected)
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction Stop
    if (-not $item.LinkType) { throw "링크가 아닙니다: $Path" }
    $wanted = [IO.Path]::GetFullPath($Expected)
    if (Test-Path -LiteralPath $Expected -PathType Leaf) {
        $fileStateChecks.Add(@{ S = $wanted; D = [IO.Path]::GetFullPath($Path) })
    }
    $matched = $false
    $actualTargets = @()

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
        $actual = [IO.Path]::GetFullPath($target)
        $actualTargets += $actual
        if ($actual.Equals($wanted, [StringComparison]::OrdinalIgnoreCase)) { $matched = $true }
    }
    if (-not $matched) {
        throw "링크 대상 불일치: $Path -> $($actualTargets -join ', ') (예상: $wanted)"
    }
}

function Assert-PathAbsent {
    param([string]$Path)
    if (Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue) {
        throw "더 이상 사용하지 않는 경로가 남아 있습니다: $Path"
    }
}

$claudeHome = Join-Path $UserHome '.claude'
$codexHome = Join-Path $UserHome '.codex'
$agentsSkills = Join-Path $UserHome '.agents\skills'

$gitTop = $null
if (Get-Command git -ErrorAction SilentlyContinue) {
    # Windows PowerShell 5.1은 Stop 상태에서 네이티브 명령의 stderr를 종료 오류로 바꾸므로 잠시 완화한다.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $gitTop = & git -C $RepoRoot rev-parse --show-toplevel 2>$null
    $ErrorActionPreference = $previousPreference
}
$isRepoRoot = $gitTop -and ([IO.Path]::GetFullPath($gitTop).TrimEnd('\') -eq $RepoRoot.TrimEnd('\'))
if ($isRepoRoot -and (& git -C $RepoRoot config --local --get core.hooksPath) -ne '.githooks') {
    throw 'core.hooksPath가 .githooks가 아닙니다.'
}

Assert-Link (Join-Path $claudeHome 'CLAUDE.md') (Join-Path $RepoRoot 'claude\CLAUDE.md')
Assert-Link (Join-Path $claudeHome 'harness-authoring.md') (Join-Path $RepoRoot 'shared\harness-authoring.md')
Assert-Link (Join-Path $claudeHome 'skill-authoring.md') (Join-Path $RepoRoot 'shared\skill-authoring.md')
Assert-Link (Join-Path $claudeHome 'agent-authoring.md') (Join-Path $RepoRoot 'shared\agent-authoring.md')
Assert-Link (Join-Path $claudeHome 'self-harness-architecture.md') (Join-Path $RepoRoot 'shared\self-harness-architecture.md')
Assert-PathAbsent (Join-Path $claudeHome 'self-harness-engineering.md')
Assert-Link (Join-Path $claudeHome 'harness-review.md') (Join-Path $RepoRoot 'shared\harness-review.md')
Assert-Link (Join-Path $claudeHome 'harness-components.md') (Join-Path $RepoRoot 'claude\harness-components.md')
Assert-Link (Join-Path $claudeHome 'self-diagnosis.md') (Join-Path $RepoRoot 'claude\self-diagnosis.md')
Assert-Link (Join-Path $claudeHome 'rules') (Join-Path $RepoRoot 'claude\rules')
Assert-Link (Join-Path $claudeHome 'agents') (Join-Path $RepoRoot 'claude\agents')
Assert-Link (Join-Path $claudeHome 'hooks') (Join-Path $RepoRoot 'claude\hooks')
Assert-Link (Join-Path $claudeHome 'commands\frontend-design.md') (Join-Path $RepoRoot 'claude\commands\frontend-design.md')
Assert-Link (Join-Path $claudeHome 'commands\frontend-design.LICENSE.txt') (Join-Path $RepoRoot 'shared\vendor\anthropics\frontend-design\LICENSE.txt')
Assert-PathAbsent (Join-Path $claudeHome 'skills\frontend-design')
Assert-Link (Join-Path $codexHome 'AGENTS.md') (Join-Path $RepoRoot 'codex\AGENTS.md')
Assert-Link (Join-Path $codexHome 'harness-authoring.md') (Join-Path $RepoRoot 'shared\harness-authoring.md')
Assert-Link (Join-Path $codexHome 'skill-authoring.md') (Join-Path $RepoRoot 'shared\skill-authoring.md')
Assert-Link (Join-Path $codexHome 'agent-authoring.md') (Join-Path $RepoRoot 'shared\agent-authoring.md')
Assert-Link (Join-Path $codexHome 'self-harness-architecture.md') (Join-Path $RepoRoot 'shared\self-harness-architecture.md')
Assert-Link (Join-Path $codexHome 'harness-review.md') (Join-Path $RepoRoot 'shared\harness-review.md')
Assert-Link (Join-Path $codexHome 'self-diagnosis.md') (Join-Path $RepoRoot 'codex\self-diagnosis.md')
Assert-Link (Join-Path $codexHome 'harness-components.md') (Join-Path $RepoRoot 'codex\harness-components.md')
Assert-PathAbsent (Join-Path $codexHome 'instruction-locations.md')
Assert-Link (Join-Path $codexHome 'agents\harness-reviewer.toml') (Join-Path $RepoRoot 'codex\agents\harness-reviewer.toml')

$skills = @('brain-storming', 'create-pull-request', 'grill-me', 'improve-code-base-architecture', 'interface-design', 'review-pull-request', 'structure-documentation', 'ubiquitous-language')
foreach ($name in $skills) {
    Assert-Link (Join-Path $claudeHome "skills\$name") (Join-Path $RepoRoot "shared\skills\$name")
    Assert-Link (Join-Path $agentsSkills $name) (Join-Path $RepoRoot "shared\skills\$name")
}
Assert-Link (Join-Path $agentsSkills 'frontend-design') (Join-Path $RepoRoot 'codex\skills\frontend-design')
foreach ($name in @('self-diagnose', 'integrate-context', 'refine-harness')) {
    Assert-Link (Join-Path $claudeHome "skills\$name") (Join-Path $RepoRoot "claude\skills\$name")
    Assert-Link (Join-Path $agentsSkills $name) (Join-Path $RepoRoot "codex\skills\$name")
}

Assert-PathAbsent (Join-Path $claudeHome 'meta-doc-critic.md')
Assert-PathAbsent (Join-Path $codexHome 'meta-doc-critic.md')
Assert-PathAbsent (Join-Path $codexHome 'agents\meta-doc-critic.toml')
Assert-PathAbsent (Join-Path $claudeHome 'agents\meta-doc-critic.md')

foreach ($name in @('self-improve', 'port-harness-change', 'ubuiquitous-language')) {
    Assert-PathAbsent (Join-Path $claudeHome "skills\$name")
    Assert-PathAbsent (Join-Path $agentsSkills $name)
}

$fileRequest = @{ repo = $RepoRoot; home = $UserHome; links = @($fileStateChecks.ToArray()) } | ConvertTo-Json -Depth 5
$requestPath = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($requestPath, $fileRequest, [Text.UTF8Encoding]::new($false))
    & python (Join-Path $RepoRoot 'scripts/windows_file_links.py') --request $requestPath --verify
    if ($LASTEXITCODE -ne 0) { throw '파일 링크 또는 설치 상태 처리 실패' }
} finally {
    Remove-Item -LiteralPath $requestPath
}

Write-Host '검증 완료: 설치 링크가 유효합니다.'
