# PLAN: Modernize Kubernetes Read-Only MCP Server

Authoritative, self-contained execution plan. This committed file is the source of truth for the
work. `CLAUDE.md` is a local convenience file that is **gitignored (not committed)**, so do not rely
on it being present in a fresh clone — read it first if it exists locally, then this file. Resume at
the first phase whose checkboxes are unticked.

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
  (FastMCP serializes them to JSON) instead of building `json.dumps(...)` strings by hand.
  (Phase 6 correction: dict returns also populate `structured_content`; bare-list returns deliver
  JSON via the text content block only — matching the AWS EKS MCP reference, which likewise emits no
  `structured_content`. See the Phase 6 FINDING note.)
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

- [x] `pyproject.toml` `dependencies = ["fastmcp>=3.3", "kubernetes>=36.0.0"]`.
- [x] `requires-python = ">=3.10"`.
- [x] Classifiers add Python 3.12, 3.13 (keep 3.10, 3.11); `[tool.black] target-version` -> py310..py313.
- [x] `version = "0.2.0"`.
- [x] `src/kubernetes_readonly_mcp/__init__.py`: `__version__ = "0.2.0"`.
- [x] Update CI matrix in `.github/workflows/test.yml` to `['3.10','3.11','3.12','3.13']`.

Verification:
- `pip install -e ".[dev]"` succeeds on Python 3.10+.
- `python -c "import kubernetes_readonly_mcp as k; print(k.__version__)"` -> `0.2.0`.
- Note: server.py still imports the bundled FastMCP here; that stays importable (mcp is a transitive
  dep of fastmcp), so the repo remains runnable until Phase 3.

Done / notes: System Python is 3.9, so verified in a `uv`-provisioned 3.12 venv (`.venv`, gitignored).
`uv pip install -e ".[dev]"` succeeded; resolved fastmcp 3.3.1, kubernetes 36.0.0, mcp 1.27.1 (transitive).
`__version__` prints `0.2.0`. Confirmed the Phase 2 note: `from mcp.server.fastmcp import FastMCP` and
`import kubernetes_readonly_mcp.server` both still import OK (repo runnable until Phase 3). Only
`pyproject.toml`, `__init__.py`, `.github/workflows/test.yml` changed. Commit: ada4392

## Phase 3 — Core rewrite: framework, init, annotations, structured output (existing 8 tools)  [STATUS: done]

- [x] Switch import to `from fastmcp import FastMCP` and `from mcp.types import ToolAnnotations`.
- [x] Remove the Q-CLI workaround entirely: delete the `resource: Any = None` params, the
      `@mcp.resource('resource://k8s')` function, and all `isinstance(resource, str)` / `hasattr` checks.
- [x] Add lazy singleton: `_manager = None`; `_get_manager()` creates `KubernetesManager()` once.
- [x] `KubernetesManager`: add `dynamic.DynamicClient(client.ApiClient())` as `self.dynamic_api`
      with a `get_dynamic_api()` accessor (alongside Core/Apps/Batch/Networking).
- [x] Add `_sanitize(obj_dict, kind)`: drop `metadata.managedFields`; if `kind == "Secret"`,
      remove `data` and `stringData` (keep `metadata` + `type`).
- [x] Convert all 8 tools: call `_get_manager()`, return native `list[dict]` / `dict` (errors as
      `{"error": ...}`), and annotate each with
      `ToolAnnotations(title=<readable>, readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)`.
- [x] Keep `main()` -> `mcp.run()` (STDIO).
- [x] Update `tests/test_server.py`: assert the dynamic client is created in init; drop any
      `resource=` usage; adjust to structured (object) returns.

Verification:
- `pytest -q` passes; `flake8 src tests`, `black --check src tests`, `isort --check-only --profile black src tests` clean.
- `python -c "from kubernetes_readonly_mcp.server import mcp; print('ok')"` imports without error.

Done / notes: server.py fully rewritten on standalone FastMCP 3.x. `_ro(title)` helper builds the
shared read-only `ToolAnnotations`; all 8 tools annotated and returning native objects (errors as
`{"error": ...}`). Lazy `_get_manager()` singleton + `dynamic_api`/`get_dynamic_api()` added;
`_sanitize()` added (used by Phase 4 generic tools, unit-tested now). Tests rewritten: dynamic-client
init assertion, structured-return + error-dict tests, `_sanitize` Secret-redaction unit test (4 pass).
Decisions made during execution (flagged for review):
  (1) Removed all `print(...)` debug calls — on STDIO transport stdout is the JSON-RPC channel, so
      prints corrupt the protocol; errors now flow only through `{"error": ...}` returns.
  (2) Dropped the now-meaningless `pretty` param from `get_logs` (it only set `json.dumps` indent,
      irrelevant with structured output). Kept `timestamps` (affects actual log content).
  (3) Added a repo `.flake8` (max-line-length=100, extend-ignore E203,W503) — flake8 had NO config
      and defaulted to 79, contradicting black's 100; CI's flake8 step was already failing on the
      original code (92 E501s). Aligning flake8 to black is required for the lint trio to pass.
Also (per user request) `CLAUDE.md` added to `.gitignore`; PLAN.md handoff references updated to treat
it as local-only. CLAUDE.md needs `git rm --cached` at commit time (still tracked from Phase 1).
Verification output (real): flake8 exit 0; black --check exit 0 (3 files unchanged); isort exit 0;
pytest 4 passed; import check prints `import ok`.
Commit: 7753dd4

## Phase 4 — Generic read-only tools (full coverage + CRDs)  [STATUS: done]

- [x] `list_resource(kind, api_version="v1", namespace=None, label_selector=None, field_selector=None)`
      -> `dyn.resources.get(api_version, kind).get(...)`, return `[_sanitize(i.to_dict(), kind) for i in res.items]`.
- [x] `get_resource(kind, name, api_version="v1", namespace=None)` -> single sanitized dict.
- [x] `list_api_resources()` -> discover via `dyn.resources.search()`; return list of
      `{group_version, kind, namespaced, verbs}` for resources whose verbs include `list` (deduped).
- [x] All three annotated read-only; GET/LIST only — never call create/replace/patch/delete.
      Wrap in try/except -> `{"error": ...}`.
- [x] Tests: mocked dynamic client for the three tools; an explicit **Secret redaction** test
      proving `data`/`stringData` are absent from output.

Verification:
- `pytest -q` passes (incl. Secret-redaction test); lint trio clean.

Done / notes: Added three generic tools after `list_nodes`, all using `_get_manager().get_dynamic_api()`
and the verified two-step dynamic-client pattern (`dyn.resources.get(api_version=, kind=)` for discovery,
then `.get(...)` for the API call). `kind` is passed to `_sanitize()` from the tool argument (not read
off each item), so Secret redaction holds even when list items omit their own `kind`. `list_api_resources`
filters on `"list" in (verbs or [])` (verbs can be None) and dedupes by `(group_version, kind)`.
Decisions (flagged): (1) generic-tool errors return `{"error": str(e)}` matching the curated list tools'
style (no 404-specific handling — the dynamic client surfaces useful messages directly). (2) `list_resource`
with `namespace=None` lists across all namespaces / cluster scope, no special-casing needed.
Tests added (5): list_resource native+sanitized, list_resource Secret redaction, get_resource Secret
redaction, list_api_resources filter+dedup+None-verbs, generic-tool error-dict. API surface verified
against installed kubernetes 36.0.0 (Resource has group_version/kind/namespaced/verbs; ResourceInstance
has to_dict). Verification output (real): pytest 9 passed; flake8 exit 0; black --check 3 files unchanged
(benign py312-vs-py313 AST-check warning); isort clean; import ok. Registered-tool check: all 11 tools
(8 curated + 3 generic) report readOnly=True, destructive=False.
Commit: 3a61ffe

## Phase 5 — README rewrite  [STATUS: done]

- [x] Intro: FastMCP 3.x + latest kubernetes client. Features: add the 3 generic tools; state
      Secret values are never exposed.
- [x] Prerequisites: Python 3.10+.
- [x] Remove the "Amazon Q CLI Setup" section and the Amazon Q example in "General MCP Host Config".
- [x] Host sections, in order, each with copy-paste config (`command: "uvx"`, `args: ["kubernetes-readonly-mcp@latest"]`):
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
- [x] Fix the misleading verification tip: `uvx kubernetes-readonly-mcp@latest` starts the STDIO
      server (it does NOT accept a tool name like `list_namespaces` as a CLI arg).
- [x] Update "Example Host Documentation" links (drop Amazon Q). Add an example prompt exercising
      the generic tool, e.g. "List all ingresses across every namespace".

Verification:
- Each JSON snippet parses (e.g. pipe through `python -m json.tool`); TOML is well-formed.
- No remaining "Amazon Q" references except the one-line "Kiro replaces Amazon Q" note.

Done / notes: README fully rewritten. Intro now cites FastMCP 3.x + official kubernetes client and
states Secret values are never exposed (metadata + type only). Features split into "Curated tools"
(the 8) and "Generic tools" (list_resource, get_resource, list_api_resources) with a Secret-safety
callout. Prereqs state Python 3.10+. "Amazon Q CLI Setup" section deleted and the Amazon Q example in
General MCP Host Config removed. Added five host sections in order — Claude Code (`claude mcp add ...`
+ project `.mcp.json`), Codex CLI (`~/.codex/config.toml` `[mcp_servers.*]`), Kiro CLI
(`~/.kiro/settings/mcp.json`, `"disabled": false`, + amazonq->kiro migration note), Antigravity
(`~/.gemini/antigravity/mcp_config.json` + Windows path + in-app open path), Claude Desktop (macOS +
Windows paths, restart). Replaced the bad `uvx ... list_namespaces` tip with an accurate "Verifying
the setup" section explaining the STDIO server waits for an MCP host and takes no tool-name CLI arg.
Example Host Documentation links updated (Amazon Q dropped; Claude Code/Codex/Kiro/Antigravity/Claude
Desktop added); added generic-tool example prompt ("List all ingresses across every namespace").
Decisions (flagged): (1) the blog/demo line previously said "running the MCP server using Amazon Q
CLI" — reworded to "Watch the demo and read the write-up at <url>" to honor the no-stray-Amazon-Q
rule while keeping the link. (2) Two Amazon Q mentions remain, both in the Kiro section and both
explicitly required by this phase's task list (successor framing + the `~/.aws/amazonq/mcp.json`
migration pointer). Verification output (real): 4/4 JSON blocks parse OK; the 1 TOML block parses OK
via the 3.12 venv and resolves to command="uvx", args=["kubernetes-readonly-mcp@latest"]; grep shows
no stray "Amazon Q" beyond the two Kiro notes and no `FastMCP 2` / bad-CLI-example leftovers.
Commit: e147d1b

## Phase 6 — Final verification & release prep  [STATUS: done, pending approval]

- [x] Full `pytest`, `flake8`, `black --check`, `isort --check`.
- [x] `python -m build` produces sdist + wheel without errors.
- [x] Live smoke test against a kind cluster (`kind create cluster`): start the server via an MCP
      host (or FastMCP client) and confirm: `list_api_resources()` returns kinds;
      `list_resource(kind="Pod", namespace="kube-system")`;
      `list_resource(kind="Ingress", api_version="networking.k8s.io/v1")` (non-core);
      `get_resource(kind="Secret", name=<x>, namespace="kube-system")` returns **no data/stringData**;
      existing curated tools still work.
- [x] Record release note: bump done at `0.2.0`; publishing is via creating a GitHub release/tag
      (triggers `publish.yml` -> PyPI). Do NOT publish without explicit user instruction.

Verification:
- All checks green with pasted output; smoke-test results recorded here.

Done / notes: All checks ran in the 3.12 `.venv`.
- Lint/test trio (real output): `pytest -q` -> 9 passed; `flake8 src tests` exit 0; `black --check src tests`
  exit 0 (3 files unchanged; benign py312-cannot-parse-py313 AST warning); `isort --check-only --profile
  black src tests` exit 0.
- Build (real output): `python -m build` -> "Successfully built kubernetes_readonly_mcp-0.2.0.tar.gz and
  kubernetes_readonly_mcp-0.2.0-py3-none-any.whl". `twine check dist/*` -> both artifacts PASSED. `dist/`,
  `build/`, `.venv`, `*.egg-info` are all gitignored (git status stays clean).
- Smoke test (real output): created `kind` cluster `k8s-mcp-smoke` (node v1.35.0, 1 node Ready). Ran a
  throwaway `smoke_test.py` driving the server through the in-memory `fastmcp.Client` (real MCP
  dispatch + serialization path). 9/9 PASS:
  (1) all 11 tools report readOnlyHint=True/destructiveHint=False;
  (2) `list_api_resources()` -> 118 resources incl. Pod & Secret;
  (3) `list_resource(Pod, kube-system)` -> 8 pods;
  (4) `list_resource(Ingress, networking.k8s.io/v1)` non-core resolves -> empty list, no error
      (cross-checked: direct dynamic client also returns 0 items; fresh cluster has no ingresses);
  (5) `list_resource(Secret, kube-system)` -> 1 secret, no `data`/`stringData`;
  (6) `get_resource(Secret, bootstrap-token-abcdef, kube-system)` -> keys {apiVersion, kind, metadata,
      type}, NO data/stringData (redaction proven meaningful: `kubectl` shows that secret carries 6
      base64 data fields of type bootstrap.kubernetes.io/token);
  (7-9) curated `list_namespaces` (5 ns incl. default+kube-system), `list_nodes` (1 node, Ready),
      `list_pods(kube-system)` (8 pods).
  `smoke_test.py` is a throwaway verification script — NOT committed (deleted after the run). The kind
  cluster is torn down post-verification (`kind delete cluster --name k8s-mcp-smoke`).
- Release note: version is `0.2.0` (in `pyproject.toml` + `__init__.py`). Publishing is GitHub-release
  triggered: `publish.yml` runs on `release: [created]` -> `python -m build` + `twine upload dist/*`
  using the `PYPI_API_TOKEN` secret. Do NOT create a release / publish without explicit user go-ahead.

FINDING flagged for review (structured output): the smoke test showed FastMCP emits real
`structured_content`/`.data` only for the **dict-returning** tools (`get_resource`, `get_events`,
`get_logs`, `get_pod_logs`). The **list-returning** tools (`list_pods`, `list_namespaces`,
`list_nodes`, `list_deployments`, `list_services`, `list_resource`, `list_api_resources`) deliver
their JSON only via the **text content block** (`structured_content` is None) — because they declare
no return-type annotation, so FastMCP builds no output schema, and a bare JSON array is not a valid
top-level structured-content object. The data is valid JSON every MCP client can read, so the tools
are fully functional, but the earlier "FastMCP emits structured content + schemas" framing is only
half-true for list tools. A naive `-> list[dict]` annotation would BREAK the error path (every tool
also returns `{"error": ...}`, a dict, on failure), so a real fix needs a union/wrapper type and is
outside the locked "no refactor" scope.
RESOLUTION (researched the AWS EKS MCP server, the read-only surface we mirror): its `list_k8s_resources`
/ `manage_k8s_resource` are typed `-> CallToolResult` and built by hand —
`CallToolResult(isError=False, content=[TextContent(summary), TextContent(json.dumps(data.model_dump()))])`
on success and `CallToolResult(isError=True, content=[TextContent(error_msg)])` on error. So the EKS
reference ALSO delivers list data as JSON in a text content block and emits NO `structured_content`;
it unifies success/error via the native `isError` flag rather than an error dict. Our list tools'
JSON-in-text-content is therefore the same observable behavior as the reference. User decision:
**accept as-is**; corrected the overstated "emits structured content + schemas" wording in this
Decisions section and in `CLAUDE.md`. (An EKS-style richer envelope — `{kind,count,items}` + Pydantic
models + `CallToolResult`/`isError` — would be a separate, out-of-scope future phase.)
Commit: a5210c9

---

## Session handoff (for a fresh context)

- Repo: `/Users/vg/experiments/k8s-mcp-server/kubernetes-readonly-mcp`; work branch `modernize-mcp-server`.
- This `PLAN.md` is the committed source of truth. `CLAUDE.md` is gitignored (local-only); read it
  first if present, then this file. Resume at the first phase whose checkboxes are unticked.
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
