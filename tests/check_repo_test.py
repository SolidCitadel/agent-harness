from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_repo  # noqa: E402


class FrontmatterTest(unittest.TestCase):
    def test_reads_top_level_fields(self):
        fields = check_repo.frontmatter("---\nname: a\ndescription: b c\npaths:\n  - \"**/x\"\n---\nbody\n")
        self.assertEqual(fields, {"name": "a", "description": "b c", "paths": ""})

    def test_crlf_is_accepted(self):
        self.assertEqual(check_repo.frontmatter("---\r\nname: a\r\n---\r\n"), {"name": "a"})

    def test_quoted_values_read_as_text(self):
        fields = check_repo.frontmatter("---\nname: \"a\"\ndescription: 'b'\n---\n")
        self.assertEqual((check_repo.text_value(fields["name"]), check_repo.text_value(fields["description"])), ("a", "b"))

    def test_inline_comment_and_continuation_lines(self):
        fields = check_repo.frontmatter("---\nname: a  # note\ndescription: >\n  first\n  second\nflag: True\n---\n")
        self.assertEqual(fields["name"], "a")
        self.assertEqual(fields["description"], "first second")
        self.assertTrue(check_repo.true_value(fields["flag"]))

    def test_quoted_true_is_not_boolean(self):
        self.assertFalse(check_repo.true_value('"true"'))

    def test_missing_or_unclosed_block_is_none(self):
        self.assertIsNone(check_repo.frontmatter("# title\n"))
        self.assertIsNone(check_repo.frontmatter("---\nname: a\n"))


class ArchitectureTest(unittest.TestCase):
    def check(self, table: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "shared").mkdir()
            (root / "shared/self-harness-architecture.md").write_text(table, encoding="utf-8")
            return check_repo.check_architecture(root)

    def test_platform_relative_and_full_paths_count(self):
        names = {Path(*output.parts[1:]).as_posix() for output in check_repo.generated_outputs()}
        table = "| " + ", ".join(f"`{name}`" for name in names) + " | 생성물 |"
        self.assertEqual(self.check(table), [])

    def test_mention_outside_table_does_not_count(self):
        names = {Path(*output.parts[1:]).as_posix() for output in check_repo.generated_outputs()}
        errors = self.check("본문 " + ", ".join(f"`{name}`" for name in names))
        self.assertIn("shared/self-harness-architecture.md 표에 생성물이 없습니다: claude/CLAUDE.md", errors)

    def test_shared_source_row_does_not_cover_output(self):
        errors = self.check("| `shared/harness-components.md` | 원본 |")
        self.assertIn("shared/self-harness-architecture.md 표에 생성물이 없습니다: claude/harness-components.md", errors)


if __name__ == "__main__":
    unittest.main()
