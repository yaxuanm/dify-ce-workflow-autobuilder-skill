#!/usr/bin/env python3
"""Validate portable Dify New Agent DSL before import.

This is a structural and portability gate. The target Dify importer and Composer
remain authoritative for version-specific semantic validation.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment setup failure
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


OUTPUT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VERSION_RE = re.compile(r"CURRENT_APP_DSL_VERSION\s*=\s*[\"']([^\"']+)[\"']")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    path: str
    message: str


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def error(self, code: str, path: str, message: str) -> None:
        self.findings.append(Finding("error", code, path, message))

    def warning(self, code: str, path: str, message: str) -> None:
        self.findings.append(Finding("warning", code, path, message))

    def info(self, code: str, path: str, message: str) -> None:
        self.findings.append(Finding("info", code, path, message))

    @property
    def errors(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "warning"]


def read_yaml(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"Could not parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("DSL root must be a YAML mapping")
    return value


def read_target_version(repo: pathlib.Path | None, report: Report) -> str | None:
    if repo is None:
        report.warning(
            "target_repo_not_provided",
            "target_repo",
            "No target Dify checkout was provided; version compatibility was not source-verified.",
        )
        return None
    version_file = repo / "api/constants/dsl_version.py"
    package_service = repo / "api/services/agent/dsl_service.py"
    discriminator = repo / "api/core/workflow/nodes/agent_v2/discriminator.py"
    if not version_file.is_file():
        report.error("target_dsl_version_missing", str(version_file), "Target checkout has no DSL version file.")
        return None
    match = VERSION_RE.search(version_file.read_text(encoding="utf-8"))
    if not match:
        report.error("target_dsl_version_unreadable", str(version_file), "Could not read CURRENT_APP_DSL_VERSION.")
        return None
    if not discriminator.is_file():
        report.error("agent_v2_not_supported", str(discriminator), "Target checkout has no Agent V2 discriminator.")
    if not package_service.is_file():
        report.error(
            "agent_packages_not_supported",
            str(package_service),
            "Target checkout has no portable Agent package service; do not generate agent_packages for it.",
        )
    return match.group(1)


def require_mapping(value: Any, path: str, report: Report) -> dict[str, Any]:
    if not isinstance(value, dict):
        report.error("expected_mapping", path, "Expected a mapping.")
        return {}
    return value


def reject_unknown_keys(
    value: dict[str, Any],
    allowed: set[str],
    path: str,
    report: Report,
    code: str,
) -> None:
    for key in sorted(set(value).difference(allowed)):
        report.error(code, f"{path}.{key}", "Field is not part of the current portable New Agent schema.")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_model(soul: dict[str, Any], path: str, report: Report) -> None:
    model = soul.get("model")
    if not isinstance(model, dict):
        report.error("agent_model_missing", f"{path}.model", "New Agent requires a configured model before publish.")
        return
    for key in ("plugin_id", "model_provider", "model"):
        if not isinstance(model.get(key), str) or not model[key].strip():
            report.error("agent_model_field_missing", f"{path}.model.{key}", f"Model {key} is required.")
    credential_ref = model.get("credential_ref")
    if isinstance(credential_ref, dict) and credential_ref.get("id"):
        report.warning(
            "workspace_model_credential",
            f"{path}.model.credential_ref",
            "Portable DSL should not depend on a workspace-local model credential id.",
        )
    elif credential_ref in (None, {}):
        report.warning(
            "model_authorization_required",
            f"{path}.model.credential_ref",
            "Select an authorized model credential after import.",
        )


def validate_tools(soul: dict[str, Any], path: str, report: Report) -> None:
    tools = soul.get("tools") or {}
    if not isinstance(tools, dict):
        report.error("agent_tools_invalid", f"{path}.tools", "Agent tools must be a mapping.")
        return
    for index, tool in enumerate(as_list(tools.get("dify_tools"))):
        tool_path = f"{path}.tools.dify_tools[{index}]"
        if not isinstance(tool, dict):
            report.error("agent_tool_invalid", tool_path, "Tool entry must be a mapping.")
            continue
        has_provider = bool(tool.get("provider_id")) or bool(tool.get("plugin_id") and tool.get("provider"))
        if not has_provider:
            report.error("agent_tool_provider_missing", tool_path, "Tool needs provider_id or plugin_id + provider.")
        credential_ref = tool.get("credential_ref")
        if isinstance(credential_ref, dict) and credential_ref.get("id"):
            report.warning(
                "workspace_tool_credential",
                f"{tool_path}.credential_ref",
                "Portable DSL should not depend on a workspace-local Tool credential id.",
            )
        if tool.get("credential_type") == "unauthorized" or not credential_ref:
            report.warning(
                "tool_authorization_required",
                tool_path,
                "Reconnect this Tool in the target workspace and run a minimum tool test.",
            )


def validate_assets(package: dict[str, Any], soul: dict[str, Any], path: str, report: Report) -> None:
    omitted = as_list(package.get("omitted_assets"))
    for group, kind in (("config_skills", "Skill"), ("config_files", "File")):
        for index, asset in enumerate(as_list(soul.get(group))):
            asset_path = f"{path}.soul.{group}[{index}]"
            if not isinstance(asset, dict):
                report.error("agent_asset_invalid", asset_path, f"{kind} reference must be a mapping.")
                continue
            if asset.get("file_id") and not asset.get("is_missing"):
                report.warning(
                    "workspace_asset_id",
                    f"{asset_path}.file_id",
                    f"{kind} file_id is workspace-local and will not be portable.",
                )
            if asset.get("is_missing") or not asset.get("file_id"):
                report.warning(
                    f"agent_{kind.lower()}_reattach_required",
                    asset_path,
                    f"Reattach this {kind} after import; YAML does not contain its payload.",
                )
    if omitted:
        report.warning(
            "agent_assets_omitted",
            f"{path}.omitted_assets",
            f"Package records {len(omitted)} omitted Skill/File asset(s); reattach them after import.",
        )


def validate_knowledge(soul: dict[str, Any], path: str, report: Report) -> None:
    knowledge = soul.get("knowledge") or {}
    if not isinstance(knowledge, dict):
        report.error("agent_knowledge_invalid", f"{path}.knowledge", "Knowledge must be a mapping.")
        return
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for index, knowledge_set in enumerate(as_list(knowledge.get("sets"))):
        set_path = f"{path}.knowledge.sets[{index}]"
        if not isinstance(knowledge_set, dict):
            report.error("knowledge_set_invalid", set_path, "Knowledge set must be a mapping.")
            continue
        set_id = str(knowledge_set.get("id") or "").strip()
        set_name = str(knowledge_set.get("name") or "").strip()
        if not set_id or set_id in seen_ids:
            report.error("knowledge_set_id_invalid", f"{set_path}.id", "Knowledge set id must be nonblank and unique.")
        if not set_name or set_name.casefold() in seen_names:
            report.error(
                "knowledge_set_name_invalid",
                f"{set_path}.name",
                "Knowledge set name must be nonblank and case-insensitively unique.",
            )
        seen_ids.add(set_id)
        seen_names.add(set_name.casefold())
        datasets = as_list(knowledge_set.get("datasets"))
        if not datasets:
            report.error("knowledge_datasets_missing", f"{set_path}.datasets", "Knowledge set needs at least one dataset.")
        for dataset_index, dataset in enumerate(datasets):
            dataset_path = f"{set_path}.datasets[{dataset_index}]"
            if not isinstance(dataset, dict) or not str(dataset.get("id") or "").strip():
                report.error("knowledge_dataset_id_missing", dataset_path, "Dataset id is required.")
            else:
                report.warning(
                    "knowledge_dataset_remap_check",
                    dataset_path,
                    "Verify this dataset exists in the target tenant and hit-test retrieval after import.",
                )
        query = knowledge_set.get("query")
        if not isinstance(query, dict) or query.get("mode") not in {"user_query", "generated_query"}:
            report.error("knowledge_query_invalid", f"{set_path}.query", "Query mode must be user_query or generated_query.")
        retrieval = knowledge_set.get("retrieval")
        if not isinstance(retrieval, dict) or retrieval.get("mode") not in {"single", "multiple"}:
            report.error("knowledge_retrieval_invalid", f"{set_path}.retrieval", "Retrieval mode must be single or multiple.")


def validate_package(package_ref: str, package: Any, report: Report) -> None:
    path = f"agent_packages.{package_ref}"
    package_map = require_mapping(package, path, report)
    reject_unknown_keys(
        package_map,
        {"schema_version", "metadata", "soul", "omitted_assets"},
        path,
        report,
        "agent_package_unknown_field",
    )
    if package_map.get("schema_version") != 1:
        report.error("agent_package_schema_invalid", f"{path}.schema_version", "Only Agent package schema_version 1 is supported.")
    metadata = require_mapping(package_map.get("metadata"), f"{path}.metadata", report)
    reject_unknown_keys(
        metadata,
        {"name", "description", "role", "icon_type", "icon", "icon_background"},
        f"{path}.metadata",
        report,
        "agent_metadata_unknown_field",
    )
    if not str(metadata.get("name") or "").strip():
        report.error("agent_metadata_name_missing", f"{path}.metadata.name", "Agent package name is required.")
    soul = require_mapping(package_map.get("soul"), f"{path}.soul", report)
    reject_unknown_keys(
        soul,
        {
            "schema_version", "prompt", "tools", "knowledge", "human", "env",
            "config_skills", "config_files", "config_note", "sandbox", "memory",
            "model", "app_features", "app_variables", "misc_legacy",
        },
        f"{path}.soul",
        report,
        "agent_soul_unknown_field",
    )
    if soul.get("schema_version", 1) != 1:
        report.error("agent_soul_schema_invalid", f"{path}.soul.schema_version", "Only Agent Soul schema_version 1 is supported.")
    validate_model(soul, f"{path}.soul", report)
    validate_tools(soul, f"{path}.soul", report)
    validate_assets(package_map, soul, path, report)
    validate_knowledge(soul, f"{path}.soul", report)


def validate_declared_outputs(outputs: Any, path: str, report: Report) -> None:
    seen: set[str] = set()
    for index, output in enumerate(as_list(outputs)):
        output_path = f"{path}[{index}]"
        if not isinstance(output, dict):
            report.error("declared_output_invalid", output_path, "Declared output must be a mapping.")
            continue
        name = str(output.get("name") or "")
        if not OUTPUT_NAME_RE.fullmatch(name):
            report.error("declared_output_name_invalid", f"{output_path}.name", "Output name is not a valid identifier.")
        if name in seen:
            report.error("declared_output_duplicate", f"{output_path}.name", "Output names must be unique per Agent node.")
        seen.add(name)


def iter_nodes(data: dict[str, Any]) -> Iterable[tuple[int, dict[str, Any]]]:
    graph = ((data.get("workflow") or {}).get("graph") or {}) if isinstance(data.get("workflow"), dict) else {}
    for index, node in enumerate(as_list(graph.get("nodes"))):
        if isinstance(node, dict):
            yield index, node


def validate_agent_nodes(data: dict[str, Any], packages: dict[str, Any], report: Report) -> tuple[int, int]:
    v2_count = 0
    legacy_count = 0
    for index, node in iter_nodes(data):
        node_data = node.get("data")
        if not isinstance(node_data, dict) or node_data.get("type") != "agent":
            continue
        path = f"workflow.graph.nodes[{index}].data"
        is_v2 = str(node_data.get("version")) == "2" and node_data.get("agent_node_kind") == "dify_agent"
        if not is_v2:
            legacy_count += 1
            report.error(
                "legacy_agent_node",
                path,
                "Agent node is not New Agent V2; regenerate it instead of changing only one legacy field.",
            )
            continue
        v2_count += 1
        binding = require_mapping(node_data.get("agent_binding"), f"{path}.agent_binding", report)
        package_ref = binding.get("package_ref")
        if not isinstance(package_ref, str) or package_ref not in packages:
            report.error(
                "agent_package_ref_invalid",
                f"{path}.agent_binding.package_ref",
                "Portable Agent V2 node must reference an existing top-level agent_packages entry.",
            )
        if binding.get("agent_id") or binding.get("current_snapshot_id"):
            report.error(
                "workspace_agent_binding",
                f"{path}.agent_binding",
                "Do not put persisted agent_id/current_snapshot_id in portable DSL.",
            )
        if binding.get("binding_type") not in {"inline_agent", "roster_agent"}:
            report.error(
                "agent_binding_type_invalid",
                f"{path}.agent_binding.binding_type",
                "binding_type must be inline_agent or roster_agent.",
            )
        job = require_mapping(node_data.get("agent_job"), f"{path}.agent_job", report)
        reject_unknown_keys(
            job,
            {
                "schema_version", "mode", "workflow_prompt", "previous_node_output_refs",
                "declared_outputs", "human_contacts", "metadata",
            },
            f"{path}.agent_job",
            report,
            "agent_job_unknown_field",
        )
        if job.get("schema_version", 1) != 1:
            report.error("agent_job_schema_invalid", f"{path}.agent_job.schema_version", "Agent job schema_version must be 1.")
        if job.get("mode", "tell_agent_what_to_do") not in {"tell_agent_what_to_do", "let_agent_figure_it_out"}:
            report.error("agent_job_mode_invalid", f"{path}.agent_job.mode", "Unknown Agent job mode.")
        validate_declared_outputs(job.get("declared_outputs"), f"{path}.agent_job.declared_outputs", report)
        metadata = job.get("metadata") or {}
        if isinstance(metadata, dict):
            locked = {
                "agent_soul", "soul", "prompt", "system_prompt", "skills", "files", "tools",
                "dify_tools", "cli_tools", "knowledge", "env", "model", "memory", "sandbox",
            }
            present = sorted(locked.intersection(metadata))
            if present:
                report.error(
                    "agent_soul_override",
                    f"{path}.agent_job.metadata",
                    f"Workflow job cannot override Agent Soul fields: {', '.join(present)}.",
                )
    return v2_count, legacy_count


def validate(data: dict[str, Any], target_repo: pathlib.Path | None) -> tuple[Report, dict[str, Any]]:
    report = Report()
    target_version = read_target_version(target_repo, report)
    imported_version = data.get("version")
    if not isinstance(imported_version, str):
        report.error("dsl_version_invalid", "version", "DSL version must be a quoted string.")
    elif target_version and imported_version != target_version:
        report.warning(
            "dsl_version_mismatch",
            "version",
            f"Artifact version is {imported_version}; target checkout reports {target_version}. Regenerate from target exports.",
        )
    if data.get("kind") != "app":
        report.error("dsl_kind_invalid", "kind", "DSL kind must be app.")
    app = require_mapping(data.get("app"), "app", report)
    mode = app.get("mode")
    packages = data.get("agent_packages") or {}
    if not isinstance(packages, dict):
        report.error("agent_packages_invalid", "agent_packages", "agent_packages must be a mapping.")
        packages = {}
    for package_ref, package in packages.items():
        validate_package(str(package_ref), package, report)

    v2_count, legacy_count = validate_agent_nodes(data, packages, report)
    if mode == "agent":
        agent = require_mapping(data.get("agent"), "agent", report)
        package_ref = agent.get("package_ref")
        if not isinstance(package_ref, str) or package_ref not in packages:
            report.error("standalone_package_ref_invalid", "agent.package_ref", "Standalone Agent must reference a package.")
        report.warning(
            "standalone_agent_unpublished",
            "agent",
            "Import creates an editable unpublished Agent draft; resolve setup and publish it before runtime use.",
        )
    elif mode in {"workflow", "advanced-chat"}:
        if packages and not v2_count:
            report.error("unused_agent_packages", "agent_packages", "Agent packages exist but no Agent V2 node references them.")
    elif packages or v2_count or legacy_count:
        report.error("agent_app_mode_invalid", "app.mode", "Agent packages require agent, workflow, or advanced-chat mode.")

    if not packages and (mode == "agent" or v2_count):
        report.error("agent_packages_missing", "agent_packages", "Portable New Agent DSL requires top-level agent_packages.")

    summary = {
        "dsl_version": imported_version,
        "target_dsl_version": target_version,
        "app_mode": mode,
        "agent_package_count": len(packages),
        "agent_v2_node_count": v2_count,
        "legacy_agent_node_count": legacy_count,
    }
    return report, summary


def write_result(path: str | None, result: dict[str, Any]) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if not path:
        print(text)
        return
    output = pathlib.Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "passed": result["passed"]}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dsl_file")
    parser.add_argument("--target-repo", help="Exact Dify checkout used by the target runtime.")
    parser.add_argument("--out")
    parser.add_argument("--fail-on-warnings", action="store_true")
    args = parser.parse_args()

    dsl_path = pathlib.Path(args.dsl_file).expanduser().resolve()
    target_repo = pathlib.Path(args.target_repo).expanduser().resolve() if args.target_repo else None
    data = read_yaml(dsl_path)
    report, summary = validate(data, target_repo)
    passed = not report.errors and not (args.fail_on_warnings and report.warnings)
    result = {
        "action": "validate-new-agent-dsl",
        "dsl_file": str(dsl_path),
        "target_repo": str(target_repo) if target_repo else None,
        "passed": passed,
        "summary": summary,
        "counts": {
            "errors": len(report.errors),
            "warnings": len(report.warnings),
            "info": len([item for item in report.findings if item.level == "info"]),
        },
        "findings": [asdict(item) for item in report.findings],
    }
    write_result(args.out, result)
    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
