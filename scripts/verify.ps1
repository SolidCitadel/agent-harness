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

& python (Join-Path $RepoRoot 'scripts\render_platform_files.py') --check
if ($LASTEXITCODE -ne 0) { throw '플랫폼 생성물 drift' }
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

& python -c "import pathlib,sys,tomllib; tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))" (Join-Path $RepoRoot 'codex\agents\harness-reviewer.toml')
if ($LASTEXITCODE -ne 0) { throw 'Codex harness reviewer agent TOML 검증 실패' }

$skillFiles = @()
foreach ($skillRoot in @('shared\skills', 'claude\skills', 'codex\skills')) {
    $skillFiles += Get-ChildItem -LiteralPath (Join-Path $RepoRoot $skillRoot) -Recurse -Filter 'SKILL.md'
}
foreach ($file in $skillFiles) {
    $text = Get-Content -Raw -LiteralPath $file.FullName
    if ($text -notmatch '(?s)^---\s*\r?\nname:\s*[^\r\n]+\r?\ndescription:\s*[^\r\n]+') {
        throw "SKILL.md frontmatter 검증 실패: $($file.FullName)"
    }
}

$frontendPolicy = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'codex\skills\frontend-design\agents\openai.yaml')
if ($frontendPolicy -notmatch '(?m)^\s*allow_implicit_invocation:\s*false\s*$') {
    throw '외부 frontend-design은 명시적 호출 전용이어야 합니다.'
}

$refineSkill = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'claude\skills\refine-harness\SKILL.md')
$refinePolicy = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'codex\skills\refine-harness\agents\openai.yaml')
if ($refineSkill -notmatch '(?m)^disable-model-invocation:\s*true\s*$' -or $refinePolicy -notmatch '(?m)^\s*allow_implicit_invocation:\s*false\s*$') {
    throw 'refine-harness는 양 플랫폼에서 명시 호출 전용이어야 합니다.'
}
$repoClaude = [IO.File]::ReadAllText((Join-Path $RepoRoot 'CLAUDE.md')).Trim()
if ($repoClaude -ne '@AGENTS.md') { throw '루트 CLAUDE.md는 AGENTS.md를 참조해야 합니다.' }

$harnessRule = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'claude\rules\harness-authoring.md')
$agentRule = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'claude\rules\agents.md')
$skillRule = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'claude\rules\skill-md.md')
$codexGlobal = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'codex\AGENTS.md')
foreach ($pattern in @('**/AGENTS.override.md', '**/.codex/rules/**/*.rules', '**/.codex/hooks.json', '**/.codex/config.toml')) {
    if ($harnessRule -notmatch [regex]::Escape($pattern)) { throw "Claude 공통 하네스 rule의 경로 누락: $pattern" }
}
foreach ($reference in @('~/.claude/harness-authoring.md', '~/.claude/harness-components.md')) {
    if ($harnessRule -notmatch [regex]::Escape($reference)) { throw "Claude 공통 하네스 rule의 참조 누락: $reference" }
}
if ($skillRule -notmatch [regex]::Escape('~/.claude/skill-authoring.md')) {
    throw 'Claude skill 작성 rule이 공통 skill 규율을 참조하지 않습니다.'
}
if ($agentRule -notmatch [regex]::Escape('**/agents/**/*.toml')) {
    throw 'Claude agent 작성 rule이 TOML agent를 포함하지 않습니다.'
}
if ($agentRule -notmatch [regex]::Escape('~/.claude/agent-authoring.md')) {
    throw 'Claude agent 작성 rule이 공통 agent 규율을 참조하지 않습니다.'
}
foreach ($reference in @('~/.codex/harness-authoring.md', '~/.codex/harness-components.md')) {
    if ($codexGlobal -notmatch [regex]::Escape($reference)) { throw "Codex 전역 하네스 라우팅 누락: $reference" }
}

$thirdParty = Get-Content -Raw -LiteralPath (Join-Path $RepoRoot 'shared\third-party-skills.json') | ConvertFrom-Json
$frontendSource = $thirdParty.'frontend-design'
if (-not $frontendSource -or $frontendSource.implicitInvocation -ne $false) {
    throw 'frontend-design 외부 출처 또는 호출 정책 메타데이터가 올바르지 않습니다.'
}
function Get-NormalizedHash {
    param([string]$Path, [switch]$RemoveClaudePolicy)
    $content = [IO.File]::ReadAllText($Path).Replace("`r`n", "`n")
    if ($RemoveClaudePolicy) {
        $content = $content.Replace("disable-model-invocation: true`n", '')
        $content = $content.Replace('license: Complete terms in frontend-design.LICENSE.txt', 'license: Complete terms in LICENSE.txt')
    }
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($content)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha256.Dispose()
    }
}

$vendorSkill = Join-Path $RepoRoot 'shared\vendor\anthropics\frontend-design\SKILL.md'
$vendorLicense = Join-Path $RepoRoot 'shared\vendor\anthropics\frontend-design\LICENSE.txt'
$skillHash = Get-NormalizedHash $vendorSkill
$licenseHash = Get-NormalizedHash $vendorLicense
$codexSkillHash = Get-NormalizedHash (Join-Path $RepoRoot 'codex\skills\frontend-design\SKILL.md')
$codexLicenseHash = Get-NormalizedHash (Join-Path $RepoRoot 'codex\skills\frontend-design\LICENSE.txt')
$claudeCommand = Join-Path $RepoRoot 'claude\commands\frontend-design.md'
$claudeCommandText = [IO.File]::ReadAllText($claudeCommand).Replace("`r`n", "`n")
$claudeFrontmatterEnd = $claudeCommandText.IndexOf("`n---`n", 4, [StringComparison]::Ordinal)
if (-not $claudeCommandText.StartsWith("---`n", [StringComparison]::Ordinal) -or $claudeFrontmatterEnd -lt 0) {
    throw 'Claude용 frontend-design command frontmatter가 올바르지 않습니다.'
}
$claudeFrontmatter = $claudeCommandText.Substring(0, $claudeFrontmatterEnd)
$claudeSkillHash = Get-NormalizedHash $claudeCommand -RemoveClaudePolicy
if ($claudeFrontmatter -notmatch '(?m)^disable-model-invocation:\s*true\s*$') {
    throw 'Claude용 frontend-design command는 명시적 호출 전용이어야 합니다.'
}
if ($skillHash -ne $frontendSource.upstreamSkillSha256 -or $licenseHash -ne $frontendSource.licenseSha256 -or $codexSkillHash -ne $skillHash -or $codexLicenseHash -ne $licenseHash -or $claudeSkillHash -ne $skillHash) {
    throw 'frontend-design 설치본이 기록된 해시와 다릅니다.'
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

Write-Host "검증 완료: 링크와 메타 파일 $($skillFiles.Count)개가 유효합니다."
