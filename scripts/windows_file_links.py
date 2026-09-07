"""Install/verify Windows file links using recorded filesystem identity."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


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
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def linked(destination, source):
    if destination.is_symlink():
        return key(os.path.join(destination.parent, os.readlink(destination))) == key(source)
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
        owned = (exists and entry is not None and entry['source'] == key(source)
                 and entry['identity'] == identity(destination)
                 and stat.S_ISREG(os.lstat(destination).st_mode))
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
        data['files'][key(destination)] = {'source': key(source), 'identity': identity(destination)}
        save(state_path, data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    try:
        run(json.loads(args.request.read_text(encoding='utf-8')), args.verify)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
