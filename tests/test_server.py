"""Tests for the Kubernetes Read-Only MCP Server."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kubernetes_readonly_mcp.server import (
    KubernetesManager,
    _sanitize,
    get_resource,
    list_api_resources,
    list_namespaces,
    list_resource,
)


@pytest.fixture
def mock_k8s_client():
    """Mock the kubernetes client, config, and dynamic modules used by the server."""
    with (
        patch("kubernetes_readonly_mcp.server.client") as mock_client,
        patch("kubernetes_readonly_mcp.server.config"),
        patch("kubernetes_readonly_mcp.server.dynamic") as mock_dynamic,
    ):
        yield mock_client, mock_dynamic


def test_kubernetes_manager_initialization(mock_k8s_client):
    """KubernetesManager wires up the typed clients plus the dynamic client."""
    mock_client, mock_dynamic = mock_k8s_client
    manager = KubernetesManager()

    mock_client.CoreV1Api.assert_called_once()
    mock_client.AppsV1Api.assert_called_once()
    mock_client.BatchV1Api.assert_called_once()
    mock_client.NetworkingV1Api.assert_called_once()

    # The dynamic client is created once and exposed via its accessor.
    mock_dynamic.DynamicClient.assert_called_once()
    assert manager.get_dynamic_api() is mock_dynamic.DynamicClient.return_value


def test_list_namespaces_returns_native_objects():
    """Tools return native Python objects (not JSON strings) for structured output."""
    ns = MagicMock()
    ns.metadata.name = "default"
    ns.status.phase = "Active"
    ns.metadata.creation_timestamp = datetime(2026, 5, 22)

    fake_manager = MagicMock()
    fake_manager.get_core_api().list_namespace.return_value.items = [ns]

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        result = list_namespaces()

    assert isinstance(result, list)
    assert result[0]["name"] == "default"
    assert result[0]["status"] == "Active"
    assert result[0]["creation_timestamp"] == "2026-05-22T00:00:00"


def test_list_namespaces_error_returns_dict():
    """Errors surface as a native {'error': ...} dict rather than a raised exception."""
    fake_manager = MagicMock()
    fake_manager.get_core_api().list_namespace.side_effect = RuntimeError("boom")

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        result = list_namespaces()

    assert result == {"error": "boom"}


def test_sanitize_redacts_secret_and_managed_fields():
    """_sanitize strips Secret data/stringData and always drops metadata.managedFields."""
    obj = {
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {"name": "s", "managedFields": [{"x": 1}]},
        "data": {"password": "c2VjcmV0"},
        "stringData": {"password": "secret"},
    }

    out = _sanitize(obj, "Secret")

    assert "data" not in out
    assert "stringData" not in out
    assert "managedFields" not in out["metadata"]
    # Non-sensitive fields are preserved.
    assert out["type"] == "Opaque"
    assert out["metadata"]["name"] == "s"


def _fake_manager_with_dynamic():
    """Build a fake manager whose dynamic client is itself a MagicMock.

    Returns (fake_manager, fake_resource) where fake_resource stands in for the
    discovered Resource (the object .get()/.search() are called on).
    """
    fake_resource = MagicMock()
    fake_manager = MagicMock()
    fake_manager.get_dynamic_api().resources.get.return_value = fake_resource
    return fake_manager, fake_resource


def test_list_resource_returns_sanitized_items():
    """list_resource returns native dicts via the dynamic client, sanitized."""
    item = MagicMock()
    item.to_dict.return_value = {
        "kind": "Ingress",
        "metadata": {"name": "web", "managedFields": [{"x": 1}]},
    }

    fake_manager, fake_resource = _fake_manager_with_dynamic()
    fake_resource.get.return_value.items = [item]

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        result = list_resource(kind="Ingress", api_version="networking.k8s.io/v1")

    # Discovery used the caller-supplied api_version + kind.
    fake_manager.get_dynamic_api().resources.get.assert_called_once_with(
        api_version="networking.k8s.io/v1", kind="Ingress"
    )
    assert isinstance(result, list)
    assert result[0]["metadata"]["name"] == "web"
    # managedFields always stripped by _sanitize.
    assert "managedFields" not in result[0]["metadata"]


def test_list_resource_redacts_secret_data():
    """Listing Secrets via the generic tool never returns data/stringData."""
    item = MagicMock()
    item.to_dict.return_value = {
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {"name": "s"},
        "data": {"password": "c2VjcmV0"},
        "stringData": {"password": "secret"},
    }

    fake_manager, fake_resource = _fake_manager_with_dynamic()
    fake_resource.get.return_value.items = [item]

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        result = list_resource(kind="Secret")

    assert "data" not in result[0]
    assert "stringData" not in result[0]
    assert result[0]["type"] == "Opaque"


def test_get_resource_redacts_secret_data():
    """get_resource(kind='Secret') returns metadata/type but never the values."""
    fake_manager, fake_resource = _fake_manager_with_dynamic()
    fake_resource.get.return_value.to_dict.return_value = {
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {"name": "db-creds", "managedFields": [{"x": 1}]},
        "data": {"password": "c2VjcmV0"},
        "stringData": {"password": "secret"},
    }

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        result = get_resource(kind="Secret", name="db-creds", namespace="kube-system")

    fake_resource.get.assert_called_once_with(name="db-creds", namespace="kube-system")
    assert "data" not in result
    assert "stringData" not in result
    assert "managedFields" not in result["metadata"]
    assert result["type"] == "Opaque"
    assert result["metadata"]["name"] == "db-creds"


def test_list_api_resources_filters_and_dedupes():
    """Only listable kinds are returned, deduplicated by (group_version, kind)."""
    pod = MagicMock(group_version="v1", kind="Pod", namespaced=True, verbs=["get", "list"])
    # Duplicate of Pod (discovery often yields repeats) should collapse to one.
    pod_dup = MagicMock(group_version="v1", kind="Pod", namespaced=True, verbs=["get", "list"])
    # Not listable -> excluded.
    binding = MagicMock(group_version="v1", kind="Binding", namespaced=True, verbs=["create"])
    # verbs=None must not raise.
    weird = MagicMock(group_version="v1", kind="Weird", namespaced=False, verbs=None)

    fake_manager = MagicMock()
    fake_manager.get_dynamic_api().resources.search.return_value = [pod, pod_dup, binding, weird]

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        result = list_api_resources()

    kinds = [r["kind"] for r in result]
    assert kinds == ["Pod"]
    assert result[0] == {
        "group_version": "v1",
        "kind": "Pod",
        "namespaced": True,
        "verbs": ["get", "list"],
    }


def test_generic_tools_errors_return_dict():
    """Dynamic-client failures surface as {'error': ...} rather than raising."""
    fake_manager = MagicMock()
    fake_manager.get_dynamic_api().resources.get.side_effect = RuntimeError("no api")

    with patch("kubernetes_readonly_mcp.server._get_manager", return_value=fake_manager):
        assert list_resource(kind="Bogus") == {"error": "no api"}
        assert get_resource(kind="Bogus", name="x") == {"error": "no api"}
