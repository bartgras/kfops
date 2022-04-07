## Installation steps:

__Note:__ In order to keep it simple, Kubernetes namespace `kfops` is used 
throughout the documentation. You can use different namespace name but remember 
to change your commands accordingly.

### Install required tools

Install Helm using [Helm install](https://helm.sh/docs/intro/install/) documentation.

### Get code and create Kubernetes namespace

Git clone [Kfops](https://github.com/bartgras/kfops) repository on your local machine and `cd` into cloned repository

In your Kubernetes cluster, create namespace `kfops`: `kubectl create namespace kfops`  

### Install Argo Events

In this step you install [Argo events](https://argoproj.github.io/argo-events/) and event bus that manages `kfops` namespace. 
Recommended method is Argo Events namespaced installation.
Notice that in namespaced installation, Argo Events are installed in `argo-events` namespace but manage and listen in `kfops` namespace.

Follow "[namespaced installation](https://argoproj.github.io/argo-events/installation/#namespace-installation)" documentation
and adapt `eventbus-controller`, `eventsource-controller` and `sensor-controller` manifests to manage `kfops` namespace.
(Simply set `--managed-namespace` to `kfops` similarly as explained in 
[Argo Events manages namespace](https://argoproj.github.io/argo-events/managed-namespace/) documentation).

__Note:__ for GKE and Openshift, follow additional steps from the argo events installation.

Next install EventBus in `kfops` namespace:

```bash
kubectl apply -f \
https://raw.githubusercontent.com/argoproj/argo-events/stable/examples/eventbus/native.yaml \
--namespace kfops
```

### Create required secrets

#### Setup your SCM (Source Code Management) system API token.

__Notice:__ Currently only Github is supported. Steps below present the setup for Github.
  
In order to setup Github API Token, refer to Github documentation how to [create GITHUB API Token](https://docs.github.com/en/github/authenticating-to-github/keeping-your-account-and-data-secure/creating-a-personal-access-token). On the "Edit personal access token" page select "repo" scope.
Take note of the username who created the token, it will be used later.

#### Create secret to store your access token

```bash
kubectl create secret generic scm-access-webhook-token \
--namespace kfops --from-literal=token="<TOKEN>"
```

Replace `<TOKEN>` is your token created in previous step.

#### Setup access to MinIO in kfops namespace:

```bash
kubectl create secret generic mlpipeline-minio-artifact \
--namespace kfops \
--from-literal=accesskey="<MINIO ACCESS KEY>" \
--from-literal=secretkey="<MINIO SECRET KEY>"
```

If you didn't change it while deploying Kubeflow, by default MinIO access key is `minio` and secret key `minio123`.

### Setup and install helm chart

Requires Helm version >=3. Check [Helm documentation](https://helm.sh/docs/intro/install/) for details.

__Note:__ Because project is still in alpha stage. The kfops helm chart isn't published but installed directly from the repo.

Steps:

* Create file `./cluster_setup/values_override.yaml` with content copied from `./cluster_setup/kfops/values.yaml`

* Adapt `./cluster_setup/values_override.yaml`. For details refer to [Helm chart values](chart_values.md) page.

* Install argo-events subchart: `helm dependency update ./cluster_setup/kfops`

* Install chart (Notice: uour CWD should be root of the cloned repository):

```bash
helm install kfops -f ./cluster_setup/values_override.yaml \
./cluster_setup/kfops \
--namespace kfops
```

__Note:__ If you make changes in your `values_override.yaml` file, you can update them on the 
cluster using Helm upgrade command:

```bash
helm upgrade kfops -f ./cluster_setup/values_override.yaml \
./cluster_setup/kfops \
--namespace kfops
```

__Notice:__ Once helm command is applied, the argo events installation component will automatically 
set repository's webhooks (e.g. in Github you can check it in repository's `Settings` -> `Webhooks`).