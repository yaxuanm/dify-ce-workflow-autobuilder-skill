# New Agent portable DSL reference

## Contents

1. Source-of-truth files
2. Support matrix
3. Standalone Agent package
4. Workflow Agent V2 package
5. Import semantics
6. Post-import checklist
7. Validation and testing
8. Build Draft and generator boundaries

## 1. Source-of-truth files

Confirm these paths in the exact target Dify checkout. Names may move in later releases.

| Concern | Current source path |
|---|---|
| App DSL version | `api/constants/dsl_version.py` |
| Agent package DTO and secret stripping | `api/services/agent/dsl_entities.py` |
| Agent package export/import | `api/services/agent/dsl_service.py` |
| App and Workflow DSL integration | `api/services/app_dsl_service.py` |
| Agent V2 discriminator | `api/core/workflow/nodes/agent_v2/discriminator.py` |
| Agent V2 publish validation | `api/core/workflow/nodes/agent_v2/validators.py` |
| Agent Soul and Workflow job schemas | `api/models/agent_config_entities.py` |
| Agent Composer endpoints | `api/controllers/console/agent/composer.py` |
| Agent publish/API endpoints | `api/controllers/console/agent/roster.py` |

At the inspected current-main snapshot, the app DSL version is `0.7.0` and portable Agent package schema version is `1`. Always re-read the target checkout rather than copying these values blindly.

## 2. Support matrix

### Legacy Agent

A legacy Agent node may also use `type: agent`, but it does not have both:

```yaml
version: '2'
agent_node_kind: dify_agent
```

Never convert a legacy node by changing only those two fields. Agent V2 stores the reusable configuration in an Agent Soul Snapshot and stores Workflow-specific instructions in a separate node binding.

### Agent V2 without portable package support

If the target has Agent V2 nodes but lacks `api/services/agent/dsl_service.py`, create/configure/publish the Agent through the target Composer API or UI, then bind it to the Workflow. Use a same-version fresh export as the artifact. Do not generate `agent_packages` for a runtime that does not implement them.

### Portable Agent DSL

Portable DSL is supported only when App DSL import/export processes top-level `agent_packages`. It supports:

- standalone `app.mode: agent` packages;
- Workflow/advanced-chat Agent V2 nodes backed by packages;
- dependency analysis for models, Tools, and Knowledge models;
- import warnings for resources that need target-workspace setup.

## 3. Standalone Agent package

Minimal structural example. Replace model/provider values with identifiers verified in the target workspace.

```yaml
version: 0.7.0
kind: app
app:
  name: Portable Research Agent
  mode: agent
  icon: "🤖"
  icon_background: '#FFEAD5'
  description: Demo-safe reusable research Agent.
  use_icon_as_answer_icon: false
agent:
  package_ref: agent_1
agent_packages:
  agent_1:
    schema_version: 1
    metadata:
      name: Portable Research Agent
      description: Demo-safe reusable research Agent.
      role: Researcher
      icon_type: emoji
      icon: "🤖"
      icon_background: '#FFEAD5'
    soul:
      schema_version: 1
      prompt:
        system_prompt: >-
          Review the request, use configured read-only evidence sources, and
          return a concise recommendation with citations and uncertainty.
      tools:
        dify_tools: []
        cli_tools: []
      knowledge:
        sets: []
      human:
        contacts: []
        tools: []
      env:
        variables: []
        secret_refs: []
      config_skills: []
      config_files: []
      config_note: Imported portable draft; configure and publish before use.
      sandbox:
        provider: null
        config: {}
      memory:
        scope: null
        budget: null
        artifacts: []
      model:
        plugin_id: VERIFIED_MODEL_PLUGIN_ID
        model_provider: VERIFIED_MODEL_PROVIDER
        model: VERIFIED_MODEL_NAME
        credential_ref: null
        model_settings:
          temperature: 0.2
      app_features:
        file_upload:
          enabled: true
      app_variables: []
      misc_legacy: {}
    omitted_assets: []
dependencies: []
```

Import creates a new Agent app and an editable unpublished draft. Current import rejects using Agent DSL to overwrite an existing Agent app.

## 4. Workflow Agent V2 package

The Workflow retains its ordinary `workflow.graph`. Add a top-level package and use this node-data shape:

```yaml
workflow:
  graph:
    nodes:
      - id: agent-review
        type: custom
        position: {x: 500, y: 200}
        positionAbsolute: {x: 500, y: 200}
        sourcePosition: right
        targetPosition: left
        data:
          type: agent
          version: '2'
          agent_node_kind: dify_agent
          title: Review with New Agent
          desc: Review live Workflow context with a portable Inline Agent.
          selected: false
          agent_binding:
            binding_type: inline_agent
            package_ref: agent_1
          agent_job:
            schema_version: 1
            mode: tell_agent_what_to_do
            workflow_prompt: >-
              Review the upstream request and return the declared fields only.
            previous_node_output_refs:
              - selector: [start-node, request]
            declared_outputs:
              - name: recommendation
                type: string
                description: Concise recommendation for downstream nodes.
                required: true
                failure_strategy:
                  retry:
                    enabled: false
                    max_retries: 0
                    retry_interval_ms: 0
                  on_failure: stop
                  default_value: null
            human_contacts: []
            metadata: {}
agent_packages:
  agent_1:
    # Same AgentPackage structure as the standalone example.
```

Important rules:

- `agent_binding` in portable DSL uses `package_ref`, not persisted `agent_id` or `current_snapshot_id`.
- `agent_job` is required for portable Workflow binding and is removed from graph data after import; the backend persists it in `WorkflowAgentNodeBinding`.
- All package-backed Workflow imports materialize node-owned Inline Agents. A source Roster binding is not preserved as a cross-workspace reusable Roster relationship.
- To reuse one Roster Agent across Workflows, import/publish the standalone Agent and bind it in the target workspace after import.
- `previous_node_output_refs` must point to real upstream nodes.
- If `declared_outputs` is empty, runtime defaults are `text`, `files`, and `json`; declare explicit outputs when downstream nodes require a stable contract.
- Declared output names must match `^[A-Za-z_][A-Za-z0-9_]*$`.
- Do not place Prompt, Skills, Files, Tools, Knowledge, model, memory, or sandbox overrides in Workflow job metadata.
- `AgentPackage`, Agent Soul, and `agent_job` use strict schemas. Remove legacy fields such as `workspace_skills` and `agent_strategy_*`; do not copy graph-projected `agent_task` or `agent_declared_outputs` into the portable package/job contract.

## 5. Import semantics

Portable export deliberately strips workspace-sensitive values.

### Model

- `credential_ref` is removed.
- The model provider plugin and selected model identifiers remain dependencies.
- Import does not prove the target workspace has an authorized model credential.

### Dify Tools

- credentials and secret-like runtime parameters are removed;
- exported Tools become `credential_type: unauthorized` with no `credential_ref`;
- provider/tool identity remains for dependency analysis;
- reconnect credentials and run a minimum tool test after import.

### Skills and Files

- binary/file payloads are not embedded in YAML;
- exported `config_skills` and `config_files` receive `file_id: ''` and `is_missing: true`;
- `omitted_assets` preserves names, sizes, hashes, and MIME hints;
- re-upload/recreate the Skill archive and File, then replace missing references;
- insert structured Skill/File Prompt mentions when their contents must be eagerly loaded every run.

Do not claim that a successful YAML import carried Skill or File content.

### Knowledge

- package DSL retains dataset IDs and names;
- import preserves datasets found in the target tenant;
- missing datasets are replaced with unresolved portable IDs and warnings;
- recreate/remap datasets, verify indexing, and hit-test retrieval.

Agent V2 uses explicit `knowledge.sets`. Each set contains:

- unique `id` and case-insensitive unique `name`;
- one or more datasets;
- `query.mode`: `user_query` or `generated_query`;
- retrieval mode/settings;
- metadata filtering: `disabled`, `automatic`, or `manual`.

### Human contacts and secrets

- workspace/contact IDs and tenant IDs are removed;
- secret references retain only non-secret metadata;
- import warnings identify unresolved contacts and secrets;
- resolve them in the target workspace before publish.

## 6. Post-import checklist

Do these in order:

1. Save the complete import response and inspect `status`, `app_mode`, and `warnings`.
2. Confirm all declared plugin dependencies are installed.
3. Select and authorize the Agent model.
4. Reconnect every Tool credential and verify a minimal read-only call.
5. Reattach each omitted Skill and File; confirm hashes/names when available.
6. Remap Knowledge datasets and verify expected retrieval hits.
7. Resolve contacts, environment variables, and secret references.
8. Validate Agent Composer configuration.
9. Apply any Build draft; Build output alone is not active configuration.
10. Publish the Agent.
11. If using a Roster Agent, bind the intended published Agent in the Workflow Composer and republish the Workflow.
12. Confirm the runtime trace reports the intended Agent and Snapshot.

## 7. Validation and testing

Static validation:

```bash
python3 "$SKILL_DIR/scripts/validate_new_agent_dsl.py" app.yml \
  --target-repo /path/to/dify \
  --out validation/new-agent.json
```

Import:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" import app.yml \
  --confirm-pending \
  --out import-result.json
```

Published Agent Service API:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" service-chat-run \
  --api-key-env DIFY_AGENT_API_KEY \
  --query "Review this demo request." \
  --inputs-json '{}' \
  --out agent-service-run.json
```

Workflow Agent V2 acceptance must prove:

- the Agent is published or the imported Inline Agent is valid;
- the binding references the intended current Snapshot;
- upstream values reach the Agent job;
- Skills/Files/Knowledge/Tools actually participate when claimed;
- declared outputs pass type validation;
- downstream nodes use the expected output;
- published behavior matches the tested draft/current version.

## 8. Build Draft and generator boundaries

### Build Draft is temporary editor state

New Agent Build Mode writes an editor-scoped Build Draft. It is not the ordinary Agent Draft and is not exported as App DSL. The reliable lifecycle is:

1. checkout/save the Build Draft;
2. review generated Prompt, Skill, File, and other changes;
3. Apply the Build Draft to the ordinary Draft;
4. validate the ordinary Draft;
5. publish the Agent to create an immutable Snapshot;
6. bind or refresh the Workflow Agent node;
7. publish and runtime-test the Workflow.

The current Console surfaces are rooted at:

```text
POST /console/api/agent
PUT  /console/api/agent/{agent_id}/composer
POST /console/api/agent/{agent_id}/composer/validate
POST /console/api/agent/{agent_id}/publish
PUT  /console/api/apps/{app_id}/workflows/draft/nodes/{node_id}/agent-composer
```

Build Draft checkout/save/apply endpoints live beside the Agent roster endpoints and must be re-read from the target checkout before automation because that surface is newer and may change independently from App DSL.

### The current graph generator is not an Agent-package generator

At the inspected current-main snapshot, the Workflow generator planner has no first-class Agent V2 node contract, its snippets do not own the V2 package schema, and the generated result is a graph rather than a complete App DSL envelope. Adding one `agent` node snippet is insufficient because New Agent portability also needs top-level `agent_packages` and import materialization.

Use one of two paths:

- **External portable YAML:** generate the whole App DSL, package, V2 node, and job; validate; import; reconcile assets and credentials.
- **Studio materialization:** generate/save a V2 node shell, then use Agent Composer to create the Inline Agent, Snapshot, and `WorkflowAgentNodeBinding`; read back the projected graph before publish.

Do not place `package_ref` in a normal graph-only save and assume it will materialize. Package materialization is an App DSL import behavior.
