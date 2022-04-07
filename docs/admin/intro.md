## In-cluster setup

### Requirements

* Assumes working cluster with domain and TLS set up.

* Requires installed Kubeflow with Ingress that uses TLS.

* Kfops relies on [Kserve](https://kserve.github.io/website/) instead of KFServing which comes with Kubeflow version 1.4 and earlier. 
  For Kubeflow version lower than v1.5, follow installation (or [migration guide](https://kserve.github.io/website/0.7/admin/migration/#migrating-from-kubeflow-based-kfserving) from KFServing) steps on the Kserve website.

__Notice:__ Kfops has been tested with Kubeflow v1.4. 


### Setup steps

__On the high level, the setup can be divided into the following steps:__

__1)__ Installation of necessary tools and cluster components (e.g. Argo Events). Creation of 
required Kubernetes Secrets followed by installation of Kfops Helm chart. 

Refer to the [in-cluster setup](cluster_setup.md) for details.

__2)__ Configuration of the in-cluster container images builder. The step is optional, 
required only if you plan to use the in-cluster images builder. 

Refer to the [images builder](image_builder.md) for details.

__3)__ Configuration of Kubernetes namespaces where your ML models 
(KServe `InferenceService`s) will be deployed. 

Refer to the [deployment](deployment.md) for details.


__Additional setup notes__

* Kubeflow already has [Argo Workflows](https://argoproj.github.io/workflows) installed in 
  the `kubeflow` namespace. Kfops uses it and only installs an additional component - 
  [Argo Events](https://argoproj.github.io/events) - to listen to Pull request comment events.

* When cluster setup is ready, single (Argo Events) endpoint is used to listen to PR 
  comment events from multiple repositories, but all configured repositories have to 
  use the same repository owner with an access webhook token defined for this owner.

* Kfops can work with all Kubeflow Pipelines execution modes (`V1_LEGACY`, `V2_COMPATIBLE`, `V2_ENGINE`)

__Tech stack summary__

* [Argo](https://argoproj.github.io/) to listen to chatops commands and execute Argo pipelines that build/run/deploy your pipelines and models to Kserve.

* [MinIO](https://min.io/) to store [Kaniko](https://github.com/GoogleContainerTools/kaniko) context files and build ML models.

Both Argo and MinIO come installed with (full version) Kubeflow; no additional installation or configuration steps are required.