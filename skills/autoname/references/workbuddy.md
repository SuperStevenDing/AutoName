# WorkBuddy on-demand naming

Use the built-in `workbuddy` adapter for explicit current-chat naming or title suggestions. Automatic mode is unavailable because no WorkBuddy lifecycle trigger schema has been verified. Skill discovery alone does not supply a recurring trigger.

## Evidence and scope

A user-supplied Windows test handoff dated 2026-11-03 reported successful native writes with `workbuddy_app_set_conversation_title`. The WorkBuddy product version was not recorded. It reported the following interface:

- `title`: 1–200 characters; the host converts newlines to spaces. AutoName validates title text and rejects newlines before writing.
- Omit optional `conversationId` to target the current conversation.
- The response contains `conversation.conversationId` and `conversation.title`.
- `changed:false` means the title already matches; an exact matching receipt can still confirm success.
- Genie app and cloud assistant conversations are not supported by the reported title tool.

The corrected render/tool/prepare/confirm flow is covered by isolated tests with synthetic receipts. Those tests do not call WorkBuddy. Run the live procedure below in the target host before treating that installation as verified.

## Install or upgrade

Run the helper from the updated skill folder. Select the actual WorkBuddy configuration root and keep private data outside the skill directory:

```bash
python scripts/autoname.py install --host workbuddy --mode on-demand --host-root "<actual-workbuddy-root>" --template "{project}｜{task}" --without-project "{task}" --max-chars 36
python scripts/autoname.py status --host workbuddy
```

Replace the root placeholder. Template and length values illustrate a choice; use the user's selected preferences. A non-interactive install must receive `--template` or `--preferences` if no preferences exist. On Windows, shared private data defaults to `%APPDATA%/AutoName`; add the original `--data-dir` when upgrading a custom location.

For an existing installation that uses a private WorkBuddy descriptor, run the updated source installer with the same host root, data directory, and skill destination, omitting `--adapter`. This replaces the stored descriptor with the built-in one and preserves existing preferences and runtime state. Do not delete preferences to migrate. The existing descriptor's `settings_file` must match `autoname.settings.json`; a location mismatch is reported rather than overwritten. If the installation is managed by a skill manager or was configured in place, update those canonical files through their owner and run their helper with `--in-place` again. Reinstallation returns `configured_pending_host_check` until an actual receipt is confirmed.

The adapter creates no hooks and writes no WorkBuddy settings file in limited modes. `autoname.settings.json` is a registration location marker, not a claimed native WorkBuddy settings schema. An explicit `--host-root` is required. Suggestion mode uses `--mode suggestion` and does not record a title write. `--mode automatic` is rejected.

## Current-chat procedure

Perform this only after an explicit naming request. Respect a title the user has asked to keep. Use the current task language and the saved preferences.

1. Send JSON containing `task` and, only when established, `project` to `render --host workbuddy`. Save the exact returned title and retain the same inputs for step 3. For example, the JSON data could be `{"task":"检查结果"}`. Use a structured process API or JSON file for actual task data; do not interpolate it into shell code.
2. Call native `workbuddy_app_set_conversation_title` with that exact title and omit `conversationId`. Retain the unmodified result. Obtain the real session ID from its `conversation.conversationId`; for a structured or text-block tool envelope, read that same object inside the envelope. A timestamped workspace folder name is not a session ID. A tool error or missing result cannot establish success.
3. Send the unchanged task/project JSON to `prepare --host workbuddy --session-id <returned-conversation-id>`. Include an absolute `directory` for the current workspace when the helper runs elsewhere. The prepared title must equal the rendered title and the host's returned title. If preferences changed or titles differ, leave the attempt incomplete and resolve the mismatch before retrying.
4. Send the unmodified native result to `confirm --host workbuddy --session-id <same-returned-id>`. A successful result has `status: renamed`; the component-owned session row becomes `done`, and `status --host workbuddy` reports `verified`. Stop after confirmation. Another explicit naming request can start a new on-demand operation.

If the current conversation's real ID is already available from trusted host context, the ordinary prepare/tool/confirm sequence also works. Every sequence requires the exact current-session ID and pending title. Neither a suggested title nor a tool call alone verifies the helper's full workflow.

## Projects and failure recovery

No host project metadata was available in the supplied test. Use a project label supplied explicitly by the user or established by supported host metadata. `project_aliases` maps an established label to its display name; it does not prove membership. When membership is unknown, omit `project` and use the saved no-project template.

Keep failed operations pending. A wrong/missing ID, wrong title, malformed receipt, or explicit error cannot complete a rename. Do not reconstruct a successful receipt from the intended title. If the title tool is unavailable for the current conversation, identify the capability gap; use suggestion mode only when the user chooses it.
