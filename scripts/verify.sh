#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
user_home="${HOME}"

while (($#)); do
  case "$1" in
    --repo-root)
      repo_root="$2"
      shift 2
      ;;
    --home)
      user_home="$2"
      shift 2
      ;;
    *)
      echo "알 수 없는 인자: $1" >&2
      exit 2
      ;;
  esac
done

repo_root="$(realpath -- "$repo_root")"
user_home="$(realpath -m -- "$user_home")"
claude_home="$user_home/.claude"
codex_home="$user_home/.codex"
agents_skills="$user_home/.agents/skills"

git_top="$(git -C "$repo_root" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$git_top" && "$(realpath -m -- "$git_top")" == "$repo_root" ]] \
  && [[ "$(git -C "$repo_root" config --local --get core.hooksPath || true)" != '.githooks' ]]; then
  echo 'core.hooksPath가 .githooks가 아닙니다.' >&2
  exit 1
fi

assert_link() {
  local path expected actual
  path="$1"
  expected="$(realpath -- "$2")"
  if [[ ! -L "$path" ]]; then
    echo "symbolic link가 아닙니다: $path" >&2
    exit 1
  fi
  actual="$(readlink -f -- "$path")"
  if [[ "$actual" != "$expected" ]]; then
    echo "링크 대상 불일치: $path -> $actual (예상: $expected)" >&2
    exit 1
  fi
}

assert_path_absent() {
  local path
  path="$1"
  if [[ -e "$path" || -L "$path" ]]; then
    echo "더 이상 사용하지 않는 경로가 남아 있습니다: $path" >&2
    exit 1
  fi
}

assert_link "$claude_home/CLAUDE.md" "$repo_root/claude/CLAUDE.md"
assert_link "$claude_home/harness-authoring.md" "$repo_root/shared/harness-authoring.md"
assert_link "$claude_home/skill-authoring.md" "$repo_root/shared/skill-authoring.md"
assert_link "$claude_home/agent-authoring.md" "$repo_root/shared/agent-authoring.md"
assert_link "$claude_home/self-harness-architecture.md" "$repo_root/shared/self-harness-architecture.md"
assert_path_absent "$claude_home/self-harness-engineering.md"
assert_link "$claude_home/harness-review.md" "$repo_root/shared/harness-review.md"
assert_link "$claude_home/harness-components.md" "$repo_root/claude/harness-components.md"
assert_link "$claude_home/self-diagnosis.md" "$repo_root/claude/self-diagnosis.md"
assert_link "$claude_home/rules" "$repo_root/claude/rules"
assert_link "$claude_home/agents" "$repo_root/claude/agents"
assert_link "$claude_home/hooks" "$repo_root/claude/hooks"
assert_link "$claude_home/commands/frontend-design.md" "$repo_root/claude/commands/frontend-design.md"
assert_link "$claude_home/commands/frontend-design.LICENSE.txt" "$repo_root/shared/vendor/anthropics/frontend-design/LICENSE.txt"
assert_path_absent "$claude_home/skills/frontend-design"
assert_link "$codex_home/AGENTS.md" "$repo_root/codex/AGENTS.md"
assert_link "$codex_home/harness-authoring.md" "$repo_root/shared/harness-authoring.md"
assert_link "$codex_home/skill-authoring.md" "$repo_root/shared/skill-authoring.md"
assert_link "$codex_home/agent-authoring.md" "$repo_root/shared/agent-authoring.md"
assert_link "$codex_home/self-harness-architecture.md" "$repo_root/shared/self-harness-architecture.md"
assert_link "$codex_home/harness-review.md" "$repo_root/shared/harness-review.md"
assert_link "$codex_home/self-diagnosis.md" "$repo_root/codex/self-diagnosis.md"
assert_link "$codex_home/harness-components.md" "$repo_root/codex/harness-components.md"
assert_path_absent "$codex_home/instruction-locations.md"
assert_link "$codex_home/agents/harness-reviewer.toml" "$repo_root/codex/agents/harness-reviewer.toml"

shared_skills=(
  brain-storming
  create-pull-request
  grill-me
  improve-code-base-architecture
  interface-design
  review-pull-request
  structure-documentation
  ubiquitous-language
)

for name in "${shared_skills[@]}"; do
  assert_link "$claude_home/skills/$name" "$repo_root/shared/skills/$name"
  assert_link "$agents_skills/$name" "$repo_root/shared/skills/$name"
done

assert_link "$agents_skills/frontend-design" "$repo_root/codex/skills/frontend-design"
for name in self-diagnose integrate-context refine-harness; do
  assert_link "$claude_home/skills/$name" "$repo_root/claude/skills/$name"
  assert_link "$agents_skills/$name" "$repo_root/codex/skills/$name"
done

assert_path_absent "$claude_home/meta-doc-critic.md"
assert_path_absent "$codex_home/meta-doc-critic.md"
assert_path_absent "$codex_home/agents/meta-doc-critic.toml"
assert_path_absent "$claude_home/agents/meta-doc-critic.md"

for name in self-improve port-harness-change ubuiquitous-language; do
  assert_path_absent "$claude_home/skills/$name"
  assert_path_absent "$agents_skills/$name"
done

echo '검증 완료: 설치 링크가 유효합니다.'
