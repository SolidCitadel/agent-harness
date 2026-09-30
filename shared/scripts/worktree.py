#!/usr/bin/env python3
"""Open, land and drop the git worktree that holds a harness revision until the user approves it.

new: branch <name> from the main checkout's HEAD into a short worktree path and install npm lockfile dependencies.
land: fold fixup commits into their targets, fast-forward the main checkout's branch, then drop the worktree.
drop: remove the worktree and branch; unmerged or uncommitted work is kept unless --discard is given."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

FOLD_PREFIXES = ("fixup!", "squash!", "amend!")


def worktree_root() -> Path:
    # Windows 경로 길이 제한(260자)에 걸리지 않도록 짧은 경로에 둔다.
    configured = os.environ.get("WORKTREE_ROOT")
    if configured:
        return Path(configured)
    return Path("C:/wt") if os.name == "nt" else Path.home() / "wt"


def git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8", env=env)
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} 실패:\n{(result.stderr or result.stdout).strip()}")
    return result.stdout.strip()


def main_checkout(path: Path) -> Path:
    """The checkout that owns the shared git directory, whichever worktree `path` is in."""
    return Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent


def worktrees(root: Path) -> dict[str, Path]:
    """Worktree paths by the branch they have checked out."""
    found: dict[str, Path] = {}
    path: Path | None = None
    for line in git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line.removeprefix("worktree "))
        elif line.startswith("branch refs/heads/") and path:
            found[line.removeprefix("branch refs/heads/")] = path
    return found


def lockfile_directories(path: Path) -> list[Path]:
    tracked = git(path, "ls-files", "-z").split("\0")
    return [path / Path(name).parent for name in tracked if Path(name).name == "package-lock.json"]


def base_branch(root: Path, name: str) -> str:
    """The branch `new` opened `name` from, so land and drop never follow a later switch of the main checkout."""
    result = subprocess.run(["git", "-C", str(root), "config", f"branch.{name}.revisionBase"], capture_output=True,
                            text=True, encoding="utf-8")
    if result.returncode != 0 or not result.stdout.strip():
        sys.exit(f"{name} 브랜치의 기준 브랜치 기록이 없습니다. worktree.py new로 만든 브랜치인지 확인하세요.")
    return result.stdout.strip()


def is_clean(path: Path) -> bool:
    return not git(path, "status", "--porcelain")


def new(repo: Path, name: str) -> int:
    root = main_checkout(repo)
    path = worktree_root() / f"{root.name}-{name}"
    if path.exists():
        sys.exit(f"이미 있는 경로입니다: {path}")
    base = git(root, "branch", "--show-current")
    if not base:
        sys.exit(f"메인 체크아웃이 브랜치에 있지 않습니다: {root}")
    git(root, "worktree", "add", "-b", name, str(path))
    git(root, "config", f"branch.{name}.revisionBase", base)
    # node_modules는 추적하지 않으므로 lockfile대로 새로 설치한다. npm 캐시를 먼저 쓴다.
    for directory in lockfile_directories(path):
        npm = shutil.which("npm")
        if not npm:
            sys.exit(f"npm을 찾지 못해 의존성을 설치하지 못했습니다: {directory}")
        result = subprocess.run([npm, "ci", "--prefer-offline", "--no-audit", "--no-fund", "--loglevel=error"],
                                cwd=directory)
        if result.returncode != 0:
            sys.exit(f"npm ci 실패: {directory}")
    print(path)
    return 0


def drop(repo: Path, name: str, discard: bool = False) -> int:
    root = main_checkout(repo)
    # Windows는 현재 디렉터리로 쓰는 폴더를 지우지 못한다.
    os.chdir(root)
    base = base_branch(root, name)
    path = worktrees(root).get(name)
    if path and not discard and not is_clean(path):
        sys.exit(f"커밋하지 않은 변경이 있습니다: {path}\n버리려면 --discard를 붙입니다.")
    merged = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", name, base]).returncode == 0
    if not merged and not discard:
        sys.exit(f"{name} 브랜치가 {base}에 병합되지 않았습니다. 버리려면 --discard를 붙입니다.")
    if path:
        git(root, "worktree", "remove", *(["--force"] if discard else []), str(path))
        try:
            path.parent.rmdir()
        except OSError:
            pass
    git(root, "branch", "-D" if discard else "-d", name)
    print(f"정리 완료: {name}")
    return 0


def land(repo: Path, name: str) -> int:
    root = main_checkout(repo)
    base = base_branch(root, name)
    if git(root, "branch", "--show-current") != base:
        sys.exit(f"메인 체크아웃이 기준 브랜치 {base}에 있지 않아 병합하지 않았습니다: {root}")
    path = worktrees(root).get(name)
    if not path:
        sys.exit(f"{name} 브랜치의 worktree가 없습니다.")
    if not is_clean(path):
        sys.exit(f"커밋하지 않은 변경이 있습니다: {path}")
    # 편집기 없이 autosquash만 적용한다. 기준 브랜치가 앞서 있으면 그 위로 옮긴다.
    env = {**os.environ, "GIT_SEQUENCE_EDITOR": ":"}
    rebase = subprocess.run(["git", "-C", str(path), "rebase", "-i", "--autosquash", base], env=env,
                            capture_output=True, text=True, encoding="utf-8")
    if rebase.returncode != 0:
        subprocess.run(["git", "-C", str(path), "rebase", "--abort"], capture_output=True)
        sys.exit(f"rebase 실패로 되돌렸습니다:\n{(rebase.stderr or rebase.stdout).strip()}")
    left = [subject for subject in git(path, "log", "--format=%s", f"{base}..{name}").splitlines()
            if subject.startswith(FOLD_PREFIXES)]
    if left:
        sys.exit("대상 커밋을 찾지 못한 정정 커밋이 남았습니다:\n" + "\n".join(left))
    git(root, "merge", "--ff-only", name)
    return drop(root, name)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("new", "land", "drop"):
        sub = commands.add_parser(command)
        sub.add_argument("name", help="브랜치 이름")
        sub.add_argument("--repo", type=Path, default=Path.cwd(), help="대상 저장소 안의 경로(기본: 현재 디렉터리)")
        if command == "drop":
            sub.add_argument("--discard", action="store_true", help="병합하지 않은 커밋과 변경을 버린다")
    args = parser.parse_args(argv)
    if args.command == "new":
        return new(args.repo, args.name)
    if args.command == "land":
        return land(args.repo, args.name)
    return drop(args.repo, args.name, args.discard)


if __name__ == "__main__":
    sys.exit(main())
