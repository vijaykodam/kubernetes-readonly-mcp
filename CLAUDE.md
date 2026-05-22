# CLAUDE.md

## Project
`kubernetes-readonly-mcp` — a read-only Kubernetes MCP server, published to PyPI and run via
`uvx kubernetes-readonly-mcp@latest`. It exposes only GET/LIST tools so AI assistants can inspect
and troubleshoot clusters without any risk of mutation.

## Layout
- `src/kubernetes_readonly_mcp/server.py` — all MCP tools and the `KubernetesManager` (API clients).
- `src/kubernetes_readonly_mcp/__init__.py` — `__version__`.
- `tests/test_server.py` — pytest suite.
- `pyproject.toml` — setuptools build, deps, entry point `kubernetes-readonly-mcp = ...server:main`.
- `PLAN.md` — current modernization plan and progress (read it for active work).

## Stack
FastMCP 3.x (standalone `fastmcp`, `from fastmcp import FastMCP`) + the official `kubernetes`
Python client. Generic tools use the dynamic client (`kubernetes.dynamic.DynamicClient`). STDIO transport.

## Hard rules
- Read-only ONLY. Never add create/update/delete/patch tools or call mutating client methods.
- Secret `data`/`stringData` is NEVER returned — only metadata + `type` (enforced in `_sanitize()`).
- Every tool is annotated `ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)`.
- Tools return native Python objects (lists/dicts); FastMCP serializes + emits structured content.
- No emojis anywhere (code, docs, commits, output).
- Commit messages must NOT include a Co-Authored-By trailer or any Claude attribution.

## Commands
- Install dev: `pip install -e ".[dev]"`
- Test: `pytest`
- Lint (CI-enforced): `flake8 src tests` · `black --check src tests` · `isort --check-only --profile black src tests`
- Build: `python -m build`
- Local cluster for smoke tests: `kind create cluster`

## Publishing
Version lives in `pyproject.toml` and `__init__.py` (keep in sync). Creating a GitHub release/tag
triggers `.github/workflows/publish.yml` -> PyPI. Never publish without explicit user instruction.

## Working protocol (when executing PLAN.md)
Work one phase at a time: do the tasks, verify with real command output, update `PLAN.md`
checkboxes, ask the user for manual approval, then commit on branch `modernize-mcp-server`.
After a commit the user may clear context; the next session resumes from `PLAN.md`.
