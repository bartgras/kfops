## Define deployment function

The purpose of deployment function is to define `KServe`'s `InferenceService` which 
Kfops will deploy the ML model to.

Make sure your `config.yaml` points at the file where the function has been defined. 
Refer to details on [main config](config.md) page.

The function uses [KServe SDK](https://kserve.github.io/website/sdk_docs/sdk_doc/) 
which closely "mimics" the YAML-based manifests.
At the first, the SDK defined function might feel more complex, but you will 
quickly notice that the YAML to Python "translation" process is fast and simple.

Why not YAML manifest? Kfops needs to inject parameters into generated inference 
service. These parameters are not defined on the function level but 
instead "managed" by Kfops.

#### Function signature

Kfops expects function signature to have following inputs, content and return value:

__Input parameters__

* Inference service name - defines part of the URL under which your service will be available. 

* Storage URI - the exact location where your trained ML model is stored.

* Namespace - namespace where the model will be deployed.

* Canary traffic percent - parameter controlled by Kfops that allows to perform canary/shadow deployment.

In other words, your function's name and input parameters should look like following:

```python
def inference_service_instance(name: str, storage_uri: str, namespace: str = 'default',
                               canary_traffic_percent: int = None):
```

__Return value__

Function has to return `V1beta1InferenceService` object instance. Support for `V1alfa` has been disabled in Kubeflow v1.5 and 
so Kfops enforces the "beta".

__Function content__

Check the example below. 
Notice that all parameters (apart from those passed as function inputs) are "hardcoded" in the function.
Specifically, these are `service_account_name` and `resources`.

The `service_account_name` has to match ServiceAccount that KServe uses 
to access your model file in MinIO. For details refer to 
[deployment](../admin/deployment.md) page in Administrator's guide.




#### Example function

Example below shows the "translation" of a simple 
Sklearn-based `InferenceService` manifest into the SDK version.

YAML manifest:

```yaml
apiVersion: "serving.kserve.io/v1beta1"
kind: "InferenceService"
metadata:
  name: <NAME>
  namespace: <NAMESPACE>
spec:
  predictor:
    serviceAccountName: <SERVICE-ACCOUNT-NAME>
    canaryTrafficPercent: <CANARY-TRAFFIC-PERCENT>
    sklearn:
      storageUri: <STORAGE-URI>
      resources:
        requests:
          cpu: 0.02
          memory: 200Mi
        limits:
          cpu: 0.02
          memory: 200Mi     
```

KServe SDK equivalent:

```python
from kubernetes import client
from kserve import constants
from kserve import utils
from kserve import V1beta1InferenceService
from kserve import V1beta1InferenceServiceSpec
from kserve import V1beta1PredictorSpec
from kserve import V1beta1TFServingSpec, V1beta1SKLearnSpec


def inference_service_instance(name: str, storage_uri: str, namespace: str = 'default',
                               canary_traffic_percent: int = None):
    isvc = V1beta1InferenceService(
        api_version=constants.KSERVE_GROUP + '/' + 'v1beta1',
        kind=constants.KSERVE_KIND,
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace),
        spec=V1beta1InferenceServiceSpec(
            predictor=V1beta1PredictorSpec(
                service_account_name='deployer',
                canary_traffic_percent=canary_traffic_percent,
                sklearn=(V1beta1SKLearnSpec(
                    storage_uri=storage_uri,
                    resources=client.V1ResourceRequirements(
                        limits={'cpu': 0.02, 'memory': '200Mi'},
                        requests={'cpu': 0.02, 'memory': '200Mi'})
                )))))

    return isvc
```

