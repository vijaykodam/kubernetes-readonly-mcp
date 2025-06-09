# Kubernetes Read Only MCP Server

A Model Context Protocol (MCP) server for safely interacting with Kubernetes clusters using read-only operations.

This MCP server was created to provide a secure way to interact with Kubernetes clusters without allowing any create, update, or delete operations. It only exposes read-only APIs to ensure your clusters remain safe while still enabling AI assistants to help you monitor and troubleshoot your Kubernetes resources.

Built with FastMCP 2.0 and the official Kubernetes Python client library.

## Blog post and Demo

Watch the demo running the MCP server using Amazon Q CLI at https://vijay.eu/posts/building-my-first-mcp-server/

## Features

This MCP server provides the following read-only tools:

- `list_pods`: List all pods in a namespace or across all namespaces
- `list_deployments`: List all deployments in a specified namespace
- `list_services`: List all services in a namespace or across all namespaces
- `list_namespaces`: List all namespaces in the cluster
- `get_events`: Get Kubernetes events from the cluster
- `get_pod_logs`: Get logs from a specific pod
- `get_logs`: Get logs from pods, deployments, jobs, or resources matching a label selector
- `list_nodes`: List all nodes in the cluster and their status

## Prerequisites

- Python 3.10 or higher needed.
- uv is installed. If not, install it using `pip install uv`
- Kubernetes cluster up and running.
- Kubeconfig configured with default context.
- For demo purposes, you can use kind and docker to setup a local k8s cluster running quickly in your local machine. Refer to this quickstart: https://kind.sigs.k8s.io/docs/user/quick-start/

## General MCP Host Configuration

Different MCP Hosts (like various AI assistants or CLIs that support MCP) manage their MCP Server configurations in unique ways. Generally, you'll need to inform your MCP Host how to start the `kubernetes-readonly-mcp` server.

This typically involves:
- Specifying the command to run the server. For `kubernetes-readonly-mcp`, this is often `uvx kubernetes-readonly-mcp@latest`, which uses `uvx` to download and run the package from PyPI.
- Providing any necessary arguments.
- Setting a working directory if required.

Please consult the documentation for your specific MCP Host on how to add and configure new MCP servers. For a detailed example of configuring an MCP server, see the "Amazon Q CLI Setup" section below, which shows how to set up this server with Amazon Q.

You can find more information about the Model Context Protocol and how different clients might implement it at:
- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- Example Host Documentation:
    1. Claude Desktop: [User Quickstart](https://modelcontextprotocol.io/quickstart/user)
    2. Amazon Q CLI: [MCP Configuration](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html)

Verification of the setup will also depend on your MCP Host. Typically, after configuration, the MCP server and its tools should become available within the host's interface.

## Amazon Q CLI Setup

This section guides you through setting up the `kubernetes-readonly-mcp` server with the Amazon Q CLI.

### 1. Install Amazon Q CLI

If you haven't already, install the Amazon Q CLI. Please follow the official installation instructions provided in the [Amazon Q Developer Guide](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html).

### 2. Configure MCP Server for Amazon Q CLI

You need to tell Amazon Q CLI how to run the `kubernetes-readonly-mcp` server. Create or update your MCP configuration file at `~/.aws/amazonq/mcp.json`.

Add the following entry to the `mcpServers` object:
```json
{
  "mcpServers": {
    "kubernetes-readonly-mcp": {
      "command": "uvx",
      "args": ["kubernetes-readonly-mcp@latest"],
      "workingDirectory": "~/",
      "userDocs": {
        "overview": "Provides read-only access to Kubernetes cluster information. Allows listing of pods, deployments, services, namespaces, nodes, and fetching logs."
      }
    }
    // Add other MCP servers here if you have them
  }
}
```
If the file or `mcpServers` object already exists, merge this configuration. Ensure the JSON is valid.

### 3. Install/Update `kubernetes-readonly-mcp`

The MCP configuration above uses `uvx` to run the `kubernetes-readonly-mcp`. `uvx` will automatically download and run the latest version of the package from PyPI if it's not already available in its cache or if a newer version is published.

To ensure you have `uv` (which provides `uvx`), install it if you haven't already:
```bash
pip install uv
```
Or, for isolated installation:
```bash
pipx install uv
```

`uvx` will handle the installation of `kubernetes-readonly-mcp` when it's first invoked by the Amazon Q CLI.

### 4. Verify MCP Server with `uvx`

Before using it with Amazon Q CLI, you can directly test if `uvx` can run the MCP server. This helps confirm that `uv` is installed correctly and the package can be fetched.

Open your terminal and run:
```bash
uvx kubernetes-readonly-mcp@latest list_namespaces
```
This command attempts to run the `list_namespaces` tool from the `kubernetes-readonly-mcp` server.
If successful, you should see a JSON output listing the namespaces in your default Kubernetes context (or an empty list if no namespaces are found, or an error if a K8s cluster is not configured). This indicates that `uvx` can execute the MCP server.

If you encounter issues, ensure your Kubernetes `kubeconfig` is correctly set up and `uv` is in your PATH.

After these steps, restart your Amazon Q CLI (if it was already running) for it to pick up the new MCP server configuration. You should then be able to invoke tools from `kubernetes-readonly-mcp` via Amazon Q.

## Example Prompts

1. "Get list of pods from my kubernetes cluster"
2. "Are there any failing pods? Debug why they are failing"
3. "Show me the logs from the nginx deployment"
4. "List all services in the default namespace"

## License

Apache License 2.0

## Disclaimer

This is an experimental project and not production-ready. Use it at your own discretion.
