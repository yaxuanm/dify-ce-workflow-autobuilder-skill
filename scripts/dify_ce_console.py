#!/usr/bin/env python3
"""Small helper for local Dify CE Console API workflow import/run/publish loops.

Defaults match a common local Dify CE Docker Compose setup:
  BASE_URL=http://localhost
  API_CONTAINER=docker-api-1

Override with:
  DIFY_BASE_URL
  DIFY_API_CONTAINER
  DIFY_CONSOLE_USER_ID

The helper intentionally redacts API keys in saved evidence.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import pathlib
import subprocess
import sys
import time
import textwrap
import warnings
from typing import Any

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import jwt
import requests


BASE_URL = os.environ.get("DIFY_BASE_URL", "http://localhost").rstrip("/")
API_CONTAINER = os.environ.get("DIFY_API_CONTAINER", "docker-api-1")


def ce_install_guide() -> str:
    return textwrap.dedent(
        """\
        # Dify CE local install guide

        Use this when local Dify CE is not installed, containers are not running, or the API
        container/SECRET_KEY cannot be discovered.

        Official docs:
        - Docker Compose quick start: https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose
        - Environment variables: https://docs.dify.ai/en/self-host/deploy/configuration/environments

        Prerequisites:
        - Docker is installed and running.
        - Docker Compose is 2.24.0 or later.
        - For local testing, use at least 2 CPU cores and 4 GiB RAM; prefer 8 GiB memory on Docker Desktop.
        - Port 80 is available, or edit EXPOSE_NGINX_PORT in dify/docker/.env before starting.

        Commands:

        ```bash
        docker compose version

        git clone --branch "$(curl -s https://api.github.com/repos/langgenius/dify/releases/latest | jq -r .tag_name)" https://github.com/langgenius/dify.git
        cd dify/docker
        cp .env.example .env
        docker compose up -d

        docker compose ps
        open http://localhost || true
        ```

        If jq is not installed, replace the clone command with:

        ```bash
        git clone https://github.com/langgenius/dify.git
        cd dify
        git fetch --tags
        git checkout "$(git describe --tags "$(git rev-list --tags --max-count=1)")"
        cd docker
        cp .env.example .env
        docker compose up -d
        ```

        After startup:
        1. Open http://localhost in a browser.
        2. Create the first console/admin account.
        3. Configure model providers/plugins needed by the workflow.
        4. Re-run the workflow builder helper.

        Quick verification:

        ```bash
        docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' | grep -E 'dify|docker-(api|web|worker|db)|postgres|redis|nginx'
        curl -I http://localhost
        ```
        """
    )


def sh(cmd: list[str], timeout: int = 30) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=timeout).strip()


def discover_user_id() -> str:
    user_id = os.environ.get("DIFY_CONSOLE_USER_ID") or os.environ.get("DIFY_USER_ID")
    if user_id:
        return user_id

    candidates = [
        "docker-db-1",
        "dify-db-1",
        "docker-postgres-1",
        "docker-db-postgres-1",
    ]
    try:
        names = sh(["docker", "ps", "--format", "{{.Names}}"], timeout=10).splitlines()
        candidates.extend(name for name in names if "postgres" in name or name.endswith("-db-1"))
    except Exception:
        pass

    seen: set[str] = set()
    query = "select id from accounts order by created_at limit 1;"
    for container in candidates:
        if container in seen:
            continue
        seen.add(container)
        try:
            output = sh(
                [
                    "docker",
                    "exec",
                    container,
                    "psql",
                    "-U",
                    "postgres",
                    "-d",
                    "dify",
                    "-t",
                    "-A",
                    "-c",
                    query,
                ],
                timeout=10,
            )
            first = output.splitlines()[0].strip() if output.strip() else ""
            if first:
                return first
        except Exception:
            continue

    raise SystemExit(
        "Could not discover Dify console user id. Set DIFY_CONSOLE_USER_ID=<account uuid> and retry."
    )


def make_console_session() -> requests.Session:
    try:
        secret = sh(["docker", "exec", API_CONTAINER, "sh", "-lc", "printenv SECRET_KEY"])
    except Exception as exc:
        raise SystemExit(
            f"Could not read SECRET_KEY from {API_CONTAINER}. Set DIFY_API_CONTAINER if the API container has a different name, "
            f"or start/install local Dify CE. Run this helper for setup guidance:\n\n"
            f"  python3 {pathlib.Path(__file__).resolve()} install-guide\n\n"
            f"Error: {exc}"
        ) from exc

    user_id = discover_user_id()
    now = int(time.time())
    access = jwt.encode(
        {
            "user_id": user_id,
            "exp": now + 3600,
            "iss": "SELF_HOSTED",
            "sub": "Console API Passport",
        },
        secret,
        algorithm="HS256",
    )
    csrf = jwt.encode({"sub": user_id, "exp": now + 3600}, secret, algorithm="HS256")
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {access}",
            "X-CSRF-Token": csrf,
            "Content-Type": "application/json",
        }
    )
    session.cookies.set("csrf_token", csrf)
    return session


def load_inputs(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    if value.strip().startswith("{"):
        return json.loads(value)
    path = pathlib.Path(value).expanduser().resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def parse_sse_events(stream_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_line in stream_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            events.append({"event": "unparsed", "raw": payload})
    return events


def redact_token(token: str | None) -> str:
    if not token:
        return ""
    return f"{token[:8]}...REDACTED"


def write_json(path: str | None, payload: dict[str, Any]) -> None:
    if not path:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    output = pathlib.Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": summarize_payload(payload)}, indent=2, ensure_ascii=False))


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status_code": payload.get("status_code"),
        "app_id": payload.get("app_id"),
        "workflow_status": payload.get("workflow_status"),
        "passed": payload.get("passed"),
    }


def cmd_import(args: argparse.Namespace) -> None:
    workflow_path = pathlib.Path(args.workflow_file).expanduser().resolve()
    yaml_content = workflow_path.read_text(encoding="utf-8")
    payload: dict[str, Any] = {"mode": "yaml-content", "yaml_content": yaml_content}
    if args.name:
        payload["name"] = args.name
    if args.app_id:
        payload["app_id"] = args.app_id

    session = make_console_session()
    response = session.post(f"{BASE_URL}/console/api/apps/imports", json=payload, timeout=args.timeout)
    try:
        body = response.json() if response.content else {}
    except Exception:
        body = {"raw": response.text}
    result = {
        "action": "import",
        "base_url": BASE_URL,
        "workflow_file": str(workflow_path),
        "status_code": response.status_code,
        "app_id": body.get("app_id"),
        "status": body.get("status"),
        "body": body,
    }
    write_json(args.out, result)
    response.raise_for_status()


def cmd_install_guide(args: argparse.Namespace) -> None:
    guide = ce_install_guide()
    if args.out:
        output = pathlib.Path(args.out).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(guide, encoding="utf-8")
        print(json.dumps({"output": str(output)}, indent=2, ensure_ascii=False))
    else:
        print(guide)


def list_doc_files(docs_dir: str, extensions: list[str]) -> list[pathlib.Path]:
    root = pathlib.Path(docs_dir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"docs dir does not exist or is not a directory: {root}")
    allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    files = [path for path in sorted(root.rglob("*")) if path.is_file() and path.suffix.lower() in allowed]
    if not files:
        raise SystemExit(f"no document files found under {root} with extensions {sorted(allowed)}")
    return files


def upload_dataset_file(session: requests.Session, path: pathlib.Path, timeout: int) -> dict[str, Any]:
    mime = mimetypes.guess_type(str(path))[0] or "text/plain"
    original_content_type = session.headers.pop("Content-Type", None)
    try:
        with path.open("rb") as file_obj:
            response = session.post(
                f"{BASE_URL}/console/api/files/upload",
                data={"source": "datasets"},
                files={"file": (path.name, file_obj, mime)},
                timeout=timeout,
            )
    finally:
        if original_content_type is not None:
            session.headers["Content-Type"] = original_content_type
    try:
        body = response.json() if response.content else {}
    except Exception:
        body = {"raw": response.text}
    result = {
        "path": str(path),
        "status_code": response.status_code,
        "body": body,
        "file_id": body.get("id"),
    }
    return result


def create_dataset(session: requests.Session, args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "name": args.name,
        "description": args.description or f"Generated by Codex from {args.docs_dir}",
        "indexing_technique": args.indexing_technique,
        "permission": args.permission,
        "provider": "vendor",
    }
    response = session.post(f"{BASE_URL}/console/api/datasets", json=payload, timeout=args.timeout)
    try:
        body = response.json() if response.content else {}
    except Exception:
        body = {"raw": response.text}
    result = {"status_code": response.status_code, "body": body, "dataset_id": body.get("id")}
    return result


def create_document_from_file_id(
    session: requests.Session,
    dataset_id: str,
    file_id: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "indexing_technique": args.indexing_technique,
        "data_source": {
            "info_list": {
                "data_source_type": "upload_file",
                "file_info_list": {"file_ids": [file_id]},
            }
        },
        "process_rule": {"mode": args.process_rule},
        "doc_form": args.doc_form,
        "doc_language": args.doc_language,
        "duplicate": True,
    }
    if args.embedding_model:
        payload["embedding_model"] = args.embedding_model
    if args.embedding_model_provider:
        payload["embedding_model_provider"] = args.embedding_model_provider
    if args.retrieval_model_json:
        payload["retrieval_model"] = load_inputs(args.retrieval_model_json)

    response = session.post(
        f"{BASE_URL}/console/api/datasets/{dataset_id}/documents",
        json=payload,
        timeout=args.timeout,
    )
    try:
        body = response.json() if response.content else {}
    except Exception:
        body = {"raw": response.text}
    docs = body.get("documents") or []
    return {
        "status_code": response.status_code,
        "body": body,
        "document_ids": [doc.get("id") for doc in docs if isinstance(doc, dict) and doc.get("id")],
        "batch": body.get("batch"),
    }


def fetch_dataset_documents(session: requests.Session, dataset_id: str, timeout: int) -> dict[str, Any]:
    response = session.get(
        f"{BASE_URL}/console/api/datasets/{dataset_id}/documents",
        params={"page": 1, "limit": 100, "fetch": "true"},
        timeout=timeout,
    )
    try:
        body = response.json() if response.content else {}
    except Exception:
        body = {"raw": response.text}
    response.raise_for_status()
    return body


def poll_indexing(session: requests.Session, dataset_id: str, timeout: int, poll_seconds: float) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_body: dict[str, Any] = {}
    terminal = {"available", "completed", "error", "paused"}
    while time.time() < deadline:
        last_body = fetch_dataset_documents(session, dataset_id, timeout=30)
        docs = last_body.get("data") or []
        statuses = [
            str(doc.get("display_status") or doc.get("indexing_status") or "").lower()
            for doc in docs
            if isinstance(doc, dict)
        ]
        if docs and all(status in terminal for status in statuses):
            return {"completed": True, "statuses": statuses, "documents": docs}
        time.sleep(poll_seconds)
    docs = last_body.get("data") or []
    statuses = [
        str(doc.get("display_status") or doc.get("indexing_status") or "").lower()
        for doc in docs
        if isinstance(doc, dict)
    ]
    return {"completed": False, "statuses": statuses, "documents": docs}


def cmd_kb_build(args: argparse.Namespace) -> None:
    files = list_doc_files(args.docs_dir, args.extensions.split(","))
    session = make_console_session()

    dataset_result = create_dataset(session, args)
    dataset_id = dataset_result["dataset_id"]
    uploads: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if dataset_result["status_code"] >= 400 or not dataset_id:
        result = {
            "action": "kb-build",
            "base_url": BASE_URL,
            "name": args.name,
            "docs_dir": str(pathlib.Path(args.docs_dir).expanduser().resolve()),
            "indexing_technique": args.indexing_technique,
            "dataset": dataset_result,
            "dataset_id": dataset_id,
            "files_found": len(files),
            "uploads": uploads,
            "documents": documents,
            "indexing": {},
            "errors": [{"stage": "dataset_create", "response": dataset_result}],
            "passed": False,
        }
        write_json(args.out, result)
        sys.exit(1)

    for path in files:
        try:
            upload = upload_dataset_file(session, path, args.timeout)
            uploads.append(upload)
            if upload["status_code"] >= 400 or not upload["file_id"]:
                errors.append({"path": str(path), "stage": "file_upload", "response": upload})
                continue
            document = create_document_from_file_id(session, dataset_id, upload["file_id"], args)
            documents.append({"path": str(path), **document})
            if document["status_code"] >= 400:
                errors.append({"path": str(path), "stage": "document_create", "response": document})
        except Exception as exc:
            errors.append({"path": str(path), "stage": "upload_or_document_create", "error": str(exc)})

    indexing = {}
    if args.wait:
        indexing = poll_indexing(session, dataset_id, args.wait_timeout, args.poll_seconds)

    result = {
        "action": "kb-build",
        "base_url": BASE_URL,
        "name": args.name,
        "docs_dir": str(pathlib.Path(args.docs_dir).expanduser().resolve()),
        "indexing_technique": args.indexing_technique,
        "dataset": dataset_result,
        "dataset_id": dataset_id,
        "files_found": len(files),
        "uploads": uploads,
        "documents": documents,
        "indexing": indexing,
        "errors": errors,
        "passed": bool(dataset_id) and not errors and (not args.wait or bool(indexing.get("completed"))),
    }
    write_json(args.out, result)
    if errors or (args.wait and not indexing.get("completed")):
        sys.exit(1)


def cmd_run_draft(args: argparse.Namespace) -> None:
    inputs = load_inputs(args.inputs_json)
    session = make_console_session()
    if args.mode == "advanced-chat":
        endpoint = f"{BASE_URL}/console/api/apps/{args.app_id}/advanced-chat/workflows/draft/run"
        payload = {"query": args.query or "", "inputs": inputs, "files": []}
    else:
        endpoint = f"{BASE_URL}/console/api/apps/{args.app_id}/workflows/draft/run"
        payload = {"inputs": inputs, "files": []}

    response = session.post(endpoint, json=payload, stream=True, timeout=args.timeout)
    stream_text = ""
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            stream_text += chunk.decode("utf-8", "ignore")

    events = parse_sse_events(stream_text)
    final = {}
    node_finished = []
    answers = []
    errors = []
    for event in events:
        data = event.get("data") or {}
        event_name = event.get("event")
        if event_name == "workflow_finished":
            final = data
        elif event_name == "node_finished":
            node_finished.append(
                {
                    "id": data.get("node_id"),
                    "title": data.get("title"),
                    "status": data.get("status"),
                    "outputs": data.get("outputs"),
                    "error": data.get("error"),
                }
            )
            if data.get("error"):
                errors.append({"node": data.get("title"), "error": data.get("error")})
        elif event_name in {"message", "agent_message"}:
            answers.append(event.get("answer") or data.get("answer") or "")
        elif event_name in {"error", "workflow_failed"}:
            errors.append(event)

    outputs = final.get("outputs") or {}
    result = {
        "action": "run-draft",
        "base_url": BASE_URL,
        "app_id": args.app_id,
        "mode": args.mode,
        "status_code": response.status_code,
        "workflow_status": final.get("status"),
        "passed": response.status_code == 200 and final.get("status") == "succeeded" and not errors,
        "query": args.query,
        "inputs": inputs,
        "answer": "\n".join([str(item) for item in answers if item]),
        "outputs": outputs,
        "node_finished": node_finished,
        "errors": errors,
        "workflow_finished": final,
        "event_count": len(events),
    }
    if args.include_raw_stream:
        result["raw_stream"] = stream_text
    write_json(args.out, result)
    if response.status_code >= 400 or errors or final.get("status") == "failed":
        sys.exit(1)


def get_or_create_api_key(session: requests.Session, app_id: str) -> tuple[dict[str, Any], str]:
    response = session.get(f"{BASE_URL}/console/api/apps/{app_id}/api-keys", timeout=30)
    response.raise_for_status()
    keys = response.json().get("data") or []
    if keys:
        token = keys[0].get("token") or ""
        return {
            "source": "existing",
            "id": keys[0].get("id"),
            "type": keys[0].get("type"),
            "token": redact_token(token),
            "created_at": keys[0].get("created_at"),
        }, token

    created_response = session.post(f"{BASE_URL}/console/api/apps/{app_id}/api-keys", json={}, timeout=30)
    created_response.raise_for_status()
    created = created_response.json()
    token = created.get("token") or ""
    return {
        "source": "created",
        "id": created.get("id"),
        "type": created.get("type"),
        "token": redact_token(token),
        "created_at": created.get("created_at"),
    }, token


def resolve_api_key(args: argparse.Namespace) -> str:
    if getattr(args, "api_key", None):
        return args.api_key
    env_name = getattr(args, "api_key_env", None) or "DIFY_APP_API_KEY"
    token = os.environ.get(env_name)
    if token:
        return token
    raise SystemExit(f"Missing app API key. Pass --api-key or set {env_name}.")


def run_service_workflow(
    api_key: str,
    inputs: dict[str, Any],
    user: str,
    response_mode: str,
    endpoint: str,
    timeout: int,
) -> dict[str, Any]:
    payload = {
        "inputs": inputs,
        "response_mode": response_mode,
        "user": user,
    }
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
        stream=response_mode == "streaming",
    )
    if response_mode == "streaming":
        stream_text = ""
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                stream_text += chunk.decode("utf-8", "ignore")
        body: dict[str, Any] = {"events": parse_sse_events(stream_text)}
        raw_stream = stream_text
    else:
        raw_stream = ""
        try:
            body = response.json() if response.content else {}
        except Exception:
            body = {"raw": response.text}
    outputs = (body.get("data") or {}).get("outputs") if isinstance(body, dict) else None
    return {
        "endpoint": endpoint,
        "status_code": response.status_code,
        "request": {"inputs": inputs, "response_mode": response_mode, "user": user},
        "response": body,
        "outputs": outputs or {},
        "task_id": (body.get("task_id") or (body.get("data") or {}).get("task_id")) if isinstance(body, dict) else None,
        "workflow_run_id": (body.get("workflow_run_id") or (body.get("data") or {}).get("id")) if isinstance(body, dict) else None,
        "raw_stream": raw_stream,
        "passed": response.status_code == 200 and bool(outputs or body),
    }


def cmd_service_run(args: argparse.Namespace) -> None:
    inputs = load_inputs(args.inputs_json)
    api_key = resolve_api_key(args)
    endpoint = args.endpoint or f"{BASE_URL}/v1/workflows/run"
    result = {
        "action": "service-run",
        "base_url": BASE_URL,
        "api_key": redact_token(api_key),
        "service_api": run_service_workflow(
            api_key=api_key,
            inputs=inputs,
            user=args.user,
            response_mode=args.response_mode,
            endpoint=endpoint,
            timeout=args.timeout,
        ),
    }
    result["passed"] = bool(result["service_api"].get("passed"))
    if not args.include_raw_stream and result["service_api"].get("raw_stream"):
        result["service_api"]["raw_stream"] = "[redacted by default; rerun with --include-raw-stream]"
    write_json(args.out, result)
    if not result["passed"]:
        sys.exit(1)


def cmd_publish_api_run(args: argparse.Namespace) -> None:
    inputs = load_inputs(args.inputs_json)
    session = make_console_session()

    publish_payload = {
        "marked_name": args.mark_name,
        "marked_comment": args.mark_comment,
    }
    publish_response = session.post(
        f"{BASE_URL}/console/api/apps/{args.app_id}/workflows/publish",
        json=publish_payload,
        timeout=args.timeout,
    )
    publish_body = publish_response.json() if publish_response.content else {}
    publish_response.raise_for_status()

    enable_response = session.post(
        f"{BASE_URL}/console/api/apps/{args.app_id}/api-enable",
        json={"enable_api": True},
        timeout=30,
    )
    enable_body = enable_response.json() if enable_response.content else {}
    enable_response.raise_for_status()

    key_meta, api_key = get_or_create_api_key(session, args.app_id)
    service_result = run_service_workflow(
        api_key=api_key,
        inputs=inputs,
        user=args.user,
        response_mode="blocking",
        endpoint=f"{BASE_URL}/v1/workflows/run",
        timeout=args.timeout,
    )
    result = {
        "action": "publish-api-run",
        "base_url": BASE_URL,
        "app_id": args.app_id,
        "publish": {"status_code": publish_response.status_code, "body": publish_body},
        "api_enable": {
            "status_code": enable_response.status_code,
            "body": {
                "id": enable_body.get("id"),
                "enable_api": enable_body.get("enable_api"),
                "mode": enable_body.get("mode"),
                "name": enable_body.get("name"),
            },
        },
        "api_key": key_meta,
        "service_api": service_result,
        "passed": bool(service_result.get("passed")),
    }
    write_json(args.out, result)
    if not result["passed"]:
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    install_parser = sub.add_parser("install-guide", help="Print local Dify CE Docker Compose install guidance.")
    install_parser.add_argument("--out", help="Optional markdown output path.")
    install_parser.set_defaults(func=cmd_install_guide)

    import_parser = sub.add_parser("import", help="Import workflow/chatflow YAML through the Console API.")
    import_parser.add_argument("workflow_file")
    import_parser.add_argument("--name")
    import_parser.add_argument("--app-id")
    import_parser.add_argument("--out")
    import_parser.add_argument("--timeout", type=int, default=60)
    import_parser.set_defaults(func=cmd_import)

    kb_parser = sub.add_parser("kb-build", help="Create a dataset and import local docs as knowledge-base documents.")
    kb_parser.add_argument("--name", required=True, help="Dataset name.")
    kb_parser.add_argument("--docs-dir", required=True, help="Directory containing .md/.txt docs to import.")
    kb_parser.add_argument("--description", default="")
    kb_parser.add_argument("--indexing-technique", choices=["high_quality", "economy"], default="high_quality")
    kb_parser.add_argument("--embedding-model")
    kb_parser.add_argument("--embedding-model-provider")
    kb_parser.add_argument("--retrieval-model-json")
    kb_parser.add_argument("--permission", default="only_me")
    kb_parser.add_argument("--process-rule", choices=["automatic"], default="automatic")
    kb_parser.add_argument("--doc-form", default="text_model")
    kb_parser.add_argument("--doc-language", default="English")
    kb_parser.add_argument("--extensions", default=".md,.txt,.html")
    kb_parser.add_argument("--wait", action="store_true", help="Poll document indexing status.")
    kb_parser.add_argument("--wait-timeout", type=int, default=300)
    kb_parser.add_argument("--poll-seconds", type=float, default=5)
    kb_parser.add_argument("--out")
    kb_parser.add_argument("--timeout", type=int, default=120)
    kb_parser.set_defaults(func=cmd_kb_build)

    run_parser = sub.add_parser("run-draft", help="Run draft workflow/chatflow and save node events.")
    run_parser.add_argument("--app-id", required=True)
    run_parser.add_argument("--mode", choices=["workflow", "advanced-chat"], default="workflow")
    run_parser.add_argument("--query")
    run_parser.add_argument("--inputs-json", default="{}")
    run_parser.add_argument("--out")
    run_parser.add_argument("--timeout", type=int, default=180)
    run_parser.add_argument("--include-raw-stream", action="store_true")
    run_parser.set_defaults(func=cmd_run_draft)

    publish_parser = sub.add_parser("publish-api-run", help="Publish, enable API, and run /v1/workflows/run.")
    publish_parser.add_argument("--app-id", required=True)
    publish_parser.add_argument("--inputs-json", default="{}")
    publish_parser.add_argument("--mark-name", default="codex-test")
    publish_parser.add_argument("--mark-comment", default="Published by Codex local CE workflow autobuilder.")
    publish_parser.add_argument("--user", default="codex-local-test")
    publish_parser.add_argument("--out")
    publish_parser.add_argument("--timeout", type=int, default=180)
    publish_parser.set_defaults(func=cmd_publish_api_run)

    service_parser = sub.add_parser("service-run", help="Run published workflow through Service API endpoint + app key.")
    service_parser.add_argument("--inputs-json", default="{}")
    service_parser.add_argument("--api-key")
    service_parser.add_argument("--api-key-env", default="DIFY_APP_API_KEY")
    service_parser.add_argument("--endpoint", help="Full endpoint URL. Defaults to DIFY_BASE_URL/v1/workflows/run.")
    service_parser.add_argument("--response-mode", choices=["blocking", "streaming"], default="blocking")
    service_parser.add_argument("--user", default="codex-service-test")
    service_parser.add_argument("--include-raw-stream", action="store_true")
    service_parser.add_argument("--out")
    service_parser.add_argument("--timeout", type=int, default=180)
    service_parser.set_defaults(func=cmd_service_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
