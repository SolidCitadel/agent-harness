"""Filesystem regressions for Windows installation ownership and refresh."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('links', Path(__file__).parents[1] / 'scripts/windows_file_links.py')
links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(links)


class FileLinksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.home = self.root / 'home'
        self.repo.mkdir()
        for platform in ['.codex', '.claude']:
            (self.home / platform).mkdir(parents=True)
        self.source = self.repo / 'rule.md'
        self.source.write_text('original')
        self.destination = self.home / '.codex/rule.md'
        self.state = self.home / '.codex/agent-harness-install-state.json'
        self.request = {'repo': str(self.repo), 'home': str(self.home), 'links': [{'S': 'rule.md', 'D': str(self.destination)}]}
        denied = OSError('symbolic links unavailable')
        denied.winerror = 1314
        self.symlink_patch = patch.object(links.os, 'symlink', side_effect=denied)
        self.symlink_patch.start()
        self.addCleanup(self.symlink_patch.stop)

    def test_windows_namespace_prefix_is_ignored(self):
        with patch.object(links.os, 'readlink', return_value='\\\\?\\' + str(self.source)):
            self.assertEqual(links.link_target(self.destination), self.source)

    def test_refresh_after_source_replacement(self):
        links.run(self.request)
        old_id = links.identity(self.destination)
        replacement = self.repo / 'replacement'
        replacement.write_text('updated')
        os.replace(replacement, self.source)
        self.assertEqual(self.destination.read_text(), 'original')
        links.run(self.request)
        self.assertEqual(self.destination.read_text(), 'updated')
        self.assertNotEqual(links.identity(self.destination), old_id)
        links.run(self.request, verify=True)
        links.run(self.request)

    def test_user_replacement_preserved(self):
        links.run(self.request)
        replacement = self.root / 'user-file'
        replacement.write_text('private')
        os.replace(replacement, self.destination)
        with self.assertRaises(ValueError):
            links.run(self.request)
        self.assertEqual(self.destination.read_text(), 'private')

    def test_unregistered_existing_link_is_adopted(self):
        os.link(self.source, self.destination)
        links.run(self.request)
        links.run(self.request, verify=True)

    def test_unregistered_stale_link_is_preserved(self):
        os.link(self.source, self.destination)
        replacement = self.repo / 'replacement'
        replacement.write_text('updated')
        os.replace(replacement, self.source)
        with self.assertRaises(ValueError):
            links.run(self.request)
        self.assertEqual(self.destination.read_text(), 'original')

    def test_corrupt_state_stops_before_mutation(self):
        self.state.write_text('{broken')
        with self.assertRaises(ValueError):
            links.run(self.request)
        self.assertFalse(self.destination.exists())

    def test_state_save_failure_is_not_success_and_can_retry(self):
        with patch.object(links, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                links.run(self.request)
        self.assertFalse(self.state.exists())
        links.run(self.request)
        links.run(self.request, verify=True)

    def test_same_content_is_not_ownership(self):
        self.destination.write_bytes(self.source.read_bytes())
        with self.assertRaises(ValueError):
            links.run(self.request)
        self.assertFalse(self.state.exists())

    def test_unchanged_install_does_not_replace_state(self):
        links.run(self.request)
        with patch.object(links, 'save', side_effect=AssertionError('unnecessary state replacement')):
            links.run(self.request)
        links.run(self.request, verify=True)

    def test_state_replacement_retries_temporary_windows_denial(self):
        denied = PermissionError('file temporarily locked')
        denied.winerror = 5
        replace = os.replace
        attempts = []

        def replace_after_unlock(source, destination):
            attempts.append(destination)
            if len(attempts) == 1:
                raise denied
            replace(source, destination)

        with patch.object(links.os, 'replace', side_effect=replace_after_unlock), \
                patch.object(links.time, 'sleep') as sleep:
            links.save(self.state, {'version': 1, 'files': {}})
        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(0.05)
        self.assertEqual(links.load(self.state), {'version': 1, 'files': {}})

    def test_persistent_denial_preserves_state_and_cleans_temporary_file(self):
        links.run(self.request)
        original = self.state.read_bytes()
        denied = PermissionError('file locked')
        denied.winerror = 5
        with patch.object(links.os, 'replace', side_effect=denied) as replace, \
                patch.object(links.time, 'sleep'):
            with self.assertRaises(PermissionError):
                links.save(self.state, {'version': 1, 'files': {}})
        self.assertEqual(replace.call_count, 6)
        self.assertEqual(self.state.read_bytes(), original)
        self.assertEqual(list(self.state.parent.glob(self.state.name + '.*')), [])

    def test_other_save_errors_are_not_retried(self):
        with patch.object(links.os, 'replace', side_effect=OSError('disk failure')) as replace, \
                patch.object(links.time, 'sleep') as sleep:
            with self.assertRaises(OSError):
                links.save(self.state, {'version': 1, 'files': {}})
        replace.assert_called_once()
        sleep.assert_not_called()


    def moved_request(self):
        generated = self.repo / 'generated.md'
        generated.write_text('generated')
        return {**self.request, 'links': [{'S': 'generated.md', 'D': str(self.destination), 'O': 'rule.md'}]}

    def test_link_recorded_for_previous_source_moves_to_new_source(self):
        links.run(self.request)
        request = self.moved_request()
        links.run(request)
        self.assertEqual(self.destination.read_text(), 'generated')
        links.run(request, verify=True)

    def test_previous_source_does_not_adopt_user_file(self):
        self.destination.write_text('private')
        with self.assertRaises(ValueError):
            links.run(self.moved_request())
        self.assertEqual(self.destination.read_text(), 'private')

    def test_symbolic_link_to_previous_source_moves_to_new_source(self):
        self.symlink_patch.stop()
        try:
            self.destination.symlink_to(self.source)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows process cannot create a symbolic link')
            raise
        self.symlink_patch.start()  # 새 링크는 권한 부족으로 hard link로 대체한다.
        request = self.moved_request()
        links.run(request)
        self.assertTrue(links.linked(self.destination, self.repo / 'generated.md'))
        links.run(request, verify=True)


if __name__ == '__main__':
    unittest.main()
