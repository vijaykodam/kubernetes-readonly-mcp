"""Tests for the Kubernetes Read-Only MCP Server."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kubernetes_readonly_mcp.server import (
    KubernetesManager,
    _sanitize,
    list_namespaces,
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
