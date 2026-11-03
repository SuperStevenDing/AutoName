"""Preference validation and deterministic, non-executable title templates."""

import json
import os
from pathlib import Path
from string import Formatter
import tempfile


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError('JSON file exceeds the size limit')
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def write_json(path, value):
    """Replace a component-owned JSON file atomically with private permissions."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Refusing to replace a symbolic link')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.autoname-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def is_linked(path):
    path = Path(path)
    return any(item.is_symlink() for item in (path, *path.parents))


def _text(value, label, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(label + ' must be a nonempty string')
    if len(value) > 10_000 or any(character in value for character in '\r\n\0'):
        raise ValueError(label + ' contains invalid title text')
    return value


def validate_template(template, without_project=False):
    _text(template, 'Template')
    fields = []
    for _, field, specification, conversion in Formatter().parse(template):
        if field is None:
            continue
        if field not in ('task', 'project') or specification or conversion:
            raise ValueError('Templates support only plain {task} and {project} fields')
        fields.append(field)
    if 'task' not in fields:
        raise ValueError('Every template must contain {task}')
    if without_project and 'project' in fields:
        raise ValueError('The fallback template cannot require {project}')
    return template


def validate_preferences(value):
    if not isinstance(value, dict) or set(value) != {'schema_version', 'enabled', 'naming'}:
        raise ValueError('Invalid preference fields')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Unsupported preference schema version')
    if type(value['enabled']) is not bool:
        raise ValueError('enabled must be a boolean')
    naming = value['naming']
    keys = {'template', 'without_project', 'max_chars', 'language', 'project_aliases'}
    if not isinstance(naming, dict) or set(naming) != keys:
        raise ValueError('Invalid naming fields')
    validate_template(naming['template'])
    validate_template(naming['without_project'], without_project=True)
    if type(naming['max_chars']) is not int or naming['max_chars'] < 1:
        raise ValueError('max_chars must be a positive integer')
    if naming['language'] != 'conversation':
        raise ValueError('language must be conversation')
    aliases = naming['project_aliases']
    if not isinstance(aliases, dict):
        raise ValueError('project_aliases must be an object')
    for key, alias in aliases.items():
        _text(key, 'Project label')
        _text(alias, 'Project alias')
    for key in ('template', 'without_project'):
        minimum = naming[key].format(task='A', project='P' if key == 'template' else '')
        if len(minimum) > naming['max_chars']:
            raise ValueError('The template leaves no room for a task; adjust its length or text')
    return value


def render_title(preferences, task, project=None, host_limit=None):
    validate_preferences(preferences)
    task = _text(task, 'Task').strip()
    naming = preferences['naming']
    if project is not None:
        project = _text(project, 'Project').strip()
        project = naming['project_aliases'].get(project, project)
    template = naming['template'] if project else naming['without_project']
    title = template.format(task=task, project=project or '').strip()
    limit = naming['max_chars']
    if host_limit is not None:
        if type(host_limit) is not int or host_limit < 1:
            raise ValueError('Invalid host title limit')
        limit = min(limit, host_limit)
    if len(title) > limit:
        raise ValueError('Title exceeds the character limit; shorten the generated task')
    return title


def make_preferences(template, without_project='{task}', max_chars=36, aliases=None,
                     enabled=False):
    return validate_preferences({
        'schema_version': 1,
        'enabled': enabled,
        'naming': {
            'template': template,
            'without_project': without_project,
            'max_chars': max_chars,
            'language': 'conversation',
            'project_aliases': aliases or {},
        },
    })
