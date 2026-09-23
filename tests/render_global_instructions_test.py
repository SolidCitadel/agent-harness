"""Rendering checks for shared subsections placed after platform instructions."""

import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "global_instructions", Path(__file__).parents[1] / "scripts/render_global_instructions.py"
)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


SOURCE = """# 공통 전역 지침

## 수행

공통 수행 본문.

### 서브에이전트

공통 위임 기준.

## 변경

공통 변경 본문.
"""


class RenderGlobalInstructionsTest(unittest.TestCase):
    def test_platform_text_precedes_shared_subsection(self):
        sections = renderer.parse_sections(SOURCE)
        template = """# 전역 지침

{{shared:수행}}

플랫폼 수행 절차.

{{shared:수행/서브에이전트}}

플랫폼 모델 선택.

{{shared:변경}}
"""

        result = renderer.rendered(template, sections, Path("template.md"))

        self.assertIn("## 수행\n\n공통 수행 본문.\n\n플랫폼 수행 절차.\n\n### 서브에이전트", result)
        self.assertIn("### 서브에이전트\n\n공통 위임 기준.\n\n플랫폼 모델 선택.\n\n## 변경", result)
        self.assertEqual(result.count("공통 위임 기준."), 1)

    def test_subsection_outside_parent_is_rejected(self):
        sections = renderer.parse_sections(SOURCE)
        template = "{{shared:수행}}\n\n{{shared:변경}}\n\n{{shared:수행/서브에이전트}}"

        with self.assertRaisesRegex(ValueError, "부모 섹션 밖"):
            renderer.rendered(template, sections, Path("template.md"))


if __name__ == "__main__":
    unittest.main()
