"""Run the configured Codex hook from repository and linked-worktree directories."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOKS = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
HANDLER = HOOKS["hooks"]["PostToolUse"][0]["hooks"][0]


class CodexHookTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="codex-hook-")
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name)
        self.repo = self.base / "main"
        self.linked = self.base / "linked"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q")
        script = self.repo / "scripts/render_hook.py"
        script.parent.mkdir()
        script.write_text("from pathlib import Path\nprint(Path(__file__).resolve().parents[1])\n", encoding="utf-8")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "-c", "user.name=Hook Test", "-c", "user.email=hook@example.invalid", "commit", "-qm", "test")
        self.git(self.repo, "worktree", "add", "-q", "--detach", str(self.linked))

    def git(self, cwd, *args):
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def hook(self, cwd):
        command = HANDLER["commandWindows" if os.name == "nt" else "command"]
        return subprocess.run(command, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8")

    def test_uses_current_checkout_from_root_and_subdirectory(self):
        self.assertTrue((self.repo / ".git").is_dir())
        self.assertTrue((self.linked / ".git").is_file())
        for root in (self.repo, self.linked):
            subdirectory = root / "nested"
            subdirectory.mkdir()
            for cwd in (root, subdirectory):
                with self.subTest(cwd=cwd):
                    result = self.hook(cwd)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(Path(result.stdout.strip()), root)

    def test_stops_at_nearest_repository_without_renderer(self):
        nested_repo = self.repo / "nested-repo"
        nested_repo.mkdir()
        self.git(nested_repo, "init", "-q")
        result = self.hook(nested_repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("render hook not found", result.stderr)

    def test_preserves_renderer_output_and_failure(self):
        script = self.linked / "scripts/render_hook.py"
        script.write_text("import sys\nprint('hook output')\nsys.exit(2)\n", encoding="utf-8")
        result = self.hook(self.linked)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "hook output")


if __name__ == "__main__":
    unittest.main()
