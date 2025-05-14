from mcp.server.fastmcp import FastMCP
from kubernetes import client, config
import json
from typing import Optional, List, Any

# Create an MCP server for readonly kubectl commands against K8s cluster
mcp = FastMCP("kubernetes-readonly-mcp")

# Kubernetes Manager Resource class
class KubernetesManager:
    """Resource that manages Kubernetes API client connections"""
    
    def __init__(self):
        """Initialize the Kubernetes client once"""
        try:
            # Try to load from kubeconfig
            config.load_kube_config()
        except Exception:
            # Fall back to in-cluster config if running in a pod
            try:
                config.load_incluster_config()
            except Exception as e:
                print(f"Failed to load Kubernetes configuration: {e}")
                raise
        
        # Initialize API clients
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.batch_api = client.BatchV1Api()
        self.networking_api = client.NetworkingV1Api()
        
    def get_core_api(self):
        """Get the CoreV1Api client"""
        return self.core_api
    
    def get_apps_api(self):
        """Get the AppsV1Api client"""
        return self.apps_api
    
    def get_batch_api(self):
        """Get the BatchV1Api client"""
        return self.batch_api
    
    def get_networking_api(self):
        """Get the NetworkingV1Api client"""
        return self.networking_api

# Initialize the Kubernetes manager as a resource
@mcp.resource('resource://k8s')
def k8s_manager():
    """Resource that provides access to Kubernetes APIs"""
    print("Initializing Kubernetes API client...")
    try:
        return KubernetesManager()
    except Exception as e:
        print(f"Error initializing Kubernetes manager: {e}")
        # Return a placeholder that will be replaced in the tool functions
        return "k8s_manager_initialization_failed"

@mcp.tool(description="List all pods in a namespace or across all namespaces")
def list_pods(namespace: Optional[str] = None, resource: Any = None):
    """
    List all pods in a specified namespace or across all namespaces if none is specified.
    
    Args:
        namespace (str, optional): The Kubernetes namespace to list pods from.
                                  If not provided, pods from all namespaces will be listed.
    
    Returns:
        JSON string containing pod information including name, namespace, pod_ip, 
        status, and labels.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        # Check if resource is a string and initialize KubernetesManager if needed
        if isinstance(resource, str):
            print(f"Resource is a string: {resource}, initializing KubernetesManager")
            resource = KubernetesManager()
        elif not hasattr(resource, 'get_core_api'):
            print(f"Resource is not a KubernetesManager instance: {type(resource)}, initializing KubernetesManager")
            resource = KubernetesManager()
            
        # Get pods based on namespace parameter
        if namespace:
            print(f"Listing pods in namespace: {namespace}")
            ret = resource.get_core_api().list_namespaced_pod(namespace=namespace, watch=False)
        else:
            print("Listing pods across all namespaces")
            ret = resource.get_core_api().list_pod_for_all_namespaces(watch=False)
        
        # Convert the response to a JSON format
        pods = []
        for i in ret.items:
            pods.append({
                "name": i.metadata.name,
                "namespace": i.metadata.namespace,
                "ip": i.status.pod_ip,
                "status": i.status.phase,
                "labels": i.metadata.labels,
                "creation_timestamp": i.metadata.creation_timestamp.isoformat() if i.metadata.creation_timestamp else None,
                "node": i.spec.node_name,
                "containers": [container.name for container in i.spec.containers]
            })
        return json.dumps(pods)
    except Exception as e:
        print(f"Error in list_pods: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool(description="List all deployments in a specified namespace")
def list_deployments(namespace: Optional[str] = None, resource: Any = None):
    """
    List all deployments in a specified namespace or across all namespaces if none is specified.
    
    Args:
        namespace (str, optional): The Kubernetes namespace to list deployments from.
                                  If not provided, deployments from all namespaces will be listed.
    
    Returns:
        JSON string containing deployment information including name, namespace, replicas, 
        available replicas, and labels.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        # Get deployments based on namespace parameter
        if namespace:
            print(f"Listing deployments in namespace: {namespace}")
            ret = resource.get_apps_api().list_namespaced_deployment(namespace=namespace, watch=False)
        else:
            print("Listing deployments across all namespaces")
            ret = resource.get_apps_api().list_deployment_for_all_namespaces(watch=False)
        
        # Convert the response to a JSON format
        deployments = []
        for item in ret.items:
            deployments.append({
                "name": item.metadata.name,
                "namespace": item.metadata.namespace,
                "replicas": item.spec.replicas,
                "available_replicas": item.status.available_replicas,
                "labels": item.metadata.labels,
                "creation_timestamp": item.metadata.creation_timestamp.isoformat() if item.metadata.creation_timestamp else None,
                "selector": item.spec.selector.match_labels if item.spec.selector else None
            })
        
        return json.dumps(deployments)
    except Exception as e:
        print(f"Error in list_deployments: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool(description="Get logs from a pod in a specified namespace")
def get_pod_logs(namespace: str, pod_name: str, container: Optional[str] = None, 
                 tail_lines: Optional[int] = None, previous: bool = False, resource: Any = None):
    """
    Get logs from a pod in a specified namespace.
    
    Args:
        namespace (str): The Kubernetes namespace where the pod is located.
        pod_name (str): The name of the pod to get logs from.
        container (str, optional): The container name within the pod. If not specified and 
                                  the pod has multiple containers, logs from the first container will be returned.
        tail_lines (int, optional): Number of lines to show from the end of the logs. If not specified, 
                                   all logs will be returned.
        previous (bool, optional): If true, return logs from a previous instantiation of the container.
                                  Default is False.
    
    Returns:
        JSON string containing the pod logs and metadata.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        # Get pod information to check if it exists and get container names
        pod_info = resource.get_core_api().read_namespaced_pod(name=pod_name, namespace=namespace)
        container_names = [container.name for container in pod_info.spec.containers]
        
        # If container is not specified and there are multiple containers, use the first one
        if not container and len(container_names) > 1:
            container = container_names[0]
            print(f"Multiple containers found in pod. Using the first container: {container}")
        elif not container and len(container_names) == 1:
            container = container_names[0]
        
        # Get logs from the specified pod and container
        logs = resource.get_core_api().read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
            previous=previous
        )
        
        # Prepare the response
        response = {
            "pod_name": pod_name,
            "namespace": namespace,
            "container": container,
            "logs": logs.split('\n'),
            "container_names": container_names,
            "status": pod_info.status.phase
        }
        
        return json.dumps(response)
    
    except client.exceptions.ApiException as e:
        print(f"API Exception in get_pod_logs: {e}")
        if e.status == 404:
            return json.dumps({"error": f"Pod {pod_name} not found in namespace {namespace}"})
        else:
            return json.dumps({"error": f"Error retrieving logs: {str(e)}"})
    except Exception as e:
        print(f"Error in get_pod_logs: {e}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@mcp.tool(description="List all services in a namespace or across all namespaces")
def list_services(namespace: Optional[str] = None, resource: Any = None):
    """
    List all services in a specified namespace or across all namespaces if none is specified.
    
    Args:
        namespace (str, optional): The Kubernetes namespace to list services from.
                                  If not provided, services from all namespaces will be listed.
    
    Returns:
        JSON string containing service information including name, namespace, type, cluster IP,
        external IP, ports, and selectors.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        # Get services based on namespace parameter
        if namespace:
            print(f"Listing services in namespace: {namespace}")
            ret = resource.get_core_api().list_namespaced_service(namespace=namespace, watch=False)
        else:
            print("Listing services across all namespaces")
            ret = resource.get_core_api().list_service_for_all_namespaces(watch=False)
        
        # Convert the response to a JSON format
        services = []
        for item in ret.items:
            ports = []
            if item.spec.ports:
                for port in item.spec.ports:
                    port_info = {
                        "name": port.name,
                        "port": port.port,
                        "target_port": port.target_port,
                        "protocol": port.protocol
                    }
                    if port.node_port:
                        port_info["node_port"] = port.node_port
                    ports.append(port_info)
            
            external_ips = item.spec.external_i_ps if hasattr(item.spec, 'external_i_ps') else None
            
            services.append({
                "name": item.metadata.name,
                "namespace": item.metadata.namespace,
                "type": item.spec.type,
                "cluster_ip": item.spec.cluster_ip,
                "external_ips": external_ips,
                "ports": ports,
                "selector": item.spec.selector,
                "creation_timestamp": item.metadata.creation_timestamp.isoformat() if item.metadata.creation_timestamp else None
            })
        
        return json.dumps(services)
    except Exception as e:
        print(f"Error in list_services: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool(description="List all namespaces in the cluster")
def list_namespaces(resource: Any = None):
    """
    List all namespaces in the Kubernetes cluster.
    
    Returns:
        JSON string containing namespace information including name, status, and creation timestamp.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        print("Listing all namespaces")
        ret = resource.get_core_api().list_namespace(watch=False)
        
        namespaces = []
        for item in ret.items:
            namespaces.append({
                "name": item.metadata.name,
                "status": item.status.phase,
                "creation_timestamp": item.metadata.creation_timestamp.isoformat() if item.metadata.creation_timestamp else None
            })
        
        return json.dumps(namespaces)
    except Exception as e:
        print(f"Error in list_namespaces: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool(description="Get Kubernetes events from the cluster for a specific namespace or all namespaces")
def get_events(namespace: Optional[str] = None, field_selector: Optional[str] = None, 
               resource: Any = None):
    """
    Get Kubernetes events from the cluster for a specific namespace or all namespaces.
    
    Args:
        namespace (str, optional): The Kubernetes namespace to get events from.
                                  If not provided, events from all namespaces will be returned.
        field_selector (str, optional): Selector to restrict the list of returned events by field.
                                       For example 'involvedObject.name=my-pod'.
    
    Returns:
        JSON string containing event information including type, reason, message, and involved object.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        if namespace:
            print(f"Getting events from namespace: {namespace}")
            events = resource.get_core_api().list_namespaced_event(namespace=namespace, field_selector=field_selector)
        else:
            print("Getting events from all namespaces")
            events = resource.get_core_api().list_event_for_all_namespaces(field_selector=field_selector)
        
        event_list = []
        for event in events.items:
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count,
                "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
                "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
                "involved_object": {
                    "kind": event.involved_object.kind,
                    "name": event.involved_object.name,
                    "namespace": event.involved_object.namespace,
                },
                "source": {
                    "component": event.source.component if event.source else None,
                    "host": event.source.host if event.source else None
                }
            })
        
        return json.dumps({
            "namespace": namespace,
            "field_selector": field_selector,
            "events": event_list
        })
    except Exception as e:
        print(f"Error in get_events: {e}")
        return json.dumps({"error": f"Error retrieving events: {str(e)}"})

@mcp.tool(description="Get logs from pods, deployments, jobs, or resources matching a label selector")
def get_logs(resource_type: str, namespace: Optional[str] = None, name: Optional[str] = None, 
             label_selector: Optional[str] = None, container: Optional[str] = None, 
             tail: Optional[int] = None, since_seconds: Optional[int] = None,
             timestamps: bool = False, pretty: bool = False, resource: Any = None):
    """
    Get logs from pods, deployments, jobs, or resources matching a label selector.
    
    Args:
        resource_type (str): Type of resource to get logs from ('pod', 'deployment', 'job', etc.)
        namespace (str, optional): The Kubernetes namespace. If not provided and name is specified, 
                                  uses the 'default' namespace. If neither name nor namespace is 
                                  provided, searches across all namespaces.
        name (str, optional): The name of the specific resource to get logs from.
        label_selector (str, optional): Label selector to filter resources (e.g. 'app=nginx').
                                       Required if name is not provided.
        container (str, optional): The container name within the pod. If not specified and 
                                  the pod has multiple containers, logs from the first container will be returned.
        tail (int, optional): Number of lines to show from the end of the logs.
        since_seconds (int, optional): Return logs newer than a relative duration in seconds.
        timestamps (bool, optional): Include timestamps at the beginning of each line. Default is False.
        pretty (bool, optional): Format the output in a more readable way. Default is False.
    
    Returns:
        JSON string containing the logs and metadata.
    """
    try:
        # Get the resource from the k8s_manager if not provided
        if resource is None:
            resource = k8s_manager()
            
        # Validate input parameters
        if not name and not label_selector:
            return json.dumps({"error": "Either name or label_selector must be provided"})
        
        # Set default namespace if name is provided but namespace is not
        if name and not namespace:
            namespace = "default"
        
        # Get pods based on the resource type and filters
        pods_to_get_logs_from = []
        
        if resource_type.lower() == 'pod' and name:
            # Direct pod access by name
            try:
                pod = resource.get_core_api().read_namespaced_pod(name=name, namespace=namespace)
                pods_to_get_logs_from.append(pod)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    return json.dumps({"error": f"Pod {name} not found in namespace {namespace}"})
                raise
        
        elif resource_type.lower() == 'deployment' and name:
            # Get pods from a deployment
            try:
                deployment = resource.get_apps_api().read_namespaced_deployment(name=name, namespace=namespace)
                selector = deployment.spec.selector.match_labels
                label_selector = ','.join([f"{k}={v}" for k, v in selector.items()])
                
                pods = resource.get_core_api().list_namespaced_pod(
                    namespace=namespace, 
                    label_selector=label_selector
                )
                pods_to_get_logs_from.extend(pods.items)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    return json.dumps({"error": f"Deployment {name} not found in namespace {namespace}"})
                raise
        
        elif resource_type.lower() == 'job' and name:
            # Get pods from a job
            try:
                job = resource.get_batch_api().read_namespaced_job(name=name, namespace=namespace)
                selector = job.spec.selector.match_labels
                label_selector = ','.join([f"{k}={v}" for k, v in selector.items()])
                
                pods = resource.get_core_api().list_namespaced_pod(
                    namespace=namespace, 
                    label_selector=label_selector
                )
                pods_to_get_logs_from.extend(pods.items)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    return json.dumps({"error": f"Job {name} not found in namespace {namespace}"})
                raise
        
        elif label_selector:
            # Get pods by label selector
            if namespace:
                pods = resource.get_core_api().list_namespaced_pod(
                    namespace=namespace, 
                    label_selector=label_selector
                )
            else:
                pods = resource.get_core_api().list_pod_for_all_namespaces(
                    label_selector=label_selector
                )
            pods_to_get_logs_from.extend(pods.items)
        
        else:
            return json.dumps({"error": f"Unsupported resource type: {resource_type} or missing required parameters"})
        
        # If no pods found
        if not pods_to_get_logs_from:
            return json.dumps({"error": "No pods found matching the specified criteria"})
        
        # Get logs from all matching pods
        results = []
        for pod in pods_to_get_logs_from:
            pod_name = pod.metadata.name
            pod_namespace = pod.metadata.namespace
            container_names = [c.name for c in pod.spec.containers]
            
            # If container is not specified and there are multiple containers, use the first one
            container_to_use = container
            if not container_to_use and len(container_names) > 1:
                container_to_use = container_names[0]
            elif not container_to_use and len(container_names) == 1:
                container_to_use = container_names[0]
            
            try:
                # Get logs from the pod
                logs = resource.get_core_api().read_namespaced_pod_log(
                    name=pod_name,
                    namespace=pod_namespace,
                    container=container_to_use,
                    tail_lines=tail,
                    timestamps=timestamps,
                    since_seconds=since_seconds
                )
                
                # Format logs based on pretty parameter
                log_lines = logs.split('\n')
                
                # Add pod result to results list
                results.append({
                    "pod_name": pod_name,
                    "namespace": pod_namespace,
                    "container": container_to_use,
                    "logs": log_lines,
                    "container_names": container_names,
                    "status": pod.status.phase
                })
            except Exception as e:
                print(f"Error getting logs for pod {pod_name}: {e}")
                results.append({
                    "pod_name": pod_name,
                    "namespace": pod_namespace,
                    "error": str(e)
                })
        
        return json.dumps({
            "resource_type": resource_type,
            "name": name,
            "namespace": namespace,
            "label_selector": label_selector,
            "results": results
        }, indent=2 if pretty else None)
    
    except Exception as e:
        print(f"Error in get_logs: {e}")
        return json.dumps({"error": f"Error retrieving logs: {str(e)}"})

def main():
    """Entry point for the MCP server when run as a script."""
    mcp.run()  # Default: uses STDIO transport

if __name__ == "__main__":
    main()
