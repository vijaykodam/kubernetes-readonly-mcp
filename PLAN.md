# PLAN: Modernize Kubernetes Read-Only MCP Server

Authoritative, self-contained execution plan. A fresh session should read `CLAUDE.md` then this
file, and resume at the first phase whose checkboxes are unticked.

Repo: `/Users/vg/experiments/k8s-mcp-server/kubernetes-readonly-mcp` · Work branch: `modernize-mcp-server`

---

## Context

`kubernetes-readonly-mcp` is a read-only Kubernetes MCP server (published to PyPI, run via
`uvx kubernetes-readonly-mcp@latest`). It currently exposes 8 curated list/get tools and a README
written around the now-deprecated Amazon Q CLI. Five problems prompt this work:

1. **Stale deps:** `kubernetes>=28.1.0`; `requires-python>=3.8` (inconsistent with 3.10+ classifiers).
2. **Framework mismatch + Q-CLI cruft:** code imports the *bundled* FastMCP 1.0
   (`from mcp.server.fastmcp import FastMCP`) while `pyproject` declares the *standalone* `fastmcp`.
   Tools carry an Amazon-Q workaround: a `resource: Any = None` injection param, an
   `@mcp.resource('resource://k8s')` function used as a plain initializer, and `isinstance(resource, str)`
   fallbacks. With Q removed, this should go.
3. **Limited coverage:** only 8 hand-written tools; no way to read arbitrary kinds or CRDs.
4. **Outdated docs:** Amazon Q-centric; missing Claude Code, Codex CLI, Kiro CLI, Antigravity.
5. **Packaging:** version must bump for a new PyPI release.

Outcome: a modern FastMCP 3.x read-only server that covers all read-only/list operations (curated +
generic), follows current MCP guidance (tool annotations, clean init, structured output), and ships
a README documenting today's MCP hosts.

## Decisions (locked)

- **Framework:** standalone **FastMCP 3.x** (`from fastmcp import FastMCP`, pin `fastmcp>=3.3`).
- **Coverage:** Hybrid — keep the 8 curated tools; add EKS-style generic tools
  `list_resource`, `get_resource`, `list_api_resources` (GET/LIST-only via the dynamic client).
- **Output:** add read-only **tool annotations** to every tool and return **native Python objects**
  (FastMCP emits structured content + schemas) instead of `json.dumps(...)` strings.
- **Init:** remove the Q-CLI workaround; use a lazy module-level singleton `_get_manager()`
  (sync, fits the synchronous kubernetes client). No per-tool `resource` param.
- **Secrets:** never return Secret `data`/`stringData`; only metadata + `type`. Enforced centrally
  via `_sanitize()` so it cannot be bypassed through `get_resource(kind="Secret")`.
- **Versions:** `kubernetes>=36.0.0` (latest, 2026-05-20), `requires-python>=3.10`, package -> `0.2.0`.
- **Docs:** remove Amazon Q section; host order = Claude Code, Codex CLI, Kiro CLI (successor to
  Amazon Q), Antigravity, Claude Desktop.

## Reference facts (verified 2026-05-22)

- kubernetes (PyPI) latest **36.0.0**, requires Python >=3.10.
- fastmcp (PyPI) latest **3.3.1** (2026-05-15), stable, Python >=3.10; `@mcp.tool` decorator intact.
- Tool annotations: `from mcp.types import ToolAnnotations`;
  `@mcp.tool(annotations=ToolAnnotations(title=..., readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))`.
- Dynamic client: `from kubernetes import dynamic`; `dyn = dynamic.DynamicClient(client.ApiClient())`;
  `api = dyn.resources.get(api_version="v1", kind="Pod")`; `api.get(namespace=, label_selector=, field_selector=)`;
  discovery via `dyn.resources.search()` (each result has `group_version`, `kind`, `namespaced`, `verbs`).
- AWS EKS MCP read-only surface we mirror: `list_k8s_resources`, `manage_k8s_resource(read)`,
  `list_api_versions`, `get_pod_logs`, `get_k8s_events`.
- CI: `.github/workflows/test.yml` enforces **flake8 + black --check + isort --check + pytest**
  (matrix 3.11/3.12; black line-length 100). `publish.yml` builds + `twine upload` on GitHub release.

---

## Per-phase protocol (REPEAT FOR EVERY PHASE)

1. Do the phase's tasks.
2. Run the phase's verification; paste real command output (no success claims without evidence).
3. Update this `PLAN.md`: tick the phase's checkboxes, add a short "Done / notes" line.
4. **Ask the user for manual approval.** Do not commit before approval.
5. On approval: `git add -A && git commit` on `modernize-mcp-server`. **No Co-Authored-By trailer
   or Claude attribution in the commit message.** Record the commit hash under the phase below.
6. The user may clear context. The next session reads `CLAUDE.md` + `PLAN.md` and starts the next
   unchecked phase.

---

## Phase 1 — Scaffolding (branch, PLAN.md, CLAUDE.md)  [STATUS: done]

- [x] Create branch `modernize-mcp-server` off `main`.
- [x] Create repo `PLAN.md` (this file).
- [x] Create repo `CLAUDE.md` (concise, <500 words).
- [x] Save user working-preferences to Claude memory:
      (a) phased work with manual-approval + commit gates and context-clear handoff via PLAN.md;
      (b) git commit messages must NOT include a Co-Authored-By trailer or Claude attribution.

Verification:
- `git branch --show-current` == `modernize-mcp-server`.
- `PLAN.md` and `CLAUDE.md` exist; `wc -w CLAUDE.md` < 500.

Done / notes: bootstrapping commit for the modernization work. Commit: 44a5cd4

## Phase 2 — Dependencies & packaging

- [ ] `pyproject.toml` `dependencies = ["fastmcp>=3.3", "kubernetes>=36.0.0"]`.
- [ ] `requires-python = ">=3.10"`.
- [ ] Classifiers add Python 3.12, 3.13 (keep 3.10, 3.11); `[tool.black] target-version` -> py310..py313.
- [ ] `version = "0.2.0"`.
- [ ] `src/kubernetes_readonly_mcp/__init__.py`: `__version__ = "0.2.0"`.
- [ ] Update CI matrix in `.github/workflows/test.yml` to `['3.10','3.11','3.12','3.13']`.

Verification:
- `pip install -e ".[dev]"` succeeds on Python 3.10+.
- `python -c "import kubernetes_readonly_mcp as k; print(k.__version__)"` -> `0.2.0`.
- Note: server.py still imports the bundled FastMCP here; that stays importable (mcp is a transitive
  dep of fastmcp), so the repo remains runnable until Phase 3.

Done / notes:  Commit:

## Phase 3 — Core rewrite: framework, init, annotations, structured output (existing 8 tools)

- [ ] Switch import to `from fastmcp import FastMCP` and `from mcp.types import ToolAnnotations`.
- [ ] Remove the Q-CLI workaround entirely: delete the `resource: Any = None` params, the
      `@mcp.resource('resource://k8s')` function, and all `isinstance(resource, str)` / `hasattr` checks.
- [ ] Add lazy singleton: `_manager = None`; `_get_manager()` creates `KubernetesManager()` once.
- [ ] `KubernetesManager`: add `dynamic.DynamicClient(client.ApiClient())` as `self.dynamic_api`
      with a `get_dynamic_api()` accessor (alongside Core/Apps/Batch/Networking).
- [ ] Add `_sanitize(obj_dict, kind)`: drop `metadata.managedFields`; if `kind == "Secret"`,
      remove `data` and `stringData` (keep `metadata` + `type`).
- [ ] Convert all 8 tools: call `_get_manager()`, return native `list[dict]` / `dict` (errors as
      `{"error": ...}`), and annotate each with
      `ToolAnnotations(title=<readable>, readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)`.
- [ ] Keep `main()` -> `mcp.run()` (STDIO).
- [ ] Update `tests/test_server.py`: assert the dynamic client is created in init; drop any
      `resource=` usage; adjust to structured (object) returns.

Verification:
- `pytest -q` passes; `flake8 src tests`, `black --check src tests`, `isort --check-only --profile black src tests` clean.
- `python -c "from kubernetes_readonly_mcp.server import mcp; print('ok')"` imports without error.

Done / notes:  Commit:

## Phase 4 — Generic read-only tools (full coverage + CRDs)

- [ ] `list_resource(kind, api_version="v1", namespace=None, label_selector=None, field_selector=None)`
      -> `dyn.resources.get(api_version, kind).get(...)`, return `[_sanitize(i.to_dict(), kind) for i in res.items]`.
- [ ] `get_resource(kind, name, api_version="v1", namespace=None)` -> single sanitized dict.
- [ ] `list_api_resources()` -> discover via `dyn.resources.search()`; return list of
      `{group_version, kind, namespaced, verbs}` for resources whose verbs include `list` (deduped).
- [ ] All three annotated read-only; GET/LIST only — never call create/replace/patch/delete.
      Wrap in try/except -> `{"error": ...}`.
- [ ] Tests: mocked dynamic client for the three tools; an explicit **Secret redaction** test
      proving `data`/`stringData` are absent from output.

Verification:
- `pytest -q` passes (incl. Secret-redaction test); lint trio clean.

Done / notes:  Commit:

## Phase 5 — README rewrite

- [ ] Intro: FastMCP 3.x + latest kubernetes client. Features: add the 3 generic tools; state
      Secret values are never exposed.
- [ ] Prerequisites: Python 3.10+.
- [ ] Remove the "Amazon Q CLI Setup" section and the Amazon Q example in "General MCP Host Config".
- [ ] Host sections, in order, each with copy-paste config (`command: "uvx"`, `args: ["kubernetes-readonly-mcp@latest"]`):
      1. **Claude Code** — `claude mcp add kubernetes-readonly-mcp -- uvx kubernetes-readonly-mcp@latest`
         (stdio default; `--` separates the command). Also show project `.mcp.json`.
      2. **Codex CLI** — `~/.codex/config.toml`:
         `[mcp_servers.kubernetes-readonly-mcp]` / `command = "uvx"` / `args = ["kubernetes-readonly-mcp@latest"]`.
         Note `codex mcp` manages servers; CLI + IDE share this config.
      3. **Kiro CLI** (successor to deprecated Amazon Q) — `~/.kiro/settings/mcp.json` (or
         `<project>/.kiro/settings/mcp.json`): standard `mcpServers` JSON with `"disabled": false`.
         Note old `~/.aws/amazonq/mcp.json` migrates to `~/.kiro/settings/mcp.json`.
      4. **Antigravity** (Google) — `~/.gemini/antigravity/mcp_config.json`
         (Windows `C:\Users\<USER>\.gemini\antigravity\mcp_config.json`); standard `mcpServers` JSON.
         Open via "..." menu -> MCP Servers -> Manage MCP Servers -> View raw config.
      5. **Claude Desktop** — `claude_desktop_config.json` (macOS
         `~/Library/Application Support/Claude/claude_desktop_config.json`; Windows
         `%APPDATA%\Claude\claude_desktop_config.json`); standard `mcpServers` JSON; restart app.
- [ ] Fix the misleading verification tip: `uvx kubernetes-readonly-mcp@latest` starts the STDIO
      server (it does NOT accept a tool name like `list_namespaces` as a CLI arg).
- [ ] Update "Example Host Documentation" links (drop Amazon Q). Add an example prompt exercising
      the generic tool, e.g. "List all ingresses across every namespace".

Verification:
- Each JSON snippet parses (e.g. pipe through `python -m json.tool`); TOML is well-formed.
- No remaining "Amazon Q" references except the one-line "Kiro replaces Amazon Q" note.

Done / notes:  Commit:

## Phase 6 — Final verification & release prep

- [ ] Full `pytest`, `flake8`, `black --check`, `isort --check`.
- [ ] `python -m build` produces sdist + wheel without errors.
- [ ] Live smoke test against a kind cluster (`kind create cluster`): start the server via an MCP
      host (or FastMCP client) and confirm: `list_api_resources()` returns kinds;
      `list_resource(kind="Pod", namespace="kube-system")`;
      `list_resource(kind="Ingress", api_version="networking.k8s.io/v1")` (non-core);
      `get_resource(kind="Secret", name=<x>, namespace="kube-system")` returns **no data/stringData**;
      existing curated tools still work.
- [ ] Record release note: bump done at `0.2.0`; publishing is via creating a GitHub release/tag
      (triggers `publish.yml` -> PyPI). Do NOT publish without explicit user instruction.

Verification:
- All checks green with pasted output; smoke-test results recorded here.

Done / notes:  Commit:

---

## Session handoff (for a fresh context)

- Repo: `/Users/vg/experiments/k8s-mcp-server/kubernetes-readonly-mcp`; work branch `modernize-mcp-server`.
- Read `CLAUDE.md` then this file; resume at the first phase whose checkboxes are unticked.
- Hard rules: read-only only (never add mutating tools); Secret `data`/`stringData` never returned;
  every tool annotated read-only; tools return native objects; FastMCP 3.x; no emojis anywhere;
  commits carry no Co-Authored-By trailer.
- Follow the Per-phase protocol: work -> verify with real output -> update PLAN.md -> get manual
  approval -> commit -> (optional context clear) -> next phase.
- Publishing to PyPI is release-triggered and requires explicit user go-ahead.

## Out of scope

- No write/mutating tools; no `--allow-write` flag (server is read-only by construction).
- No new transports (STDIO only).
- No actual PyPI publish in these phases (only version bump + build verification).
- No refactor beyond `_get_manager()` / `_sanitize()` and the per-tool changes above.
