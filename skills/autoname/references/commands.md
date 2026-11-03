# Bundled commands

Examples below run from the skill folder. Replace host identifiers and private paths with values from the actual installation. Use the same Python interpreter for installation and its hooks.

Running `python3 scripts/autoname.py` without arguments opens host selection and first-run setup in a terminal. Guided npx and a global `autoname` command forward to this same helper; the standalone skill ZIP works without Node.

## Install and configure

```bash
python3 scripts/autoname.py install --host codex
python3 scripts/autoname.py install --host codex --template '{task} · {project}' --max-chars 40
python3 scripts/autoname.py install --host codex --preferences /path/to/private/draft.json
python3 scripts/autoname.py configure --host codex --template '{project}: {task}'
python3 scripts/autoname.py status --host codex
python3 scripts/autoname.py disable --host codex
python3 scripts/autoname.py enable --host codex
python3 scripts/autoname.py uninstall --host codex
```

A terminal install opens the wizard when no preferences exist. Inside an agent, prefer the host's form and pass the resulting private preferences file. `--ui-language zh` selects the terminal wizard language only; it does not set future title language.

For a standard skill-manager import, add `--in-place` to `install` and set the host/data roots to the selected scope. The helper uses the canonical imported folder, including when the visible agent path is a symlink. This registers integration without claiming the manager's files. It is not an npm dependency-install script; file-only imports configure themselves when the skill is first used.

Use `--data-dir`, `--host-root`, and `--skills-dir` when selecting nondefault locations or scope. Existing preferences are preserved by reinstall. Partial `configure` changes preserve the other fields. A new user request can use `enable` after `disable`; reinstalling alone does not override a disabled switch.

## Render a preview or suggestion

```bash
printf '%s' '{"task":"Review results","project":"Demo"}' | python3 scripts/autoname.py render --host codex --preferences assets/preferences.example.json
```

This static example is safe to copy. For actual user text, supply a JSON stdin payload through a structured process/file API; do not concatenate it into shell syntax. Omit `project` when membership is unknown. Rendering does not install, enable, or rename anything. Preference and task values should not be stored in the public repository.

## Native current-chat title tools

For an enrolled automatic chat, use `prepare --host <host> --session-id <current-id>` with JSON stdin containing `task` and optional `project`. The response contains the validated title. Call the host's supported title tool with that exact title. The registered `PostToolUse` hook verifies the response.

For Codex, use its native `set_thread_title` and omit `threadId` and `source` to target the calling chat. On-demand native adapters have no recurring hook; after an actual tool success, pass the unmodified tool response to `confirm --host <host> --session-id <current-id>` through JSON stdin. Never manufacture a confirmation result.

If the user supplies a protected title or asks to keep the current one, run `skip --host <host> --session-id <current-id>` to stop pending automatic requests for that chat. This does not claim a title write. Do not skip preliminary greetings; those should wait for a clear task.

## Local SDK and bridge writers

Use `apply --host <host> --session-id <current-id>` with the same task/project JSON for a Claude SDK or local command writer. The helper renders the title, calls only the selected local writer, verifies its result, and records success. It does not make a model request.

For on-demand calls, include `directory` in JSON stdin when the helper process is not running from the conversation's actual project directory. For example: `{"task":"Review results","directory":"/path/to/current/project"}`. This is the current working context used for scoped session lookup, not evidence for a project display label. Each explicit call refreshes the directory, including retries after a failed lookup.

The Claude writer requires a compatible official `claude-agent-sdk` in the interpreter used by the helper. It scopes metadata operations to the current session and project directory and preserves existing custom titles. A missing optional SDK is reported instead of silently selecting a different mode.

The [adapter guide](adapters.md) defines the generic bridge's JSON request and confirmation. `hook` is an internal event entry; its errors fail open and omit raw input from logs.
