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
assert_link "$claude_home/commands/frontend-design.md" "$repo_root/claude/commands/frontend-design.md"
assert_link "$claude_home/commands/frontend-design.LICENSE.txt" "$repo_root/shared/vendor/anthropics/frontend-design/LICENSE.txt"
if [[ -e "$claude_home/skills/frontend-design" || -L "$claude_home/skills/frontend-design" ]]; then
  echo "더 이상 사용하지 않는 경로가 남아 있습니다: $claude_home/skills/frontend-design" >&2
  exit 1
fi
assert_link "$codex_home/AGENTS.md" "$repo_root/codex/AGENTS.md"
assert_link "$codex_home/agents/meta-doc-critic.toml" "$repo_root/codex/agents/meta-doc-critic.toml"

shared_skills=(
  brain-storming
  grill-me
  improve-code-base-architecture
  interface-design
  review-pull-request
  structure-documentation
  ubuiquitous-language
  port-harness-change
)

for name in "${shared_skills[@]}"; do
  assert_link "$claude_home/skills/$name" "$repo_root/shared/skills/$name"
  assert_link "$agents_skills/$name" "$repo_root/shared/skills/$name"
done

assert_link "$agents_skills/frontend-design" "$repo_root/codex/skills/frontend-design"

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

frontend_policy="$repo_root/codex/skills/frontend-design/agents/openai.yaml"
if ! grep -Eq '^[[:space:]]*allow_implicit_invocation:[[:space:]]*false[[:space:]]*$' "$frontend_policy"; then
  echo '외부 frontend-design은 명시적 호출 전용이어야 합니다.' >&2
  exit 1
fi

read -r expected_skill_hash expected_license_hash implicit < <(
  python -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8"))["frontend-design"]; print(d["upstreamSkillSha256"],d["licenseSha256"],d["implicitInvocation"])' "$repo_root/shared/third-party-skills.json"
)
normalized_hash() { tr -d '\r' < "$1" | sha256sum | cut -d ' ' -f 1; }
actual_skill_hash="$(normalized_hash "$repo_root/shared/vendor/anthropics/frontend-design/SKILL.md")"
actual_license_hash="$(normalized_hash "$repo_root/shared/vendor/anthropics/frontend-design/LICENSE.txt")"
codex_skill_hash="$(normalized_hash "$repo_root/codex/skills/frontend-design/SKILL.md")"
codex_license_hash="$(normalized_hash "$repo_root/codex/skills/frontend-design/LICENSE.txt")"
claude_skill_hash="$(tr -d '\r' < "$repo_root/claude/commands/frontend-design.md" | sed -e '/^disable-model-invocation:[[:space:]]*true[[:space:]]*$/d' -e 's|^license: Complete terms in frontend-design\.LICENSE\.txt$|license: Complete terms in LICENSE.txt|' | sha256sum | cut -d ' ' -f 1)"
claude_frontmatter="$(tr -d '\r' < "$repo_root/claude/commands/frontend-design.md" | awk 'NR == 1 { if ($0 != "---") exit 2; next } $0 == "---" { found = 1; exit } { print } END { if (!found) exit 2 }')"
if ! grep -Eq '^disable-model-invocation:[[:space:]]*true[[:space:]]*$' <<<"$claude_frontmatter"; then
  echo 'Claude용 frontend-design command는 명시적 호출 전용이어야 합니다.' >&2
  exit 1
fi
if [[ "${implicit,,}" != 'false' || "${actual_skill_hash^^}" != "$expected_skill_hash" || "${actual_license_hash^^}" != "$expected_license_hash" || "${codex_skill_hash^^}" != "${actual_skill_hash^^}" || "${codex_license_hash^^}" != "${actual_license_hash^^}" || "${claude_skill_hash^^}" != "${actual_skill_hash^^}" ]]; then
  echo 'frontend-design 설치본 또는 호출 정책이 기록된 메타데이터와 다릅니다.' >&2
  exit 1
fi

printf '검증 완료: symbolic link와 메타 파일 %d개가 유효합니다.\n' "$skill_count"
