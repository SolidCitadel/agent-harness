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

python_bin="$(command -v python3 || command -v python)"
"$python_bin" "$repo_root/scripts/render_global_instructions.py" --check

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
assert_link "$claude_home/meta-doc-critic.md" "$repo_root/shared/meta-doc-critic.md"
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
assert_link "$codex_home/meta-doc-critic.md" "$repo_root/shared/meta-doc-critic.md"
assert_link "$codex_home/harness-components.md" "$repo_root/codex/harness-components.md"
assert_path_absent "$codex_home/instruction-locations.md"
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
assert_link "$claude_home/skills/refine-harness" "$repo_root/claude/skills/refine-harness"
assert_link "$agents_skills/refine-harness" "$repo_root/shared/skills/refine-harness"

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

refine_skill="$repo_root/claude/skills/refine-harness/SKILL.md"
refine_policy="$repo_root/shared/skills/refine-harness/agents/openai.yaml"
if ! grep -Eq '^disable-model-invocation:[[:space:]]*true[[:space:]]*$' "$refine_skill" \
  || ! grep -Eq '^[[:space:]]*allow_implicit_invocation:[[:space:]]*false[[:space:]]*$' "$refine_policy"; then
  echo 'refine-harness는 양 플랫폼에서 명시 호출 전용이어야 합니다.' >&2
  exit 1
fi
if ! grep -Fq '~/.agents/skills/refine-harness/SKILL.md' "$refine_skill"; then
  echo 'Claude refine-harness 어댑터가 shared 정본을 참조하지 않습니다.' >&2
  exit 1
fi
if [[ "$(tr -d '\r' < "$repo_root/CLAUDE.md")" != '@AGENTS.md' ]]; then
  echo '루트 CLAUDE.md는 AGENTS.md를 참조해야 합니다.' >&2
  exit 1
fi

harness_rule="$repo_root/claude/rules/harness-authoring.md"
agent_rule="$repo_root/claude/rules/agents.md"
skill_rule="$repo_root/claude/rules/skill-md.md"
codex_global="$repo_root/codex/AGENTS.md"
for pattern in '**/AGENTS.override.md' '**/.codex/rules/**/*.rules' '**/.codex/hooks.json' '**/.codex/config.toml'; do
  if ! grep -Fq -- "$pattern" "$harness_rule"; then
    echo "Claude 공통 하네스 rule의 경로 누락: $pattern" >&2
    exit 1
  fi
done
if ! grep -Fq -- '~/.claude/harness-authoring.md' "$harness_rule"; then
  echo 'Claude 공통 하네스 rule이 공통 작성 규율을 참조하지 않습니다.' >&2
  exit 1
fi
if ! grep -Fq -- '~/.claude/skill-authoring.md' "$skill_rule"; then
  echo 'Claude skill 작성 rule이 공통 skill 규율을 참조하지 않습니다.' >&2
  exit 1
fi
if ! grep -Fq -- '**/agents/**/*.toml' "$agent_rule"; then
  echo 'Claude agent 작성 rule이 TOML agent를 포함하지 않습니다.' >&2
  exit 1
fi
if ! grep -Fq -- '~/.claude/agent-authoring.md' "$agent_rule"; then
  echo 'Claude agent 작성 rule이 공통 agent 규율을 참조하지 않습니다.' >&2
  exit 1
fi
for reference in '~/.codex/harness-authoring.md' '~/.codex/harness-components.md'; do
  if ! grep -Fq -- "$reference" "$codex_global"; then
    echo "Codex 전역 하네스 라우팅 누락: $reference" >&2
    exit 1
  fi
done

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
