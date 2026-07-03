# Dify CE Workflow Autobuilder Skill

## 中文简介

这个 Codex skill 用来在本地或自托管 Dify CE 环境中，根据一段需求自动完成 Dify workflow / chatflow 的生成、导入、测试和迭代。它不只适用于连接企业数据源，也可以用于搜索、social listening、marketing research、内容监测、RAG、工具调用和自动化 demo。

你只需要给 Codex 一个 demo 需求或 workflow context，它会尽量一键完成以下流程：

1. 从需求生成 Dify workflow / chatflow DSL
2. 自动导入到 Dify Studio
3. 构建并接入 Knowledge Base
4. 运行 Draft Run 测试
5. 根据 trace 自动 Debug 和持续迭代
6. 生成测试报告和交付说明

## 主要功能

- **指导安装 Dify CE**  
  如果本地没有安装或没有启动 Dify CE，skill 会返回 Docker Compose 安装指引，而不是继续执行导入或测试命令。

- **从需求到 Studio 导入**  
  根据用户提供的需求、demo context 或 workflow plan，生成 Dify DSL，并通过本地 Console API 自动导入到 Dify Studio。

- **按需构建 Knowledge Base**  
  如果用户明确要求使用 Knowledge Base / RAG，或确认了 skill 提出的 KB 方案，skill 会准备 KB 文档、导入并索引，然后把 dataset id 接入 workflow。

- **支持搜索、社媒监听和 Marketing 场景**  
  对于 web search、social listening、competitor monitoring、campaign research、content monitoring 等需求，skill 会优先探索可用插件、工具、Agent、搜索/爬虫能力或 API，而不是把场景强行塞进固定节点模板。

- **探索插件和工具能力**  
  如果需求需要搜索、爬取、社媒、CRM、邮件、数据库、广告/营销分析等能力，skill 会先检查可用插件/工具和凭证条件。安装插件、配置凭证、调用外部服务或启动本地 mock service 前，会先征求用户确认。

- **自动 Debug 和 Draft Run 测试**  
  导入后会运行 draft workflow / chatflow，检查节点执行、分支、HTTP/tool 调用、Knowledge Retrieval 结果、LLM 输出和最终结果。

- **支持持续迭代**  
  如果导入失败、节点报错、retrieval 结果不完整、LLM 输出和证据不一致，skill 会基于 run evidence 修改 workflow 并重新测试。

- **生成测试报告**  
  完成后会输出 app id、测试输入、运行结果、trace evidence、mock 数据说明、当前限制和下一步建议。

## 适用环境

这个 skill 适合：

- 本地或自托管 Dify CE
- Codex 可以访问 shell / Docker
- Dify API container 可以读取 `SECRET_KEY`
- 已创建 Dify console account
- workflow 所需模型 provider / plugin credentials 已配置，或可以使用 mock service

不适合直接用于：

- Dify Cloud
- 无法访问容器或 `SECRET_KEY` 的客户环境
- 生产数据迁移或破坏性 workspace 操作

## 怎么使用

把整个 skill 目录放到 Codex skills 目录中：

```bash
~/.codex/skills/dify-ce-workflow-autobuilder/
```

目录里至少包含：

```text
SKILL.md
README.md
scripts/
  dify_ce_console.py
```

然后新开一个 Codex session，让 Codex 重新加载 skills。

你可以直接给一个需求，例如：

```text
Use the dify-ce-workflow-autobuilder skill.

Build a procurement policy copilot in my local Dify CE.
The app should answer purchase approval questions.
Use a Knowledge Base for policy documents.
Use a mock HTTP service for vendor risk lookup.
Import the workflow into Dify Studio, run draft tests, debug failures, and generate a test report.
```

中文也可以：

```text
使用 dify-ce-workflow-autobuilder skill。

帮我在本地 Dify CE 里生成一个采购政策助手。
它需要根据采购金额、供应商风险和合同周期判断审批路径。
政策内容放在 Knowledge Base 里。
供应商风险用 mock HTTP service 查询。
请自动生成 workflow、导入 Studio、运行 Draft Run 测试、Debug，并输出测试报告。
```

如果本地 CE 没有启动，也可以让 skill 输出安装指引：

```bash
python3 scripts/dify_ce_console.py install-guide
```

## Notes

- 只有在用户明确要求或确认方案后，skill 才会创建/上传 Knowledge Base 或启动本地 mock service。
- 插件安装、外部搜索/爬取、可能产生费用或 rate limit 的调用，需要用户确认后再执行。
- Knowledge Base 默认会优先使用 high-quality indexing 和当前 workspace 中最好的可用 embedding model。
- 用户只需要提供必要信息，例如数据来源、是真实数据还是 mock、数据位置、是否安全可导入、代表性测试问题。
- 低层参数如 embedding model、top-k、chunking、rerank 默认由 skill 选择；用户可以在 Dify Knowledge 页面后续自行调参。
- 对于需要多个证据维度的场景，skill 会倾向使用多个 targeted Knowledge Retrieval 节点，而不是只依赖一个宽泛 query。

欢迎大家测试并提出意见。

---

# Dify CE Workflow Autobuilder Skill

## Overview

This Codex skill helps build, import, test, debug, and iterate Dify workflow / chatflow apps in a local or self-hosted Dify CE environment. It is not limited to enterprise data-source workflows; it can also support search, social listening, marketing research, content monitoring, RAG, tool use, and automation demos.

You only need to provide a demo requirement or workflow context. The skill will try to complete the full workflow-building loop:

1. Generate Dify workflow / chatflow DSL from requirements
2. Import the app into Dify Studio
3. Build and connect Knowledge Bases when explicitly requested or approved
4. Run Draft Run tests
5. Debug failures from trace evidence and iterate
6. Generate a test report and handoff summary

## Key Capabilities

- **Guide Dify CE installation**  
  If local Dify CE is not installed or not running, the skill returns Docker Compose installation guidance instead of continuing with import or debug commands.

- **Generate and import into Studio**  
  From a requirement, demo context, or workflow plan, the skill generates Dify DSL and imports it into Dify Studio through the local Console API.

- **Build Knowledge Bases when requested or approved**  
  If the user explicitly asks for a Knowledge Base / RAG, or confirms the proposed KB plan, the skill prepares KB documents, imports/indexes them, and wires dataset IDs into workflow nodes.

- **Support Search, Social Listening, and Marketing Use Cases**  
  For web search, social listening, competitor monitoring, campaign research, and content monitoring, the skill explores available plugins, tools, Agent patterns, search/crawler capabilities, or APIs instead of forcing every workflow into a fixed node template.

- **Explore Plugins and Tools**  
  When a workflow needs search, crawling, social platforms, CRM, email, databases, ads/marketing analytics, or other external capabilities, the skill checks available plugins/tools and credential requirements first. It asks for confirmation before installing plugins, configuring credentials, making external calls, or starting local mock services.

- **Run Draft Tests and Debug**  
  After import, the skill runs draft workflows / chatflows and checks node execution, branch routing, HTTP/tool calls, Knowledge Retrieval results, LLM output, and final outputs.

- **Iterate Until Passing**  
  If import fails, nodes error, retrieval is incomplete, or the final answer contradicts source evidence, the skill uses saved run evidence to revise the workflow and test again.

- **Generate Test Reports**  
  The final handoff includes app id, test inputs, run results, trace evidence, mock data notes, current limitations, and recommended next steps.

## Supported Environment

This skill is intended for:

- Local or self-hosted Dify CE
- Shell and Docker access from Codex
- Access to the Dify API container `SECRET_KEY`
- An existing Dify console account
- Configured model providers / plugin credentials, or mock services for demo use

It is not a direct fit for:

- Dify Cloud
- Locked-down customer environments without container or `SECRET_KEY` access
- Production data migration or destructive workspace operations

## How to Use

Place the skill folder under:

```bash
~/.codex/skills/dify-ce-workflow-autobuilder/
```

The folder should include:

```text
SKILL.md
README.md
scripts/
  dify_ce_console.py
```

Then start a new Codex session so Codex can reload the available skills.

Example prompt:

```text
Use the dify-ce-workflow-autobuilder skill.

Build a procurement policy copilot in my local Dify CE.
The app should answer purchase approval questions.
Use a Knowledge Base for policy documents.
Use a mock HTTP service for vendor risk lookup.
Import the workflow into Dify Studio, run draft tests, debug failures, and generate a test report.
```

To print local CE installation guidance:

```bash
python3 scripts/dify_ce_console.py install-guide
```

## Notes

- Knowledge Bases default to strong settings, such as high-quality indexing and the best configured embedding model available in the workspace.
- The skill creates/uploads Knowledge Bases or starts local mock services only when explicitly requested by the user or after the user confirms the proposed plan.
- Plugin installation, external search/crawling, and calls that may incur cost or rate limits require user confirmation before execution.
- Users only need to provide necessary decisions: data source, mock vs real data, data location, safety/permission boundaries, and representative test questions.
- Low-level settings such as embedding model, top-k, chunking, and rerank can be tuned later in Dify Knowledge settings.
- For workflows requiring multiple evidence facets, the skill may use multiple targeted Knowledge Retrieval nodes instead of a single broad retrieval query.

Feedback and test results are welcome.
