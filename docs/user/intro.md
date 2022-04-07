## Introduction

__Notice:__ Make sure you have followed the steps in the [Administrator guide](../admin/intro.md) 
before continuing with the setup below.

The following page explains how to configure a new code repository (with ML model and pipeline) 
to work together with Kfops.
First, you will need to make small changes on the cluster, then create all configuration 
files required by Kfops.

### "Per project" cluster setup

Kfops assumes that each of your projects (ML models) is stored in separate 
code repositories. 
The "per project" setup has to be repeated each time the new repository is being "linked" 
to your cluster setup.

Each time you add a new repository, you need to modify cluster settings so that Kfops can 
register webhook and listen to chatops commands from it.

The modification is straightforward: Change Helm values override file (`./cluster_setup/values_override.yaml`) by adding repository names in the `repositoriesNames` section. Next run `helm upgrade ...` command.
Helm upgrade will create the repository's webhooks for the newly added repository. 
Refer to [Helm chart setup](../admin/cluster_setup.md#setup-and-deploy-helm-chart) for details.

### Project structure and config files

In order to keep the Kfops configuration consistent across all of your repositores, 
conform to following file structure in your repository:

```yaml
config_files/
  ⊢ config.yaml
  ⊢ kaniko-manifest.yaml
  ⊢ deployment.py
pipeline/
  ⊢ pipeline_function.py
```

#### `config.yaml`

Project's main configuration file. 
Kfops requires the main repository config file to be named `config.yaml` and 
located in `config_files/` folder.
Click [here](config.md) for details.

#### File `kaniko-manifest.yaml`

The file is optional, required only if you want to build images inside the cluster. 
File location and name has to be kept unchanged (`config_files/kaniko-manifest.yaml`).
Click [here](../admin/image_builder.md) setup for details.

#### File `pipeline_function.py`

Contains project's ([Python function-based](https://www.kubeflow.org/docs/components/pipelines/sdk/python-function-components/)) Kubeflow Pipeline.
The filename and location has to be defined in `config.yaml` file.
Click [here](pipeline_function.md) for setup details.

#### File `deployment.py`

The file contains deployment function. The filename and location has to be defined in 
config.yaml file. Click [here](deployment_function.md) for setup details.
