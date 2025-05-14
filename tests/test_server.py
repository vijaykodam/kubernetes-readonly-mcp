"""Tests for the Kubernetes Read-Only MCP Server."""

import pytest
from unittest.mock import MagicMock, patch

from kubernetes_readonly_mcp.server import KubernetesManager


@pytest.fixture
def mock_k8s_client():
    """Mock the Kubernetes client."""
    with patch("kubernetes_readonly_mcp.server.client") as mock_client:
        with patch("kubernetes_readonly_mcp.server.config") as mock_config:
            yield mock_client


def test_kubernetes_manager_initialization(mock_k8s_client):
    """Test that the KubernetesManager initializes correctly."""
    manager = KubernetesManager()
    # Verify that the config was loaded
    mock_k8s_client.CoreV1Api.assert_called_once()
    mock_k8s_client.AppsV1Api.assert_called_once()
    mock_k8s_client.BatchV1Api.assert_called_once()
    mock_k8s_client.NetworkingV1Api.assert_called_once()
