"""Reversible, owned-file installation and non-destructive hook merging."""

import copy
import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from .adapters import load_adapter, validate_mode
from .config import is_linked, read_json, validate_preferences, write_json

SKILL_ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_skill_files(root=SKILL_ROOT):
    files = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError('Skill distributions cannot contain symbolic links')
        if not path.is_file():
            continue
        if relative.parts[0] not in ('SKILL.md', 'agents', 'assets', 'references', 'scripts'):
            continue
        if path.suffix not in ('.md', '.py', '.json', '.yaml'):
            raise ValueError('Unexpected file in the skill distribution')
        files.append(path)
    return files


def _command(arguments):
    return subprocess.list2cmdline(arguments) if sys.platform == 'win32' else shlex.join(arguments)


def hook_entries(adapter, entry, data):
    command = _command([sys.executable, str(entry), 'hook', '--host', adapter['id'], '--data-dir', str(data)])
    def group(matcher=None):
        item = {'hooks': [{'type': 'command', 'command': command, 'timeout': 5}]}
        if matcher:
            item['matcher'] = matcher
        return item
    return {'SessionStart': [group('^(startup|fork)$')],
            'UserPromptSubmit': [group()],
            'PostToolUse': [group()]}


def remove_owned(settings, owned):
    result = copy.deepcopy(settings)
    hooks = result.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('Host hooks must be an object')
    for event, entries in owned.items():
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            raise ValueError('Host hook groups must be arrays')
        for original in entries:
            original_metadata = {key: value for key, value in original.items() if key != 'hooks'}
            kept = []
            for group in groups:
                metadata = {key: value for key, value in group.items() if key != 'hooks'}
                if metadata == original_metadata:
                    group = copy.deepcopy(group)
                    group['hooks'] = [handler for handler in group.get('hooks', []) if handler not in original['hooks']]
                    if not group['hooks']:
                        continue
                kept.append(group)
            groups = kept
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    return result


def _settings(path):
    value = read_json(path) if path.exists() else {}
    if not isinstance(value, dict) or not isinstance(value.get('hooks', {}), dict):
        raise ValueError('Host configuration must contain an object of hooks')
    for groups in value.get('hooks', {}).values():
        if not isinstance(groups, list) or any(not isinstance(group, dict) or not isinstance(group.get('hooks'), list) for group in groups):
            raise ValueError('Invalid existing hook groups')
    return value


def install(host, host_root, data, preferences, mode='automatic', descriptor=None, skills_dir=None, in_place=False):
    host_root, data = Path(host_root).resolve(), Path(data).resolve()
    adapter = load_adapter(host, descriptor)
    validate_mode(adapter, mode)
    state_dir = data / 'hosts' / host
    manifest_path = state_dir / 'install.json'
    for path in (data / 'preferences.json', manifest_path, state_dir / 'adapter.json', state_dir / 'settings-before.json'):
        if is_linked(path):
            raise ValueError('Private installation files cannot be symbolic links')
    previous = read_json(manifest_path) if manifest_path.exists() else None
    if in_place and skills_dir:
        raise ValueError('Choose either in-place configuration or an installation directory')
    destination = SKILL_ROOT if in_place else (Path(skills_dir).resolve() if skills_dir else host_root / 'skills') / 'autoname'
    settings_path = host_root / adapter['settings_file']
    if settings_path.resolve().is_relative_to(destination.resolve()) or data.is_relative_to(destination.resolve()):
        raise ValueError('Host settings and private state must be outside the distributed skill directory')
    needs_settings = mode == 'automatic' or bool(previous and previous['owned_hooks'])
    if (needs_settings and is_linked(settings_path)) or is_linked(destination):
        raise ValueError('Refusing to replace a symbolic host configuration')
    settings = _settings(settings_path) if needs_settings else {}
    if previous:
        if previous['skill_dir'] != str(destination) or previous['settings_path'] != str(settings_path):
            raise ValueError('Uninstall the existing registration before changing its locations')
        settings = remove_owned(settings, previous['owned_hooks'])
    preferences_path = data / 'preferences.json'
    preferences = validate_preferences(read_json(preferences_path) if preferences_path.exists() else preferences)
    preferences = copy.deepcopy(preferences)
    if not preferences_path.exists():
        preferences['enabled'] = mode == 'automatic'
    sources = public_skill_files()
    hashes = {}
    for source in sources:
        relative = source.relative_to(SKILL_ROOT)
        target = destination / relative
        if is_linked(target):
            raise ValueError('Refusing to replace a symbolic skill file')
        if target.exists() and source.resolve() != target.resolve():
            prior_hash = (previous or {}).get('owned_files', {}).get(str(relative))
            if prior_hash is None or digest(target) != prior_hash:
                raise ValueError('An unowned or modified skill file would be overwritten')
        hashes[str(relative)] = digest(source)
    if destination.resolve() == SKILL_ROOT.resolve():
        # File-only imports are preexisting user files; registration does not take ownership.
        hashes = (previous or {}).get('owned_files', {})
    owned = hook_entries(adapter, destination / 'scripts/autoname.py', data) if mode == 'automatic' else {}
    if owned:
        hooks = settings.setdefault('hooks', {})
        for event, groups in owned.items():
            hooks.setdefault(event, []).extend(groups)
    status = 'configured_pending_host_check' if mode != 'suggestion' else 'suggestion_ready'
    manifest = {'schema_version': 1, 'host': host, 'mode': mode, 'status': 'installing',
                'settings_path': str(settings_path), 'skill_dir': str(destination),
                'owned_hooks': owned, 'owned_files': hashes}
    # Record ownership first so an interrupted copy remains removable.
    write_json(manifest_path, manifest)
    # All inputs and ownership checks finish before the first host-file write.
    for source in sources:
        target = destination / source.relative_to(SKILL_ROOT)
        if target.resolve() != source.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    if needs_settings:
        if settings_path.exists():
            write_json(state_dir / 'settings-before.json', read_json(settings_path))
        write_json(settings_path, settings)
    write_json(preferences_path, preferences)
    write_json(state_dir / 'adapter.json', adapter)
    manifest['status'] = status
    write_json(manifest_path, manifest)
    return {'status': status, 'mode': mode, 'host': host, 'automatic_requested': preferences['enabled'],
            'next': 'Reload the host and check its hook trust settings; confirm naming in a new chat.' if owned else 'Invoke AutoName in the selected mode.'}


def uninstall(host, data):
    state_dir = Path(data) / 'hosts' / host
    manifest_path = state_dir / 'install.json'
    if not manifest_path.is_file():
        return {'status': 'not_installed', 'host': host}
    manifest = read_json(manifest_path)
    settings_path = Path(manifest['settings_path'])
    if settings_path.exists() and manifest['owned_hooks']:
        write_json(settings_path, remove_owned(_settings(settings_path), manifest['owned_hooks']))
    destination = Path(manifest['skill_dir'])
    retained = 0
    for relative, original_hash in manifest['owned_files'].items():
        target = destination / relative
        if is_linked(target) or (target.exists() and digest(target) != original_hash):
            retained += 1
        elif target.is_file():
            target.unlink()
    if destination.is_dir() and not is_linked(destination):
        for directory in sorted((p for p in destination.rglob('*') if p.is_dir() and not is_linked(p)), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            destination.rmdir()
        except OSError:
            pass
    manifest['status'] = 'uninstalled'
    manifest['owned_hooks'] = {}
    write_json(manifest_path, manifest)
    return {'status': 'uninstalled', 'preferences_retained': True, 'modified_files_retained': retained}


def installation_status(host, data):
    manifest_path = Path(data) / 'hosts' / host / 'install.json'
    if not manifest_path.is_file():
        return {'host': host, 'status': 'not_installed', 'preferences_saved': (Path(data) / 'preferences.json').is_file()}
    manifest = read_json(manifest_path)
    if manifest['status'] == 'uninstalled':
        return {'host': host, 'status': 'uninstalled', 'mode': manifest['mode']}
    preferences = validate_preferences(read_json(Path(data) / 'preferences.json'))
    healthy = (Path(manifest['skill_dir']) / 'scripts/autoname.py').is_file()
    try:
        validate_mode(load_adapter(host, Path(data) / 'hosts' / host / 'adapter.json'), manifest['mode'])
        settings = _settings(Path(manifest['settings_path'])) if manifest['owned_hooks'] else {}
        for event, entries in manifest['owned_hooks'].items():
            for original in entries:
                metadata = {key: value for key, value in original.items() if key != 'hooks'}
                healthy = healthy and any(
                    {key: value for key, value in group.items() if key != 'hooks'} == metadata and
                    all(handler in group['hooks'] for handler in original['hooks'])
                    for group in settings.get('hooks', {}).get(event, []))
    except (ValueError, OSError):
        healthy = False
    return {'host': host, 'status': manifest['status'] if healthy else 'incomplete',
            'mode': manifest['mode'], 'preferences_saved': True,
            'automatic_requested': preferences['enabled'], 'registration_intact': bool(healthy),
            'live_result_confirmed': bool(healthy and manifest['status'] == 'verified')}
