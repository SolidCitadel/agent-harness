from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared/scripts"))
import worktree  # noqa: E402

IDENTITY = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def commit(cwd: Path, file: str, text: str, message: str) -> None:
    (cwd / file).write_text(text, encoding="utf-8")
    git(cwd, "add", file)
    git(cwd, "commit", "-q", "-m", message)


class WorktreeTest(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.addCleanup(os.chdir, self.cwd)
        base = Path(scratch.name).resolve()
        self.repo, self.root = base / "repo", base / "wt"
        patcher = mock.patch.dict(os.environ, {**IDENTITY, "WORKTREE_ROOT": str(self.root)})
        patcher.start()
        self.addCleanup(patcher.stop)
        git(base, "init", "-q", "-b", "main", str(self.repo))
        git(self.repo, "config", "core.hooksPath", "no-hooks")
        commit(self.repo, "a.txt", "1\n", "init")

    def test_new_branches_from_head_into_short_path(self):
        worktree.new(self.repo, "rev")
        path = self.root / "repo-rev"
        self.assertEqual(git(path, "branch", "--show-current"), "rev")
        self.assertEqual(worktree.main_checkout(path).resolve(), self.repo)

    def test_lockfile_directories_are_found_at_any_depth(self):
        commit(self.repo, "package-lock.json", "{}", "root lock")
        (self.repo / "tools/qa").mkdir(parents=True)
        commit(self.repo, "tools/qa/package-lock.json", "{}", "tool lock")
        self.assertEqual(sorted(worktree.lockfile_directories(self.repo)), [self.repo, self.repo / "tools/qa"])

    def test_land_folds_fixups_and_fast_forwards(self):
        worktree.new(self.repo, "rev")
        path = self.root / "repo-rev"
        commit(path, "a.txt", "2\n", "change a")
        commit(path, "b.txt", "b\n", "add b")
        commit(path, "a.txt", "3\n", "fixup! change a")
        worktree.land(path, "rev")
        self.assertEqual(git(self.repo, "log", "--format=%s", "-3").splitlines(), ["add b", "change a", "init"])
        self.assertEqual((self.repo / "a.txt").read_text(encoding="utf-8"), "3\n")
        self.assertFalse(path.exists())
        self.assertFalse(self.root.exists())
        self.assertEqual(git(self.repo, "branch", "--list", "rev"), "")

    def test_land_targets_the_recorded_base_branch(self):
        worktree.new(self.repo, "rev")
        path = self.root / "repo-rev"
        commit(path, "a.txt", "2\n", "change a")
        git(self.repo, "switch", "-q", "-c", "other")
        with self.assertRaises(SystemExit):
            worktree.land(path, "rev")
        self.assertEqual(git(self.repo, "log", "--format=%s", "-1", "main"), "init")
        git(self.repo, "switch", "-q", "main")
        worktree.land(path, "rev")
        self.assertEqual(git(self.repo, "log", "--format=%s", "-1", "main"), "change a")

    def test_drop_keeps_unmerged_work_unless_discarded(self):
        worktree.new(self.repo, "rev")
        path = self.root / "repo-rev"
        commit(path, "a.txt", "2\n", "change a")
        with self.assertRaises(SystemExit):
            worktree.drop(self.repo, "rev")
        self.assertTrue(path.exists())
        worktree.drop(self.repo, "rev", discard=True)
        self.assertFalse(path.exists())
        self.assertEqual(git(self.repo, "branch", "--list", "rev"), "")

    def test_drop_keeps_uncommitted_changes(self):
        worktree.new(self.repo, "rev")
        (self.root / "repo-rev" / "a.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            worktree.drop(self.repo, "rev")


if __name__ == "__main__":
    unittest.main()
