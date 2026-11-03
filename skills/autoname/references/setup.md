# First-time setup and configuration

## Entry

Resolve the helper relative to this skill's location: `scripts/autoname.py`. Invoke it through the chosen Python interpreter. Examples in [commands.md](commands.md) assume the current directory is the skill folder; repository examples add `skills/autoname/`.

An installation request authorizes the necessary skill copy and hook registration. This repository's development does not install into the author's real settings. During an actual user's installation, select their host and scope from available context; ask only when the choice affects where settings will apply.

A human terminal can run the helper without arguments to choose the host and enter the wizard, or use `install --host <host>` to skip host selection. The guided Node/npx entry forwards the same terminal input and arguments. A non-interactive agent receives a JSON `setup_required` result and exit code 2 when the host or preferences are missing. File-only skill imports start the following flow when first invoked.

## Agent-led interaction

1. Detect the host and its supported interfaces. Use a built-in adapter or follow [adapters.md](adapters.md). Prefer automatic naming; if only a limited mode is available, obtain the user's choice before using it.
2. Use the host's question form or conversation to collect the title format. Offer project-first, task-first, and task-only presets with free text for custom formats. A natural-language description may be normalized into a template.
3. Offer an editable length suggestion of 36 and a no-project fallback of `{task}`. Collect project aliases only when wanted. Do not ask for a separate title language: each future task determines it.
4. Write the chosen values into a separate private draft JSON outside the skill and public repository, such as `draft.json` in a private temporary directory. Keep it separate from the installed `preferences.json` so previewing a draft does not replace existing settings. Start from [preferences.example.json](../assets/preferences.example.json), retain `enabled: false`, and replace the examples with the user's choices. Use a structured file writer; never interpolate template or task strings into shell code.
5. Use `render --preferences <private-draft>` with JSON stdin to preview a verified-project title and a no-project title. A short Chinese/English comparison can explain language behavior. These are examples, not real renames. Resolve invalid or impossible templates before installing.
6. Once choices are settled, call `install` with the host, selected mode, and private draft. For files already installed by a skill manager, also pass `--in-place` so its symlinks or copies remain manager-owned. Use the project host root for a project-scoped import, and the user host root only for a user-scoped installation. Let the helper merge its hooks and preserve unrelated settings. Do not ask for the same installation approval again; complete any actual host trust step that the user must perform.
7. Run `status`. Report registration, missing dependencies, reload/trust steps, and whether a live title result has been confirmed. Do not rename the installation chat just to turn a preview into a test.

Existing valid preferences are reused without repeating the wizard on every chat. Cancelling leaves automatic naming disabled; an uninstalled draft remains a draft. Hooks are non-interactive and never wait for terminal input.

## Preference contract

| Field | Meaning |
| --- | --- |
| `schema_version` | `1`. |
| `enabled` | Shared automatic-naming request switch; the example starts with `false`. A new automatic installation enables it after local registration. Host runtime verification is tracked separately. |
| `naming.template` | Format when the project is verified. |
| `naming.without_project` | Format when project membership is unknown. |
| `naming.max_chars` | Positive integer maximum length of the completed title, subject to a lower host limit. |
| `naming.language` | `conversation`: use the current clear task's language. |
| `naming.project_aliases` | Exact verified project-label to display-label mappings. |

Templates support plain `{task}` and `{project}` fields, configurable order, and literal text. Every template contains `{task}`; the no-project fallback cannot require `{project}`. Unknown fields, attribute access, conversions, and format specifications are rejected. Doubled braces can express a literal brace. Values are never evaluated as code.

An overlong rendered title returns an error so the agent can shorten generated wording while retaining the format. The setup wizard uses fitting previews; if a useful title cannot fit, revise the limit or fixed text with the user.

## Locations, changes, and removal

The shared data directory defaults to the operating system's user configuration directory under `autoname` (`AutoName` under `%APPDATA%` on Windows). Use `--data-dir` for an explicit location. Each adapter stores private registration and state under `hosts/<adapter-id>/`.

The built-in Codex root defaults to `CODEX_HOME` or the usual user Codex directory; Claude Code uses `CLAUDE_CONFIG_DIR` or its usual user directory. Both copy the skill under `skills/autoname`. Use `--host-root` and `--skills-dir` when the host's actual skill-loading location or chosen scope differs. Additional agents require an explicit host root.

`configure` can change only the specified format, fallback, length, or alias fields while retaining the others. Use `disable` and `enable` for the shared switch. Reinstallation preserves existing preferences, including a disabled state. New preferences affect future titles; existing chat renames require a new user request.

`uninstall` removes recorded hooks and unchanged installer-owned files. It retains edited or preexisting files, preferences, runtime state, and private backups. If the user requests complete data removal, explain the selected data directory and remove only that component-owned data under the user's authorization.
