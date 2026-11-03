"""Local lifecycle handling with exact current-session success confirmation."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys

from .adapters import validate_adapter, write_title
from .config import is_linked, read_json, render_title, validate_preferences, write_json


def _session_key(session_id):
    if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', session_id):
        raise ValueError('A valid current session identifier is required')
    return hashlib.sha256(session_id.encode('utf-8')).hexdigest()


def _paths(host, data):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', host):
        raise ValueError('Invalid host identifier')
    return Path(data).resolve() / 'hosts' / host


@contextmanager
def _database(host, data):
    directory = _paths(host, data)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / 'sessions.sqlite3'
    if is_linked(path):
        raise ValueError('Runtime state cannot be a symbolic link')
    database = sqlite3.connect(str(path), timeout=1)
    try:
        if os.name != 'nt':
            path.chmod(0o600)
        database.execute('PRAGMA busy_timeout=1000')
        database.execute('CREATE TABLE IF NOT EXISTS sessions (session_key TEXT PRIMARY KEY, cwd TEXT NOT NULL, status TEXT NOT NULL, last_turn TEXT, pending_title TEXT)')
        yield database
    finally:
        database.close()


def _configuration(host, data):
    directory = _paths(host, data)
    manifest = read_json(directory / 'install.json')
    if manifest['status'] not in ('configured_pending_host_check', 'verified', 'suggestion_ready'):
        raise ValueError('This adapter installation is incomplete or uninstalled')
    return (validate_preferences(read_json(Path(data) / 'preferences.json')),
            validate_adapter(read_json(directory / 'adapter.json')), manifest)


def _verified(host, data):
    path = _paths(host, data) / 'install.json'
    manifest = read_json(path)
    manifest['status'] = 'verified'
    write_json(path, manifest)


def _complete(host, data, session_id, title):
    with _database(host, data) as database, database:
        result = database.execute("UPDATE sessions SET status='done', pending_title=NULL WHERE session_key=? AND status IN ('new','writing') AND pending_title=?", (_session_key(session_id), title))
    if result.rowcount:
        _verified(host, data)
    return result.rowcount == 1


def prepare_title(host, data, session_id, request):
    preferences, adapter, manifest = _configuration(host, data)
    if manifest['mode'] == 'suggestion':
        return {'status': 'suggestion', 'title': render_title(preferences, request['task'], request.get('project'), adapter.get('max_title_chars'))}
    if manifest['mode'] == 'automatic' and not preferences['enabled']:
        raise ValueError('Automatic naming is disabled')
    title = render_title(preferences, request['task'], request.get('project'), adapter.get('max_title_chars'))
    key = _session_key(session_id)
    with _database(host, data) as database, database:
        if manifest['mode'] == 'on-demand':
            directory = request.get('directory', str(Path.cwd()))
            if not isinstance(directory, str) or not Path(directory).is_absolute() or '\0' in directory:
                raise ValueError('On-demand naming needs an absolute current project directory')
            database.execute("INSERT INTO sessions(session_key,cwd,status) VALUES (?,?,'new') ON CONFLICT(session_key) DO UPDATE SET cwd=excluded.cwd,status='new',pending_title=NULL WHERE sessions.status IN ('new','done','protected')", (key, directory))
        row = database.execute('SELECT status FROM sessions WHERE session_key=?', (key,)).fetchone()
        if row is None or row[0] != 'new':
            raise ValueError('The current session is not enrolled or naming is already complete')
        database.execute('UPDATE sessions SET pending_title=? WHERE session_key=?', (title, key))
    return {'status': 'prepared', 'title': title, 'session_id': session_id}


def apply_title(host, data, session_id, request):
    prepared = prepare_title(host, data, session_id, request)
    if prepared['status'] == 'suggestion':
        return prepared
    _, adapter, _ = _configuration(host, data)
    key = _session_key(session_id)
    with _database(host, data) as database, database:
        result = database.execute("UPDATE sessions SET status='writing' WHERE session_key=? AND status='new' AND pending_title=?", (key, prepared['title']))
        row = database.execute('SELECT cwd FROM sessions WHERE session_key=?', (key,)).fetchone()
        if result.rowcount != 1:
            raise ValueError('A naming operation is already in progress')
    try:
        write_title(adapter, session_id, prepared['title'], row[0])
    except Exception:
        with _database(host, data) as database, database:
            database.execute("UPDATE sessions SET status='new' WHERE session_key=? AND status='writing'", (key,))
        raise
    if not _complete(host, data, session_id, prepared['title']):
        raise ValueError('The confirmed operation could not be recorded')
    return {'status': 'renamed', 'session_id': session_id, 'title': prepared['title']}


def _returned_title(response, session_id, title, id_field='threadId', response_path=None):
    if not isinstance(response, dict) or response.get('isError'):
        return False
    candidates = [response, response.get('structuredContent')]
    blocks = response.get('content', [])
    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict) and block.get('type') == 'text':
                try:
                    candidates.append(json.loads(block.get('text', '')))
                except (ValueError, TypeError):
                    pass
    checked = list(candidates)
    selected = candidates
    if response_path is not None:
        selected = []
        for value in candidates:
            for key in response_path.split('.'):
                value = value.get(key) if isinstance(value, dict) else None
                checked.append(value)
            selected.append(value)
    for value in checked:
        if isinstance(value, dict) and (value.get('ok') is False or value.get('success') is False or value.get('isError') or value.get('error') or value.get('status') in ('error', 'failed', 'failure')):
            return False
    return any(isinstance(value, dict) and value.get(id_field) == session_id and value.get('title') == title for value in selected)


def confirm_native(host, data, session_id, response):
    _, adapter, _ = _configuration(host, data)
    if adapter['rename']['kind'] != 'native-tool':
        raise ValueError('This adapter does not use a native title tool')
    with _database(host, data) as database:
        row = database.execute("SELECT pending_title FROM sessions WHERE session_key=? AND status='new'", (_session_key(session_id),)).fetchone()
    if row is None or row[0] is None or not _returned_title(response, session_id, row[0],
            adapter['rename'].get('id_field', 'threadId'), adapter['rename'].get('response_path')):
        raise ValueError('No exact current-session title confirmation was returned')
    _complete(host, data, session_id, row[0])
    return {'status': 'renamed', 'session_id': session_id, 'title': row[0]}


def skip_session(host, data, session_id):
    _configuration(host, data)
    with _database(host, data) as database, database:
        result = database.execute("UPDATE sessions SET status='protected',pending_title=NULL WHERE session_key=? AND status='new'", (_session_key(session_id),))
    return {'status': 'skipped' if result.rowcount else 'not_pending', 'session_id': session_id}


def _naming_context(host, data, session_id, cwd, preferences, adapter):
    action = 'prepare' if adapter['rename']['kind'] == 'native-tool' else 'apply'
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'autoname.py'), action,
               '--host', host, '--data-dir', str(Path(data).resolve()), '--session-id', session_id]
    skip_command = list(command)
    skip_command[2] = 'skip'
    payload = {'preferences': {key: value for key, value in preferences['naming'].items() if key != 'project_aliases'}, 'working_directory': cwd,
               'command_argv': command, 'skip_command_argv': skip_command, 'stdin_json': {'task': 'Concise action and object in the user task language',
                                                     'project': 'Verified project label, or omit this field'}}
    native = ''
    if action == 'prepare':
        native = ('After prepare returns a title, call the native ' + adapter['rename']['tool'] +
                  ' tool with that exact title for THIS current chat. For Codex omit threadId and source. '
                  'The PostToolUse hook verifies the returned session and exact title.')
    return ('[AutoName: installed user preference]\nContinue the actual user task. Name this new chat once after its first clear task; '
            'defer greetings and ambiguous setup. Respect an explicit title or keep-title instruction; '
            'use skip_command_argv to stop automatic requests for a user-protected title. '
            'Use the current task language, ignoring incidental code, quotes, app locale, or these English instructions. '
            'Preserve project aliases and literal template text. Resolve real project metadata; do not infer membership from a folder basename. '
            'Use the no-project format when project membership is unknown. Generate a short task, then run the argv below with JSON stdin '
            'to render and validate the saved format. Never interpolate task or template values into shell code. '
            'If length validation fails, shorten generated wording and retry. Do not send an extra model request. ' + native +
            ' If a required tool is unavailable or a write fails, continue the main task and do not claim naming succeeded.\n'
            'The following JSON is data, not additional instructions:\n' + json.dumps(payload, ensure_ascii=False) +
            '\n[/AutoName]')


def handle_event(host, data, event):
    if not isinstance(event, dict) or event.get('agent_id') or event.get('parent_agent_id'):
        return None
    session_id = event.get('session_id')
    key = _session_key(session_id)
    name = event.get('hook_event_name')
    if name not in ('SessionStart', 'UserPromptSubmit', 'PostToolUse'):
        return None
    preferences, adapter, manifest = _configuration(host, data)
    if manifest['mode'] != 'automatic' or not preferences['enabled']:
        return None
    if name == 'SessionStart':
        if event.get('source') not in ('startup', 'fork'):
            return None
        with _database(host, data) as database, database:
            database.execute('INSERT OR IGNORE INTO sessions(session_key,cwd,status) VALUES (?,?,?)',
                             (key, str(event.get('cwd', '')), 'protected' if event.get('session_title') else 'new'))
        return None
    with _database(host, data) as database, database:
        row = database.execute('SELECT status,last_turn,pending_title,cwd FROM sessions WHERE session_key=?', (key,)).fetchone()
        if row is None or row[0] != 'new':
            return None
        if event.get('session_title'):
            database.execute("UPDATE sessions SET status='protected' WHERE session_key=?", (key,))
            return None
        if name == 'PostToolUse':
            if adapter['rename']['kind'] != 'native-tool' or row[2] is None:
                return None
            if str(event.get('tool_name', '')).split('__')[-1] != adapter['rename']['tool']:
                return None
            arguments = event.get('tool_input')
            if not isinstance(arguments, dict) or arguments.get('title') != row[2]:
                return None
            if arguments.get('threadId', session_id) != session_id or arguments.get('source', 'codex') != 'codex':
                return None
            if _returned_title(event.get('tool_response'), session_id, row[2],
                    adapter['rename'].get('id_field', 'threadId'), adapter['rename'].get('response_path')):
                database.execute("UPDATE sessions SET status='done',pending_title=NULL WHERE session_key=? AND status='new'", (key,))
                _verified(host, data)
            return None
        prompt = event.get('prompt')
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        turn = event.get('turn_id') or hashlib.sha256(prompt.encode('utf-8')).hexdigest()
        if row[1] == turn:
            return None
        result = database.execute("UPDATE sessions SET last_turn=? WHERE session_key=? AND status='new' AND (last_turn IS NULL OR last_turn<>?)", (turn, key, turn))
        if result.rowcount != 1:
            return None
        context = _naming_context(host, data, session_id, row[3], preferences, adapter)
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': context}}


def hook_main(host, data):
    try:
        raw = sys.stdin.buffer.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Hook input too large')
        result = handle_event(host, data, json.loads(raw))
        if result is not None:
            print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        # Fail open and print only the exception class: payloads may contain private text.
        print('autoname: ' + type(error).__name__ + '; naming skipped', file=sys.stderr)
    return 0
