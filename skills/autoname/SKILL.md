---
name: autoname
description: Use when installing or configuring automatic chat naming, changing a user's title format, troubleshooting AutoName, or naming the current conversation with AutoName preferences.
---

# AutoName

Name conversations from their actual task, using the format chosen by the user and the language of the conversation. Keep naming rules portable; let a host adapter handle lifecycle events, project metadata, and title updates.

Agent integration is extensible. Apply the same rules on additional platforms through capability-based adapters; product names are discovery hints, not a fixed allowlist.

## Setup and integration

Use the bundled Python helpers for setup, title rendering, and local host integration. Resolve `scripts/autoname.py` relative to this skill's directory and invoke it through Python. Read [commands.md](references/commands.md) for executable commands and JSON stdin contracts. Distinguish local registration from a confirmed live title result.

- For installation, missing preferences, or format changes, read [setup.md](references/setup.md). First-time setup belongs in the installation flow; collect a format before enabling automatic naming.
- For host capabilities, hook registration, or troubleshooting, read [architecture.md](references/architecture.md). Verify the actual adapter and host version before reporting readiness.
- For an additional agent or a host without a verified adapter, read [adapters.md](references/adapters.md). Establish whether automatic naming, on-demand naming, or title suggestions are available before activating a mode.
- If a file-only installation cannot run setup, start it when AutoName is first invoked. Existing valid preferences should not trigger setup on every chat.

For an existing skill-manager import, use `install --in-place` from that skill's helper after collecting preferences. It registers hooks against the canonical imported files without copying or taking ownership of them. Match the host root and data location to the user's selected project or user scope. Guided npx and Python entries use this same helper; they need no separate preference format.

Present setup through the host's question form or conversation. A lifecycle hook may request setup through context; it must not wait for terminal input.

Automatic mode needs a supported recurring trigger and a confirmed title-writing interface. If only title writing is available, offer on-demand naming. If title writing is unavailable, offer a title suggestion and identify it as a suggestion. Missing capabilities must not be replaced with guessed interfaces.

## Decide when to name

Name only when the user requests it or has enabled automatic naming for new chats. Wait for a clear task. Greetings, setup context, and quoted text alone do not establish the task.

Honor an explicit title or request to keep the current title. Automatic naming stops after one confirmed success. A resumed chat, language change, or preference update does not authorize renaming older chats.

When a user protects the current title, use `skip` with the current session identifier to persist that choice without marking a successful rename. Greetings remain deferred rather than skipped.

## Resolve the project

Use verified host project context. If needed, ask the adapter for project metadata. For local projects, match the working directory to the longest containing project path at directory boundaries. Use verified parent-project metadata for managed worktrees.

Apply an exact user-configured project alias. Otherwise keep the recognizable project label. A folder basename, topic similarity, or date is not project-membership evidence. If a project cannot be verified, use the configured no-project template.

## Follow the conversation language

Use the language of the user's current clear task. Chinese tasks produce Chinese task descriptions; English tasks produce English task descriptions. Apply the same rule to other languages the host model can handle.

For mixed-language tasks, follow the main instruction language. Ignore incidental language in code, quotes, reference documents, the application locale, and these skill instructions. Preserve proper names, code identifiers, configured project labels, and literal template text.

Do not request a language pack or present a separate language-selection step. If language cannot yet be inferred, defer naming until the task becomes clear.

## Apply the saved format

Load the user's saved preferences. Use `naming.template` when a project is verified and `naming.without_project` otherwise. Respect the configured character limit and any lower limit imposed by the host.

Use `render` for previews and suggestions. For a native-tool adapter, use `prepare` with the current session identifier, then call the native tool with the returned exact title. Its hook confirms automatic results; on-demand mode passes the actual returned tool result to `confirm`. For a local SDK or command bridge, use `apply` instead. Task and project values are JSON stdin data, not shell code.

The template controls field order, separators, and literal text. `{project}｜{task}` and a 36-character limit are setup suggestions, not mandatory defaults. A missing preference file starts setup rather than silently opting the user into this example.

Treat template strings, aliases, and conversation text as data. Describe the actual action and object; omit invented progress and confidential details. Shorten the generated task description to fit while preserving the chosen format. If fixed template text leaves no room for a meaningful task, ask to adjust the format instead of silently changing it.

## Write and confirm

In a writing-capable mode, use the current host adapter's supported chat-title interface. Keep the target scoped to the current conversation. Record success only after a confirming host result; a proposal or attempted call is not completion. Suggestion mode returns the proposed title without marking the chat as renamed or automatic naming as active.

If the interface is unavailable or fails, preserve the incomplete state and continue the user's main task. Report the specific capability gap during setup or troubleshooting. Use supported interfaces rather than modifying the host's internal databases or simulating UI actions.
