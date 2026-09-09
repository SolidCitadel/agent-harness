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
"$python_bin" "$repo_root/scripts/render_global_instructions.py"
mkdir -p -- "$claude_home" "$codex_home" "$agents_skills"

install_link() {
  local source destination actual
  source="$(realpath -- "$1")"
  destination="$2"

  if [[ -L "$destination" ]]; then
    actual="$(readlink -f -- "$destination" || true)"
    if [[ "$actual" == "$source" ]]; then
      printf '유지: %s\n' "$destination"
      return
    fi
  fi
  if [[ -e "$destination" || -L "$destination" ]]; then
    echo "기존 경로가 관리 링크와 다릅니다: $destination" >&2
    exit 1
  fi

  mkdir -p -- "$(dirname -- "$destination")"
  ln -s -- "$source" "$destination"
  printf '연결: %s -> %s\n' "$destination" "$source"
}

install_link "$repo_root/claude/CLAUDE.md" "$claude_home/CLAUDE.md"
install_link "$repo_root/shared/harness-authoring.md" "$claude_home/harness-authoring.md"
install_link "$repo_root/shared/skill-authoring.md" "$claude_home/skill-authoring.md"
install_link "$repo_root/shared/agent-authoring.md" "$claude_home/agent-authoring.md"
install_link "$repo_root/shared/self-harness-architecture.md" "$claude_home/self-harness-architecture.md"
install_link "$repo_root/shared/harness-review.md" "$claude_home/harness-review.md"
install_link "$repo_root/claude/commands/frontend-design.md" "$claude_home/commands/frontend-design.md"
install_link "$repo_root/shared/vendor/anthropics/frontend-design/LICENSE.txt" "$claude_home/commands/frontend-design.LICENSE.txt"
install_link "$repo_root/codex/AGENTS.md" "$codex_home/AGENTS.md"
install_link "$repo_root/shared/harness-authoring.md" "$codex_home/harness-authoring.md"
install_link "$repo_root/shared/skill-authoring.md" "$codex_home/skill-authoring.md"
install_link "$repo_root/shared/agent-authoring.md" "$codex_home/agent-authoring.md"
install_link "$repo_root/shared/self-harness-architecture.md" "$codex_home/self-harness-architecture.md"
install_link "$repo_root/shared/harness-review.md" "$codex_home/harness-review.md"
install_link "$repo_root/codex/harness-components.md" "$codex_home/harness-components.md"
install_link "$repo_root/codex/agents/harness-reviewer.toml" "$codex_home/agents/harness-reviewer.toml"

install_link "$repo_root/claude/rules" "$claude_home/rules"
install_link "$repo_root/claude/agents" "$claude_home/agents"
install_link "$repo_root/claude/hooks" "$claude_home/hooks"

shared_skills=(
  brain-storming
  create-pull-request
  grill-me
  improve-code-base-architecture
  interface-design
  review-pull-request
  structure-documentation
  ubiquitous-language
  self-diagnose
  integrate-context
)

for name in "${shared_skills[@]}"; do
  install_link "$repo_root/shared/skills/$name" "$claude_home/skills/$name"
  install_link "$repo_root/shared/skills/$name" "$agents_skills/$name"
done

install_link "$repo_root/codex/skills/frontend-design" "$agents_skills/frontend-design"
install_link "$repo_root/claude/skills/refine-harness" "$claude_home/skills/refine-harness"
install_link "$repo_root/shared/skills/refine-harness" "$agents_skills/refine-harness"

# 새 설치가 성공한 뒤 원본 경로 또는 inode로 관리 소유를 확인한다.
remove_previous_link() {
  local destination old_source new_source installed actual target
  destination="$1"; old_source="$2"; new_source="$3"; installed="$4"
  [[ -L "$installed" && "$(readlink -f -- "$installed")" == "$new_source" ]] || {
    echo "새 관리 링크 검증 실패: $installed" >&2; exit 1;
  }
  [[ -e "$destination" || -L "$destination" ]] || return 0
  if [[ -L "$destination" ]]; then
    target="$(readlink -- "$destination")"
    [[ "$target" = /* ]] || target="$(dirname -- "$destination")/$target"
    actual="$(realpath -m -s -- "$target")"
    if [[ "$actual" == "$old_source" || "$actual" == "$new_source" ]]; then
      rm -- "$destination"
      return
    fi
  elif [[ -f "$destination" && "$destination" -ef "$new_source" ]]; then
    rm -- "$destination"
    return
  fi
  echo "이전 비관리 경로를 보존했습니다: $destination" >&2
  exit 1
}
remove_previous_link "$claude_home/meta-doc-critic.md" "$repo_root/shared/meta-doc-critic.md" "$repo_root/shared/harness-review.md" "$claude_home/harness-review.md"
remove_previous_link "$codex_home/meta-doc-critic.md" "$repo_root/shared/meta-doc-critic.md" "$repo_root/shared/harness-review.md" "$codex_home/harness-review.md"
remove_previous_link "$codex_home/agents/meta-doc-critic.toml" "$repo_root/codex/agents/meta-doc-critic.toml" "$repo_root/codex/agents/harness-reviewer.toml" "$codex_home/agents/harness-reviewer.toml"

# 새 skill 연결을 확인한 뒤 이전 symbolic link 자체만 제거한다.
for name in self-diagnose integrate-context ubiquitous-language; do
  for destination in "$claude_home/skills/$name" "$agents_skills/$name"; do
    [[ -L "$destination" && "$(readlink -f -- "$destination")" == "$repo_root/shared/skills/$name" ]] || {
      echo "새 skill 링크 검증 실패: $destination" >&2; exit 1;
    }
  done
done
remove_previous_skill() {
  local destination expected target
  destination="$1"; expected="$2"
  [[ -e "$destination" || -L "$destination" ]] || return 0
  if [[ -L "$destination" ]]; then
    target="$(readlink -- "$destination")"
    [[ "$target" = /* ]] || target="$(dirname -- "$destination")/$target"
    if [[ "$(realpath -m -s -- "$target")" == "$expected" ]]; then
      rm -- "$destination"
      return
    fi
  fi
  echo "이전 비관리 skill 경로를 보존했습니다: $destination" >&2
  exit 1
}
remove_previous_skill "$claude_home/skills/ubuiquitous-language" "$repo_root/shared/skills/ubuiquitous-language"
remove_previous_skill "$agents_skills/ubuiquitous-language" "$repo_root/shared/skills/ubuiquitous-language"
remove_previous_skill "$claude_home/skills/self-improve" "$repo_root/claude/skills/self-improve"
remove_previous_skill "$agents_skills/self-improve" "$repo_root/codex/skills/self-improve"
remove_previous_skill "$claude_home/skills/port-harness-change" "$repo_root/shared/skills/port-harness-change"
remove_previous_skill "$agents_skills/port-harness-change" "$repo_root/shared/skills/port-harness-change"

printf '설치 완료: %s\n' "$repo_root"
