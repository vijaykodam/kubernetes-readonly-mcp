# Kubernetes Read-Only MCP Server

A Model Context Protocol (MCP) server for safely interacting with Kubernetes clusters using read-only operations.

This MCP server was created to provide a secure way to interact with Kubernetes clusters without allowing any create, update, or delete operations. It only exposes read-only APIs to ensure your clusters remain safe while still enabling AI assistants to help you monitor and troubleshoot your Kubernetes resources.

Built with FastMCP 2.0 and the official Kubernetes Python client library.

## Features

This MCP server provides the following read-only tools:

- `list_pods`: List all pods in a namespace or across all namespaces
- `list_deployments`: List all deployments in a specified namespace
- `list_services`: List all services in a namespace or across all namespaces
- `list_namespaces`: List all namespaces in the cluster
- `get_events`: Get Kubernetes events from the cluster
- `get_pod_logs`: Get logs from a specific pod
- `get_logs`: Get logs from pods, deployments, jobs, or resources matching a label selector

## Installation

### From PyPI

```bash
pip install kubernetes-readonly-mcp
```

### From Source

```bash
git clone https://github.com/vijaykodam/kubernetes-readonly-mcp.git
cd kubernetes-readonly-mcp
pip install -e .
```

## Usage

### Running as a standalone MCP server

```bash
kubernetes-readonly-mcp
```

### Adding to your MCP configuration

Add this to your `mcp.json`:

```json
{
  "mcpServers": {
    "kubernetes-readonly-mcp": {
        "command": "uvx",
        "args": ["-y", "kubernetes-readonly-mcp@latest"]
    }
  }
}
```

### Verify Installation

Verify that your MCP Host/Client is restarted and the kubernetes-readonly-mcp MCP server is visible in the list.

You can use Amazon Q CLI, Claude Desktop, VSCode + Cline, or any other MCP-compatible client.

## Example Prompts

1. "Get list of pods from my kubernetes cluster"
2. "Are there any failing pods? Debug why they are failing"
3. "Show me the logs from the nginx deployment"
4. "List all services in the default namespace"

## Development

To set up the development environment:

```bash
pip install -e ".[dev]"
```

## License

Apache License 2.0

## Disclaimer

This is an experimental project. Use it at your own risk. This is not production-ready.
