## Deployment setup

Currently Kfops supports two endpoints (production and staging) where ML models can be deployed.
The settings below explain how to configure Kubernetes "production" and "staging" namespaces (with "staging" being optional) to work with Kfops.

The name of your staging and production namespaces can be set per each code repository that is being 
integrated with Kfops. For details refer to "deployment" section in [main config](../user/config.md) file.

### Configure deployment namespaces

__Note:__ Steps below are based on [this source](https://kserve.github.io/website/modelserving/storage/s3/s3/).

Manifests below create deployment namespace and configure KServe access to the MinIO service 
where ML models are stored after training.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: <NAMESPACE>
  labels:
    # Enable Istio (optional)
    istio-injection: enabled
---
apiVersion: v1
kind: Secret
metadata:
  name: minio-access-for-deployment
  namespace: <NAMESPACE>
  annotations:
    serving.kserve.io/s3-endpoint: minio-service.kubeflow:9000
    serving.kserve.io/s3-usehttps: "0"
    serving.kserve.io/s3-verifyssl: "0"
    serving.kserve.io/s3-region: us-east-1
type: Opaque
# Note: Use `stringData` for raw credential string or `data` for base64 encoded string
stringData: 
  # Modify only if you changed minio credentials
  AWS_ACCESS_KEY_ID: minio  
  AWS_SECRET_ACCESS_KEY: minio123
```

Remember to replace `<NAMESPACE>` with your namespace name.

Next, create `ServiceAccount` as follows:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deployer
  namespace: <NAMESPACE>
secrets:
- name: minio-access-for-deployment
```

Remember to replace `<NAMESPACE>` with your namespace name.

Created `ServiceAccount` `name` is going to be used by your repository's deployment function. 
For details refer to [deployment function](../user/deployment_function.md) in User guide. 


__Notice:__ `Namespace`, `Secret` and `ServiceAccount` have to be created separately per each (production and staging) namespace.
