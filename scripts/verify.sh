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

assert_link "$claude_home/CLAUDE.md" "$repo_root/claude/CLAUDE.md"
assert_link "$claude_home/rules" "$repo_root/claude/rules"
assert_link "$claude_home/agents" "$repo_root/claude/agents"
assert_link "$claude_home/hooks" "$repo_root/claude/hooks"
assert_link "$codex_home/AGENTS.md" "$repo_root/codex/AGENTS.md"
assert_link "$codex_home/agents/meta-doc-critic.toml" "$repo_root/codex/agents/meta-doc-critic.toml"

shared_skills=(
  brain-storming
  frontend-design
  grill-me
  improve-code-base-architecture
  interface-design
  structure-documentation
  ubuiquitous-language
  port-harness-change
)

for name in "${shared_skills[@]}"; do
  assert_link "$claude_home/skills/$name" "$repo_root/shared/skills/$name"
  assert_link "$agents_skills/$name" "$repo_root/shared/skills/$name"
done

assert_link "$claude_home/skills/self-improve" "$repo_root/claude/skills/self-improve"
assert_link "$agents_skills/self-improve" "$repo_root/codex/skills/self-improve"

critic="$repo_root/codex/agents/meta-doc-critic.toml"
for key in name description developer_instructions; do
  if ! grep -Eq "^${key}[[:space:]]*=" "$critic"; then
    echo "critic agent 필드 누락: $key" >&2
    exit 1
  fi
done

skill_count=0
while IFS= read -r -d '' skill; do
  first_lines="$(head -n 10 -- "$skill")"
  if [[ "$(head -n 1 -- "$skill")" != '---' ]] \
    || ! grep -Eq '^name:[[:space:]]*[^[:space:]]' <<<"$first_lines" \
    || ! grep -Eq '^description:[[:space:]]*[^[:space:]]' <<<"$first_lines"; then
    echo "SKILL.md frontmatter 검증 실패: $skill" >&2
    exit 1
  fi
  ((skill_count += 1))
done < <(find "$repo_root/shared/skills" "$repo_root/claude/skills" "$repo_root/codex/skills" -name SKILL.md -type f -print0)

printf '검증 완료: symbolic link와 메타 파일 %d개가 유효합니다.\n' "$skill_count"
