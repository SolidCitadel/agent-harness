"""Link ownership rules of scripts/install.py on symbolic-link platforms."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import install  # noqa: E402

REPO = Path(os.path.realpath(Path(__file__).resolve().parent.parent))


@unittest.skipIf(install.WINDOWS, "Windows는 junction·hard link 분기를 쓴다")
class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        # 저장소 git 설정 검사는 설치기 흐름의 일부라 여기서는 링크 규칙만 본다.
        patcher = patch.object(install, "is_repository_root", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def install(self):
        install.install_links(REPO, self.home)
        install.remove_renamed(REPO, self.home)
        install.remove_old_skills(REPO, self.home)
        install.verify(REPO, self.home)

    def link(self, destination, source):
        path = self.home / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(REPO / source, path)
        return path

    def test_fresh_install_verifies_and_repeats(self):
        self.install()
        self.install()

    def test_unmanaged_path_is_preserved(self):
        path = self.home / ".claude/CLAUDE.md"
        path.parent.mkdir(parents=True)
        path.write_text("mine")
        with self.assertRaises(install.InstallError):
            install.install_links(REPO, self.home)
        self.assertEqual(path.read_text(), "mine")

    def test_link_to_previous_source_is_replaced(self):
        self.link(".claude/self-diagnosis.md", "shared/self-diagnosis.md")
        self.link(".claude/skills/refine-harness", "shared/skills/refine-harness")
        self.install()
        self.assertTrue(install.points_to(self.home / ".claude/self-diagnosis.md", REPO / "claude/self-diagnosis.md"))

    def test_renamed_and_removed_links_are_cleaned(self):
        self.link(".claude/meta-doc-critic.md", "shared/meta-doc-critic.md")
        self.link(".agents/skills/self-improve", "codex/skills/self-improve")
        self.install()
        self.assertFalse(os.path.lexists(self.home / ".claude/meta-doc-critic.md"))
        self.assertFalse(os.path.lexists(self.home / ".agents/skills/self-improve"))

    def test_unmanaged_old_skill_directory_is_preserved(self):
        path = self.home / ".claude/skills/self-improve"
        path.mkdir(parents=True)
        with self.assertRaises(install.InstallError):
            self.install()
        self.assertTrue(path.is_dir())

    def test_user_alias_through_managed_link_is_preserved(self):
        self.install()
        alias = self.home / ".claude/meta-doc-critic.md"
        os.symlink(self.home / ".claude/harness-review.md", alias)
        with self.assertRaises(install.InstallError):
            install.remove_renamed(REPO, self.home)
        self.assertTrue(os.path.lexists(alias))

    def test_hard_link_of_new_source_at_renamed_path_is_cleaned(self):
        self.install()
        renamed = self.home / ".claude/meta-doc-critic.md"
        os.link(REPO / "shared/harness-review.md", renamed)
        install.remove_renamed(REPO, self.home)
        self.assertFalse(os.path.lexists(renamed))

    def test_verify_rejects_wrong_target(self):
        self.install()
        path = self.home / ".codex/AGENTS.md"
        path.unlink()
        os.symlink(REPO / "claude/CLAUDE.md", path)
        with self.assertRaises(install.InstallError):
            install.verify(REPO, self.home)


@unittest.skipIf(install.WINDOWS, "실제 Windows에서는 모의 없이 설치 시뮬레이션이 이 분기를 실행한다")
class WindowsBranchWiringTest(unittest.TestCase):
    """Runs the Windows branch on Linux with directory links standing in for junctions, so the request built for
    the file-link module, previous-source replacement and verification are exercised by every commit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        patches = [patch.object(install, "WINDOWS", True),
                   patch.object(install, "is_repository_root", return_value=False),
                   patch.object(install, "create_junction", side_effect=lambda source, destination: os.symlink(source, destination))]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_install_replace_previous_and_verify(self):
        previous = self.home / ".claude/self-diagnosis.md"
        previous.parent.mkdir(parents=True)
        os.symlink(REPO / "shared/self-diagnosis.md", previous)
        for _ in range(2):
            install.install_links(REPO, self.home)
            install.verify(REPO, self.home)
        self.assertTrue(install.points_to(previous, REPO / "claude/self-diagnosis.md"))
        self.assertTrue((self.home / ".claude/agent-harness-install-state.json").is_file())


if __name__ == "__main__":
    unittest.main()
