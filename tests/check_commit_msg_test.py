from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_commit_msg  # noqa: E402

BODY = "shared: tighten refinement\n\nWhy it changed.\n\n"


class TouchesHarnessTest(unittest.TestCase):
    def test_harness_paths(self):
        self.assertTrue(check_commit_msg.touches_harness(["shared/harness-authoring.md"]))
        self.assertTrue(check_commit_msg.touches_harness(["AGENTS.md"]))
        self.assertFalse(check_commit_msg.touches_harness(["scripts/install.py", "tests/install_test.py"]))


class ProblemsTest(unittest.TestCase):
    def test_request_with_review(self):
        message = BODY + "Trigger: request\nRevised-By: claude-opus-5-5 (claude-code)\nReviewed-By: gpt-6-sol (codex exec)\n"
        self.assertEqual(check_commit_msg.problems(message), [])

    def test_failure_needs_failure_model(self):
        message = BODY + "Trigger: failure\nRevised-By: human\nReviewed-By: none\n"
        self.assertEqual(len(check_commit_msg.problems(message)), 1)
        self.assertEqual(check_commit_msg.problems(message + "Failure-Model: unknown\n"), [])

    def test_failure_model_only_for_failure(self):
        message = BODY + "Trigger: refine\nFailure-Model: unknown\nRevised-By: human\nReviewed-By: none\n"
        self.assertEqual(len(check_commit_msg.problems(message)), 1)

    def test_missing_and_malformed(self):
        errors = check_commit_msg.problems(BODY + "Trigger: fix\nRevised-By: opus\n")
        self.assertEqual(len(errors), 3)

    def test_fixup_follows_target_commit(self):
        self.assertEqual(check_commit_msg.problems("fixup! shared: tighten refinement\n"), [])
        self.assertEqual(len(check_commit_msg.problems("amend! shared: tighten refinement\n")), 3)

    def test_trailers_must_be_last_paragraph(self):
        message = "s: x\n\nTrigger: request\nRevised-By: human\nReviewed-By: none\n\nTrailing prose.\n"
        self.assertEqual(len(check_commit_msg.problems(message)), 3)

    def test_comment_lines_and_crlf_ignored(self):
        message = (BODY + "Trigger: request\nRevised-By: human\nReviewed-By: none\n# comment\n").replace("\n", "\r\n")
        self.assertEqual(check_commit_msg.problems(message), [])


if __name__ == "__main__":
    unittest.main()
