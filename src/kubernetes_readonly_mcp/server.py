"""Read-only Kubernetes MCP server.

Exposes GET/LIST-only tools so AI assistants can inspect and troubleshoot
clusters with no risk of mutation. Every tool is annotated read-only and
returns native Python objects (FastMCP emits structured content + schemas).
"""

from typing import Optional

from fastmcp import FastMCP
from kubernetes import client, config, dynamic
from mcp.types import ToolAnnotations

# Create an MCP server for read-only operations against a Kubernetes cluster.
mcp = FastMCP("kubernetes-readonly-mcp")


def _ro(title: str) -> ToolAnnotations:
    """Build the read-only annotation set shared by every tool."""
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )


class KubernetesManager:
    """Manages Kubernetes API client connections (read-only use)."""

    def __init__(self):
        """Initialize the Kubernetes clients once."""
        try:
            # Try to load from kubeconfig.
            config.load_kube_config()
        except Exception:
            # Fall back to in-cluster config if running in a pod.
            config.load_incluster_config()

        # Initialize the typed API clients used by the curated tools.
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.batch_api = client.BatchV1Api()
        self.networking_api = client.NetworkingV1Api()
        # Dynamic client powers the generic read-any-kind tools (incl. CRDs).
        self.dynamic_api = dynamic.DynamicClient(client.ApiClient())

    def get_core_api(self):
        """Get the CoreV1Api client."""
        return self.core_api

    def get_apps_api(self):
        """Get the AppsV1Api client."""
        return self.apps_api

    def get_batch_api(self):
        """Get the BatchV1Api client."""
        return self.batch_api

    def get_networking_api(self):
        """Get the NetworkingV1Api client."""
        return self.networking_api

    def get_dynamic_api(self):
        """Get the dynamic client."""
        return self.dynamic_api


# Lazy module-level singleton: the synchronous kubernetes client is created
# once on first tool use, not at import time.
_manager = None


def _get_manager() -> "KubernetesManager":
    """Return the shared KubernetesManager, creating it on first use."""
    global _manager
    if _manager is None:
        _manager = KubernetesManager()
    return _manager


def _sanitize(obj_dict, kind):
    """Strip noisy/sensitive fields from a resource dict.

    - Always drops ``metadata.managedFields`` (large, low value).
    - For ``Secret`` kinds, removes ``data`` and ``stringData`` so secret
      values are never returned; only metadata and ``type`` remain.

    This is the single chokepoint enforcing Secret redaction, so it cannot be
    bypassed (e.g. via a generic ``get_resource(kind="Secret")`` call).
    """
    if not isinstance(obj_dict, dict):
        return obj_dict
    metadata = obj_dict.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("managedFields", None)
    if kind == "Secret":
        obj_dict.pop("data", None)
        obj_dict.pop("stringData", None)
    return obj_dict


@mcp.tool(
    description="List all pods in a namespace or across all namespaces",
    annotations=_ro("List Pods"),
)
def list_pods(namespace: Optional[str] = None):
    """
    List all pods in a specified namespace or across all namespaces if none is specified.

    Args:
        namespace (str, optional): The Kubernetes namespace to list pods from.
                                  If not provided, pods from all namespaces will be listed.

    Returns:
        A list of pod dicts including name, namespace, ip, status, labels, node, and containers.
    """
    try:
        core = _get_manager().get_core_api()
        if namespace:
            ret = core.list_namespaced_pod(namespace=namespace, watch=False)
        else:
            ret = core.list_pod_for_all_namespaces(watch=False)

        pods = []
        for i in ret.items:
            pods.append(
                {
                    "name": i.metadata.name,
                    "namespace": i.metadata.namespace,
                    "ip": i.status.pod_ip,
                    "status": i.status.phase,
                    "labels": i.metadata.labels,
                    "creation_timestamp": (
                        i.metadata.creation_timestamp.isoformat()
                        if i.metadata.creation_timestamp
                        else None
                    ),
                    "node": i.spec.node_name,
                    "containers": [container.name for container in i.spec.containers],
                }
            )
        return pods
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(
    description="List all deployments in a specified namespace",
    annotations=_ro("List Deployments"),
)
def list_deployments(namespace: Optional[str] = None):
    """
    List all deployments in a specified namespace or across all namespaces if none is specified.

    Args:
        namespace (str, optional): The Kubernetes namespace to list deployments from.
                                  If not provided, deployments from all namespaces will be listed.

    Returns:
        A list of deployment dicts including name, namespace, replicas, available_replicas,
        labels, and selector.
    """
    try:
        apps = _get_manager().get_apps_api()
        if namespace:
            ret = apps.list_namespaced_deployment(namespace=namespace, watch=False)
        else:
            ret = apps.list_deployment_for_all_namespaces(watch=False)

        deployments = []
        for item in ret.items:
            deployments.append(
                {
                    "name": item.metadata.name,
                    "namespace": item.metadata.namespace,
                    "replicas": item.spec.replicas,
                    "available_replicas": item.status.available_replicas,
                    "labels": item.metadata.labels,
                    "creation_timestamp": (
                        item.metadata.creation_timestamp.isoformat()
                        if item.metadata.creation_timestamp
                        else None
                    ),
                    "selector": (item.spec.selector.match_labels if item.spec.selector else None),
                }
            )
        return deployments
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(
    description="Get logs from a pod in a specified namespace",
    annotations=_ro("Get Pod Logs"),
)
def get_pod_logs(
    namespace: str,
    pod_name: str,
    container: Optional[str] = None,
    tail_lines: Optional[int] = None,
    previous: bool = False,
):
    """
    Get logs from a pod in a specified namespace.

    Args:
        namespace (str): The Kubernetes namespace where the pod is located.
        pod_name (str): The name of the pod to get logs from.
        container (str, optional): The container name within the pod. If not specified and
                                  the pod has multiple containers, logs from the first
                                  container will be returned.
        tail_lines (int, optional): Number of lines to show from the end of the logs.
                                   If not specified, all logs will be returned.
        previous (bool, optional): If true, return logs from a previous instantiation of the
                                  container. Default is False.

    Returns:
        A dict containing the pod logs and metadata.
    """
    try:
        core = _get_manager().get_core_api()

        # Get pod information to check if it exists and get container names.
        pod_info = core.read_namespaced_pod(name=pod_name, namespace=namespace)
        container_names = [container.name for container in pod_info.spec.containers]

        # If container is not specified, default to the first container.
        if not container and container_names:
            container = container_names[0]

        logs = core.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
            previous=previous,
        )

        return {
            "pod_name": pod_name,
            "namespace": namespace,
            "container": container,
            "logs": logs.split("\n"),
            "container_names": container_names,
            "status": pod_info.status.phase,
        }

    except client.exceptions.ApiException as e:
        if e.status == 404:
            return {"error": f"Pod {pod_name} not found in namespace {namespace}"}
        return {"error": f"Error retrieving logs: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


@mcp.tool(
    description="List all services in a namespace or across all namespaces",
    annotations=_ro("List Services"),
)
def list_services(namespace: Optional[str] = None):
    """
    List all services in a specified namespace or across all namespaces if none is specified.

    Args:
        namespace (str, optional): The Kubernetes namespace to list services from.
                                  If not provided, services from all namespaces will be listed.

    Returns:
        A list of service dicts including name, namespace, type, cluster_ip, external_ips,
        ports, and selector.
    """
    try:
        core = _get_manager().get_core_api()
        if namespace:
            ret = core.list_namespaced_service(namespace=namespace, watch=False)
        else:
            ret = core.list_service_for_all_namespaces(watch=False)

        services = []
        for item in ret.items:
            ports = []
            if item.spec.ports:
                for port in item.spec.ports:
                    port_info = {
                        "name": port.name,
                        "port": port.port,
                        "target_port": port.target_port,
                        "protocol": port.protocol,
                    }
                    if port.node_port:
                        port_info["node_port"] = port.node_port
                    ports.append(port_info)

            external_ips = item.spec.external_i_ps if hasattr(item.spec, "external_i_ps") else None

            services.append(
                {
                    "name": item.metadata.name,
                    "namespace": item.metadata.namespace,
                    "type": item.spec.type,
                    "cluster_ip": item.spec.cluster_ip,
                    "external_ips": external_ips,
                    "ports": ports,
                    "selector": item.spec.selector,
                    "creation_timestamp": (
                        item.metadata.creation_timestamp.isoformat()
                        if item.metadata.creation_timestamp
                        else None
                    ),
                }
            )
        return services
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(
    description="List all namespaces in the cluster",
    annotations=_ro("List Namespaces"),
)
def list_namespaces():
    """
    List all namespaces in the Kubernetes cluster.

    Returns:
        A list of namespace dicts including name, status, and creation_timestamp.
    """
    try:
        ret = _get_manager().get_core_api().list_namespace(watch=False)

        namespaces = []
        for item in ret.items:
            namespaces.append(
                {
                    "name": item.metadata.name,
                    "status": item.status.phase,
                    "creation_timestamp": (
                        item.metadata.creation_timestamp.isoformat()
                        if item.metadata.creation_timestamp
                        else None
                    ),
                }
            )
        return namespaces
    except Exception as e:
        return {"error": str(e)}


@mcp.tool(
    description="Get Kubernetes events from the cluster for a specific namespace or all namespaces",
    annotations=_ro("Get Events"),
)
def get_events(namespace: Optional[str] = None, field_selector: Optional[str] = None):
    """
    Get Kubernetes events from the cluster for a specific namespace or all namespaces.

    Args:
        namespace (str, optional): The Kubernetes namespace to get events from.
                                  If not provided, events from all namespaces will be returned.
        field_selector (str, optional): Selector to restrict the list of returned events by field.
                                       For example 'involvedObject.name=my-pod'.

    Returns:
        A dict containing the requested namespace, field_selector, and a list of events.
    """
    try:
        core = _get_manager().get_core_api()
        if namespace:
            events = core.list_namespaced_event(namespace=namespace, field_selector=field_selector)
        else:
            events = core.list_event_for_all_namespaces(field_selector=field_selector)

        event_list = []
        for event in events.items:
            event_list.append(
                {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "count": event.count,
                    "first_timestamp": (
                        event.first_timestamp.isoformat() if event.first_timestamp else None
                    ),
                    "last_timestamp": (
                        event.last_timestamp.isoformat() if event.last_timestamp else None
                    ),
                    "involved_object": {
                        "kind": event.involved_object.kind,
                        "name": event.involved_object.name,
                        "namespace": event.involved_object.namespace,
                    },
                    "source": {
                        "component": event.source.component if event.source else None,
                        "host": event.source.host if event.source else None,
                    },
                }
            )

        return {
            "namespace": namespace,
            "field_selector": field_selector,
            "events": event_list,
        }
    except Exception as e:
        return {"error": f"Error retrieving events: {str(e)}"}


@mcp.tool(
    description="Get logs from pods, deployments, jobs, or resources matching a label selector",
    annotations=_ro("Get Logs"),
)
def get_logs(
    resource_type: str,
    namespace: Optional[str] = None,
    name: Optional[str] = None,
    label_selector: Optional[str] = None,
    container: Optional[str] = None,
    tail: Optional[int] = None,
    since_seconds: Optional[int] = None,
    timestamps: bool = False,
):
    """
    Get logs from pods, deployments, jobs, or resources matching a label selector.

    Args:
        resource_type (str): Type of resource to get logs from ('pod', 'deployment', 'job', etc.)
        namespace (str, optional): The Kubernetes namespace. If not provided and name is
                                  specified, uses the 'default' namespace. If neither name nor
                                  namespace is provided, searches across all namespaces.
        name (str, optional): The name of the specific resource to get logs from.
        label_selector (str, optional): Label selector to filter resources (e.g. 'app=nginx').
                                       Required if name is not provided.
        container (str, optional): The container name within the pod. If not specified and
                                  the pod has multiple containers, logs from the first
                                  container will be returned.
        tail (int, optional): Number of lines to show from the end of the logs.
        since_seconds (int, optional): Return logs newer than a relative duration in seconds.
        timestamps (bool, optional): Include timestamps at the beginning of each line.
                                  Default is False.

    Returns:
        A dict containing the logs and metadata.
    """
    try:
        manager = _get_manager()
        core = manager.get_core_api()

        # Validate input parameters.
        if not name and not label_selector:
            return {"error": "Either name or label_selector must be provided"}

        # Set default namespace if name is provided but namespace is not.
        if name and not namespace:
            namespace = "default"

        # Resolve the set of pods to read logs from.
        pods_to_get_logs_from = []

        if resource_type.lower() == "pod" and name:
            # Direct pod access by name.
            try:
                pod = core.read_namespaced_pod(name=name, namespace=namespace)
                pods_to_get_logs_from.append(pod)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    return {"error": f"Pod {name} not found in namespace {namespace}"}
                raise

        elif resource_type.lower() == "deployment" and name:
            # Get pods from a deployment.
            try:
                deployment = manager.get_apps_api().read_namespaced_deployment(
                    name=name, namespace=namespace
                )
                selector = deployment.spec.selector.match_labels
                label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])

                pods = core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
                pods_to_get_logs_from.extend(pods.items)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    return {"error": f"Deployment {name} not found in namespace {namespace}"}
                raise

        elif resource_type.lower() == "job" and name:
            # Get pods from a job.
            try:
                job = manager.get_batch_api().read_namespaced_job(name=name, namespace=namespace)
                selector = job.spec.selector.match_labels
                label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])

                pods = core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
                pods_to_get_logs_from.extend(pods.items)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    return {"error": f"Job {name} not found in namespace {namespace}"}
                raise

        elif label_selector:
            # Get pods by label selector.
            if namespace:
                pods = core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
            else:
                pods = core.list_pod_for_all_namespaces(label_selector=label_selector)
            pods_to_get_logs_from.extend(pods.items)

        else:
            return {
                "error": (
                    f"Unsupported resource type: {resource_type} or missing required parameters"
                )
            }

        # If no pods found.
        if not pods_to_get_logs_from:
            return {"error": "No pods found matching the specified criteria"}

        # Get logs from all matching pods.
        results = []
        for pod in pods_to_get_logs_from:
            pod_name = pod.metadata.name
            pod_namespace = pod.metadata.namespace
            container_names = [c.name for c in pod.spec.containers]

            # If container is not specified, default to the first container.
            container_to_use = container
            if not container_to_use and container_names:
                container_to_use = container_names[0]

            try:
                logs = core.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=pod_namespace,
                    container=container_to_use,
                    tail_lines=tail,
                    timestamps=timestamps,
                    since_seconds=since_seconds,
                )

                results.append(
                    {
                        "pod_name": pod_name,
                        "namespace": pod_namespace,
                        "container": container_to_use,
                        "logs": logs.split("\n"),
                        "container_names": container_names,
                        "status": pod.status.phase,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "pod_name": pod_name,
                        "namespace": pod_namespace,
                        "error": str(e),
                    }
                )

        return {
            "resource_type": resource_type,
            "name": name,
            "namespace": namespace,
            "label_selector": label_selector,
            "results": results,
        }

    except Exception as e:
        return {"error": f"Error retrieving logs: {str(e)}"}


@mcp.tool(
    description="List all nodes in the cluster",
    annotations=_ro("List Nodes"),
)
def list_nodes():
    """
    Lists all nodes in the Kubernetes cluster, providing detailed information for each.

    The information includes node name, current status (e.g., Ready, NotReady), assigned roles,
    IP addresses, resource capacity and allocatable resources, node info (kubelet version,
    OS image, container runtime), creation timestamp, labels, and taints.

    Returns:
        A list of node dicts with the details above, or a dict with an "error" key on failure.
    """
    try:
        ret = _get_manager().get_core_api().list_node(watch=False)

        nodes = []
        for item in ret.items:
            # Extract node status.
            status = None
            for condition in item.status.conditions:
                if condition.type == "Ready":
                    status = "Ready" if condition.status == "True" else "NotReady"
                    break

            # Extract node roles.
            roles = [role for role in item.metadata.labels if "node-role.kubernetes.io" in role]
            if not roles:
                roles = ["<none>"]  # Handle nodes with no specific role label.

            # Extract IP addresses.
            addresses = {address.type: address.address for address in item.status.addresses}

            node_info = item.status.node_info
            nodes.append(
                {
                    "name": item.metadata.name,
                    "status": status,
                    "roles": roles,
                    "addresses": addresses,
                    "capacity": {
                        "cpu": item.status.capacity.get("cpu"),
                        "memory": item.status.capacity.get("memory"),
                        "pods": item.status.capacity.get("pods"),
                    },
                    "allocatable": {
                        "cpu": item.status.allocatable.get("cpu"),
                        "memory": item.status.allocatable.get("memory"),
                        "pods": item.status.allocatable.get("pods"),
                    },
                    "node_info": {
                        "kubelet_version": node_info.kubelet_version,
                        "os_image": node_info.os_image,
                        "container_runtime_version": node_info.container_runtime_version,
                    },
                    "creation_timestamp": (
                        item.metadata.creation_timestamp.isoformat()
                        if item.metadata.creation_timestamp
                        else None
                    ),
                    "labels": item.metadata.labels,
                    "taints": (
                        [
                            {
                                "key": taint.key,
                                "value": taint.value,
                                "effect": taint.effect,
                            }
                            for taint in item.spec.taints
                        ]
                        if item.spec.taints
                        else []
                    ),
                }
            )

        return nodes
    except Exception as e:
        return {"error": str(e)}


def main():
    """Entry point for the MCP server when run as a script."""
    mcp.run()  # Default: uses STDIO transport.


if __name__ == "__main__":
    main()
