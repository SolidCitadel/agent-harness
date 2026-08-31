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
stamp="$(date +%Y%m%d-%H%M%S)"
claude_home="$user_home/.claude"
codex_home="$user_home/.codex"
agents_skills="$user_home/.agents/skills"
snapshot_root="$repo_root/.migration-snapshots/$stamp"
claude_snapshot="$snapshot_root/claude"
codex_snapshot="$snapshot_root/codex"
agents_snapshot="$snapshot_root/agents"

mkdir -p -- "$claude_home" "$codex_home" "$agents_skills"

install_link() {
  local source destination snapshot_root snapshot_relative actual snapshot_path
  source="$(realpath -- "$1")"
  destination="$2"
  snapshot_root="$3"
  snapshot_relative="$4"

  if [[ -L "$destination" ]]; then
    actual="$(readlink -f -- "$destination" || true)"
    if [[ "$actual" == "$source" ]]; then
      printf '유지: %s\n' "$destination"
      return
    fi
  fi

  if [[ -e "$destination" || -L "$destination" ]]; then
    snapshot_path="$snapshot_root/$snapshot_relative"
    mkdir -p -- "$(dirname -- "$snapshot_path")"
    mv -- "$destination" "$snapshot_path"
    printf '스냅샷: %s -> %s\n' "$destination" "$snapshot_path"
  fi

  mkdir -p -- "$(dirname -- "$destination")"
  ln -s -- "$source" "$destination"
  printf '연결: %s -> %s\n' "$destination" "$source"
}

if [[ -e "$claude_home/.git" ]]; then
  legacy_snapshot="$claude_snapshot/legacy-repository"
  mkdir -p -- "$legacy_snapshot"
  mv -- "$claude_home/.git" "$legacy_snapshot/.git"
  if [[ -e "$claude_home/.gitignore" ]]; then
    mv -- "$claude_home/.gitignore" "$legacy_snapshot/.gitignore"
  fi
  printf '기존 ~/.claude Git 메타데이터 스냅샷: %s\n' "$legacy_snapshot"
fi

install_link "$repo_root/claude/CLAUDE.md" "$claude_home/CLAUDE.md" "$claude_snapshot" 'CLAUDE.md'
install_link "$repo_root/claude/self-harness-engineering.md" "$claude_home/self-harness-engineering.md" "$claude_snapshot" 'self-harness-engineering.md'
install_link "$repo_root/codex/AGENTS.md" "$codex_home/AGENTS.md" "$codex_snapshot" 'AGENTS.md'
install_link "$repo_root/codex/agents/meta-doc-critic.toml" "$codex_home/agents/meta-doc-critic.toml" "$codex_snapshot" 'agents/meta-doc-critic.toml'

install_link "$repo_root/claude/rules" "$claude_home/rules" "$claude_snapshot" 'rules'
install_link "$repo_root/claude/agents" "$claude_home/agents" "$claude_snapshot" 'agents'
install_link "$repo_root/claude/hooks" "$claude_home/hooks" "$claude_snapshot" 'hooks'

shared_skills=(
  brain-storming
  frontend-design
  grill-me
  improve-code-base-architecture
  interface-design
  review-pull-request
  structure-documentation
  ubuiquitous-language
  port-harness-change
)

for name in "${shared_skills[@]}"; do
  install_link "$repo_root/shared/skills/$name" "$claude_home/skills/$name" "$claude_snapshot" "skills/$name"
  install_link "$repo_root/shared/skills/$name" "$agents_skills/$name" "$agents_snapshot" "skills/$name"
done

install_link "$repo_root/claude/skills/self-improve" "$claude_home/skills/self-improve" "$claude_snapshot" 'skills/self-improve'
install_link "$repo_root/codex/skills/self-improve" "$agents_skills/self-improve" "$agents_snapshot" 'skills/self-improve'

printf '설치 완료: %s\n' "$repo_root"
