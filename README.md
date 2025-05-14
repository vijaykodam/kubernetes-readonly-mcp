# Kubernetes Read Only MCP Server

A Model Context Protocol (MCP) server for safely interacting with Kubernetes clusters using read-only operations.

This MCP server was created to provide a secure way to interact with Kubernetes clusters without allowing any create, update, or delete operations. It only exposes read-only APIs to ensure your clusters remain safe while still enabling AI assistants to help you monitor and troubleshoot your Kubernetes resources.

Built with FastMCP 2.0 and the official Kubernetes Python client library.

## Blog Post and Demo Video

Read more about running the MCP server using Amazon Q CLI at https://vijay.eu/posts/building-my-first-mcp-server/

## Features

This MCP server provides the following read-only tools:

- `list_pods`: List all pods in a namespace or across all namespaces
- `list_deployments`: List all deployments in a specified namespace
- `list_services`: List all services in a namespace or across all namespaces
- `list_namespaces`: List all namespaces in the cluster
- `get_events`: Get Kubernetes events from the cluster
- `get_pod_logs`: Get logs from a specific pod
- `get_logs`: Get logs from pods, deployments, jobs, or resources matching a label selector

## Prerequisites

- Kubernetes cluster creation and configuring your kubectl must be done before starting the installation. Default K8s context will be used.
- For demo purposes, you can use kind and docker to setup a local k8s cluster running quickly in your local machine.
- Refer to this quickstart: https://kind.sigs.k8s.io/docs/user/quick-start/

## Installation

### MCP configuration

Add this to your MCP Server configuration file:

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

Every MCP Hosts/Clients manages their MCP Server configuration differently.
If you are using it for the first time then most probably mcp configuration file might not be present. 
You might have to create it and paste the above JSON text into it.

Here is related documentation for Claude Desktop and Amazon Q CLI:

1. Claude Desktop: https://modelcontextprotocol.io/quickstart/user
2. Amazon Q CLI: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html

### Verify Installation

Verify that your MCP Host/Client is restarted and the kubernetes-readonly-mcp MCP server is visible in the list.

You can use Amazon Q CLI, Claude Desktop, VSCode + Cline, or any other MCP-compatible client.

## Example Prompts

1. "Get list of pods from my kubernetes cluster"
2. "Are there any failing pods? Debug why they are failing"
3. "Show me the logs from the nginx deployment"
4. "List all services in the default namespace"

## License

Apache License 2.0

## Disclaimer

This is an experimental project and not production-ready. Use it at your own discretion.
