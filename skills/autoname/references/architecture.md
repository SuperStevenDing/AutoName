# Architecture and verification

## Components

| Component | Responsibility |
| --- | --- |
| `SKILL.md` | First-run interaction, task understanding, language, verified project context, and naming authorization. |
| `scripts/autoname.py` | Command entry for humans and agents. |
| `autoname_lib/config.py` | Preference validation, inert templates, and exact title rendering. |
| `autoname_lib/install.py` | Owned-file installation, hook merging, status checks, and reversible uninstall. |
| `autoname_lib/adapters.py` | Built-in or explicit descriptors and local supported title writers. |
| `autoname_lib/runtime.py` | Enrollment, deduplication, pending titles, and exact result confirmation. |

The current host model chooses a concise task description in the user's language. Helpers validate and render its text; they do not call another model. Runtime data is separate from distributed source.

The repository's `bin/autoname.cjs` is a dependency-free Node launcher for npm/npx. It finds a compatible Python interpreter, forwards terminal input and arguments, and preserves backend exit codes. npm packages include the same skill folder; direct Python and ZIP installations keep working without Node. npm dependency installation does not register hooks.

## Host integrations

The Codex adapter registers `SessionStart`, `UserPromptSubmit`, and `PostToolUse` in the chosen root's `hooks.json`. It enrolls only `startup` and `fork`, injects instructions after a submitted prompt, and confirms the native current-chat title tool. A preparation command stores the exact pending title; a failed or mismatched result cannot complete it. The implementation follows [Codex hooks](https://learn.chatgpt.com/docs/hooks). Check the host's trust policy and whether hooks have been disabled; the installer preserves unrelated configuration.

The Claude Code adapter uses the same documented event family in `settings.json`. The current model calls the helper, which uses the optional official SDK's `rename_session` and `get_session_info` for a local write and readback. It preserves a preexisting custom title. See [Claude Code hooks](https://code.claude.com/docs/en/hooks) and [the Python SDK session metadata methods](https://code.claude.com/docs/en/agent-sdk/python). No model query or history listing is used by the writer.

Additional agents use [explicit descriptors and bridges](adapters.md). Codex and Claude hook schemas are implemented. An unrelated schema needs a schema adapter rather than an assumed filename or event. WorkBuddy's [plugin guide](https://www.workbuddy.cn/docs/workbuddy/Plugins) establishes Skill and Hook plugin categories; its programmatic title writer remains unverified.

## Installation and readiness

The terminal installation entry starts a wizard. An agent-led installation follows [setup.md](setup.md), and non-interactive missing preferences return `setup_required`. Native file-only imports trigger setup when the skill is first invoked.

The default action also selects a host interactively when none was provided. Standard skill-manager imports use `--in-place` to register their existing canonical directory. Symbolic links and copied files remain owned by the manager, and selected project scope determines the hook root.

Installation validates inputs and ownership before host-file writes, records an installing manifest for interruption recovery, copies public skill files, merges owned handlers, and saves private registration. It does not overwrite user-modified skill files. Files already present in a file-only import are not silently claimed as new installer-owned files.

`enabled` records permission to request automatic naming. Installation status separately records `configured_pending_host_check`, `verified`, `incomplete`, or an uninstalled state. Only a confirming current-chat title result establishes runtime verification. A command returning registration success is not a live desktop test.

Updates preserve preferences and the user's disabled switch. Uninstall removes only recorded handlers and unchanged owned files, and does not follow substituted directory links. Preferences, state, and private configuration backups are retained in the data directory.

## Runtime state and privacy

Each host uses its own component-owned SQLite file. Session identifiers are hashed for database keys. Rows contain the host writer's working directory, last-turn identifier or a prompt hash for deduplication, state, and a pending title until success. Raw prompts, transcripts, and tool payloads are not stored or logged.

Runtime errors print only exception classes in hook mode, and return control to the main task. Templates and aliases remain data. Command bridges receive JSON through stdin with `shell=False` and must return the exact requested session and title.

Source and release checks reject personal paths, local account identifiers, credentials, non-example emails, links, and runtime-state files. Packaging uses an explicit public-file selection and deterministic metadata. Installation-specific preferences and backups never belong in the distributed skill.

## Validation scope

Unit and integration fixtures exercise real local files, SQLite, command processes, hook merging, repeat installation, uninstall, success/failure confirmation, Unicode templates, and release packaging. The Claude SDK boundary is represented by a controlled test double; this is not a live Claude session test. Validate actual hook delivery, trust settings, display updates, and optional SDK compatibility in the target host before publishing a live compatibility claim.
