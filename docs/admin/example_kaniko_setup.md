
## Example Kaniko Pod setup

Following is example configuration of `kaniko-manifest.yaml` that can push images to [Docker Hub registry](https://hub.docker.com).

If you're using other registry (like e.g. Amazon ECR or Azure Container Registry) the steps are almost similar.
Refer to [kaniko documentation](https://github.com/GoogleContainerTools/kaniko#pushing-to-different-registries) for more details.

### Steps:

#### 1. Create manifest file from template

Copy `config_files_templates/kaniko-manifest.yaml` into your project's `config_files/kaniko-manifest.yaml`

#### 2.  Add authentication section

Follow steps in [kaniko docs](https://github.com/GoogleContainerTools/kaniko#pushing-to-docker-hub) for Docker Hub to create `config.json` file.

"Load" `config.json` on your cluster using Kubernetes `Secret`:

```bash
kubectl create secret generic docker-config --from-file=<path to config.json> --namespace <NAMESPACE>
```

__Notice:__ `<NAMESPACE>` by default is `kfops` but if you used different one during 
"Per cluster setup" (in command `helm install`) then change it accordingly.

Modify the manifest by adding created `ConfigMap` as a volume mounted to `/kaniko/.docker/`

```yaml
apiVersion: v1
kind: Pod
metadata:
  generateName: cluster-image-builder-
  labels:
    name: cluster-image-builder
  #Note: By default namespace "kfops" is applied automatically
spec:
  containers:  
  - name: cluster-image-builder
    image: gcr.io/kaniko-project/executor:latest
    # Note: Do not specify "args" because they will be overwritten 
    # args: ...
    volumeMounts:
    ########## Added section
    - name: docker-config
      mountPath: /kaniko/.docker/
    ########## Added section end  
  restartPolicy: Never
  volumes:
  ########## Added section
  - name: docker-config
    secret:
      secretName: docker-config
  ########## Added section end
```


#### 3. Add Kaniko Pod cache volume

It is recommended to add cache volume to store cached docker layers from previous builds.
This will significantly speed up the build process. Refer to [kaniko documentation](https://github.com/GoogleContainerTools/kaniko#caching-base-images) for details.

Cache volume is `Pod`s standard Kubernets `PersistentVolumeClaim`. 

Create file `cache-pvc.yaml` with example manifest:

```yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: dockerfile-claim
  # Change the namespace
  # By default the namespace should be kfops
  namespace: <NAMESPACE> 
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
```      

Run `kubectl apply -f builder-pvc.yaml`.

Next, adapt your manifest to mount the volume into your Kaniko pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  generateName: cluster-image-builder-
  labels:
    name: cluster-image-builder
  #Note: By default namespace "kfops" is applied automatically
spec:
  containers:  
  - name: cluster-image-builder
    image: gcr.io/kaniko-project/executor:latest
    # Note: Do not specify "args" because they will be overwritten 
    # args: ...
    volumeMounts:
    - name: docker-config
      mountPath: /kaniko/.docker/
    ########## Added section  
    - name: dockerfile-storage
      mountPath: /cache
    ########## Added section end
  restartPolicy: Never
  volumes:
  - name: docker-config
    configMap:
      name: docker-config
  ########## Added section    
  - name: dockerfile-storage
    persistentVolumeClaim:
      claimName: dockerfile-claim
  ########## Added section
```
