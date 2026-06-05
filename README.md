# Kubernetes Read Only MCP Server

A Model Context Protocol (MCP) server for safely interacting with Kubernetes clusters using read-only operations.

This MCP server was created to provide a secure way to interact with Kubernetes clusters without allowing any create, update, or delete operations. It only exposes read-only APIs to ensure your clusters remain safe while still enabling AI assistants to help you monitor and troubleshoot your Kubernetes resources.

Built with [FastMCP 3.x](https://gofastmcp.com/) (the standalone `fastmcp` framework) and the official Kubernetes Python client library. Secret values are never exposed: for any `Secret`, only its metadata and `type` are returned, never `data` or `stringData`.

## Blog post and Demo

Watch the demo and read the write-up at https://vijay.eu/posts/building-my-first-mcp-server/

## Features

This MCP server provides the following read-only tools. Every tool is annotated read-only (`readOnlyHint=True`, `destructiveHint=False`) and returns native structured data.

### Curated tools

- `list_pods`: List all pods in a namespace or across all namespaces
- `list_deployments`: List all deployments in a specified namespace
- `list_services`: List all services in a namespace or across all namespaces
- `list_namespaces`: List all namespaces in the cluster
- `get_events`: Get Kubernetes events from the cluster
- `get_pod_logs`: Get logs from a specific pod
- `get_logs`: Get logs from pods, deployments, jobs, or resources matching a label selector
- `list_nodes`: List all nodes in the cluster and their status

### Generic tools (any kind, including CRDs)

These use the Kubernetes dynamic client, so they work for built-in kinds and Custom Resources alike. They are GET/LIST only and never mutate the cluster.

- `list_resource`: List resources of any `kind` (e.g. `Ingress`, `ConfigMap`, a CRD), optionally scoped by `api_version`, `namespace`, `label_selector`, and `field_selector`.
- `get_resource`: Get a single resource of any `kind` by `name` (with optional `api_version` and `namespace`).
- `list_api_resources`: Discover which resource kinds the cluster exposes and can be listed (returns `group_version`, `kind`, `namespaced`, and `verbs`), so you know what to pass to the tools above.

> Secret safety: even `list_resource`/`get_resource` with `kind="Secret"` return only metadata and `type` — the `data` and `stringData` fields are always stripped before output.

## Prerequisites

- Python 3.10 or higher.
- `uv` is installed (it provides `uvx`). If not, install it with `pip install uv` (or `pipx install uv`).
- Kubernetes cluster up and running.
- Kubeconfig configured with a default context.
- For demo purposes, you can use kind and Docker to set up a local Kubernetes cluster quickly on your machine. Refer to this quickstart: https://kind.sigs.k8s.io/docs/user/quick-start/

## General MCP Host Configuration

Different MCP Hosts (AI assistants or CLIs that support MCP) manage their MCP server configurations in different ways. Generally, you tell your MCP Host how to start the `kubernetes-readonly-mcp` server. This involves:

- The command to run the server. For `kubernetes-readonly-mcp` this is `uvx kubernetes-readonly-mcp@latest`, which uses `uvx` to download and run the package from PyPI.
- Any necessary arguments.
- A working directory, if the host requires one.

`uvx` handles downloading and running `kubernetes-readonly-mcp` on first invocation; no separate install step is needed. The server communicates over STDIO.

Host-specific, copy-paste configuration follows below. You can find more information about the Model Context Protocol at:

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- Example Host Documentation:
    1. Claude Code: [MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
    2. Codex CLI: [MCP](https://github.com/openai/codex)
    3. Kiro CLI: [MCP Configuration](https://kiro.dev/docs/mcp/)
    4. Antigravity: MCP Servers (configured via the in-app "Manage MCP Servers" view)
    5. Claude Desktop: [User Quickstart](https://modelcontextprotocol.io/quickstart/user)

## Host Setup

### 1. Claude Code

Add the server with the CLI (the `--` separates Claude Code's own flags from the command to run; STDIO is the default transport):

```bash
claude mcp add kubernetes-readonly-mcp -- uvx kubernetes-readonly-mcp@latest
```

To share the server with a project (committed to the repo), create a `.mcp.json` at the project root:

```json
{
  "mcpServers": {
    "kubernetes-readonly-mcp": {
      "command": "uvx",
      "args": ["kubernetes-readonly-mcp@latest"]
    }
  }
}
```

### 2. Codex CLI

Codex CLI reads MCP servers from `~/.codex/config.toml`. Add a table:

```toml
[mcp_servers.kubernetes-readonly-mcp]
command = "uvx"
args = ["kubernetes-readonly-mcp@latest"]
```

You can also manage servers with the `codex mcp` subcommands. The Codex CLI and IDE extension share this configuration.

### 3. Kiro CLI

Kiro CLI is the successor to the now-deprecated Amazon Q CLI. Configure servers in `~/.kiro/settings/mcp.json` (user scope) or `<project>/.kiro/settings/mcp.json` (project scope):

```json
{
  "mcpServers": {
    "kubernetes-readonly-mcp": {
      "command": "uvx",
      "args": ["kubernetes-readonly-mcp@latest"],
      "disabled": false
    }
  }
}
```

If you previously used Amazon Q, migrate your old `~/.aws/amazonq/mcp.json` entries to `~/.kiro/settings/mcp.json`.

### 4. Antigravity (Google)

Antigravity reads MCP servers from `~/.gemini/antigravity/mcp_config.json` (on Windows, `C:\Users\<USER>\.gemini\antigravity\mcp_config.json`):

```json
{
  "mcpServers": {
    "kubernetes-readonly-mcp": {
      "command": "uvx",
      "args": ["kubernetes-readonly-mcp@latest"]
    }
  }
}
```

You can open this file from the app: the "..." menu -> MCP Servers -> Manage MCP Servers -> View raw config.

### 5. Claude Desktop

Edit `claude_desktop_config.json` (on macOS, `~/Library/Application Support/Claude/claude_desktop_config.json`; on Windows, `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kubernetes-readonly-mcp": {
      "command": "uvx",
      "args": ["kubernetes-readonly-mcp@latest"]
    }
  }
}
```

Restart Claude Desktop after editing so it picks up the new server.

## Verifying the setup

`kubernetes-readonly-mcp` is a STDIO MCP server: running it starts a process that speaks the MCP protocol over standard input/output and waits for an MCP host to connect. It does not take a tool name as a command-line argument.

To confirm `uvx` can fetch and launch the package, run:

```bash
uvx kubernetes-readonly-mcp@latest
```

The process will start and wait silently for an MCP client (press Ctrl+C to stop). It will not print a namespace list — tools are invoked by an MCP host, not from the shell. Beyond that, verification depends on your MCP host: after configuration, the server and its tools should appear in the host's interface, where you can invoke them.

## Example Prompts

1. "Get list of pods from my kubernetes cluster"
2. "Are there any failing pods? Debug why they are failing"
3. "Show me the logs from the nginx deployment"
4. "List all services in the default namespace"
5. "List all ingresses across every namespace" (uses the generic `list_resource` tool with `kind="Ingress"`, `api_version="networking.k8s.io/v1"`)

## License

Apache License 2.0

## Disclaimer

This is an experimental project and not production-ready. Use it at your own discretion.
