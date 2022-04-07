# Steps required to create development environment

## Create a cluster

Following documentation assumes [K3d](https://k3d.io/) is going to be used in development.
Make sure you use K3d version `>=5.0.0` and create new k3d cluster using steps 
from [K3d documentation](https://k3d.io/v5.0.0/usage/registries/#using-a-local-registry).

In `k3d cluster create` step, make sure you map additional volume like follows:

```bash
k3d cluster create kfc --api-port 6550 --servers 1 --port 8080:80@loadbalancer \
    --registry-create k3d-kfc-registry:0.0.0.0:5000 --wait \
    --volume <PROJECT_PATH>:/project@all
```

`<PROJECT_PATH>` is path to folder with sample project where all config files/folders and sample 
Kubeflow Pipeline has been defined. Refer to "Per project setup" in main Readme.md file.

__Notice:__ Make sure your volumes mapping are correct. They cannot be modified after cluster creation.

Create entry in your hosts file (e.g. on Unix/mac it's the `/etc/hosts` file): `127.0.0.1 k3d-kfc-registry`

__Sidenote:__ At the moment K3d on MacOS has an issue with "Docker desktop" using version `>4.2.0`.
See [this](https://github.com/rancher/k3d/issues/890) and [this](https://github.com/kubeflow/manifests/issues/2087)
for details. Simpliest solution is to use "Docker desktop" version `4.2.0`.

### Install applications necessary for development

* [Skaffold](https://skaffold.dev/docs/install/) 

* [Helm](https://helm.sh/docs/intro/install/)


### Install Kubeflow from manifests 

Follow instructions on [kubeflow/manifests](https://github.com/kubeflow/manifests) Readme page.

In other words execute the following commands:
```bash
git clone https://github.com/kubeflow/manifests
cd manifests
while ! kustomize build example | kubectl apply -f -; do echo "Retrying to apply resources"; sleep 10; done
```

Depending on what you're planning to work on, you can remove some components like e.g. Tensorboard controller or Katib.
Simply comment them out in `example/kustomization.yaml` file.

__Additional installation steps:__

1) Install [Argo CLI](https://github.com/argoproj/argo-workflows/releases).

2) Create namespace `kfops` using `kubectl create namespace kfops` command.

3) Depending on Kubeflow version you're installing, K3d (or more specifically K3s) uses Containerd 
instead of docker container runtime. 
If you used "standalone" manifests, you need to switch to 
[Argo Emissary executor](https://www.kubeflow.org/docs/components/pipelines/installation/choose-executor/) 
by running in cloned `kubeflow/manifests` repo 
([source](https://kserve.github.io/website/admin/serverless/)):

```bash
kustomize build apps/pipeline/upstream/env/platform-agnostic-multi-user-emissary/ | \
kubectl apply -f -
```

4) Remember that Kfops uses Kserve instead of KFServing. With K3d installed on fresh development cluster together 
with Kubeflow manifests, it's easy to install KServe with one additional command: 

```bash
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.7.0/kserve.yaml
```


5) Create python virtual environment and install all packages from `requirements.txt`

__Sidenote:__ If using macOS and docker desktop and some containers are crashing 
because of error `too many files open`, check 
[this fix](https://github.com/kubeflow/manifests/issues/2087#)


## Development process

### Configure sample project

Refer to [user guide](user/intro.md) for details how to setup the sample project. Remember that your 
sample project should be set in the `<PROJECT_PATH>` folder.

If you intend to build images in the cluster, below are ready manifests that will work with your K3d cluster.
First create `PVC` on the cluster:

```yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: dockerfile-claim
  namespace: kfops
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
```

Next, copy below manifest into project's `config_files/kaniko-manifest.yaml` folder 
(Notice: don't apply it on the cluster, Kfops loads it and uses as a template):

```yaml
apiVersion: v1
kind: Pod
metadata:
  generateName: cluster-image-builder-
  labels:
    name: cluster-image-builder
spec:
  containers:  
  - name: cluster-image-builder
    image: gcr.io/kaniko-project/executor:latest
    volumeMounts:
    - name: dockerfile-storage
      mountPath: /cache
  restartPolicy: Never
  volumes:
  - name: dockerfile-storage
    persistentVolumeClaim:
      claimName: dockerfile-claim
```


Also, with in-cluster registry to build images with Kaniko, make sure you set in `config.yaml`:

* Set `image_builder.container_registry_uri` to `k3d-kfc-registry:5000`

* Set `image_builder.insecure` to `true`. This flag allows Kaniko to push to in-cluster insecure registry.

### Start development

Enable virtual environment with installed (from `requirements.txt`) Python packages.

Execute `make develop`. The commands runs [Skaffold](http://skaffold.dev/) command `skaffold dev` that builds 
the container image and runs `helm` install with manifests from `cluster_setup` folder 
using development helm values (`cluster_setup/values_dev.yaml`). 

Notice that `<PROJECT_PATH>` is mapped as volume. Changes in the folder will not trigger `skaffold` image rebuild.

If `skaffold dev` fails, revise documentation's "Per cluster setup" installation steps and then run it again.

### Execute workflow from command line

__Note:__ The command uses predefined manifest from file `manual-workflow-submit.yaml` which mimics event sent from Pull Request.

In order to run workflow, in separate terminal, execute: `make run_workflow command=<COMMAND>` 

The `<COMMAND>` is one of `/build`, `/run`, `/build_run` or `/deploy`. 
It accepts additional parameters similarly to how it would be typed in PR comment, 
e.g. `make run_workflow command="/deploy --run-id=<RUN_ID>"`.

## Commands useful during development

### Clean workflows

`make clean_workflows`

### Check workflow execution results

`argo logs @latest -n kfops`

### Access Kubeflow UI

* Run in separate terminal: `kubectl port-forward -n istio-system svc/istio-ingressgateway 8080:80`

* Open in browser: `http://localhost:8080`

### List images on k3d cluster:

`docker exec k3d-kfc-server-0 sh -c "ctr image list -q"`


## Publish new package version

Currently is a manual process. Steps:

* Set new tag for container `image` in `cluster_setup/kfops/values.yaml` to new version. 
  Where tag to change is `<TAG>` in `image: bartgras/kfops:<TAG>`

* Set the same tag for variable `__version__` in `package/__init__.py` 

* Create repository tag and push to github. E.g. for tag `v1.0.0`: 

```
git tag v1.0.0
git push origin v1.0.0
```

__Notice:__ Git tag should have `v` prefix while `image` and `__version__` should not.

Pushing to new tag to repository will automatically build and push to Docker Hub - image `bartgras/kfops` with new tag.
