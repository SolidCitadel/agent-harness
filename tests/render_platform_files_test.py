"""Rendering checks for platform slots in shared sources."""

import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "platform_files", Path(__file__).parents[1] / "scripts/render_platform_files.py"
)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


VALUES = renderer.parse_values(
    """"경로" = '''`~/.codex/rule.md`'''

"절차" = '''
플랫폼 절차.
'''

"절" = '''
## 플랫폼 전용 절

### 하위 절

첫 문단.

두 번째 문단.
'''

"빈 값" = ''
""",
    Path("platform-text.toml"),
)


class RenderPlatformFilesTest(unittest.TestCase):
    def render(self, text):
        return renderer.rendered(text, VALUES, Path("source.md"), set())

    def test_inline_slot_is_filled(self):
        self.assertEqual(self.render("{{platform:경로}}를 읽는다.\n"), "`~/.codex/rule.md`를 읽는다.\n")

    def test_block_slot_keeps_paragraph_spacing(self):
        self.assertEqual(self.render("앞.\n\n{{platform:절차}}\n\n뒤.\n"), "앞.\n\n플랫폼 절차.\n\n뒤.\n")

    def test_block_value_keeps_headings_and_paragraphs(self):
        self.assertEqual(
            self.render("## 공통\n\n본문.\n\n{{platform:절}}\n\n## 다음\n"),
            "## 공통\n\n본문.\n\n## 플랫폼 전용 절\n\n### 하위 절\n\n첫 문단.\n\n두 번째 문단.\n\n## 다음\n",
        )

    def test_empty_block_slot_removes_line_and_one_blank(self):
        self.assertEqual(self.render("앞.\n\n{{platform:빈 값}}\n\n뒤.\n"), "앞.\n\n뒤.\n")

    def test_empty_frontmatter_slot_removes_line(self):
        self.assertEqual(self.render("---\nname: x\n{{platform:빈 값}}\n---\n"), "---\nname: x\n---\n")

    def test_unknown_slot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "알 수 없는 플랫폼 문구"):
            self.render("{{platform:없음}}\n")

    def test_duplicate_value_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "TOML 형식 오류"):
            renderer.parse_values('"이름" = "가"\n"이름" = "나"\n', Path("platform-text.toml"))

    def test_slot_left_inside_value_is_rejected(self):
        values = renderer.parse_values('"값" = "{{platform:없음}}"\n', Path("platform-text.toml"))
        with self.assertRaisesRegex(ValueError, "빈칸이 남았습니다"):
            renderer.rendered("{{platform:값}}\n", values, Path("source.md"), set())

    def test_non_string_value_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "문자열"):
            renderer.parse_values('"이름" = 1\n', Path("platform-text.toml"))


if __name__ == "__main__":
    unittest.main()
