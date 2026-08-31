[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$UserHome = $HOME
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$UserHome = [IO.Path]::GetFullPath($UserHome)

function Assert-Link {
    param([string]$Path, [string]$Expected)
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction Stop
    if (-not $item.LinkType) { throw "링크가 아닙니다: $Path" }
    $wanted = [IO.Path]::GetFullPath($Expected)
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

$claudeHome = Join-Path $UserHome '.claude'
$codexHome = Join-Path $UserHome '.codex'
$agentsSkills = Join-Path $UserHome '.agents\skills'

Assert-Link (Join-Path $claudeHome 'CLAUDE.md') (Join-Path $RepoRoot 'claude\CLAUDE.md')
Assert-Link (Join-Path $claudeHome 'rules') (Join-Path $RepoRoot 'claude\rules')
Assert-Link (Join-Path $claudeHome 'agents') (Join-Path $RepoRoot 'claude\agents')
Assert-Link (Join-Path $claudeHome 'hooks') (Join-Path $RepoRoot 'claude\hooks')
Assert-Link (Join-Path $codexHome 'AGENTS.md') (Join-Path $RepoRoot 'codex\AGENTS.md')
Assert-Link (Join-Path $codexHome 'agents\meta-doc-critic.toml') (Join-Path $RepoRoot 'codex\agents\meta-doc-critic.toml')

$skills = @('brain-storming', 'frontend-design', 'grill-me', 'improve-code-base-architecture', 'ubuiquitous-language', 'port-harness-change')
foreach ($name in $skills) {
    Assert-Link (Join-Path $claudeHome "skills\$name") (Join-Path $RepoRoot "shared\skills\$name")
    Assert-Link (Join-Path $agentsSkills $name) (Join-Path $RepoRoot "shared\skills\$name")
}
Assert-Link (Join-Path $claudeHome 'skills\self-improve') (Join-Path $RepoRoot 'claude\skills\self-improve')
Assert-Link (Join-Path $agentsSkills 'self-improve') (Join-Path $RepoRoot 'codex\skills\self-improve')

& python -c "import pathlib,sys,tomllib; tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))" (Join-Path $RepoRoot 'codex\agents\meta-doc-critic.toml')
if ($LASTEXITCODE -ne 0) { throw 'Codex critic agent TOML 검증 실패' }

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

Write-Host "검증 완료: 링크와 메타 파일 $($skillFiles.Count)개가 유효합니다."
