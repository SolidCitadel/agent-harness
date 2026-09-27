#!/usr/bin/env python3
"""After pull·checkout·rebase, rerun the installer when this clone is the installed harness, so new links follow the new commit."""

from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def installed_here(root: Path, home: Path) -> bool:
    # ~/.claude/rules는 설치기가 이 저장소의 claude/rules에 거는 디렉터리 링크(Windows는 junction)다.
    link = home / ".claude" / "rules"
    return os.path.lexists(link) and Path(os.path.realpath(link)) == Path(os.path.realpath(root / "claude" / "rules"))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    if not installed_here(root, Path.home()):
        return 0
    env = {key: value for key, value in os.environ.items()
           if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_PREFIX"}}
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if os.name == "nt":
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "scripts" / "install.ps1")]
        result = subprocess.run(command, cwd=root, env=env)
    else:
        result = subprocess.run(["bash", str(root / "scripts" / "install.sh")], cwd=root, env=env,
                                capture_output=True, text=True, encoding="utf-8")
        # 바뀐 링크와 오류만 보여 준다.
        for line in (result.stdout + result.stderr).splitlines():
            if not line.startswith("유지:"):
                print(line)
    if result.returncode != 0:
        print("하네스 재설치에 실패했습니다. 위 메시지를 확인하고 설치기를 직접 실행하세요.", file=sys.stderr)
    warn_unchecked_head(root, env)
    return 0


def warn_unchecked_head(root: Path, env: dict[str, str]) -> None:
    """Server-side merges, web edits and --no-verify commits skip the pre-commit check, so check the HEAD tree itself.

    The installer re-renders the working tree, so checking the working tree would hide drift the commit carries."""
    archive = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", "HEAD"], env=env, capture_output=True)
    if archive.returncode != 0:
        return
    with tempfile.TemporaryDirectory() as tree:
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
            try:
                bundle.extractall(tree, filter="data")
            except TypeError:  # 3.11.4 이전에는 filter 인자가 없다.
                bundle.extractall(tree)
        check = subprocess.run([sys.executable, str(Path(tree) / "scripts" / "check_repo.py"), "--static"], cwd=tree, env=env)
    if check.returncode != 0:
        print("HEAD 커밋이 저장소 검사를 통과하지 못했습니다. 위 항목을 고쳐 커밋하세요.", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
