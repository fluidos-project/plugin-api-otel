import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent import app

client = TestClient(app)

reload_payload = {
    "namespace": "monitoring",
    "label_selector": "app.kubernetes.io/name=opentelemetrycollector"
}


def test_reload_success():
    """
    Simulates that the pod is found and the command is executed successfully.
    """
    with patch("agent.find_pod_by_label", return_value="otel-pod-123"), \
         patch("agent.send_signal_to_pod", return_value={"message": "Signal HUP sent to pod 'otel-pod-123'."}):

        response = client.post("/reload", json=reload_payload)
        assert response.status_code == 200
        assert "Signal HUP sent" in response.json()["message"]


def test_reload_pod_not_found():
    """
    Simulates that the pod is not found.
    """
    with patch("agent.find_pod_by_label", return_value=None):
        response = client.post("/reload", json=reload_payload)
        assert response.status_code == 500
        assert "OpenTelemetry pod not found" in response.json()["detail"]


def test_reload_command_failure():
    """
    Simulates that the pod is found but kubectl fails.
    """
    with patch("agent.find_pod_by_label", return_value="otel-pod-123"), \
         patch("agent.send_signal_to_pod", side_effect=Exception("Command failed")):

        response = client.post("/reload", json=reload_payload)
        assert response.status_code == 500
        assert "Command failed" in response.json()["detail"]
