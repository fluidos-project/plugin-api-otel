# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Json
import yaml
# from kubernetes import client, config
from typing import Any
import subprocess

# Initialize FastAPI
app = FastAPI()


class OTELConfiguration(BaseModel):
    namespace: str
    receivers:  Json[Any]
    processors: Json[Any]
    exporters:  Json[Any]
    service:    Json[Any]




# Data model for the pipeline request
class PipelineRequest(BaseModel):
    prometheusExporter: str
    domainID: str
    flavorID: str

# Data model for updating an existing pipeline
class UpdatePipelineRequest(BaseModel):
    domainID: str
    flavorID: str
    newExporter: str = None
    newProcessors: dict = None


# Load Kubernetes configuration
def load_kubernetes_config():
    try:
        # Load in-cluster configuration when running inside the cluster
        config.load_incluster_config()
    except:
        # Load kubeconfig for external execution
        config.load_kube_config()


# Update receiver structure
def __update_receiver(receiver: dict, configmap: dict):
    if receiver:
        for r in receiver:
            # Check level matches
            if r in configmap:
                configmap = configmap[r]
                continue 
            else:
                configmap.extend(r)
    print(configmap)


def __update_processor(processor: dict, configmap: dict):
    if processor:
        for p in processor:
            # Check level matches
            if p in configmap:
                configmap = configmap[p]
                continue 
            else:
                configmap.extend(p)
    print(configmap)


def __load_test_configmap(configmapfile):
    with open("test/template.yaml") as file:
        try:
            return yaml.safe_load(file) 
        except yaml.YAMLError as exc:
            print(exc)

# Update the ConfigMap with the new pipeline configuration
def update_configmap(namespace: str, configmap_name: str, new_pipeline: dict):
    try:
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        # Retrieve the current ConfigMap
        configmap_yaml = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap      = yaml.safe_load(configmap_yaml.data['collector.yaml'])
    except:
        print("No Kubeconfig, entering DEBUG mode")
        configmap = __load_test_configmap(__load_test_configmap)
        print(f"TESTING: {configmap}")

    # Extract pipeline details
    receiver    = new_pipeline['receivers']
    processor   = new_pipeline['processors']
    exporter    = new_pipeline['exporters']
    service     = new_pipeline['service']

    __update_receiver(receiver, configmap['receiver'])



# Update the ConfigMap with the new pipeline configuration
# def update_configmap(namespace: str, configmap_name: str, new_data: dict):
#     load_kubernetes_config()
#     v1 = client.CoreV1Api()

#     # Retrieve the current ConfigMap
#     configmap = v1.read_namespaced_config_map(configmap_name, namespace)
#     configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])

#     # Extract pipeline details
#     domainID = new_data["domainID"]
#     flavorID = new_data["flavorID"]
#     exporter = new_data["prometheusExporter"]

#     # Define the new filter
#     filter_name = f"filter/basicmetrics{domainID}{flavorID}"
#     configmap_yaml["processors"][filter_name] = {
#         "error_mode": "ignore",
#         "metrics": {
#             "metric": [
#                 f'resource.attributes["k8s.node.name"] != "{flavorID}"'
#             ]
#         }
#     }

#     # Define the new exporter
#     exporter_name = f"prometheusremotewrite/{domainID}"
#     configmap_yaml["exporters"][exporter_name] = {
#         "endpoint": exporter
#     }

#     # Define the new pipeline
#     pipeline_name = f"metrics/{domainID}{flavorID}"
#     configmap_yaml["service"]["pipelines"][pipeline_name] = {
#         "receivers": ["kubeletstats", "prometheus", "otlp", "k8s_cluster", "hostmetrics"],
#         "processors": [filter_name, "attributes/metrics", "k8sattributes", "resource", "batch"],
#         "exporters": [exporter_name]
#     }

#     # Auxiliary action: add an attribute to verify updates
#     configmap_yaml["processors"]["attributes/metrics"]["actions"].append({
#         "action": "insert",
#         "key": "source",
#         "value": "opentelemetry"
#     })

#     # Convert the updated dictionary back to YAML
#     updated_yaml = yaml.safe_dump(configmap_yaml)
#     configmap.data['collector.yaml'] = updated_yaml

#     # Apply the updated ConfigMap
#     v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
#     print(f"ConfigMap '{configmap_name}' successfully updated.")


# Update the ConfigMap by removing a pipeline
def delete_pipeline_from_configmap(namespace: str, configmap_name: str, pipeline_data: dict):
    load_kubernetes_config()
    v1 = client.CoreV1Api()

    # Retrieve the current ConfigMap
    configmap = v1.read_namespaced_config_map(configmap_name, namespace)
    configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])

    # Extract pipeline details
    domainID = pipeline_data["domainID"]
    flavorID = pipeline_data["flavorID"]

    # Construct names for the filter, exporter, and pipeline
    filter_name = f"filter/basicmetrics{domainID}{flavorID}"
    exporter_name = f"prometheusremotewrite/{domainID}"
    pipeline_name = f"metrics/{domainID}{flavorID}"

    # Remove the pipeline, exporter, and filter if they exist
    if pipeline_name in configmap_yaml["service"]["pipelines"]:
        del configmap_yaml["service"]["pipelines"][pipeline_name]
    else:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    if exporter_name in configmap_yaml["exporters"]:
        del configmap_yaml["exporters"][exporter_name]

    if filter_name in configmap_yaml["processors"]:
        del configmap_yaml["processors"][filter_name]
    
    # Delete "key": "source" and "value": "opentelemetry" (action)
    configmap_yaml["processors"]["attributes/metrics"]["actions"] = [
        action for action in configmap_yaml["processors"]["attributes/metrics"]["actions"]
        if not (action.get("key") == "source" and action.get("value") == "opentelemetry")
    ]


    # Convert the updated dictionary back to YAML
    updated_yaml = yaml.safe_dump(configmap_yaml)
    configmap.data['collector.yaml'] = updated_yaml

    # Apply the updated ConfigMap
    v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
    print(f"Pipeline '{pipeline_name}' successfully deleted from ConfigMap '{configmap_name}'.")


# List all pods in a namespace
def list_pods(namespace):
    load_kubernetes_config()
    v1 = client.CoreV1Api()

    pods = v1.list_namespaced_pod(namespace)
    print(f"Found {len(pods.items)} pods in namespace '{namespace}'.")
    return [pod.metadata.name for pod in pods.items]


# Find a pod by its label
def find_pod_by_label(namespace, label_selector):
    load_kubernetes_config()
    v1 = client.CoreV1Api()

    pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)
    if pods.items:
        print(f"Pod found with label '{label_selector}': {pods.items[0].metadata.name}")
        return pods.items[0].metadata.name
    else:
        print(f"No pods found with label '{label_selector}' in namespace '{namespace}'.")
        return None
    

# Send a signal to a specific container in a pod using kubectl debug
def send_signal_to_pod(namespace, pod_name, signal="HUP"):
    load_kubernetes_config()
    command = [
        "kubectl", "debug", "-it", pod_name, "-n", namespace, 
        "--image=busybox", "--target=opentelemetrycollector", 
        "--", "/bin/sh", "-c", f"kill -{signal} 1"
    ]

    try:
        subprocess.run(command, check=True)
        print(f"Signal {signal} sent to container in pod '{pod_name}'.")
        return {"message": f"Signal {signal} sent to pod '{pod_name}'."}
    except subprocess.CalledProcessError as e:
        print(f"Error sending signal to pod: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
# Endpoints

# Endpoint to create a new pipeline
@app.post("/configuration")
def add_pipeline(request: PipelineRequest):
    try:
        namespace = "monitoring"
        configmap_name = "collector-config"

        # Update the ConfigMap with the new pipeline
        update_configmap(namespace, configmap_name, request.dict())

        return {"message": "Pipeline created and ConfigMap successfully updated."}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

    
# Endpoint to create a new pipeline
@app.post("/addpipeline/transfermetrics")
def add_pipeline(request: PipelineRequest):
    try:
        namespace = "monitoring"
        configmap_name = "collector-config"

        # Update the ConfigMap with the new pipeline
        update_configmap(namespace, configmap_name, request.dict())

        return {"message": "Pipeline created and ConfigMap successfully updated."}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to delete a pipeline
@app.delete("/deletepipeline/transfermetrics")
def delete_pipeline(request: PipelineRequest):
    try:
        namespace = "monitoring"
        configmap_name = "collector-config"

        # Delete the pipeline from the ConfigMap
        delete_pipeline_from_configmap(namespace, configmap_name, request.dict())

        return {"message": "Pipeline successfully deleted from ConfigMap"}
    except Exception as e:
        print(f"Error deleting pipeline from ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to list all pipelines in the ConfigMap
@app.get("/listpipelines")
def list_pipelines():
    try:
        namespace = "monitoring"
        configmap_name = "collector-config"
        
        # Load Kubernetes config
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        
        # Retrieve the current ConfigMap
        configmap = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])
        
        # Extract the pipelines
        pipelines = configmap_yaml.get("service", {}).get("pipelines", {})
        
        return {"pipelines": list(pipelines.keys())}
    except Exception as e:
        print(f"Error listing pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to update an existing pipeline
@app.put("/updatepipeline")
def update_pipeline(request: UpdatePipelineRequest):
    try:
        namespace = "monitoring"
        configmap_name = "collector-config"

        # Load Kubernetes config
        load_kubernetes_config()
        v1 = client.CoreV1Api()

        # Retrieve the current ConfigMap
        configmap = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])

        # Identify the pipeline and related components
        domainID = request.domainID
        flavorID = request.flavorID
        pipeline_name = f"metrics/{domainID}{flavorID}"
        exporter_name = f"prometheusremotewrite/{domainID}"
        filter_name = f"filter/basicmetrics{domainID}{flavorID}"

        # Ensure the pipeline exists
        if pipeline_name not in configmap_yaml.get("service", {}).get("pipelines", {}):
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

        # Update the exporter if specified
        if request.newExporter:
            configmap_yaml["exporters"][exporter_name] = {"endpoint": request.newExporter}

        # Update the processors if specified
        if request.newProcessors:
            configmap_yaml["processors"][filter_name] = request.newProcessors

        # Auxiliary action: add an attribute to verify update_pipeline
        configmap_yaml["processors"]["attributes/metrics"]["actions"].append({
            "action": "insert",
            "key": "update",
            "value": "pipeline"
        })

        # Convert the updated dictionary back to YAML
        updated_yaml = yaml.safe_dump(configmap_yaml)
        configmap.data['collector.yaml'] = updated_yaml

        # Apply the updated ConfigMap
        v1.replace_namespaced_config_map(configmap_name, namespace, configmap)

        return {"message": f"Pipeline '{pipeline_name}' updated successfully."}
    except Exception as e:
        print(f"Error updating pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to reload the OpenTelemetry Collector configuration
@app.post("/reload")
def reload_config():
    try:
        namespace = "monitoring"
        label_selector = "app.kubernetes.io/name=opentelemetrycollector"

        # Find the OpenTelemetry pod by its label
        pod_name = find_pod_by_label(namespace, label_selector)
        if not pod_name:
            raise HTTPException(status_code=404, detail="OpenTelemetry pod not found")

        # Send the SIGHUP signal to the container using kubectl debug
        return send_signal_to_pod(namespace, pod_name)

    except Exception as e:
        print(f"Error reloading configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    # import uvicorn
    # uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)
    new_pipeline = {'receivers': {'hostmetrics': {'testing': 1} }}
    update_configmap(None, None, new_pipeline)