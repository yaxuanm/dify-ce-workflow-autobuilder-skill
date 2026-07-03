---
name: dify-ce-workflow-autobuilder
description: Automatically design, generate, import, test, debug, publish, and verify Dify workflows or chatflows in a local Dify CE environment. Use when the user wants Codex to build a Dify workflow from requirements, use local CE/console API, import DSL automatically, run draft tests, inspect node traces, iterate failures, or turn a demo plan into working Dify apps. Start by cloning or locating the Dify repo for product/schema grounding.
---

# Dify CE Workflow Autobuilder

## Purpose

Build Dify workflows end to end in a local CE environment: turn requirements into a capability-proof plan, generate workflow DSL, import it through the Console API, run draft tests, inspect traces, fix failures, publish when needed, and verify the Service API.

This skill is for local/self-hosted Dify CE work, especially demo workflows where the user expects Codex to keep iterating until the workflow runs.

## Preconditions

Use this skill when the environment is a **local or self-hosted Dify CE deployment**, normally started with Docker or Docker Compose, and Codex can access the host shell.

Expected baseline:

- Dify is running locally or on a reachable self-hosted machine.
- The API service is containerized, commonly named `docker-api-1`.
- Codex can run `docker ps` and `docker exec` on the host.
- Codex can read `SECRET_KEY` from the API container to create a short-lived Console API JWT.
- The Dify web/API base URL is reachable, usually `http://localhost`.
- A console account already exists in the local Dify instance.
- Model providers and plugin credentials needed by the workflow are already configured, or the task includes configuring/mocking them.

If Dify CE is **not installed or not running**, do not continue into workflow import/debug commands. Return the CE installation guide below, tailored to the user's OS when known, and ask them to run the setup or grant permission for Codex to do it.

This skill is **not** the right default for:

- Dify Cloud where Codex cannot access the backend container or `SECRET_KEY`.
- A locked-down customer environment where shell/container access is unavailable.
- Production data migration or destructive workspace cleanup unless the user explicitly asks.

For non-local or locked-down environments, fall back to public/service APIs, exported DSL review, manual import instructions, or ask for a workspace/API credential path.

## Golden Rule

Start from what the user or customer needs to prove, not from nodes. The workflow is only good when the required scenarios pass and the trace proves the right data sources, branches, calculations, and final answer behavior.

Before building, show the user a concise proposed structure and wait for confirmation unless they have already approved that structure in the same turn. The structure should cover app shape, main workflows/chatflows, data sources, node families, mock vs real boundaries, and validation scenarios. Do not generate DSL, create/import knowledge bases, create/start mock services, import apps, or run Console API automation until the user confirms the structure or explicitly asks to proceed without confirmation.

If any part of the proposed solution is ambiguous in a way that changes the app surface, data-source boundary, credential boundary, privacy posture, or validation criteria, ask the user a short clarification question before designing or building. If the user's intent is clear enough to choose the app surface and data-source boundaries safely, make the choice in the proposed structure and explain it briefly instead of asking unnecessary questions.

## Generation Quality Gate

Before importing a generated workflow, audit the DSL for node composition and demo fidelity. Do not treat "imports successfully" as a good generation.

### Capability And Integration Selection First

Start from the capability the demo must prove, then choose the best available implementation surface. Dify official nodes are important schema/product grounding, but they are not a ceiling. Marketplace/installed plugins, Agent nodes, tool nodes, search tools, crawler/browser-style tools, HTTP APIs, and user-approved mock services can all be valid first-class implementation choices when they fit the requirement.

Before choosing a Code node, check Dify's official node capabilities and the available plugin/tool options. Use the most specific node, plugin, or tool that matches the job. Current official node families include:

- Start / User Input
- LLM
- Knowledge Retrieval
- Answer
- Output
- Agent
- Question Classifier
- If-Else
- Human Input
- Iteration
- Loop
- Code
- Template
- Variable Aggregator
- Document Extractor
- Variable Assigner
- Parameter Extractor
- HTTP Request
- List Operator
- Tool

Use the official docs, installed/Marketplace plugin information, and the local Dify repo/exported DSL examples to confirm exact schema and availability for the local version before generating YAML. If the local version differs from current docs or plugin examples, follow the local Dify version for DSL compatibility and note the difference in the report.

Regenerate or revise the DSL before import when any of these are true:

- A workflow that needs natural-language understanding, generation, personalization, summarization, classification, extraction, or comparison has no LLM-backed node (`LLM`, `Question Classifier`, `Parameter Extractor`, `Agent`, or a plugin/tool that clearly performs the AI step).
- A workflow proves RAG, semantic search, source attribution, policy lookup, catalog search, document grounding, or content grounding without a Knowledge Retrieval node or a documented external retrieval/tool equivalent.
- A workflow proves live data, operational actions, database queries, third-party integrations, notifications, webhooks, or mutable system behavior without a Tool, HTTP Request, plugin node, or documented mock service boundary.
- A workflow proves web search, social listening, marketing research, competitor monitoring, lead/account research, content monitoring, crawler-based extraction, or trend analysis without first checking suitable search/browser/crawler/social/marketing plugins or tools.
- A generated app collapses the whole demo into one or two large Code nodes.
- Code nodes contain large static datasets, full catalogs, long natural-language templates, customer-facing prose, or behavior that should live in KB docs, mock-data files, tool responses, workflow variables, Template nodes, or LLM prompts.
- A conversational user experience is built as a technical workflow with many manual inputs when it should be an `advanced-chat` app with defaults, hidden/pre-filled context, routing, memory, or conversation variables.

Use Code nodes for deterministic work only: parsing small payloads, normalizing tool outputs, calculating numeric/business rules, selecting from already-retrieved candidates, validating required fields, deduplicating or merging arrays, and assembling structured context for downstream nodes. Code may create a deterministic fallback summary, but it should not be the primary writer, classifier, extractor, retriever, router, or integration boundary when a dedicated Dify node can do that.

Prefer these official nodes before Code:

| Need | Prefer These Nodes Before Code |
|---|---|
| User intent routing | Question Classifier, Parameter Extractor, If-Else for simple deterministic checks |
| Structured extraction from natural language | Parameter Extractor, LLM structured output |
| Answer writing or personalized messages | LLM, Answer, Template for deterministic formatting |
| Retrieval or source-grounded answers | Knowledge Retrieval plus LLM context |
| External data or actions | Tool, plugin-provided tool nodes, HTTP Request, user-approved mock service |
| Web search / research | Search plugin/tool, Agent with search tool, browser/crawler plugin, HTTP API when no plugin is suitable |
| Social listening / marketing monitoring | Social/search/crawler/plugin tool, Agent with tools, scheduled/batch workflow, HTTP API when no plugin is suitable |
| File/document processing | Document Extractor, List Operator, LLM vision where appropriate |
| Batch processing | Iteration, Loop, List Operator, Variable Aggregator |
| Persistent conversational state | Variable Assigner, conversation variables, memory-enabled LLM nodes |
| Human review or approval | Human Input |
| API/workflow return values | Output for workflows, Answer for chatflows |

Common app-shape expectations:

| Pattern | Minimum Expected Shape |
|---|---|
| Conversational assistant | `advanced-chat`, User Input/Start, Question Classifier or Parameter Extractor when routing/extraction is needed, Tool/HTTP/Knowledge Retrieval for real sources, LLM final answer, Answer nodes for routed responses. |
| Retrieval-grounded Q&A | User Input/Start, Knowledge Retrieval, LLM using retrieval context, Answer/Output with source-aware wording. |
| External action or live lookup | User Input/Start, Parameter Extractor or deterministic input validation, Tool/HTTP/plugin node, If-Else or error branch, LLM/Template/Answer/Output for the result. |
| Batch or proactive processing | Trigger/User Input, Tool/HTTP/plugin/mock-data boundary for batch source, Iteration/List Operator where the batch should be itemized, If-Else for deterministic conditions, LLM/Template for generated content, Tool/HTTP for send/write actions when claimed, Output summary. |
| Evaluation or comparison | Shared retrieved/tool context, two or more LLM or tool variants, deterministic comparison/diagnosis node only after variant outputs exist, trace-friendly outputs. |
| Web/social/marketing research | Input/topic/source config, search/crawler/social/plugin tool or Agent, Iteration/List Operator for result sets, LLM extraction/synthesis, citation/source output, optional schedule/monitor summary. |

After generation, report the node mix (`start`, `question-classifier`, `tool`, `http-request`, `knowledge-retrieval`, `code`, `llm`, `answer/end`) and explicitly call out whether the app is a **schema/import smoke**, **demo-ready visual**, **LLM-backed demo**, **schedule-trigger proof**, or **production-shaped prototype**.

## API Surfaces

Use two API surfaces, and do not confuse them:

1. **Console API: build-time and debug-time automation**
   - Purpose: import DSL, update draft apps, run draft workflows/chatflows, inspect streamed node events, publish apps, enable API, create/reuse app API keys.
   - Auth: short-lived Console API JWT signed with local `SECRET_KEY` from the Dify API container.
   - Typical endpoints:
     - `POST /console/api/apps/imports`
     - `POST /console/api/apps/{app_id}/workflows/draft/run`
     - `POST /console/api/apps/{app_id}/advanced-chat/workflows/draft/run`
     - `POST /console/api/apps/{app_id}/workflows/publish`
     - `POST /console/api/apps/{app_id}/api-enable`
     - `GET/POST /console/api/apps/{app_id}/api-keys`
   - Use this for iterative debugging because it exposes draft behavior and node-level SSE events.

2. **Service API: published app integration test**
   - Purpose: simulate the frontend, portal, service, or external caller using endpoint + API key.
   - Auth: app API key, usually `Authorization: Bearer <app_api_key>`.
   - Typical endpoint:
     - `POST /v1/workflows/run`
   - Use this after publish to prove embeddability and integration behavior. Compare with Console API draft run when UI/draft behavior differs from published API behavior.

## Standard Run Loop

1. **Clone or locate Dify first**
   - If a Dify repo path is provided, use it.
   - Otherwise, from the workspace:

```bash
if [ ! -d dify/.git ]; then
  git clone https://github.com/langgenius/dify.git dify
fi
```

   - Inspect the repo and any exported examples before generating DSL. Useful areas include `api/core/workflow`, app/workflow import code, plugin/tool schemas, and existing exported workflow YAMLs in the user's workspace.
   - Do not edit the Dify repo unless the user explicitly asks. Use it as schema/product grounding.

2. **Confirm local CE access**
   - Verify the local environment is running:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | rg 'dify|docker-(api|web|worker|db)|postgres|redis'
curl -I http://localhost
```

   - If Docker is missing, no Dify containers are running, the API container cannot be found, or `curl` cannot reach the base URL, stop and return this local CE install guide instead of attempting Console API calls:

```bash
# Prerequisites:
# - Docker installed and running
# - Docker Compose 2.24.0 or later
docker compose version

# Clone the latest Dify release and start CE with Docker Compose.
git clone --branch "$(curl -s https://api.github.com/repos/langgenius/dify/releases/latest | jq -r .tag_name)" https://github.com/langgenius/dify.git
cd dify/docker
cp .env.example .env
docker compose up -d

# Check containers and open the setup wizard.
docker compose ps
open http://localhost || true
```

   - Official references:
     - Docker Compose quick start: `https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose`
     - Environment variables: `https://docs.dify.ai/en/self-host/deploy/configuration/environments`
   - Minimum practical checks:
     - Docker is running.
     - `docker compose version` reports 2.24.0 or later.
     - The host has enough resources for local CE; use at least 2 CPU cores and 4 GiB RAM, and prefer 8 GiB memory on Docker Desktop.
     - Port 80 is free, or change `EXPOSE_NGINX_PORT` in `dify/docker/.env` before starting.
   - After startup, create the first console account in the browser. The Console API helper needs a local account because its short-lived JWT is signed for an account id.
   - If installing inside the current workspace would conflict with an existing `dify/` checkout, create a separate folder such as `/Users/<user>/Desktop/dify-ce-local` and run the commands there.
   - The helper can print this guide directly:

```bash
python3 "$SKILL_DIR/scripts/dify_ce_console.py" install-guide
```

   - Default assumptions from the user's local CE setup:
     - Base URL: `http://localhost`
     - API container: `docker-api-1`
     - Console API auth can be created by signing JWTs with `SECRET_KEY` from the API container.
   - If the container names differ, discover them from `docker ps` and pass overrides to the helper with environment variables.

3. **Define the proof plan before writing DSL**
   - Extract capabilities, demo scenarios, go/no-go signals, data sources, and expected outputs.
   - Present a concise structure for user confirmation before building:
     - app surface: `advanced-chat`, `workflow`, frontend-backed app, or a combination
     - major workflows/chatflows and their responsibilities
     - data sources: KB, Tool/plugin, HTTP/mock service, database, uploaded files, public API, or manual input
     - node-family sketch: classifier, extractor, retrieval, tool/API, code, template, LLM, answer/output
     - real vs mock boundaries and production replacement path
     - 2-5 representative test scenarios
   - Wait for user confirmation before generating DSL, building KBs, creating mock services, importing apps, running draft tests, publishing, or enabling API access. If the user only asked for architecture/design, stop after the structure and next-step recommendation.
   - Separate:
     - what must be implemented in workflow nodes
     - what can be shown in Dify UI/logs
     - what should be mocked and clearly labeled
   - Prefer customer-style queries and expected outputs over internal node descriptions.
   - Write an acceptance matrix before generating DSL:
     - node-shape expectations
   - required real data boundaries (KB, Tool/plugin, HTTP/mock service, database, API, file input, or human review)
     - search/listening/marketing source boundaries, such as web search, crawler, social platform, ads/CRM/analytics system, RSS/news, or approved mock data
     - where LLM must be used
     - where Code is acceptable
     - draft-run test cases and expected route/output
   - If Code nodes become the dominant part of the workflow, pause and reconsider whether official nodes such as Question Classifier, Parameter Extractor, Template, List Operator, Iteration, Tool, HTTP Request, Knowledge Retrieval, or LLM would express the behavior more clearly.

4. **Design the app surface**
   - Use a **chatflow / advanced-chat** when the user experience should be conversational and the user should not manually fill many technical inputs.
   - Use a **workflow** when the flow is batch, scheduled, evaluation-oriented, API-first, or requires explicit structured inputs.
   - If the user's intent clearly describes a conversational internal assistant, support bot, knowledge assistant, employee copilot, account assistant, or multi-turn helper, choose `advanced-chat` in the proposal by default and include the routing/classifier shape.
   - If the user's intent clearly describes batch processing, scheduled scans, API-first automation, structured evaluation, report generation, or one-shot backend processing, choose `workflow` in the proposal by default.
   - If the app surface is ambiguous and either `advanced-chat` or `workflow` could materially change the user experience, ask a concise clarification question before generating DSL.
   - If multiple capabilities belong to one user journey, do not split them into separate workflows only because the requirement table has many rows.
   - Add a Question Classifier or router before expensive retrieval/tool calls when not every question needs every data source.
   - For conversational apps, default to `advanced-chat` with a classifier/router when the app has distinct user intents. A plain workflow is acceptable for service/API proof, scheduled/batch work, or exposing an underlying automation canvas, but it is usually not the primary end-user chat experience.

5. **Build the DSL**
   - Use existing exported YAMLs as local patterns when possible.
   - Avoid a single long Code-node-only line. That shape is hard to explain, hard to inspect, and usually fails to prove Dify's workflow value.
   - Keep independent lookups parallel where the canvas supports it. For example, after intent/profile preparation, run profile lookup, structured DB query, KB retrieval, and live API lookup in parallel when they do not depend on each other.
   - Use LLM nodes for language generation, explanation, summarization, classification, prompt-variant comparison, and final user-facing answers.
   - Use Code nodes for deterministic business rules only: calculations, thresholds, constrained selection from upstream candidates, validation, normalization, structured aggregation, and safe fallback envelopes.
   - The final answer for a conversational demo should normally pass through an LLM node unless the proof point is strictly structured/API-only.
   - For generated natural-language content, use an LLM node unless the text is a fixed deterministic status message. Code may prepare context and fallback fields; it should not be the only personalized writer.
   - Use Knowledge Retrieval nodes for user-approved RAG/semantic search requirements. Do not fake retrieval with hard-coded content lists if the customer is evaluating retrieval.
   - Use Tool/plugin/Agent/HTTP nodes for live data, search, social listening, crawler extraction, marketing research, and external actions. Prefer a suitable installed or Marketplace-listed plugin/tool over HTTP Request whenever one exists and can be configured.
   - Keep configuration values out of Code nodes where possible. Use workflow variables, environment variables, input defaults, mock-data files, KB documents, or service config files instead.

6. **Use Marketplace-listed plugins and tools first when an integration, search, or research capability is needed**
   - This is generic for every project and every external system.
   - Before using HTTP Request or a local mock service, check whether Dify already has a Marketplace-listed plugin, installed plugin, Agent tool, or built-in provider for the required capability: web search, crawler/browser extraction, social listening, news/RSS, database, storage, CRM, email, ads/marketing analytics, collaboration tool, model provider, data warehouse, or API service.
   - Let Codex choose the best-fit plugin based on the requirement, available credentials, local installability, maintenance/source confidence, and whether the plugin exposes the exact action needed.
   - Official or well-maintained plugins are preferred when several Marketplace-listed plugins overlap, but the rule is not limited to official plugins.
   - Plugin discovery must be portable. Do not rely on any user's local checkout, historical DSL files, memory, or machine-specific context unless that source exists inside the current workspace or was explicitly provided for this run.
   - Portable plugin discovery fallback order:
     1. If the current workspace has a Dify repo with `dify/api/core/dsl_agent/plugin_resolver.py`, use it and report that source.
     2. If no local resolver exists and network is available, clone or update `https://github.com/langgenius/dify-official-plugins.git` in the current workspace and inspect provider/tool manifests there.
     3. If package identifiers are needed and network is available, query the public Marketplace manifest at `https://marketplace.dify.ai/api/v1/dist/plugins/manifest.json`. If the batch endpoint is unavailable or returns 403, use this public manifest fallback.
     4. If network is unavailable, use only sources already present in the workspace or explicitly provided by the user. If those sources are insufficient to identify an exact plugin schema, stop at a design/manual-install artifact and state what source is missing.
     5. If the chosen plugin requires credentials, stop at the credential boundary and label it clearly. Missing credentials are not a DSL-generation failure.
   - Do not embed a static plugin catalog inside this skill. The plugin list changes over time, so generated workflows must be grounded in current workspace files, cloned official/plugin sources, Marketplace responses, installed plugin metadata, or user-provided plugin documentation.
   - For every generated artifact that uses plugin discovery, save a short `plugin-discovery.md` or report section with: discovery sources, selected plugin/tool, exact package identifier when verified, credential boundary, and whether any machine-specific context was used.
   - Treat plugin installation and provider configuration as separate steps:
     - **Plugin dependency in DSL:** the app declares which plugin package it needs.
     - **Plugin installation:** the workspace has the plugin package installed.
     - **Provider/tool configuration:** the workspace has the required credentials or default provider settings for that plugin/tool.
     - Import success does not prove provider configuration. A draft run error such as a missing/default provider usually means the package or credential/configuration layer is incomplete.
   - Before installing any missing plugin, show the user a confirmation prompt. When the current Codex surface supports a native confirmation dialog, use that dialog; otherwise ask a concise explicit confirmation in chat. The confirmation should name the plugin, source, version/package identifier when known, why it is needed, and any expected credential/cost/network implications.
   - After the user confirms installation, install through the safest available path:
     - Prefer Dify's current Console API or plugin management API only after verifying the endpoint and request schema in the current Dify repo/version.
     - If the API path is unavailable or uncertain, guide the user through Dify's Marketplace/plugin UI and keep the workflow at the manual-install boundary.
     - Save install evidence or the manual-install instructions in the artifact report.
   - After installation, check whether the selected plugin/tool needs provider credentials or configuration:
     - If configuration is required and credentials are not available, stop and tell the user exactly what must be configured in Dify before draft run can pass.
     - If the user provides credentials or points to an approved secret source, configure them through Dify's provider/plugin credential UI or verified Console API. Do not print secrets in logs or reports.
     - If automatic configuration is unsafe, unavailable, or ambiguous, provide precise UI steps and mark draft run as blocked on credentials/configuration.
   - Do not claim a plugin-backed workflow is tested until the plugin is installed, configured, and at least one minimal tool invocation or draft run has succeeded.
   - Recommended plugin flow:
     1. Identify the capability and target system, such as web search, crawler/browser extraction, social platform, news/RSS source, SQL database, data warehouse, storage service, collaboration tool, CRM, email provider, ads/marketing analytics, model provider, or internal API.
     2. Search installed plugins and Marketplace-listed plugin sources for matching providers/actions.
     3. Pick the best-fit plugin. Prefer exact action coverage and clean credential configuration over a generic HTTP workaround.
     4. Check whether the plugin is already installed and whether the needed provider/tool credentials are configured.
     5. Ask for user confirmation before installing a missing plugin, configuring credentials, making external network calls that may incur cost/rate limits, or scraping/crawling third-party sites.
     6. Install missing plugins only after confirmation, using a verified API path or guided UI/manual steps.
     7. Configure credentials through Dify's plugin/provider credential UI or the matching Console API if the current repo exposes one and the user has approved the secret source.
     8. Run a minimal tool test first, such as `select 1`, list one record, fetch one search result, crawl one known URL, send to a test endpoint, or fetch one known object.
     9. Only then wire the plugin node into the workflow DSL or call the plugin-backed workflow tested.
   - Use HTTP Request only when:
     - no suitable Marketplace-listed or installed plugin exists
     - the customer system is custom/internal
     - the demo intentionally uses a small mock service
     - the selected plugin cannot be configured in the available environment and the limitation is documented
   - In reports, state whether a node uses a Marketplace-listed plugin, installed plugin, HTTP Request, or a mock service. Do not present HTTP Request as plugin proof.
   - For search, social listening, and marketing workflows, report the source coverage, rate-limit/cost assumptions, credential status, and whether the result is live, mocked, cached, or manually seeded.

7. **Build knowledge bases when the workflow needs retrieval**
   - Do not create, upload, or index a Knowledge Base unless the user explicitly asks for a KB/RAG/document-retrieval source, provides an existing dataset id, or confirms a proposed KB plan.
   - If the requirements imply retrieval, such as semantic search, source attribution, document grounding, catalog lookup, policy lookup, product documentation lookup, or compliance text, first propose the KB approach and ask for confirmation. Do not silently build a KB just because retrieval would be useful.
   - If the user has not approved a KB, design the workflow with a documented placeholder, manual setup instructions, or an existing-dataset input variable instead of creating/uploading/indexing documents.
   - Do not ask the user to tune low-level KB parameters by default. Use strong defaults and expose only the decisions the user must own.
   - Do not create or upload a KB until the data-source boundary is clear. Ask only the necessary clarification questions:
     - What content should the KB contain, in plain business terms?
     - Is the content real user/customer-provided data, generated mock data, public data, an existing Dify dataset, or a hybrid?
     - If user-provided or public, where is the data: local path, uploaded file, URL, cloud drive, database export, existing dataset id, or another system?
     - Is the data safe to ingest into the local CE environment? Flag any privacy, PII, customer-confidential, licensing, or retention constraints.
     - What are 2-5 representative questions the KB must answer?
   - If these answers are missing and the choice changes trust, privacy, or architecture, pause and ask the user before building. If the user explicitly wants a mock demo and no real data is available, create clearly labeled mock documents and report them as mock data.
   - Default KB settings unless the user asks otherwise:
     - Indexing technique: `high_quality`
     - Embedding provider/model: best configured embedding model available in the local workspace; prefer a strong OpenAI embedding model when configured, such as `text-embedding-3-large`
     - Retrieval method: `hybrid_search` when supported, because it balances semantic and keyword matching
     - Chunk structure: choose a sensible default from the source type; use parent-child for long structured documents when supported, Q&A for explicit question/answer pairs, and general mode for simple short documents or demo mock docs
     - Metadata: infer practical fields from the data source and requirement, then keep them visible in the decision record
     - Top K / score threshold / rerank: use safe defaults first; tune only after hit-testing shows a retrieval-quality issue
   - Tell the user that these retrieval settings can be tuned later in Dify Knowledge settings if they want to optimize precision, recall, cost, or latency.
   - Choose the KB path based on source:
     - **User-provided files:** copy or reference them into a dedicated `knowledge-base-docs/source/` or transformed folder, preserving originals when possible.
     - **User-provided structured exports:** convert rows into retrieval-friendly documents only after deciding which columns are searchable text and which are metadata.
     - **Existing Dify dataset:** reuse the dataset id when it is already indexed and appropriate; do not rebuild unless the user asks or the schema/content is stale.
     - **Public web/docs:** use only if the user approves that source, save source URLs, and keep copyright-safe summaries or transformed docs.
     - **Mock data:** generate small, realistic, explicitly labeled mock docs with enough variety to test retrieval, filters, and failure cases.
   - Keep a short KB decision record in the artifact folder, for example:

```markdown
# Knowledge Base Build Decision

- Data source:
- Source owner / permission:
- Mock or real:
- Source paths / URLs:
- Transformations:
- Metadata fields:
- Test queries:
- KB defaults used:
- Known gaps:
```

   - Prepare KB documents under a local folder, ideally one concept per file:

```text
knowledge-base-docs/
  source/
  product-catalog/
    item-001.md
    item-002.md
  policy-docs/
    policy-001.md
```

   - Put demo-safe metadata in the document text itself, preferably near the top, even if you also configure Dify metadata fields. Keep metadata generic and source-derived; do not invent customer attributes that were not provided:

```markdown
---
source_system: demo_catalog
region: example-region
audience: example-audience
category: example-category
effective_date: 2026-01-01
---
```

   - Before upload, run a quick document review:
     - Confirm files are readable and not empty.
     - Confirm generated mock data is labeled as mock.
     - Confirm user-provided data did not get silently rewritten beyond the intended transformation.
     - Confirm metadata values match the source data.
     - Confirm the KB content does not include secrets or unintended PII.
   - Create/import the KB with the bundled helper:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/dify-ce-workflow-autobuilder"
python "$SKILL_DIR/scripts/dify_ce_console.py" kb-build \
  --name "Demo Product Catalog HQ" \
  --docs-dir /absolute/path/to/knowledge-base-docs/product-catalog \
  --indexing-technique high_quality \
  --embedding-model text-embedding-3-large \
  --embedding-model-provider langgenius/openai/openai \
  --out /absolute/path/to/kb-product-catalog-result.json
```

   - If high-quality indexing fails because the local CE model provider is not configured, either configure the embedding provider or temporarily use `--indexing-technique economy` and clearly mark the semantic-search proof as weaker.
   - Poll indexing status before claiming retrieval is tested. KB creation, document upload, indexing completion, retrieval hit-testing, and workflow retrieval are separate evidence layers.
   - If metadata APIs are available, create metadata fields and apply document metadata. If they are unavailable in the local CE version, keep metadata in the document body/front matter and validate filtering through retrieval output and downstream logic.
   - After KB creation, wire the returned dataset IDs into the workflow DSL's Knowledge Retrieval nodes, then import the workflow.
   - For retrieval-grounded final answers, add a prompt guard or deterministic branch so the LLM does not invent policy/source facts when `Knowledge Retrieval` returns an empty list or irrelevant context. The final answer should say the KB did not return enough evidence and give a safe next step.
   - If the answer must prove several distinct evidence facets, such as approval thresholds, vendor risk, contract terms, regional rules, or product eligibility, do not rely on one broad retrieval query just because it returns some documents. Build enriched retrieval queries from the structured inputs and, when needed, use multiple targeted Knowledge Retrieval nodes so each required proof point has matching evidence.
   - During draft-run validation, compare at least one final answer against the source KB document text. If the LLM contradicts the retrieved/source document, treat the run as failed even when `workflow_finished.status` is `succeeded`.
   - During draft-run validation, check that every required evidence facet from the acceptance matrix is represented in retrieved documents. A non-empty retrieval result is not enough if it misses a required policy area.

8. **Build supporting services only if the workflow needs them**
   - This step is conditional. Do not create a service just because it is possible.
   - Do not create, start, or bind a local mock/supporting service unless the user explicitly asks for a local service/mock API/live API boundary, or confirms a proposed service plan. First explain why the service is needed, what external system it simulates, what local port it will use, what data it will serve, and how it will be stopped.
   - If the user has not approved a local service, design the workflow with a documented placeholder, manual setup instructions, or a non-running mock contract instead of launching a process.
   - Build a local service only when the proof point requires a live tool/API boundary, for example:
     - account lookup, billing lookup, subscription lookup
     - CRM task creation, email/push send simulation, webhook receiver
     - proprietary system lookup that should not be mocked inside a Code node
     - success/failure/timeout behavior that the customer explicitly wants to see
   - Keep the service small and explicit:

```text
mock-services/
  lookup_service.py
  README.md
```

   - Every service should expose:
     - `GET /health` for preflight
     - one or more deterministic demo endpoints
     - a success case
     - at least one demo-safe failure case when failure handling is a requirement
   - Prefer demo-safe failure envelopes when the workflow should continue, for example HTTP 200 with `{ "lookup_status": "timeout" }`, instead of a transport-level 504 that may stop the workflow before the final answer can explain the failure.
   - If the customer needs true transport failure behavior, add a separate endpoint or query flag for that case and test it separately.
   - From local Dify containers, check networking carefully:
     - use `http://host.docker.internal:<port>` when the service runs on the host
     - use `http://<service-name>:<port>` when the service runs on the same Docker network
     - use the future demo-server hostname/IP after migration
   - Save a `README.md` describing endpoints, sample responses, and which workflow nodes call them.
   - Smoke-test before importing/running the workflow:

```bash
curl http://localhost:8765/health
curl http://localhost:8765/record/demo_success
curl http://localhost:8765/record/demo_timeout
```

   - For every generated HTTP/tool dependency, test at least one real business endpoint, not only `/health`. If the workflow calls `GET /profile/{id}`, `GET /records`, `POST /send`, or any domain-specific endpoint, warm and verify those endpoints before the Dify draft run.
   - If a service cold-starts slowly, run the endpoint once outside Dify first and record that preflight result. Do not diagnose a draft-run failure as a DSL problem until the service endpoint is known to return from both the host and, when relevant, the Dify API container.
   - From the Dify API container, verify host/container networking when a generated URL uses `host.docker.internal`, `api:<port>`, or another Docker-network hostname:

```bash
docker exec docker-api-1 sh -lc 'python - <<'"'"'PY'"'"'
import urllib.request
for url in ["http://host.docker.internal:8765/health", "http://api:8765/health"]:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            print(url, r.status)
    except Exception as exc:
        print(url, "ERR", exc)
PY'
```

   - Wire the service into Tool/HTTP/plugin nodes. Do not hide a required API behavior inside a large Code node if the point of the demo is tool-calling.
   - In the final report, label the service clearly as mock/demo infrastructure and state the production replacement path.

9. **Import via Console API**
   - Use Console API for automatic import. This is the local-CE path that avoids manual UI import during iteration.
   - Before import, run the Generation Quality Gate and save or report the node mix. If the node mix reveals a code-only or hard-coded proof, improve the DSL first.
   - Use the bundled helper:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/dify-ce-workflow-autobuilder"
python "$SKILL_DIR/scripts/dify_ce_console.py" import \
  /absolute/path/to/workflow.yml \
  --name "Demo App Name" \
  --out /absolute/path/to/import-result.json
```

   - To update an existing app, pass `--app-id`.
   - Save every import result as evidence.
   - Debug import failures from the saved response body first. Common causes: invalid DSL schema, missing plugin dependency, unavailable model provider, bad app mode, unsupported node type for the local Dify version, or stale dataset IDs.

10. **Run and debug draft apps with Console API**
   - This is the primary debug loop before publishing.
   - Workflow app:

```bash
python "$SKILL_DIR/scripts/dify_ce_console.py" run-draft \
  --app-id "$APP_ID" \
  --mode workflow \
  --inputs-json /absolute/path/to/inputs.json \
  --out /absolute/path/to/run-result.json
```

   - Chatflow / advanced-chat app:

```bash
python "$SKILL_DIR/scripts/dify_ce_console.py" run-draft \
  --app-id "$APP_ID" \
  --mode advanced-chat \
  --query "What should I do next based on my current context?" \
  --inputs-json '{}' \
  --out /absolute/path/to/chat-run-result.json
```

   - Evaluate:
     - HTTP status
     - `workflow_finished.status`
     - final outputs/answer
     - node order and branch route
     - retrieved documents and source labels
     - tool/plugin outputs
     - code calculation outputs
     - whether irrelevant branches were skipped
   - Save the run result JSON and use it to drive the next DSL edit. Do not guess from the final answer alone.

11. **Debug and iterate**
   - Import failure: inspect DSL version, node schema, app mode, missing plugin declarations, model provider names, invalid variable references, and YAML structure.
   - Draft run failure: inspect node error, inputs shape, missing variables, unreachable tool URL, model provider error, plugin credential issue, or branch condition type mismatch.
   - Retrieval mismatch: validate dataset indexing, metadata fields, retrieval query, filters, top-k, reranker/embedding setting, and whether the final LLM saw the retrieved context.
   - Missing evidence facet: if the final answer needs multiple policy/source categories but retrieval only returns one category, add targeted retrieval queries/nodes or metadata filters before calling the workflow demo-ready.
   - Retrieval-empty hallucination: if retrieval output is empty but the final answer includes specific policy, catalog, compliance, or documentation claims, revise the prompt/branching before calling the demo ready.
   - KB build failure: inspect dataset create response, file upload response, document create response, embedding provider availability, indexing status, file extension support, duplicate dataset names, and CE/EE metadata API availability.
   - Tool/API mismatch: check container networking (`host.docker.internal` vs service name), HTTP status, timeout behavior, response JSON shape, and whether the workflow halts on transport errors.
   - Supporting-service mismatch: check the service process, `/health`, port binding, Docker/container network path, endpoint contract, timeout branch, and whether the workflow is calling the host URL or the in-network URL.
   - Database/plugin issue: separate credential/OAuth failure from query/schema failure. Prove a minimal connectivity query or fixed demo query before complex workflow logic.
   - LLM instability: keep deterministic fallback fields in Code/Template nodes, but do not hide that the LLM is being used for final wording.
   - Scheduled trigger wording: describe it as one scheduled scan with internal condition evaluation unless there is truly a second trigger.

12. **Publish and create/reuse an app API key when needed**

```bash
python "$SKILL_DIR/scripts/dify_ce_console.py" publish-api-run \
  --app-id "$APP_ID" \
  --inputs-json /absolute/path/to/service-inputs.json \
  --out /absolute/path/to/service-api-result.json
```

   - This publishes the draft workflow, enables API access, gets or creates an app API key, calls `/v1/workflows/run`, and saves redacted evidence.
   - Never print full API keys, JWTs, passwords, private keys, or customer secrets.
   - This path proves the published workflow can be called by a frontend or external service.

13. **Run and debug with Service API endpoint + key**
   - If the user provides an API endpoint and key, or after `publish-api-run` creates a key, use Service API testing for published behavior:

```bash
export DIFY_APP_API_KEY="<redacted-app-key>"
python "$SKILL_DIR/scripts/dify_ce_console.py" service-run \
  --inputs-json /absolute/path/to/service-inputs.json \
  --out /absolute/path/to/service-run-result.json
```

   - Or pass an explicit endpoint/key:

```bash
python "$SKILL_DIR/scripts/dify_ce_console.py" service-run \
  --endpoint "http://localhost/v1/workflows/run" \
  --api-key "<redacted-app-key>" \
  --inputs-json '{"record_id":"demo_001","query":"What is the current status?"}' \
  --out /absolute/path/to/service-run-result.json
```

   - Compare Service API outputs with Console API draft outputs when:
     - UI test passes but published API fails
     - published API returns old behavior
     - API inputs differ from chat inputs
     - app was not published after DSL changes
     - API key belongs to a different app
   - Debug Service API failures by checking status code, response body, output schema, app publish state, API enable state, API key, input JSON, and model/tool errors.

14. **Report honestly**
    - Say what is built, imported, tested, and passing.
    - Separate imported/indexed/setup evidence from true workflow run evidence.
    - State mock data clearly.
    - State whether knowledge-base documents were generated/imported/indexed and whether retrieval was actually run.
    - State whether any supporting service was built, what it simulates, and which production system would replace it.
    - List gaps and whether they are demo gaps, production gaps, data gaps, or product gaps.

## User Preference Rules From Prior Feedback

- Do not hard-code behavior that should be demonstrated through retrieval, tool calls, or profile data.
- Do not put large mock datasets or business logic directly inside Code nodes when they should live in KB docs, mock-data files, structured DB tables, plugin calls, or supporting services.
- If a workflow needs a knowledge base but the user did not explicitly request or approve one, propose the KB plan and wait for confirmation before generating/importing/indexing documents.
- If a workflow needs an API/tool boundary but the user did not explicitly request or approve a local service, propose the service plan and wait for confirmation before creating or starting any process.
- Do not make the user enter many technical fields for a conversational demo. Use chatflow, defaults, hidden/pre-filled context, lookup nodes, or a frontend wrapper.
- Add a classifier/router so simple routed questions do not run expensive or irrelevant retrieval/tool branches.
- Search Marketplace-listed and installed plugins first for integrations whenever available; do not default to HTTP Request just because it is easy.
- Let Codex choose the best-fit plugin for the requirement, then explicitly document plugin selection, installation, and credential configuration before claiming that integration is covered.
- Keep data-source roles clean:
  - Knowledge base: searchable documents, policies, examples, product/content catalogs, and other text-heavy reference material.
  - Structured database or warehouse: records, metrics, completion/status data, structured rules, and analytics-ready tables.
  - API/tool/plugin: live lookup, mutable operational data, external actions, sends, writes, and third-party services.
- Use Code nodes for deterministic math and selection, not for hiding the whole demo.
- Use LLM nodes for final answers, explanation, reasoning summaries, and prompt comparisons when the customer expects a natural response.
- Design for parallel branches when source calls are independent; avoid unnecessary serial pipelines.
- Show trace/logs as proof after the answer, not as the main demo story.
- For A/B requirements, say prompt comparison or test-set evaluation unless real production traffic splitting is implemented.
- For scheduled or proactive workflows, describe the real implementation accurately: one schedule/webhook/manual trigger can scan, evaluate conditions internally, generate content/actions for matches, and return skipped/summary results.
- If a visual checklist is needed, create a separate HTML file. Do not bury HTML inside the script markdown.

## Expected Artifacts

Keep artifacts together in a dedicated folder such as:

```text
<case>-demo-assets/
  workflows/
  mock-data/
  knowledge-base-docs/
  mock-services/
    README.md
    <service>.py
  scripts/
  kb-import-result.json
  service-health-result.json
  import-result.json
  run-result.json
  service-run-result.json
  service-api-result.json
  coverage-gap-tracker.md
  demo-operator-runbook.md
```

Use `rg --files` and clear filenames so future runs can recover status quickly.

## Portable Bootstrap Test

Run an empty-workspace bootstrap test when changing the skill's bootstrap, plugin discovery, or DSL generation guidance. The goal is to prove portability, not local runtime success.

```text
cwd=<fresh temporary directory>
No dify repo
No dify-official-plugins repo
No local Dify CE required for this layer
No extracted workflow samples
Unset DIFY_DSL_AGENT_PLUGIN_REPOS and other Dify/plugin env vars

Prompt:
Use any integration-heavy workflow requirement that needs a Marketplace-listed plugin/tool and an LLM or workflow node.

Expected:
- The skill discovers that no Dify repo exists in the cwd.
- The skill clones Dify or explicitly asks for a Dify repo for schema grounding.
- The skill discovers that no dify-official-plugins repo exists in the cwd.
- The skill clones/fetches dify-official-plugins or queries the official Marketplace manifest.
- The skill finds a suitable plugin/tool for the requested capability and records the provider/tool schema source.
- The skill produces a DSL or import-ready artifact.
- The skill does not depend on local historical DSL files, memory, nearby repos, or machine-specific context.
- The skill does not claim import, draft run, plugin execution, or Service API validation unless a Dify CE runtime, console account, model provider, plugin installation, and credentials are actually available.
- If local Dify CE is visible on the host but was not bootstrapped for this test, the skill may report it as host context but must not use it as evidence for portability.
```

## Output Format

When reporting progress, use:

```markdown
## Status

## Built / Changed

## Tested

## Current Gaps

## Next Iteration

## Files
```

For a final handoff, include app names, app IDs, exact test queries/inputs, evidence files, and any mock/service dependencies.
