"""Windows file links for scripts/install.py: symbolic links, or hard links recorded by filesystem identity."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time


def identity(path):
    value = os.lstat(path)
    return {'volume': str(value.st_dev), 'file': str(value.st_ino)}


def key(path):
    return os.path.normcase(os.path.abspath(path))


def load(path):
    if not os.path.lexists(path):
        return {'version': 1, 'files': {}}
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Invalid state path: {path}')
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data) != {'version', 'files'} or data['version'] != 1 or not isinstance(data['files'], dict):
        raise ValueError(f'Invalid state schema: {path}')
    for destination, entry in data['files'].items():
        if (not os.path.isabs(destination) or not isinstance(entry, dict)
            or set(entry) != {'source', 'identity'} or not isinstance(entry['source'], str)
            or not os.path.isabs(entry['source']) or not isinstance(entry['identity'], dict)
            or set(entry['identity']) != {'volume', 'file'}
            or not all(isinstance(v, str) and v.isdecimal() for v in entry['identity'].values())):
            raise ValueError(f'Invalid state entry: {path}')
    return data


def save(path, data):
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        # Windows readers and scanners can briefly prevent replacing a closed file.
        # Keep the old state intact and retry only the replacement, for at most 1.55s.
        delays = (0.05, 0.1, 0.2, 0.4, 0.8)
        for attempt in range(len(delays) + 1):
            try:
                os.replace(temporary, path)
                break
            except OSError as error:
                if getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == len(delays):
                    raise
                time.sleep(delays[attempt])
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def link_target(path):
    """Where a symbolic link or junction points, one level only. Windows reports targets with the \\\\?\\ or \\??\\
    namespace prefix, which is dropped so the target compares with ordinary paths."""
    target = os.readlink(path)
    for prefix, replacement in (('\\\\?\\UNC\\', '\\\\'), ('\\??\\UNC\\', '\\\\'), ('\\\\?\\', ''), ('\\??\\', '')):
        if target.startswith(prefix):
            target = replacement + target[len(prefix):]
            break
    return Path(os.path.normpath(os.path.join(path.parent, target)))


def linked(destination, source):
    if destination.is_symlink():
        return key(link_target(destination)) == key(source)
    return destination.is_file() and source.is_file() and os.path.samefile(destination, source)


def run(request, verify=False):
    repo, home = Path(request['repo']), Path(request['home'])
    states = {}
    # Validate both state files before any destination mutation.
    for platform in ['.claude', '.codex']:
        path = home / platform / 'agent-harness-install-state.json'
        states[platform] = (path, load(path))
    prepared = []
    for item in request['links']:
        source = Path(os.path.abspath(repo / item['S']))
        destination = Path(os.path.abspath(item['D']))
        relative = destination.relative_to(home)
        if relative.parts[0] not in states or not source.is_file():
            raise ValueError(f'Invalid managed path: {destination}')
        state_path, data = states[relative.parts[0]]
        entry = data['files'].get(key(destination))
        exists = os.path.lexists(destination)
        current = linked(destination, source)
        # A link recorded for, or pointing at, the previous source 'O' stays managed when that source changes.
        sources = [source] + ([Path(os.path.abspath(repo / item['O']))] if item.get('O') else [])
        owned = exists and (
            (entry is not None and entry['source'] in [key(path) for path in sources]
             and entry['identity'] == identity(destination) and stat.S_ISREG(os.lstat(destination).st_mode))
            or (os.path.islink(destination) and any(linked(destination, path) for path in sources[1:])))
        if verify:
            if not (current and entry and entry['source'] == key(source)
                    and entry['identity'] == identity(destination)):
                raise ValueError(f'Link/state mismatch: {destination}')
        elif exists and not current and not owned:
            raise ValueError(f'Unmanaged path preserved: {destination}')
        prepared.append((source, destination, current, state_path, data))
    if verify:
        return
    for source, destination, current, state_path, data in prepared:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not current:
            fd, temporary = tempfile.mkstemp(prefix=destination.name + '.', dir=destination.parent)
            os.close(fd)
            os.unlink(temporary)
            try:
                try:
                    os.symlink(source, temporary)
                except OSError as error:
                    if getattr(error, 'winerror', None) != 1314:
                        raise
                    os.link(source, temporary)
                os.replace(temporary, destination)
            finally:
                if os.path.lexists(temporary):
                    os.unlink(temporary)
        if not linked(destination, source):
            raise ValueError(f'New link verification failed: {destination}')
        entry = {'source': key(source), 'identity': identity(destination)}
        if data['files'].get(key(destination)) != entry:
            data['files'][key(destination)] = entry
            save(state_path, data)

