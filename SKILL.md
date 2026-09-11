---
name: dify-ce-workflow-autobuilder
description: Design, generate, validate, import, test, debug, publish, and verify Dify CE or self-hosted Enterprise workflows, chatflows, standalone New Agent apps, and Workflow Agent V2 nodes. Use when Codex needs to turn requirements into Dify DSL, create portable agent_packages, connect a published New Agent to a Workflow, use difyctl or Console/Service APIs, inspect traces, or iterate until an app works. Ground every generated artifact in the exact target Dify checkout and version.
---

# Dify Self-Hosted Workflow and New Agent Autobuilder

Build Dify apps end to end. Turn requirements into an acceptance plan, generate version-matched DSL, import it, resolve workspace-specific dependencies, test the correct runtime surface, debug from traces, publish when requested, and verify the published behavior.

## Non-negotiable rules

1. Locate the exact target Dify checkout and runtime before generating YAML. Do not infer current schema from an older exported DSL.
2. Protect existing deployments, uncommitted repositories, and user data. Inventory first; never restart, upgrade, clean, or replace a running stack unless explicitly requested.
3. Start from the business proof and data boundaries, not from node count.
4. Show a concise proposed app structure and wait for confirmation unless the user already approved it or explicitly asked to proceed autonomously.
5. Treat import, configuration, publish, draft execution, published execution, and external delivery as separate evidence layers.
6. Never print credentials, API keys, JWTs, private keys, or secret values.

## Preconditions

Use the automated Console path only when Dify CE or Enterprise is local/self-hosted and Codex can reach the host shell and API container. Typical requirements are:

- a reachable Dify web/API base URL;
- a running API container, commonly `docker-api-1`;
- access to `SECRET_KEY` for a short-lived local Console JWT;
- an existing console account;
- configured model providers and any required plugin credentials.

For Dify Cloud or locked-down environments, review or generate portable DSL, use supported public/Service APIs, or provide manual UI steps. Do not assume backend access.

If no compatible Dify runtime is installed or running, use:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" install-guide
```

## Ground the target version

Before designing nodes, inspect the target checkout:

```bash
rg -n 'CURRENT_APP_DSL_VERSION' <dify-repo>/api/constants/dsl_version.py
test -f <dify-repo>/api/services/agent/dsl_service.py && echo agent-package-dsl-supported
test -f <dify-repo>/api/core/workflow/nodes/agent_v2/discriminator.py -o \
     -f <dify-repo>/api/core/workflow/nodes/agent_v2/validators.py && echo agent-v2-supported
```

Read exported DSLs from that same runtime when available. Prefer a fresh export from the target workspace as the canonical shape.

Classify support:

- **Legacy only:** no recognized Agent V2 implementation or portable Agent package service. Generate only schemas supported by that version.
- **Agent V2 without portable packages:** create/publish the Agent through the verified Composer/Agent APIs or UI, then bind it to the Workflow. Do not invent a portable package.
- **Portable New Agent DSL:** `agent_packages` import/export is present. Follow [references/new-agent-dsl.md](references/new-agent-dsl.md).

Never present current-main fields as valid for an older release merely because both use a node named `agent`.

Also inspect the Agent backend/runtime path before promising an executable New Agent. A valid UI schema or successful DSL import does not prove that the API/worker can reach the Agent backend.

## Choose the app surface

Use the smallest surface that proves the requirement:

| Need | Default surface |
|---|---|
| Reusable autonomous worker with Prompt, Skills, Files, Knowledge, and Tools | Standalone New Agent app (`app.mode: agent`) |
| Event-driven or governed business process around flexible judgment | Workflow with an Agent V2 node |
| Conversational, multi-turn assistant with routing | `advanced-chat` |
| Batch, scheduled, evaluation, or API-first processing | `workflow` |
| Reuse one published Agent across several Workflows | Standalone roster Agent plus explicit Workflow Composer binding |

If the user experience or portability changes materially based on this choice, ask one concise question before building.

## New Agent generation rules

When the target supports portable Agent DSL, choose one of these patterns:

1. **Standalone Agent package**
   - top-level `app.mode: agent`;
   - `agent.package_ref` points to a top-level `agent_packages` entry;
   - import creates an editable, unpublished Agent draft;
   - validate the draft, resolve missing resources, then publish it.

2. **Workflow-contained Inline Agent**
   - Workflow graph node data uses `type: agent`, `version: '2'`, and `agent_node_kind: dify_agent`;
   - `agent_binding.package_ref` points to a top-level package;
   - `agent_job` contains only Workflow-specific instructions, previous-node references, contacts, and declared outputs;
   - import materializes a node-owned Inline Agent and a Snapshot.

3. **Existing reusable Roster Agent**
   - create/import and publish the standalone Agent first;
   - bind it to the Workflow through the verified Composer API or Studio UI;
   - republish the Workflow and confirm its binding points to the intended published Snapshot;
   - never hard-code workspace database IDs into portable DSL.

Keep Agent Soul and Workflow job responsibilities separate:

- **Agent Soul:** system Prompt, model, Skills, Files, Tools, Knowledge sets, memory, sandbox, app features.
- **Workflow job:** live task Prompt, upstream output references, declared output contract, Workflow-scoped human contacts.
- Do not override Soul fields through `agent_job.metadata`.
- Do not carry legacy fields such as `workspace_skills`, `agent_strategy_*`, or graph-projected `agent_task` into `AgentPackage`. Current package, Soul, and job DTOs reject unknown fields.

## New Agent Skill packages

When a New Agent needs reusable business rules, SOPs, output standards, playbooks, tool-use instructions, or other guidance that should be editable outside the main prompt, propose a Dify Agent config Skill package instead of putting everything into `system_prompt`.

Before generating or uploading any Agent Skill package, show the user a concise Agent design and wait for confirmation. Include:

- Agent purpose and app surface;
- what stays in the Agent Prompt;
- what will be packaged into one or more Skill zip files;
- any Knowledge, Files, Tools, local services, or plugin credentials the Agent will depend on;
- whether the Skill package is demo-safe, based on user-provided content, or expected to be edited later;
- the tests that will prove the Skill is actually used.

Generate a Skill zip only after the user confirms that boundary or explicitly asks to proceed autonomously. The package must contain a valid `SKILL.md` with YAML frontmatter `name` and `description`; keep the name stable and user-editable. Treat the zip as a user-owned artifact: users may download, edit `SKILL.md` or supporting files, and ask Codex to re-upload and retest it.

Dify Agent Skill packages are not Dify Plugins. Do not call them plugins. They are uploaded as Agent config skills and stored as zip archives; portable Agent DSL may reference them as omitted/missing assets, but the zip payload itself must be uploaded or reattached in the target workspace.

Portable export intentionally removes or weakens workspace-specific resources:

- Skill and File payloads are omitted and become missing references;
- model and tool credentials are removed;
- Dify tools become unauthorized until reconnected;
- missing Knowledge datasets are replaced with unresolved placeholders;
- human-contact database IDs are removed.

Therefore, import success is never enough. Read all import warnings and complete the post-import setup checklist before publishing. See [references/new-agent-dsl.md](references/new-agent-dsl.md).

Build Mode is not a fourth portable format. Its Build Draft is editor-scoped temporary state. The generated Skill/File/Prompt changes must be reviewed and **Applied** to the ordinary Agent Draft before an export can contain them. Apply still does not publish the Agent.

Do not assume Dify's built-in graph generator can emit a New Agent app merely because it can generate Workflow nodes. At the inspected current-main version, its planner/build result is graph-only and does not own top-level `agent_packages`. Use one of these supported paths instead:

- generate a complete external App DSL envelope with `agent_packages`, then import it; or
- create a V2 node shell in Studio, save the Workflow Draft, and use the Workflow Agent Composer API/UI to materialize the binding.

Never save a graph-only `package_ref` and expect ordinary Workflow graph sync to create an Agent package or Snapshot.

## Standard workflow

### 1. Inspect before changing anything

- Locate all relevant Dify checkouts and identify the target runtime.
- Check repository state without modifying unrelated work.
- Inventory containers, ports, app mode, installed plugins, configured providers, and existing datasets.
- Prefer a separate current-version stack when an older demo environment must remain stable.

### 2. Define the proof plan

Record:

- app surface and New Agent pattern;
- proposed Agent purpose, Prompt responsibilities, and whether any Agent Skill zip should be generated;
- real versus mock data boundaries;
- required model, Knowledge, Tools, Skills, Files, triggers, and human approval;
- expected node families and output contract;
- two to five representative tests;
- go/no-go criteria and destructive/external-write boundaries.

### 3. Select capabilities before Code nodes

Prefer the most specific Dify surface:

- intent routing: Question Classifier or Parameter Extractor;
- retrieval: Knowledge Retrieval or New Agent Knowledge sets;
- flexible multi-source judgment: New Agent with read-only tools;
- external reads/writes: plugin Tool or verified HTTP API;
- human approval: Human Input;
- deterministic parsing, validation, math, and routing: Code/If-Else;
- natural-language synthesis: LLM or Agent;
- chat response: Answer; Workflow result: Output/End.

Do not collapse the demo into one large Code node. Keep independent source calls parallel when possible.

### 4. Discover plugins portably

Check installed plugins and current Marketplace sources before using HTTP Request or creating a mock service. Prefer exact action coverage and clean credential setup over a generic integration.

Use this discovery order:

1. target Dify checkout and installed-plugin metadata;
2. `dify-official-plugins` for official manifests;
3. current Marketplace manifest;
4. user-provided plugin documentation.

Treat dependency declaration, installation, authorization, and a successful tool call as four separate checks. Ask before installing a plugin, configuring a secret, incurring cost, or calling a mutable external action.

### 5. Design Knowledge correctly

- Use Knowledge for searchable documents and product/policy context.
- Use structured stores for records, metrics, statuses, votes, and transactional history.
- Use Tools/APIs for live lookups and external writes.
- Do not create or upload a Knowledge Base until the user approved the content and privacy boundary.
- Verify upload, indexing, retrieval hit quality, and downstream use separately.
- In New Agent, configure explicit `knowledge.sets`; each set owns datasets, query mode, retrieval settings, and metadata filtering.

### 6. Generate and validate DSL

Use target-version exports as patterns. Save generated YAML under a dedicated case folder.

For any New Agent artifact, run:

```bash
python3 "$SKILL_DIR/scripts/validate_new_agent_dsl.py" \
  /absolute/path/to/app.yml \
  --target-repo /absolute/path/to/dify \
  --out /absolute/path/to/new-agent-validation.json
```

Fix every error before import. Warnings are setup work, not cosmetic notes. Use `--fail-on-warnings` for a strict portable-delivery gate.

For non-Agent DSL, still audit:

- top-level DSL version and app mode;
- node and edge IDs;
- variable selectors and output schemas;
- plugin dependencies and provider names;
- dataset IDs and credentials;
- whether the node mix proves the requested capability.

### 7. Import

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" import \
  /absolute/path/to/app.yml \
  --name "Demo App" \
  --out /absolute/path/to/import-result.json
```

If the import returns `pending`, inspect dependencies and confirm only after the user-approved dependency boundary is still valid:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" import \
  /absolute/path/to/app.yml \
  --confirm-pending \
  --out /absolute/path/to/import-result.json
```

Do not update an existing standalone Agent app through `--app-id`; current Agent package import creates a new Agent app. Workflow and advanced-chat drafts may be updated when the target endpoint supports it.

### 8. Resolve imported New Agent setup

After import:

1. inspect `warnings` from the import result;
2. select an authorized model credential;
3. reinstall/authorize Tools and test each minimum read action;
4. reattach omitted Skill archives and Files, then insert structured Prompt references when their content must load every run;
5. remap Knowledge datasets and verify retrieval;
6. resolve human contacts and secrets;
7. validate Composer state;
8. publish the Agent draft;
9. for roster reuse, bind the published Agent to the Workflow and publish the Workflow again.

For deterministic standalone Agent lifecycle operations in a local/self-hosted target, the helper exposes:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-create --name "Demo Agent" --out agent-create.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-build-checkout --agent-id "$AGENT_ID" --out build-checkout.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-build-save --agent-id "$AGENT_ID" --payload-json build-payload.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-build-apply --agent-id "$AGENT_ID" --out build-apply.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-composer --agent-id "$AGENT_ID" --payload-json composer.json --validate-only
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-publish --agent-id "$AGENT_ID" --version-note "Validated demo version"
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-inspect --agent-id "$AGENT_ID" --out agent-inspect.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-skill-package --skill-dir /absolute/path/to/agent-skill --out skill-package.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-skill-upload --agent-id "$AGENT_ID" --skill-dir /absolute/path/to/agent-skill --out skill-upload.json
python3 "$SKILL_DIR/scripts/dify_ce_console.py" agent-skills-list --agent-id "$AGENT_ID" --out skills-list.json
```

Use Composer payloads copied from or validated against the exact target version. Do not invent Build/Composer fields from an older release.

Build Mode produces a reviewable draft. It does not replace Apply, configuration validation, publish, binding, or runtime testing.

For a Build-driven Agent, record these as separate evidence states:

1. Build Draft generated;
2. Build Draft reviewed and Applied to the ordinary Draft;
3. ordinary Draft validated;
4. Agent published to an immutable Snapshot;
5. Workflow Draft bound to that Agent/Snapshot;
6. Workflow published with the intended binding;
7. runtime trace verified.

### 9. Test the correct surface

Use `difyctl` first when available:

```bash
difyctl help -o json
difyctl auth whoami
difyctl describe app "$APP_ID" -o json
difyctl run app "$APP_ID" --inputs-file /absolute/path/to/inputs.json -o json
```

Use Console draft runs for Workflow/advanced-chat iteration:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" run-draft \
  --app-id "$APP_ID" --mode workflow \
  --inputs-json /absolute/path/to/inputs.json \
  --out /absolute/path/to/draft-run.json
```

Use the published Service API for final integration proof:

```bash
# Workflow
python3 "$SKILL_DIR/scripts/dify_ce_console.py" service-run \
  --api-key-env DIFY_APP_API_KEY \
  --inputs-json /absolute/path/to/inputs.json \
  --out /absolute/path/to/service-run.json

# Standalone New Agent / chat endpoint
python3 "$SKILL_DIR/scripts/dify_ce_console.py" service-chat-run \
  --api-key-env DIFY_AGENT_API_KEY \
  --query "Run the approved demo task." \
  --inputs-json '{}' \
  --out /absolute/path/to/agent-service-run.json
```

For a Workflow Agent V2 node, verify the trace shows the intended Agent and Snapshot, the upstream values reached `agent_job`, declared outputs match type, and downstream branches consumed the expected fields.

If the Agent invokes an internal ask-human action, treat `paused` as an expected intermediate state rather than success or failure. Capture the run/session and approval form identifiers, resume through the target version's supported Human Input endpoint, then verify that the same Agent binding/Snapshot continues to a terminal result. Do not mark the test passed at the pause boundary.

### 10. Debug from evidence

- Import failure: DSL version, app mode, Agent package refs, plugin dependencies, unsupported nodes, bad YAML.
- Import warnings: omitted assets, missing datasets, unauthorized Tools, missing secrets or contacts.
- Publish failure: unpublished roster Agent, missing model, invalid Tool authorization, unresolved Knowledge, invalid previous-node topology, invalid declared outputs.
- Runtime failure: model/provider, tool credential, Knowledge retrieval, network path, input type, output contract, branch selector.
- Paused Agent: unresolved ask-human form, expired request, wrong resume token, or resume applied to a different run.
- Published mismatch: stale Agent Snapshot binding or Workflow not republished after Agent changes.

Save node events and trace evidence. Do not infer success from the final text alone.

### 11. Report honestly

Separate:

- generated and statically validated;
- imported with warnings;
- configured and published;
- draft-tested;
- Service-API-tested;
- external delivery/write verified.

Label all mock data and supporting services. List remaining demo, production, data, and product gaps.

## Expected artifacts

```text
<case>-demo-assets/
  workflows/
  agents/
  knowledge-base-docs/
  mock-data/
  mock-services/
  validation/
  import-result.json
  run-result.json
  service-run-result.json
  demo-operator-runbook.md
```

## Output format

```markdown
## Status

## Built / Changed

## Tested

## Current Gaps

## Next Iteration

## Files
```

Include exact app names/IDs, test inputs, evidence paths, target Dify version, DSL version, Agent package mode, import warnings, and any mock or credential dependency.
