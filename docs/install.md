## Installation

On a high level, the setup process can be divided into the cluster and per-project steps.

__Cluster setup__ - Performed once per Kubernetes cluster. Assumes cluster has already 
Kubeflow installed. Refer to the [Administrator guide](admin/intro.md) for details.

__Per project (ML model repository) setup__ - Steps required to integrate Kfops 
with a new code repository (with ML model and pipeline). 
Refer to the [User guide](user/intro.md) for details.

____________

__Notice:__
Currently, only Github is supported as a source for chatops commands but, the project has
been architected to easily extend it with other Source Control Management Systems.