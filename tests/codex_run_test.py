from pathlib import Path
import subprocess
import sys
import tempfile
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "claude/skills/codex-exec/scripts"))
import codex_run  # noqa: E402


class RepoRootTest(unittest.TestCase):
    def test_repository_subdirectory_resolves_to_top_level(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch).resolve()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "sub").mkdir()
            self.assertEqual(codex_run.repo_root(root / "sub").resolve(), root)

    def test_directory_outside_git_is_kept(self):
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(codex_run.repo_root(Path(scratch)), Path(scratch))


class AgentOverridesTest(unittest.TestCase):
    def test_instructions_and_model_become_config_overrides(self):
        with tempfile.TemporaryDirectory() as home:
            (Path(home) / "agents").mkdir()
            (Path(home) / "agents/reviewer.toml").write_text(
                'name = "reviewer"\nsandbox_mode = "read-only"\nmodel = "m1"\n'
                'developer_instructions = """\n읽고 "따른다".\n"""\n', encoding="utf-8")
            overrides = codex_run.agent_overrides("reviewer", Path(home))
        self.assertEqual(overrides, ["-c", 'developer_instructions="읽고 \\"따른다\\"."', "-c", 'model="m1"'])

    def test_no_agent(self):
        self.assertEqual(codex_run.agent_overrides(None), [])


class ArgumentsTest(unittest.TestCase):
    def test_exec_fixes_read_only_root_and_output(self):
        arguments = codex_run.exec_arguments(Path("R"), Path("out.md"), search=True, images=["a.png", "b.png"],
                                             agent=["-c", "developer_instructions=\"x\""])
        self.assertEqual(arguments[:2], ["--search", "exec"])
        self.assertEqual(arguments[arguments.index("-s") + 1], "read-only")
        self.assertEqual(arguments[arguments.index("-C") + 1], "R")
        self.assertLess(arguments.index("b.png"), arguments.index("-o"))
        self.assertEqual(arguments[-3:], ["-o", "out.md", "-"])

    def test_user_model_follows_agent_overrides(self):
        arguments = codex_run.exec_arguments(Path("R"), Path("out.md"), model="m2", effort="low",
                                             agent=["-c", 'model="m1"'])
        self.assertLess(arguments.index('model="m1"'), arguments.index("m2"))
        self.assertIn('model_reasoning_effort="low"', arguments)

    def test_resume_restates_read_only_sandbox(self):
        arguments = codex_run.resume_arguments("S1", Path("out.md"))
        self.assertEqual(arguments[:2], ["exec", "resume"])
        self.assertIn('sandbox_mode="read-only"', arguments)
        self.assertEqual(arguments[-4:], ["S1", "-o", "out.md", "-"])


class RunMetadataTest(unittest.TestCase):
    def test_values_from_log_header(self):
        log = "workdir: R\nmodel: gpt-6-luna\nreasoning effort: high\nsession id: 0199-abc\n"
        self.assertEqual(codex_run.header(log, "session id"), "0199-abc")
        self.assertEqual(codex_run.header(log, "model"), "gpt-6-luna")
        self.assertEqual(codex_run.header(log, "reasoning effort"), "high")

    def test_find_run_by_session(self):
        with tempfile.TemporaryDirectory() as base:
            run = Path(base) / "20260930-1"
            run.mkdir()
            (run / "meta.json").write_text(json.dumps({"session": "S1", "cwd": "C"}), encoding="utf-8")
            self.assertEqual(codex_run.find_run("S1", Path(base))["cwd"], "C")


class RepoRootErrorTest(unittest.TestCase):
    def test_git_failure_other_than_outside_repository_stops(self):
        with tempfile.TemporaryDirectory() as scratch:
            with self.assertRaises(SystemExit):
                codex_run.repo_root(Path(scratch) / "missing")


class ResolveModelTest(unittest.TestCase):
    def cache(self, home: str) -> Path:
        models = [{"slug": "gpt-6.1-sol", "visibility": "list", "priority": 1},
                  {"slug": "gpt-6-luna", "visibility": "list", "priority": 4},
                  {"slug": "gpt-5.6-luna", "visibility": "list", "priority": 9},
                  {"slug": "gpt-7-luna", "visibility": "hide", "priority": 0}]
        (Path(home) / "models_cache.json").write_text(json.dumps({"models": models}), encoding="utf-8")
        return Path(home)

    def test_family_resolves_to_newest_listed_model(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(codex_run.resolve_model("luna", self.cache(home)), "gpt-6-luna")
            self.assertEqual(codex_run.resolve_model("sol", self.cache(home)), "gpt-6.1-sol")

    def test_model_id_passes_through(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(codex_run.resolve_model("gpt-9-sol", Path(home)), "gpt-9-sol")
            self.assertIsNone(codex_run.resolve_model(None, Path(home)))

    def test_unresolved_family_stops(self):
        with tempfile.TemporaryDirectory() as home:
            with self.assertRaises(SystemExit):
                codex_run.resolve_model("terra", self.cache(home))


if __name__ == "__main__":
    unittest.main()
