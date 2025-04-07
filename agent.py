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
    
class OTELReload(BaseModel):
    namespace: Any
    label_selector: Any

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
    try:
        for key, value in new_configmap.items():
            if key in configmap and isinstance(value, dict):
                # Check level matches
                __update_configmap(value, configmap[key])
            else:
                configmap[key] = value
    except Exception as e:
        print(f"Error updating configmap: {e}")
        raise HTTPException(status_code=500, detail=f"Fail to update configmap: {e}")
            
# Delete keys from the configmap 
def __remove_configmap(keys_to_remove: dict, configmap: dict):
    try:
        for key, value in keys_to_remove.items():
            if key in configmap:
                if isinstance(value, dict) and isinstance(configmap[key], dict):
                    __remove_configmap(value, configmap[key])
                elif isinstance(value, list) and isinstance(configmap[key], list):
                    configmap[key] = [item for item in configmap[key] if item not in value]
                elif configmap[key] == value:
                    del configmap[key]
    except Exception as e:
        print(f"Error removing configmap: {e}")
        raise HTTPException(status_code=500, detail=f"Fail to remove configmap: {e}")

            
def __load_test_configmap():
    with open("test/template.yaml") as file:
        try:
            return yaml.safe_load(file) 
        except yaml.YAMLError as exc:
            print(exc)
            
def __clean_empty(d):
    """
    Clean empty values from a dictionary.
    """
    if not isinstance(d, dict):
        return d

    return {
        k: __clean_empty(v)
        for k, v in d.items()
        if v not in (None, {}, [], '') and not (isinstance(v, dict) and not __clean_empty(v))
    }


# Update the ConfigMap with the new pipeline configuration
def update_configmap(namespace: str, configmap_name: str, new_pipeline: dict):
    try:
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        # Retrieve the current ConfigMap
        configmap           = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap_yaml      = yaml.safe_load(configmap.data['collector.yaml'])
    except Exception as e:
        if configmap_name is None:
            print("No Kubeconfig, entering DEBUG mode")
            configmap_yaml = yaml.safe_load(__load_test_configmap()['data']['collector.yaml'])
            print(f"TESTING: {configmap_yaml}")
        else:
            raise HTTPException(status_code=500, detail=f"Fail to load Kubeconfig: {e}")

    # Extract pipeline details
    receiver    = new_pipeline['receivers']  if 'receivers' in new_pipeline else None
    processor   = new_pipeline['processors'] if 'processors' in new_pipeline else None 
    exporter    = new_pipeline['exporters']  if 'exporters' in new_pipeline else None 
    service     = new_pipeline['service']    if 'service' in new_pipeline else None
    
    updates_new_configmaps = [(receiver, 'receivers'), (processor, 'processors'), (exporter, 'exporters'), (service, 'service')]
    for new_configmap in updates_new_configmaps:
        __update_configmap(new_configmap[0], configmap_yaml[new_configmap[1]])
    if configmap_name is not None:
        try:
            updated_yaml = yaml.safe_dump(configmap_yaml)
            configmap.data['collector.yaml'] = updated_yaml
            v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
            return configmap
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fail to replace configmap: {e}")
    else:
        return configmap_yaml
        
        
        
        
def add_configmap(namespace: str, configmap_name: str, new_configmap: dict):
    try:
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        # Retrieve the current ConfigMap
        configmap           = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap_yaml      = yaml.safe_load(configmap.data['collector.yaml'])
    except Exception as e:
        if configmap_name is None:
            print("No Kubeconfig, entering DEBUG mode")
            configmap_yaml = yaml.safe_load(__load_test_configmap()['data']['collector.yaml'])
            print(f"TESTING: {configmap_yaml}")
            configmap_yaml = new_configmap
            return configmap_yaml
        else:
            raise HTTPException(status_code=500, detail=f"Fail to load Kubeconfig: {e}")

    if configmap_name is not None:
        try:
            updated_yaml = yaml.safe_dump(configmap_yaml)
            configmap.data['collector.yaml'] = updated_yaml
            v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
            return configmap
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fail to replace configmap: {e}")
    else:
        return configmap_yaml

        
        
def remove_configmap(namespace: str, configmap_name: str, remove_pipeline: dict):
    try:
        load_kubernetes_config()
        v1 = client.CoreV1Api()
        # Retrieve the current ConfigMap
        configmap           = v1.read_namespaced_config_map(configmap_name, namespace)
        configmap_yaml      = yaml.safe_load(configmap.data['collector.yaml'])
    except Exception as e:
        if configmap_name is None:
            print("No Kubeconfig, entering DEBUG mode")
            configmap_yaml = yaml.safe_load(__load_test_configmap()['data']['collector.yaml'])
            print(f"TESTING: {configmap_yaml}")
        else:
            raise HTTPException(status_code=500, detail=f"Fail to load Kubeconfig: {e}")

    # Extract pipeline details
    receiver    = remove_pipeline['receivers']  if 'receivers' in remove_pipeline else dict()
    processor   = remove_pipeline['processors'] if 'processors' in remove_pipeline else dict()
    exporter    = remove_pipeline['exporters']  if 'exporters' in remove_pipeline else dict() 
    service     = remove_pipeline['service']    if 'service' in remove_pipeline else dict()
    
    update_remove_configmaps = [(receiver, 'receivers'), (processor, 'processors'), (exporter, 'exporters'), (service, 'service')]
    for new_configmap in update_remove_configmaps:
        __remove_configmap(new_configmap[0], configmap_yaml[new_configmap[1]])
    configmap_yaml = __clean_empty(configmap_yaml)
    if configmap_name is not None:
        try:
            updated_yaml = yaml.safe_dump(configmap_yaml)
            configmap.data['collector.yaml'] = updated_yaml
            v1.replace_namespaced_config_map(configmap_name, namespace, configmap)
            return configmap
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fail to replace configmap: {e}")
    else:
        return configmap_yaml



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
        namespace = data['namespace']
        configmap_name = data['configmap_name']

        # Update the ConfigMap with the new pipeline
        new_configmap = update_configmap(namespace, configmap_name, request.model_dump())

        return {"message": "Pipeline created and ConfigMap successfully updated"}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/configurations")
def add_pipeline(request: OTELConfiguration):
    try:
        data = request.model_dump()
        namespace = data['namespace']
        configmap_name = data['configmap_name']

        # Update the ConfigMap with the new pipeline
        new_configmap = add_configmap(namespace, configmap_name, request.model_dump())

        return {"message": "Pipeline created and ConfigMap successfully updated"}
    except Exception as e:
        print(f"Error updating ConfigMap: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.delete("/configurations")
def remove_pipeline(request: OTELConfiguration):
    try:
        data = request.model_dump()
        namespace = data['namespace']
        configmap_name = data['configmap_name']

        # Update the ConfigMap with the new pipeline
        configmap = remove_configmap(namespace, configmap_name, request.model_dump())

        # return {"message": "Pipeline deleted and ConfigMap successfully updated. \n", "configmap": configmap}
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
        return configmap_yaml
    except Exception as e:
        print(f"Error listing pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Endpoint to reload the OpenTelemetry Collector configuration
@app.post("/reload")
def reload_config(request: OTELReload):
    try:
        namespace = request.model_dump()['namespace']
        label_selector =  request.model_dump()['label_selector'] if  request.model_dump()['namespace'] is not None else "app.kubernetes.io/name=opentelemetrycollector"

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
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True, workers=1)