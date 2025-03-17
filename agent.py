from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yaml
from kubernetes import client, config
from typing import Any, Dict
import subprocess

# Initialize FastAPI
app = FastAPI()


class OTELConfiguration(BaseModel):
    namespace: Any
    configmap_name: Any
    receivers: Dict[str, Any]
    processors: Dict[str, Any]
    exporters: Dict[str, Any]
    service: Dict[str, Any]

# Load Kubernetes configuration
def load_kubernetes_config():
    try:
        # Load in-cluster configuration when running inside the cluster
        config.load_incluster_config()
    except config.ConfigException:
        # Load kubeconfig for external execution
        config.load_kube_config()


# Update receiver structure
def __update_configmap(new_configmap: dict, configmap: dict): 
    for key, value in new_configmap.items():
        if key in configmap and isinstance(value, dict):
            # Check level matches
            __update_configmap(value, configmap[key])
        else:
            configmap[key] = value
        
# Delete keys from the configmap 
def __remove_configmap(keys_to_remove: dict, configmap: dict):
    for key, value in keys_to_remove.items():
        if key in configmap and  key != 'pipelines':
            del configmap[key]
        elif  isinstance(value, dict):
            __remove_configmap(value, configmap[key])
            
def __load_test_configmap():
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
        print(configmap_yaml.data)
        configmap      = yaml.safe_load(configmap_yaml.data['collector.yaml'])
    except Exception as e:
        if configmap_name is None:
            print("No Kubeconfig, entering DEBUG mode")
            configmap = yaml.safe_load(__load_test_configmap()['data']['collector.yaml'])
            print(f"TESTING: {configmap}")
        else:
            raise Exception(status_code=500, detail=f"Fail to load Kubeconfig: {e}")

    # Extract pipeline details
    receiver    = new_pipeline['receivers']  if 'receivers' in new_pipeline else None
    processor   = new_pipeline['processors'] if 'processors' in new_pipeline else None 
    exporter    = new_pipeline['exporters']  if 'exporters' in new_pipeline else None 
    service     = new_pipeline['service']    if 'service' in new_pipeline else None
    
    updates_new_configmaps = [receiver, processor, exporter, service]
    
    for new_configmap in updates_new_configmaps:
        __update_configmap(new_configmap, configmap['receivers'])
    if configmap_name is not None:
        try:
            v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
            return configmap
        except Exception as e:
            raise Exception(status_code=500, detail=f"Fail to replace configmap: {e}")
    else:
        return configmap
        
        
        
        
def add_configmap(namespace: str, configmap_name: str, new_configmap: dict):
    try:
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        # Retrieve the current ConfigMap
        configmap_yaml = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap      = yaml.safe_load(configmap_yaml.data['collector.yaml'])
    except Exception as e:
        if configmap_name is None:
            print("No Kubeconfig, entering DEBUG mode")
            configmap = yaml.safe_load(__load_test_configmap()['data']['collector.yaml'])
            print(f"TESTING: {configmap}")
            configmap = new_configmap
            return configmap
        else:
            raise Exception(status_code=500, detail=f"Fail to load Kubeconfig: {e}")

    try:
        v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
    except Exception as e:
        raise Exception(status_code=500, detail=f"Fail to replace configmap: {e}")

        
        
def remove_configmap(namespace: str, configmap_name: str, remove_pipeline: dict):
    try:
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        # Retrieve the current ConfigMap
        configmap_yaml = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap      = yaml.safe_load(configmap_yaml.data['collector.yaml'])
    except Exception as e:
        if configmap_name is None:
            print("No Kubeconfig, entering DEBUG mode")
            configmap = yaml.safe_load(__load_test_configmap()['data']['collector.yaml'])
            print(f"TESTING: {configmap}")
        else:
            raise Exception(status_code=500, detail=f"Fail to load Kubeconfig: {e}")

    # Extract pipeline details
    receiver    = remove_pipeline['receivers']  if 'receivers' in remove_pipeline else dict()
    processor   = remove_pipeline['processors'] if 'processors' in remove_pipeline else dict()
    exporter    = remove_pipeline['exporters']  if 'exporters' in remove_pipeline else dict() 
    service     = remove_pipeline['service']    if 'service' in remove_pipeline else dict()
    
    update_remove_configmaps = [(receiver, 'receivers'), (processor, 'processors'), (exporter, 'exporters'), (service, 'service')]
    for new_configmap in update_remove_configmaps:
        __remove_configmap(new_configmap[0], configmap[new_configmap[1]])


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
# def delete_pipeline_from_configmap(namespace: str, configmap_name: str, pipeline_data: dict):
#     load_kubernetes_config()
#     v1 = client.CoreV1Api()

#     # Retrieve the current ConfigMap
#     configmap = v1.read_namespaced_config_map(configmap_name, namespace)
#     configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])

#     # Extract pipeline details
#     domainID = pipeline_data["domainID"]
#     flavorID = pipeline_data["flavorID"]

#     # Construct names for the filter, exporter, and pipeline
#     filter_name = f"filter/basicmetrics{domainID}{flavorID}"
#     exporter_name = f"prometheusremotewrite/{domainID}"
#     pipeline_name = f"metrics/{domainID}{flavorID}"

#     # Remove the pipeline, exporter, and filter if they exist
#     if pipeline_name in configmap_yaml["service"]["pipelines"]:
#         del configmap_yaml["service"]["pipelines"][pipeline_name]
#     else:
#         raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

#     if exporter_name in configmap_yaml["exporters"]:
#         del configmap_yaml["exporters"][exporter_name]

#     if filter_name in configmap_yaml["processors"]:
#         del configmap_yaml["processors"][filter_name]
    
#     # Delete "key": "source" and "value": "opentelemetry" (action)
#     configmap_yaml["processors"]["attributes/metrics"]["actions"] = [
#         action for action in configmap_yaml["processors"]["attributes/metrics"]["actions"]
#         if not (action.get("key") == "source" and action.get("value") == "opentelemetry")
#     ]


#     # Convert the updated dictionary back to YAML
#     updated_yaml = yaml.safe_dump(configmap_yaml)
#     configmap.data['collector.yaml'] = updated_yaml

#     # Apply the updated ConfigMap
#     v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
#     print(f"Pipeline '{pipeline_name}' successfully deleted from ConfigMap '{configmap_name}'.")


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
@app.put("/configurations")
def update_pipeline(request: OTELConfiguration):
    try:
        data = request.model_dump()
        namespace = data['namespace'] if 'namespace' in data else None
        configmap_name = data['configmap_name'] if 'configmap_name' in data  else None

        # Update the ConfigMap with the new pipeline
        new_configmap = update_configmap(namespace, configmap_name, request.model_dump())

        return {"message": "Pipeline created and ConfigMap successfully updated", "configmap": new_configmap}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/configurations")
def add_pipeline(request: OTELConfiguration):
    try:
        data = request.model_dump()
        namespace = data['namespace'] if 'namespace' in data else None
        configmap_name = data['configmap_name'] if 'configmap_name' in data  else None

        # Update the ConfigMap with the new pipeline
        new_configmap = add_configmap(namespace, configmap_name, request.model_dump())

        return {"message": "Pipeline created and ConfigMap successfully updated", "configmap": new_configmap}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.delete("/configurations")
def remove_pipeline(request: OTELConfiguration):
    try:
        data = request.model_dump()
        namespace = data['namespace'] if 'namespace' in data else None
        configmap_name = data['configmap_name'] if 'configmap_name' in data  else None

        # Update the ConfigMap with the new pipeline
        remove_configmap(namespace, configmap_name, request.model_dump())

        return {"message": "Pipeline deleted and ConfigMap successfully updated."}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/configurations")
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
    

    
# # Endpoint to create a new pipeline
# @app.post("/addpipeline/transfermetrics")
# def add_pipeline(request: PipelineRequest):
#     try:
#         namespace = "monitoring"
#         configmap_name = "collector-config"

#         # Update the ConfigMap with the new pipeline
#         update_configmap(namespace, configmap_name, request.dict())

#         return {"message": "Pipeline created and ConfigMap successfully updated."}
#     except Exception as e:
#         print(f"Error updating ConfigMap: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to delete a pipeline
# @app.delete("/deletepipeline/transfermetrics")
# def delete_pipeline(request: PipelineRequest):
#     try:
#         namespace = "monitoring"
#         configmap_name = "collector-config"

#         # Delete the pipeline from the ConfigMap
#         delete_pipeline_from_configmap(namespace, configmap_name, request.dict())

#         return {"message": "Pipeline successfully deleted from ConfigMap"}
#     except Exception as e:
#         print(f"Error deleting pipeline from ConfigMap: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to list all pipelines in the ConfigMap
# @app.get("/listpipelines")
# def list_pipelines():
#     try:
#         namespace = "monitoring"
#         configmap_name = "collector-config"
        
#         # Load Kubernetes config
#         load_kubernetes_config()
#         v1 = client.CoreV1Api()
        
#         # Retrieve the current ConfigMap
#         configmap = v1.read_namespaced_config_map(configmap_name, namespace)
#         configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])
        
#         # Extract the pipelines
#         pipelines = configmap_yaml.get("service", {}).get("pipelines", {})
        
#         return {"pipelines": list(pipelines.keys())}
#     except Exception as e:
#         print(f"Error listing pipelines: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
    

# # Endpoint to update an existing pipeline
# @app.put("/updatepipeline")
# def update_pipeline(request: UpdatePipelineRequest):
#     try:
#         namespace = "monitoring"
#         configmap_name = "collector-config"

#         # Load Kubernetes config
#         load_kubernetes_config()
#         v1 = client.CoreV1Api()

#         # Retrieve the current ConfigMap
#         configmap = v1.read_namespaced_config_map(configmap_name, namespace)
#         configmap_yaml = yaml.safe_load(configmap.data['collector.yaml'])

#         # Identify the pipeline and related components
#         domainID = request.domainID
#         flavorID = request.flavorID
#         pipeline_name = f"metrics/{domainID}{flavorID}"
#         exporter_name = f"prometheusremotewrite/{domainID}"
#         filter_name = f"filter/basicmetrics{domainID}{flavorID}"

#         # Ensure the pipeline exists
#         if pipeline_name not in configmap_yaml.get("service", {}).get("pipelines", {}):
#             raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

#         # Update the exporter if specified
#         if request.newExporter:
#             configmap_yaml["exporters"][exporter_name] = {"endpoint": request.newExporter}

#         # Update the processors if specified
#         if request.newProcessors:
#             configmap_yaml["processors"][filter_name] = request.newProcessors

#         # Auxiliary action: add an attribute to verify update_pipeline
#         configmap_yaml["processors"]["attributes/metrics"]["actions"].append({
#             "action": "insert",
#             "key": "update",
#             "value": "pipeline"
#         })

#         # Convert the updated dictionary back to YAML
#         updated_yaml = yaml.safe_dump(configmap_yaml)
#         configmap.data['collector.yaml'] = updated_yaml

#         # Apply the updated ConfigMap
#         v1.replace_namespaced_config_map(configmap_name, namespace, configmap)

#         return {"message": f"Pipeline '{pipeline_name}' updated successfully."}
#     except Exception as e:
#         print(f"Error updating pipeline: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to reload the OpenTelemetry Collector configuration
@app.post("/reload")
def reload_config(request: OTELConfiguration):
    try:
        namespace = request.model_dump()['namespace']
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
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)
    # new_pipeline = {'receivers': {'hostmetrics': {'collection_interval': '1s'}, 'kubeletstats': {'collection_interval': '1'} }, 'service': {'pipelines': {'metrics/fluidosmonitoring': {} }}}
    # remove_configmap(None, None, new_pipeline)