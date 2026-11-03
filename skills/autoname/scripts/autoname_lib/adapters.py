"""Capability-based host descriptors and supported local title writers."""

import importlib
from pathlib import Path
import re
import subprocess
import json

from .config import read_json

BUILTINS = {
    'codex': {'id': 'codex', 'hook_style': 'codex', 'settings_file': 'hooks.json',
              'rename': {'kind': 'native-tool', 'tool': 'set_thread_title'}},
    'claude-code': {'id': 'claude-code', 'hook_style': 'claude', 'settings_file': 'settings.json',
                    'rename': {'kind': 'claude-sdk'}},
}


def validate_adapter(value):
    if not isinstance(value, dict) or set(value) - {'id', 'hook_style', 'settings_file', 'rename', 'max_title_chars'}:
        raise ValueError('Invalid adapter fields')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', str(value.get('id', ''))):
        raise ValueError('Invalid adapter identifier')
    if value.get('hook_style') not in ('codex', 'claude', 'none'):
        raise ValueError('Unsupported hook schema; use none until a schema adapter is implemented')
    path = value.get('settings_file', '')
    if not isinstance(path, str) or not path or Path(path).is_absolute() or '..' in Path(path).parts or '\\' in path:
        raise ValueError('settings_file must be a relative path inside the selected host root')
    rename = value.get('rename')
    if not isinstance(rename, dict) or rename.get('kind') not in ('native-tool', 'claude-sdk', 'command', 'suggestion'):
        raise ValueError('Invalid title writer')
    if rename['kind'] == 'native-tool' and not re.fullmatch(r'[A-Za-z0-9_.-]+', str(rename.get('tool', ''))):
        raise ValueError('Invalid native tool name')
    if rename['kind'] == 'command':
        command = rename.get('command')
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item or '\0' in item for item in command):
            raise ValueError('The bridge command must be a nonempty argument array')
    limit = value.get('max_title_chars')
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('Invalid host title limit')
    return value


def load_adapter(host, descriptor=None):
    value = read_json(descriptor) if descriptor else BUILTINS.get(host)
    if value is None:
        raise ValueError('Unknown agent: supply an explicit adapter descriptor')
    value = validate_adapter(value)
    if value['id'] != host:
        raise ValueError('Adapter identifier does not match --host')
    return value


def writer_available(adapter):
    kind = adapter['rename']['kind']
    if kind == 'suggestion':
        return False
    if kind == 'claude-sdk':
        try:
            sdk = importlib.import_module('claude_agent_sdk')
            return callable(getattr(sdk, 'rename_session', None)) and callable(getattr(sdk, 'get_session_info', None))
        except ImportError:
            return False
    return True


def validate_mode(adapter, mode):
    if mode not in ('automatic', 'on-demand', 'suggestion'):
        raise ValueError('Invalid execution mode')
    if mode != 'suggestion' and not writer_available(adapter):
        raise ValueError('A title writer is unavailable; install the optional SDK or explicitly choose suggestion mode')
    if mode == 'automatic' and adapter['hook_style'] == 'none':
        raise ValueError('Automatic mode needs a supported native trigger; choose a limited mode explicitly')


def write_title(adapter, session_id, title, directory):
    """Confirm a local supported writer; never start an extra model request."""
    kind = adapter['rename']['kind']
    if kind == 'claude-sdk':
        sdk = importlib.import_module('claude_agent_sdk')
        before = sdk.get_session_info(session_id, directory=directory)
        if before is None:
            raise ValueError('The current session was not found')
        if getattr(before, 'custom_title', None):
            raise ValueError('An existing custom title must be preserved')
        sdk.rename_session(session_id, title, directory=directory)
        after = sdk.get_session_info(session_id, directory=directory)
        if after is None or getattr(after, 'custom_title', None) != title:
            raise ValueError('The host did not confirm the requested title')
        return {'ok': True, 'session_id': session_id, 'title': title}
    if kind == 'command':
        request = {'session_id': session_id, 'title': title, 'directory': directory}
        result = subprocess.run(adapter['rename']['command'], input=json.dumps(request, ensure_ascii=False),
                                capture_output=True, text=True, timeout=5, shell=False)
        if result.returncode != 0 or len(result.stdout) > 1_000_000:
            raise ValueError('The local title bridge failed')
        response = json.loads(result.stdout)
        if not isinstance(response, dict) or response.get('ok') is not True or response.get('session_id') != session_id or response.get('title') != title:
            raise ValueError('The local title bridge did not confirm the exact session and title')
        return response
    raise ValueError('Use the native title tool or return a suggestion for this adapter')
