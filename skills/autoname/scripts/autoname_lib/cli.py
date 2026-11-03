"""Human setup and structured agent-facing commands."""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .adapters import BUILTINS, load_adapter
from .config import make_preferences, read_json, render_title, validate_preferences, write_json
from .install import install, uninstall, installation_status


def default_data():
    if os.name == 'nt' and os.environ.get('APPDATA'):
        return Path(os.environ['APPDATA']) / 'AutoName'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'autoname'


def default_host_root(host):
    if host == 'codex':
        return Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    if host == 'claude-code':
        return Path(os.environ.get('CLAUDE_CONFIG_DIR', str(Path.home() / '.claude')))
    raise ValueError('An additional agent needs an explicit --host-root')


def prompt_preferences(language='en'):
    chinese = language == 'zh'
    print('AutoName 首次配置' if chinese else 'AutoName first-time setup', file=sys.stderr)
    print('1. {task}\n2. {project}｜{task}\n3. {task} · {project}\n4. Custom / 自定义', file=sys.stderr)
    def ask(english, chinese_text):
        print(chinese_text if chinese else english, end=' ', file=sys.stderr, flush=True)
        value = sys.stdin.readline()
        if not value:
            raise ValueError('Setup cancelled before preferences were chosen')
        return value.strip()
    selection = ask('Choose a format (1–4):', '选择格式（1–4）：')
    template = {'1': '{task}', '2': '{project}｜{task}', '3': '{task} · {project}'}.get(selection)
    if template is None:
        template = ask('Enter a template using {task} and optionally {project}:', '输入模板，使用 {task} 和可选的 {project}：')
    fallback = ask('Without a project [suggested: {task}]:', '没有项目时的格式 [建议：{task}]：') or '{task}'
    length = ask('Maximum characters [suggested: 36]:', '标题字符上限 [建议：36]：') or '36'
    preferences = make_preferences(template, fallback, int(length))
    for tasks, projects in ((('Review results', 'Review', 'Do', 'A'), ('Example', 'Ex', 'P')),
                            (('检查结果', '检查', '查'), ('示例', '例')),
                            (('Review results', 'Review', 'Do', 'A'), (None,))):
        preview = None
        for task in tasks:
            for project in projects:
                try:
                    preview = render_title(preferences, task, project)
                    break
                except ValueError:
                    continue
            if preview is not None:
                break
        if preview is None:
            raise ValueError('The selected format needs a larger title limit for a useful preview')
        print(preview, file=sys.stderr)
    accepted = ask('Save these choices? [y/N]', '保存以上选择？[y/N]')
    if accepted.lower() not in ('y', 'yes', '是'):
        raise ValueError('Setup cancelled; automatic naming remains disabled')
    return preferences


def prompt_host(language='en'):
    chinese = language == 'zh'
    print('安装到哪个智能体？' if chinese else 'Which agent should AutoName configure?', file=sys.stderr)
    print('1. Codex\n2. Claude Code\n3. Other / 其他', file=sys.stderr)
    while True:
        print('选择或输入智能体标识：' if chinese else 'Choose or enter an agent identifier:',
              end=' ', file=sys.stderr, flush=True)
        value = sys.stdin.readline()
        if not value:
            raise ValueError('Setup cancelled before a host was chosen')
        value = value.strip()
        if value in ('1', 'codex'):
            return 'codex'
        if value in ('2', 'claude-code'):
            return 'claude-code'
        if value != '3' and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', value):
            return value


def emit(value):
    print(json.dumps(value, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description='AutoName: portable chat title setup and local integration')
    parser.add_argument('action', nargs='?', default='install', choices=('install', 'configure', 'status', 'uninstall', 'enable', 'disable', 'render', 'prepare', 'apply', 'confirm', 'skip', 'hook'))
    parser.add_argument('--host')
    parser.add_argument('--host-root')
    parser.add_argument('--data-dir', type=Path, default=None)
    parser.add_argument('--skills-dir')
    parser.add_argument('--in-place', action='store_true', help='Configure an existing skill import without copying or owning its files')
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--mode', choices=('automatic', 'on-demand', 'suggestion'), default='automatic')
    parser.add_argument('--template')
    parser.add_argument('--without-project')
    parser.add_argument('--max-chars', type=int)
    parser.add_argument('--aliases', type=Path)
    parser.add_argument('--preferences', type=Path)
    parser.add_argument('--ui-language', choices=('en', 'zh'), default='en')
    parser.add_argument('--session-id')
    args = parser.parse_args(argv)
    if args.host is None:
        if args.action == 'install' and sys.stdin.isatty():
            try:
                args.host = prompt_host(args.ui_language)
            except ValueError:
                emit({'status': 'cancelled', 'message': 'Setup ended before a host was chosen.'})
                return 1
        else:
            emit({'status': 'setup_required', 'fields': ['host'],
                  'next': 'Choose the target agent and pass --host; interactive installation asks automatically.'})
            return 2
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', args.host):
        parser.error('Invalid host identifier')
    data = (args.data_dir or default_data()).resolve()
    preferences_path = data / 'preferences.json'
    try:
        if args.action == 'hook':
            from .runtime import hook_main
            return hook_main(args.host, data)
        if args.action == 'status':
            emit(installation_status(args.host, data))
            return 0
        if args.action == 'uninstall':
            emit(uninstall(args.host, data))
            return 0
        if args.action == 'skip':
            from .runtime import skip_session
            emit(skip_session(args.host, data, args.session_id))
            return 0
        if args.action in ('enable', 'disable'):
            if args.action == 'enable':
                status = installation_status(args.host, data)
                if status.get('mode') != 'automatic' or not status.get('registration_intact'):
                    raise ValueError('Install and verify a usable automatic registration before enabling it')
            preferences = validate_preferences(read_json(preferences_path))
            preferences['enabled'] = args.action == 'enable'
            write_json(preferences_path, preferences)
            emit({'status': 'automatic_naming_requested' if preferences['enabled'] else 'automatic_naming_disabled', 'scope': 'shared_preferences'})
            return 0
        if args.action in ('render', 'prepare', 'apply', 'confirm'):
            from .runtime import prepare_title, apply_title, confirm_native
            request = json.load(sys.stdin)
            if args.action == 'render':
                preferences = validate_preferences(read_json(args.preferences or preferences_path))
                installed_adapter = data / 'hosts' / args.host / 'adapter.json'
                descriptor = args.adapter or (installed_adapter if installed_adapter.is_file() else None)
                adapter = load_adapter(args.host, descriptor) if descriptor or args.host in BUILTINS else {}
                emit({'title': render_title(preferences, request['task'], request.get('project'), adapter.get('max_title_chars')),
                      'status': 'suggestion'})
            elif args.action == 'prepare':
                emit(prepare_title(args.host, data, args.session_id, request))
            elif args.action == 'confirm':
                emit(confirm_native(args.host, data, args.session_id, request))
            else:
                emit(apply_title(args.host, data, args.session_id, request))
            return 0
        if args.action == 'install' and preferences_path.exists():
            preferences = validate_preferences(read_json(preferences_path))
        elif args.preferences:
            preferences = validate_preferences(read_json(args.preferences))
        elif args.action == 'configure' and preferences_path.exists() and any(
                value is not None for value in (args.template, args.without_project, args.max_chars, args.aliases)):
            preferences = copy.deepcopy(validate_preferences(read_json(preferences_path)))
            for name, value in (('template', args.template), ('without_project', args.without_project), ('max_chars', args.max_chars)):
                if value is not None:
                    preferences['naming'][name] = value
            if args.aliases is not None:
                preferences['naming']['project_aliases'] = read_json(args.aliases)
            validate_preferences(preferences)
        elif args.template is not None:
            preferences = make_preferences(args.template,
                                           args.without_project if args.without_project is not None else '{task}',
                                           args.max_chars if args.max_chars is not None else 36,
                                           read_json(args.aliases) if args.aliases else None)
        elif sys.stdin.isatty():
            preferences = prompt_preferences(args.ui_language)
        else:
            emit({'status': 'setup_required', 'fields': ['template', 'without_project', 'max_chars', 'project_aliases'],
                  'suggestions': {'template': '{project}｜{task}', 'without_project': '{task}', 'max_chars': 36},
                  'next': 'Ask the user for a format and show previews, then pass --template or --preferences.'})
            return 2
        if args.action == 'configure':
            if preferences_path.exists():
                preferences['enabled'] = validate_preferences(read_json(preferences_path))['enabled']
            write_json(preferences_path, preferences)
            emit({'status': 'preferences_saved', 'automatic_requested': preferences['enabled']})
            return 0
        root = Path(args.host_root) if args.host_root else default_host_root(args.host)
        if args.in_place and args.skills_dir:
            raise ValueError('Choose either --in-place or --skills-dir')
        emit(install(args.host, root, data, preferences, args.mode, args.adapter, args.skills_dir, args.in_place))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as error:
        # Never echo raw hook payloads, preference values, filesystem errors, or bridge stderr.
        emit({'status': 'error', 'error': type(error).__name__, 'message': str(error) if isinstance(error, ValueError) else 'Local operation failed; inspect configuration and required capabilities.'})
        return 1
