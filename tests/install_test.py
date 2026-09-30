"""Link ownership rules of scripts/install.py."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import install  # noqa: E402

REPO = Path(os.path.realpath(Path(__file__).resolve().parent.parent))


@unittest.skipIf(install.WINDOWS, "테스트 헬퍼가 디렉터리 링크를 symbolic link로 만들지만 Windows 설치기는 junction을 쓴다")
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
        install.remove_retired_links(REPO, self.home)
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

    def test_retired_directory_link_is_removed_but_user_directory_kept(self):
        path = self.home / ".claude/agents"
        path.parent.mkdir(parents=True)
        os.symlink(REPO / "claude/agents", path, target_is_directory=True)
        self.install()
        self.assertFalse(os.path.lexists(path))
        path.mkdir()
        self.install()
        self.assertTrue(path.is_dir())

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
    """Runs the Windows branch on Linux with directory links standing in for junctions, so previous-source replacement
    and verification are exercised by every commit."""

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
        state = self.home / ".codex/agent-harness-install-state.json"
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({"version": 1, "files": {}}))
        for _ in range(2):
            install.install_links(REPO, self.home)
            install.verify(REPO, self.home)
        self.assertTrue(install.points_to(previous, REPO / "claude/self-diagnosis.md"))
        self.assertFalse(os.path.lexists(state))


class HardLinkMigrationTest(unittest.TestCase):
    """Hard links left by the earlier Windows fallback become symbolic links, and nothing else is taken over."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(os.path.realpath(self.tmp.name))
        self.repo, self.home = root / "repo", root / "home"
        self.repo.mkdir()
        self.source = self.repo / "rule.md"
        self.source.write_text("original")
        self.link = install.Link("rule.md", ".claude/rule.md")
        self.destination = self.home / self.link.destination
        self.destination.parent.mkdir(parents=True)
        self.state = self.home / ".claude/agent-harness-install-state.json"

    def record(self, source=None):
        info = os.lstat(self.destination)
        entry = {"source": install.state_key(source or self.source),
                 "identity": {"volume": str(info.st_dev), "file": str(info.st_ino)}}
        self.state.write_text(json.dumps({"version": 1, "files": {install.state_key(self.destination): entry}}))

    def move_to_generated_source(self):
        generated = self.repo / "generated.md"
        generated.write_text("generated")
        self.link = install.Link("generated.md", ".claude/rule.md", "rule.md")
        return generated

    def install(self):
        install.install_link(self.repo, self.home, self.link, install.load_install_state(self.home))

    def test_current_hard_link_becomes_symbolic_link(self):
        os.link(self.source, self.destination)
        self.install()
        self.assertTrue(install.points_to(self.destination, self.source))

    def test_recorded_stale_hard_link_becomes_symbolic_link(self):
        os.link(self.source, self.destination)
        self.record()
        replacement = self.repo / "replacement"
        replacement.write_text("updated")
        os.replace(replacement, self.source)
        self.install()
        self.assertTrue(install.points_to(self.destination, self.source))
        self.assertEqual(self.destination.read_text(), "updated")

    def test_file_replaced_by_user_is_preserved(self):
        os.link(self.source, self.destination)
        self.record()
        replacement = self.home / "mine"
        replacement.write_text("private")
        os.replace(replacement, self.destination)
        with self.assertRaises(install.InstallError):
            self.install()
        self.assertEqual(self.destination.read_text(), "private")

    def test_hard_link_recorded_for_previous_source_moves_to_new_source(self):
        os.link(self.source, self.destination)
        self.record()
        replacement = self.repo / "replacement"
        replacement.write_text("updated")
        os.replace(replacement, self.source)
        generated = self.move_to_generated_source()
        self.install()
        self.assertTrue(install.points_to(self.destination, generated))

    def test_previous_source_does_not_adopt_user_file(self):
        self.destination.write_text("private")
        self.move_to_generated_source()
        with self.assertRaises(install.InstallError):
            self.install()
        self.assertEqual(self.destination.read_text(), "private")

    def test_same_content_is_not_ownership(self):
        self.destination.write_text("original")
        with self.assertRaises(install.InstallError):
            self.install()
        self.assertFalse(self.destination.is_symlink())

    def test_missing_symlink_permission_keeps_hard_link(self):
        os.link(self.source, self.destination)
        denied = OSError("symbolic links unavailable")
        denied.winerror = 1314
        with patch.object(install.os, "symlink", side_effect=denied):
            with self.assertRaisesRegex(install.InstallError, "개발자 모드"):
                self.install()
        self.assertTrue(os.path.samefile(self.destination, self.source))
        self.assertEqual(sorted(path.name for path in self.destination.parent.iterdir()), ["rule.md"])

    def test_unrelated_file_beside_destination_is_untouched(self):
        other = self.destination.with_name(".rule.md.agent-harness-link")
        other.write_text("mine")
        self.install()
        self.assertEqual(other.read_text(), "mine")

    def test_corrupt_state_stops(self):
        self.state.write_text("{broken")
        with self.assertRaises(install.InstallError):
            install.load_install_state(self.home)

    def test_windows_namespace_prefix_is_ignored(self):
        with patch.object(install.os, "readlink", return_value="\\\\?\\" + str(self.source)):
            self.assertEqual(install.link_target(self.destination), self.source)


if __name__ == "__main__":
    unittest.main()
