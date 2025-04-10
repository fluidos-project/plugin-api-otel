import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent import app
import json

client = TestClient(app)

@pytest.fixture
def base_payload():
    return {
        "namespace": None,
        "configmap_name": None,
        "receivers": {
            "hostmetrics": {
                "collection_interval": "1s"
            },
            "kubeletstats": {
                "collection_interval": "1"
            }
        },
        "processors": {
            "batch": {}
        },
        "exporters": {
            "prometheus": {
                "endpoint": "0.0.0.0:8889"
            }
        },
        "service": {
            "pipelines": {
                "metrics/fluidosmonitoring": {
                    "receivers": ["hostmetrics", "kubeletstats"],
                    "processors": ["batch"],
                    "exporters": ["prometheus"]
                }
            }
        }
    }

@pytest.fixture
def partial_payload():
    return {
        "namespace": None,
        "configmap_name": None,
        "receivers": {
            "hostmetrics": {
                "collection_interval": "5s"
            }
        },
        "exporters": {
            "prometheus": {
                "endpoint": "0.0.0.0:8889"
            }
        }
    }

@pytest.fixture
def empty_payload():
    return {
        "namespace": None,
        "configmap_name": None,
        "receivers": {},
        "processors": {},
        "exporters": {},
        "service": {}
    }


# PUT
def test_put_update_pipeline(base_payload):
    """
    Test PUT to /configurations to update an existing ConfigMap structure (DEBUG mode).
    """
    response = client.put("/configurations", json=base_payload)
    assert response.status_code == 200
    assert "Pipeline created and ConfigMap successfully updated" in response.json()["message"]


def test_put_partial_payload(partial_payload):
    """
    Test PUT with partial payload (only receivers and exporters).
    """

    response = client.put("/configurations", json=partial_payload)
    assert response.status_code == 422


def test_put_with_empty_fields(empty_payload):
    """
    Test PUT with all valid keys but empty structures.
    """

    response = client.put("/configurations", json=empty_payload)
    assert response.status_code == 200
    assert "Pipeline created and ConfigMap successfully updated" in response.json()["message"]


# POST
def test_post_add_pipeline(base_payload):
    """
    Test POST to /configurations to replace ConfigMap content (DEBUG mode).
    """
    response = client.post("/configurations", json=base_payload)
    assert response.status_code == 200
    assert "Pipeline created and ConfigMap successfully updated" in response.json()["message"]


def test_post_partial_payload(partial_payload):
    """
    Test POST with partial payload (only receivers and exporters).
    """

    response = client.post("/configurations", json=partial_payload)
    assert response.status_code == 422


def test_post_with_empty_fields(empty_payload):
    """
    Test POST with all valid keys but empty structures.
    """

    response = client.post("/configurations", json=empty_payload)
    assert response.status_code == 200
    assert "Pipeline created and ConfigMap successfully updated" in response.json()["message"]


# DELETE
def test_delete_pipeline():
    """
    Test DELETE to /configurations to remove specific processors (DEBUG mode).
    """
    delete_payload = {
        "namespace": None,
        "configmap_name": None,
        "receivers": {},
        "processors": {
            "filter/privacy": {
                "metrics": {
                    "exclude": {
                        "match_type": "regexp",
                        "metric_names": [
                            "node_disk_info"
                        ]
                    }
                }
            }
        },
        "exporters": {},
        "service": {}
    }

    response = client.request(
        method="DELETE",
        url="/configurations",
        headers={"Content-Type": "application/json"},
        content=json.dumps(delete_payload)
    )
    assert response.status_code == 200
    assert "Pipeline deleted and ConfigMap successfully updated" in response.json()["message"]

def test_delete_partial_payload(partial_payload):
    """
    Test DELETE with partial payload (only receivers and exporters).
    """

    response = client.request("DELETE", "/configurations", json=partial_payload)
    assert response.status_code == 422


def test_delete_with_empty_fields(empty_payload):
    """
    Test DELETE with all valid keys but empty structures.
    """

    response = client.request("DELETE", "/configurations", json=empty_payload)
    assert response.status_code == 200
    assert "Pipeline deleted and ConfigMap successfully updated" in response.json()["message"]