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
"$python_bin" "$repo_root/scripts/render_platform_files.py"

# 저장소의 커밋 전 검사를 쓰도록 이 저장소의 git hook 경로만 설정한다. 다른 값이 있으면 보존하고 중단한다.
git_top="$(git -C "$repo_root" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$git_top" && "$(realpath -m -- "$git_top")" == "$repo_root" ]]; then
  hooks_path="$(git -C "$repo_root" config --local --get core.hooksPath || true)"
  if [[ -z "$hooks_path" ]]; then
    # 전역 hook 경로나 .git/hooks의 사용자 hook이 있으면 설정이 그것을 끄게 되므로 보존하고 중단한다.
    inherited="$(git -C "$repo_root" config --get core.hooksPath || true)"
    default_hooks="$(git -C "$repo_root" rev-parse --git-path hooks)"
    [[ "$default_hooks" = /* ]] || default_hooks="$repo_root/$default_hooks"
    custom_hooks="$(find "$default_hooks" -maxdepth 1 ! -type d ! -name '*.sample' -print 2>/dev/null || true)"
    if [[ -n "$inherited" || -n "$custom_hooks" ]]; then
      echo '기존 git hook이 있어 설치를 중단했습니다:' "$inherited" $custom_hooks >&2
      echo '기존 hook을 .githooks로 옮기거나 연결한 뒤 git config --local core.hooksPath .githooks를 설정하고 설치기를 다시 실행하세요.' >&2
      exit 1
    fi
    git -C "$repo_root" config --local core.hooksPath .githooks
    echo '연결: core.hooksPath -> .githooks'
  elif [[ "$hooks_path" != '.githooks' ]]; then
    echo "기존 core.hooksPath가 관리 값과 다릅니다: $hooks_path" >&2
    exit 1
  fi
else
  echo 'git을 찾지 못했거나 저장소 루트가 git 작업 트리가 아니어서 core.hooksPath를 설정하지 않았습니다.'
fi

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

# 같은 경로의 원본이 공통 파일에서 플랫폼 생성물로 바뀐 경우, 이전 원본을 가리키는 관리 링크만 제거한다.
retire_link() {
  local destination old_source target
  destination="$1"; old_source="$2"
  [[ -L "$destination" ]] || return 0
  target="$(readlink -- "$destination")"
  [[ "$target" = /* ]] || target="$(dirname -- "$destination")/$target"
  if [[ "$(realpath -m -s -- "$target")" == "$old_source" ]]; then
    rm -- "$destination"
    printf '이전 관리 링크 제거: %s\n' "$destination"
  fi
}

install_link "$repo_root/claude/CLAUDE.md" "$claude_home/CLAUDE.md"
install_link "$repo_root/shared/harness-authoring.md" "$claude_home/harness-authoring.md"
install_link "$repo_root/shared/skill-authoring.md" "$claude_home/skill-authoring.md"
install_link "$repo_root/shared/agent-authoring.md" "$claude_home/agent-authoring.md"
install_link "$repo_root/shared/self-harness-architecture.md" "$claude_home/self-harness-architecture.md"
install_link "$repo_root/shared/harness-review.md" "$claude_home/harness-review.md"
install_link "$repo_root/claude/harness-components.md" "$claude_home/harness-components.md"
retire_link "$claude_home/self-diagnosis.md" "$repo_root/shared/self-diagnosis.md"
install_link "$repo_root/claude/self-diagnosis.md" "$claude_home/self-diagnosis.md"
install_link "$repo_root/claude/commands/frontend-design.md" "$claude_home/commands/frontend-design.md"
install_link "$repo_root/shared/vendor/anthropics/frontend-design/LICENSE.txt" "$claude_home/commands/frontend-design.LICENSE.txt"
install_link "$repo_root/codex/AGENTS.md" "$codex_home/AGENTS.md"
install_link "$repo_root/shared/harness-authoring.md" "$codex_home/harness-authoring.md"
install_link "$repo_root/shared/skill-authoring.md" "$codex_home/skill-authoring.md"
install_link "$repo_root/shared/agent-authoring.md" "$codex_home/agent-authoring.md"
install_link "$repo_root/shared/self-harness-architecture.md" "$codex_home/self-harness-architecture.md"
install_link "$repo_root/shared/harness-review.md" "$codex_home/harness-review.md"
retire_link "$codex_home/self-diagnosis.md" "$repo_root/shared/self-diagnosis.md"
install_link "$repo_root/codex/self-diagnosis.md" "$codex_home/self-diagnosis.md"
install_link "$repo_root/codex/harness-components.md" "$codex_home/harness-components.md"
install_link "$repo_root/codex/agents/harness-reviewer.toml" "$codex_home/agents/harness-reviewer.toml"

install_link "$repo_root/claude/rules" "$claude_home/rules"
install_link "$repo_root/claude/agents" "$claude_home/agents"
install_link "$repo_root/claude/hooks" "$claude_home/hooks"

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

# 같은 이름의 플랫폼별 skill로 바뀐 이전 shared skill 링크만 먼저 제거하고, 그 밖의 경로는 install_link가 판정한다.
for name in self-diagnose integrate-context refine-harness; do
  retire_link "$claude_home/skills/$name" "$repo_root/shared/skills/$name"
  retire_link "$agents_skills/$name" "$repo_root/shared/skills/$name"
  install_link "$repo_root/claude/skills/$name" "$claude_home/skills/$name"
  install_link "$repo_root/codex/skills/$name" "$agents_skills/$name"
done

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
  install_link "$repo_root/shared/skills/$name" "$claude_home/skills/$name"
  install_link "$repo_root/shared/skills/$name" "$agents_skills/$name"
done

install_link "$repo_root/codex/skills/frontend-design" "$agents_skills/frontend-design"

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
for destination in "$claude_home/skills/ubiquitous-language" "$agents_skills/ubiquitous-language"; do
  [[ -L "$destination" && "$(readlink -f -- "$destination")" == "$repo_root/shared/skills/ubiquitous-language" ]] || {
    echo "새 skill 링크 검증 실패: $destination" >&2; exit 1;
  }
done
for pair in "$claude_home/skills/integrate-context:$repo_root/claude/skills/integrate-context" "$agents_skills/integrate-context:$repo_root/codex/skills/integrate-context"; do
  [[ -L "${pair%%:*}" && "$(readlink -f -- "${pair%%:*}")" == "${pair#*:}" ]] || {
    echo "새 skill 링크 검증 실패: ${pair%%:*}" >&2; exit 1;
  }
done
remove_previous_skill "$claude_home/skills/ubuiquitous-language" "$repo_root/shared/skills/ubuiquitous-language"
remove_previous_skill "$agents_skills/ubuiquitous-language" "$repo_root/shared/skills/ubuiquitous-language"
remove_previous_skill "$claude_home/skills/self-improve" "$repo_root/claude/skills/self-improve"
remove_previous_skill "$agents_skills/self-improve" "$repo_root/codex/skills/self-improve"
remove_previous_skill "$claude_home/skills/port-harness-change" "$repo_root/shared/skills/port-harness-change"
remove_previous_skill "$agents_skills/port-harness-change" "$repo_root/shared/skills/port-harness-change"

printf '설치 완료: %s\n' "$repo_root"
bash "$repo_root/scripts/verify.sh" --repo-root "$repo_root" --home "$user_home"
