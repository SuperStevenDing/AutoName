# Integrating additional agents

Use this contract when adding an agent platform or assessing an unfamiliar host. The bundled installer accepts explicit JSON descriptors and supports the Codex and Claude hook schemas. Local JSON bridges provide an extension point for additional supported title APIs. Another hook schema requires an implementation and validation of that schema.

## Descriptor and bridge

Start from [adapter.example.json](../assets/adapter.example.json). Use `install --host <descriptor-id> --adapter <private-descriptor> --host-root <actual-root> --mode <chosen-mode>`. Descriptors and private bridge paths belong outside the distributed skill. The example uses suggestion mode until actual interfaces have been established.

`id` is a stable lowercase identifier. `hook_style` is `codex`, `claude`, or `none`; use a named schema only after verifying that the host implements it. `settings_file` is relative to the chosen host root. The installer does not guess WorkBuddy or another agent's settings directory.

`rename.kind` is `native-tool`, `claude-sdk`, `command`, or `suggestion`. A native tool supplies `tool` and optionally `id_field` for its response session key. A command writer supplies an explicit `command` argument array. It runs with `shell=False` and a five-second timeout, receives only the current session, proposed title, and project directory, and must return an exact confirmation.

Request on stdin: `{"session_id":"current-session","title":"Review results","directory":"/path/to/project"}`.

Successful stdout: `{"ok":true,"session_id":"current-session","title":"Review results"}`.

Bridge failure, malformed output, a mismatched session or title, or an explicit failure response leaves naming incomplete. Bridge code must use the host's supported interface; the generic helper does not grant access to arbitrary chat internals. The current agent model supplies task wording and language, so a bridge does not need a second model request.

On-demand `prepare`/`apply` input accepts an explicit absolute `directory` for the current conversation's project context. Supply it when executing from the skill folder or another directory. The helper refreshes it on each explicit call; automatic mode instead uses the enrolled host event's directory.

## Discover capabilities

Identify the actual host, version, execution environment, and current conversation. Inspect available tools, documented APIs or SDKs, native commands, plugin facilities, and lifecycle events as relevant. Use official documentation and observed results to establish each capability; preserve unknowns as unknowns.

| Capability | What to establish |
| --- | --- |
| Instruction entry | How the host receives the shared skill instructions or an equivalent native package. |
| Setup entry | Whether installation can start onboarding, or first use must do so. |
| Recurring trigger | Whether a native event can run AutoName when a new chat receives a task. |
| Conversation target | How an operation is scoped to the current chat. |
| Title write | Which supported interface updates that chat's displayed title. |
| Confirmation | What returned result or readback proves the title was applied. |
| Project context | Whether real project membership can be obtained; otherwise use the configured fallback. |
| Settings and state | Which supported locations store preferences, adapter registration, and component-owned runtime state. |

Record each capability as supported, unsupported, or unknown, together with its source and version scope. A product-name match can select a candidate adapter, but capability checks establish actual readiness. Do not infer compatibility from a similar settings directory or event name.

## Select an execution mode

| Mode | Required capabilities | Observable outcome |
| --- | --- | --- |
| Automatic naming | Instruction entry, recurring trigger, current-chat targeting, title write, and confirmation. | A new chat is renamed after a clear task, and one confirmed success stops automatic renaming. |
| On-demand naming | Instruction entry, current-chat targeting, title write, and confirmation. | An explicit invocation renames the current chat; no automatic trigger is claimed. |
| Title suggestions | Instruction entry and sufficient task context. | The agent returns a title in the chosen format and language for the user to apply. |

If the host cannot load the skill directly, an adapter may use a documented native instruction or plugin entry to deliver the same rules. If no supported entry is established, leave integration unverified and identify the missing interface.

Unknown title-writing or confirmation support does not permit a successful-renaming claim. Offer the supported mode rather than guessing an API, editing internal state, or treating a suggested title as an applied one.

When automatic naming was requested, a limited mode requires the user's choice. Keep the original automatic integration marked unavailable or pending; accepting a suggestion or an on-demand rename does not verify automatic support.

## Keep the shared behavior portable

Reuse the [setup and preference contract](setup.md) and the naming rules in [SKILL.md](../SKILL.md). Host-specific event names, request fields, settings paths, and response parsing belong in the adapter.

Add a distinct adapter registration containing a stable identifier, version scope, capability evidence, available modes, and installation and removal ownership. Preserve shared naming preferences when changing hosts. Track enrollment, pending operations, and confirmed success per host and conversation so identifiers or setup state do not leak across integrations.

For automatic mode, register only the native triggers required for the chosen workflow. For on-demand or suggestion mode, keep that mode usable without hook support. Use the configured no-project template when the host cannot establish project membership.

## Add and validate an integration

1. Establish instruction loading, onboarding entry, and capability evidence for the actual environment.
2. Implement the host adapter using supported interfaces and the shared preference contract.
3. Validate title format, conversation language, aliases, character limits, and the no-project fallback.
4. For writing-capable modes, verify current-chat targeting, successful writes, failure reporting, and respect for manual titles.
5. For automatic mode, verify first-clear-task timing, duplicate delivery, stop-after-success, and resumed-chat behavior.
6. Verify setup recovery, configuration preservation, and removal of only AutoName-owned registrations.
7. Document the tested host versions and modes. Keep proposed support separate from implemented and verified support.

New integrations should extend the adapter layer while leaving shared naming rules usable by existing agents. Runtime adapters can use the language and packaging supported by their host; the common contract does not require one SDK or one hook format.
