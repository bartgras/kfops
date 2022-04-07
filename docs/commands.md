## Commands reference

Assumes the cluster and project have been successfully configured. 
Refer to [Installation](install.md) for details.

### Running `kfc` command

__Notice:__ Ensure your environment (e.g., Jupyter notebook that comes preinstalled with Kubeflow)
has been appropriately configured to access Kubeflow Pipelines. Refer to details in 
[Kubeflow documentation](https://www.kubeflow.org/docs/components/pipelines/sdk/connect-api/#multi-user-mode).


Once installed with `pip install kfc`, run `kfc --help` to print full command reference.

It is recommended to install a specific version of kfc: `pip install kfc==<version>`, 
the `<version>` should match the Kfops version installed in the cluster.

### Running chatops commands

__Notice:__ In-cluster (Argo) workflow that executes chatops commands has been already configured to access kKubeflow Pipelines.

Executed in the context of Pull Request.

Complete list with explanations:

* `/build` - Compiles Kubeflow Pipeline using code in PR. Optionally, if was configured, builds and pushes to container registry images built.

* `/run` - Executed Kubeflow Pipeline.

* `/build_run` - `/build` and `/run` in single command.

* `/deploy` - Deploys the model. Requires the pipeline to be already run in the same PR (otherwise it will report an error). If the run was executed more than once, `/deploy` will deploy the model from the last pipeline run. If you want to deploy a specific (Kubeflow Pipelines) run ID, use `/deploy --run-id=<RUN-ID>` where `<RUN-ID>` will be reported in PR after successfull pipeline execution.

* `/staging_deploy` - Similar to `/deploy` but deploys ML model to the staging environment.