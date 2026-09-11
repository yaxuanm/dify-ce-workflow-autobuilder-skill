# Dify Workflow and New Agent Autobuilder Skill

## 中文简介

这个 Codex Skill 用于在本地或自托管 Dify CE / Enterprise 环境中，设计、生成、导入、测试、调试和验证：

- Workflow / Chatflow；
- 独立 New Agent App；
- Workflow 中的 Agent V2 节点；
- New Agent 与 Workflow 的发布、绑定和运行验证。

它会先读取目标 Dify checkout 和当前 DSL 版本，再决定使用旧节点、Agent V2 Composer，还是带顶层 `agent_packages` 的可移植 DSL。不会把旧版本导出的 Agent 节点直接套到新版本。

## 适配版本与验证状态

这个 Skill 不是按固定版本号硬编码生成 DSL，而是会先检查目标 Dify checkout 和运行环境，再选择可用能力：

- 检测当前 App DSL 版本，例如 `CURRENT_APP_DSL_VERSION`；
- 检测是否支持 Workflow Agent V2 节点；
- 检测是否支持带顶层 `agent_packages` 的 New Agent 可移植 DSL；
- 检测是否具备 New Agent Skill zip 上传、发布和运行测试所需的 Console API；
- 如果目标版本不支持某项能力，会降级为该版本可用的 Workflow / Chatflow / Composer 流程，或停在可导入 DSL 与配置说明。

已验证环境：

- Dify CE，本地自托管；
- Dify checkout：`main`，commit `0ca99312c1`，2026-08-20；
- App DSL：`0.7.0`；
- 已验证能力：Workflow / Chatflow 生成与导入、New Agent DSL 导入与发布、Workflow Agent V2 路径探测、New Agent Service API 测试、New Agent config Skill zip 打包与上传。
- Dify Enterprise，自托管 runtime `3.12.1`；
- 企业版已只读验证能力：App DSL `0.7.0`、`agent_packages` import/export、`AppMode.AGENT`、Agent DSL service、Workflow Agent V2 validators、Agent config Skill zip upload/list/download API。

版本边界：

- Dify 早期版本如果没有 Agent V2 或 `agent_packages`，不会生成 New Agent portable package；
- 如果没有可访问的本地或自托管 Dify runtime，只产出可导入 artifact、安装引导和配置说明，不会声称已完成导入或测试；
- 插件、模型、Knowledge dataset、文件、Skill zip 和凭证属于 workspace 资源，跨环境导入后需要重新安装、授权、上传或映射。

## New Agent 支持范围

Skill 会明确区分以下状态：

1. Build Draft 已生成；
2. Build Draft 已 Apply 到普通 Draft；
3. Agent Draft 已验证；
4. Agent 已 Publish，并产生不可变 Snapshot；
5. Workflow Draft 已绑定正确 Agent/Snapshot；
6. Workflow 已 Publish；
7. 运行 trace 已证明实际调用了目标 Agent。

当前 App DSL 通过顶层 `agent_packages` 搬运 Agent Soul。Workflow Agent V2 节点使用：

```yaml
data:
  type: agent
  version: '2'
  agent_node_kind: dify_agent
  agent_binding:
    binding_type: inline_agent
    package_ref: agent_1
  agent_job:
    schema_version: 1
    mode: tell_agent_what_to_do
```

`Agent Soul` 保存 Prompt、Model、Skills、Files、Tools、Knowledge、Memory 等可复用能力；`agent_job` 只描述当前 Workflow 节点的任务、上游输入和输出契约。

## 可移植性限制

New Agent DSL 不是完整 workspace clone。导出/导入后通常仍需：

- 重新上传 Skill 和 File；YAML 不包含它们的实际文件内容；
- 重新授权模型和 Tool；凭证不会导出；
- 重新映射目标 workspace 的 Knowledge dataset；
- 重新配置 human contact、环境变量和 secret；
- 读取并解决 import warnings；
- 发布 Agent，并在需要时重新绑定/发布 Workflow。

跨 workspace 导入 Workflow package 时，原来的 Roster identity 不会被保留，节点会 materialize 为 Inline Agent。需要多个 Workflow 共享同一个 Agent 时，应先导入/创建独立 Agent、发布它，再在目标 workspace 绑定。

## New Agent Skill zip

当 New Agent 需要可复用的业务规则、SOP、输出规范或工具使用说明时，Skill 会先给出 Agent 设计方案，说明哪些内容放在 Prompt、哪些内容打包成 New Agent config Skill zip。用户确认后，Codex 才会生成、上传并测试 Skill zip。

Skill zip 是用户可编辑资产，不是 Dify Plugin。用户可以修改 `SKILL.md` 或补充文件，然后让 Codex 重新打包、上传和测试。

## 主要文件

```text
SKILL.md
agents/openai.yaml
references/new-agent-dsl.md
scripts/dify_ce_console.py
scripts/validate_new_agent_dsl.py
```

## 使用方式

把目录安装到：

```text
~/.codex/skills/dify-ce-workflow-autobuilder/
```

### 企业版 / 远程自托管用法

**方式 1：Codex 能 SSH 到 Dify Enterprise 服务器**

这是最自动化的方式，适合用户自己的 self-hosted Enterprise、测试环境或 demo 环境。用户提供服务器连接信息和 Dify 入口，例如：

```text
这是我的 Dify Enterprise 服务器：
host: <server-host-or-ip>
ssh user: <user>
ssh key: <local-private-key-path>
Dify 入口: https://<dify-domain> 或 http://<host>

请用 dify-ce-workflow-autobuilder skill 生成并测试一个 workflow/chatflow。
```

Skill 会先做只读检查，再等待用户确认设计方案。确认后才会继续：

1. 检查 Dify 版本、容器、DSL 版本、Agent/Workflow 支持情况；
2. 输出 app 设计方案，等待确认；
3. 生成 DSL、Agent package 或 Agent Skill zip；
4. 通过服务器本地 Console API 导入到 Enterprise；
5. 检查依赖、模型、插件、Knowledge、Skill zip；
6. 执行 draft run、publish 或 Service API test；
7. 根据 trace 自动 debug；
8. 输出已验证结果和剩余配置边界。

**方式 2：Codex 不能 SSH，只生成 artifact**

适合客户环境不能提供 shell access、不能暴露 Console API，或只允许人工导入 Studio 的情况。Skill 会：

1. 根据需求生成 DSL、Agent Skill zip、Knowledge 文档或本地服务说明；
2. 静态校验目标版本和结构；
3. 标注需要安装的插件、模型、凭证和 Knowledge；
4. 提供导入说明和测试 checklist；
5. 停在可导入 artifact，不会声称已完成 draft run 或 runtime debug。

然后可以这样请求：

```text
Use the dify-ce-workflow-autobuilder skill.

Build a standalone New Agent for product-evidence review and place it in an
event-driven Workflow. Ground the DSL in my current Dify checkout, generate a
portable agent package, validate it, import it, report omitted assets and
authorization gaps, publish only after configuration passes, then verify the
published Agent and Workflow traces.
```

静态校验 New Agent DSL：

```bash
python3 scripts/validate_new_agent_dsl.py /absolute/path/to/app.yml \
  --target-repo /absolute/path/to/dify \
  --out /absolute/path/to/validation.json
```

导入并显式确认 dependency-pending 状态：

```bash
python3 scripts/dify_ce_console.py import /absolute/path/to/app.yml \
  --confirm-pending \
  --out /absolute/path/to/import-result.json
```

本地自托管环境还可以分别执行 New Agent 生命周期操作：

```bash
python3 scripts/dify_ce_console.py agent-create --name "Demo Agent"
python3 scripts/dify_ce_console.py agent-build-checkout --agent-id "$AGENT_ID"
python3 scripts/dify_ce_console.py agent-build-save --agent-id "$AGENT_ID" --payload-json build-payload.json
python3 scripts/dify_ce_console.py agent-build-apply --agent-id "$AGENT_ID"
python3 scripts/dify_ce_console.py agent-composer --agent-id "$AGENT_ID" --payload-json composer.json --validate-only
python3 scripts/dify_ce_console.py agent-publish --agent-id "$AGENT_ID"
python3 scripts/dify_ce_console.py agent-inspect --agent-id "$AGENT_ID"
```

生成并上传 New Agent config Skill zip：

```bash
python3 scripts/dify_ce_console.py agent-skill-package \
  --skill-dir /absolute/path/to/agent-skill \
  --out /absolute/path/to/skill-package.json

python3 scripts/dify_ce_console.py agent-skill-upload \
  --agent-id "$AGENT_ID" \
  --skill-dir /absolute/path/to/agent-skill \
  --out /absolute/path/to/skill-upload.json

python3 scripts/dify_ce_console.py agent-skills-list \
  --agent-id "$AGENT_ID" \
  --out /absolute/path/to/skills-list.json
```

测试已发布 New Agent：

```bash
python3 scripts/dify_ce_console.py service-chat-run \
  --api-key-env DIFY_AGENT_API_KEY \
  --query "Review this demo request." \
  --inputs-json '{}' \
  --out /absolute/path/to/agent-run.json
```

## 安全边界

- 不会在没有明确授权时重启、升级或清理现有 Dify 环境。
- 不会打印模型、Tool、JWT、SSH 或 API 密钥。
- 导入、配置、Apply、Publish、运行和外部写入会分别记录证据。
- 创建 Knowledge、安装插件、配置凭证、产生费用或执行外部写入前会确认边界。
- Build Draft 未 Apply、Agent 未 Publish、Workflow 未重新发布时，不会声称新配置已生效。

---

## English overview

This Codex Skill builds and verifies Dify Workflows, Chatflows, standalone New Agent apps, and Workflow Agent V2 nodes against the exact target checkout.

It adds version-aware handling for:

- App DSL `0.7.0`-style `agent_packages` when supported by the target;
- standalone `app.mode: agent` imports;
- Agent V2 discriminators and portable `package_ref` bindings;
- Agent Soul versus Workflow `agent_job` ownership;
- Build Draft → Apply → validate → publish → bind → runtime evidence;
- omitted Skill/File assets, reset Tool/model credentials, unresolved Knowledge, contacts, and secrets;
- published New Agent testing through `/v1/chat-messages`.

The built-in Workflow graph generator is not assumed to be an Agent-package generator. The Skill either creates a complete portable App DSL envelope or uses Studio/Composer to materialize a V2 node and binding.

Import success is not treated as runtime readiness. The Skill reports static validation, import warnings, configuration, publish state, binding state, draft tests, published tests, and external delivery separately.
