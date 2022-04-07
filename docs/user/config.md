## File: `config.yaml`

Contains settings for the project's pipeline, container image builder and deployment. 

The `pipeline` related settings can be overridden during development (with `kfc` command). Parameters can be overridden with `kfc`'s  `--set` flag and/or separate override file (e.g. `kfc build_run --config-override override.yaml`).

The reasoning behind overrides is to allow easy experimentation, e.g. execute pipeline with different input parameters which point at smaller, development dataset.


___Why yaml file:___

* Idea similar to [configuration as a code](https://en.wikipedia.org/wiki/Infrastructure_as_code),

* Gives more flexibility by allowing to modify the config per each push to the (Pull Request) branch,

* Keeps all most important preferences in single place,

* Standardizes the setup across all of yours (ML model) repositories.


In it's basic form, your `config.yaml` will look similar to:

```yaml
repository:
  owner: my-repo-username
  name: my-model-repo-name
pipeline:
  name: Sklearn Iris
  description: Example pipeline to show how to configure your project
  namespace: my-user-profile-name
  experiment_name: My amazing experiment
  pipeline_path: my_pipeline/pipeline.py
  pipeline_args:
    parameter_name: 'parameter_value' 
deployment:
  inference_service_name: sklearn-iris
  inference_service_function_path: config_files/deployment.py
  pre_deployment_test_sample_input_path: test_deployment/input.json
  production: 
    namespace: prod
  staging:
    namespace: staging
image_builder:
  container_registry_uri: my-registry
  images:
    - name: my_image_name
      dockerfile_folder_path: containers/my_image_name
      other_folders_path:
        - containers/lib
```

Check explanation of each section (with additional, optional parameters) below.

### Section `repository`

Repository related settings.

```yaml
repository:

  # The owner of your pipeline/model repository. 
  # E.g. if using Github, it is the OWNER part from https://github.com/OWNER/
  owner: my-repo-username

  # Repository name (REPOSITORY part of https://github.com/OWNER/REPOSITORY)
  name: my-model-repo-name
```

### Section `pipeline`

Kubeflow Pipeline related settings.

```yaml 
pipeline:

  # Kubeflow pipeline name
  name: Sklearn Iris

  # Optional. Description for your pipeline
  description: Example pipeline to show how to configure your project

  # Kubernetes namespace (Kubeflow profile) in which pipeline will be executed.
  # Note: It assumes you have access to this profile. Otherwise you won't be able to see results in Kubeflow UI.
  # For details refer to https://www.kubeflow.org/docs/components/multi-tenancy/getting-started/
  namespace: my-user-profile-name

  # Kubeflow Experiment name this pipeline will be stored under.
  experiment_name: My amazing experiment

  # Path to file where your pipeline code is located.
  # Note: Path is relative to root folder of your repository.
  pipeline_path: my_pipeline/pipeline.py

  # Optional. Name of the pipeline function.
  # Required only if multiple pipeline functions were defined in the file.
  pipeline_function_name: my_pipeline_func

  # Optional. Allows to choose Kubeflow Pipelines execution mode.
  # Valid selections are: V1_LEGACY, V2_COMPATIBLE, V2_ENGINE
  # If not defined V2_COMPATIBLE is used
  pipeline_execution_mode: V2_COMPATIBLE

  # Pipeline run parameters.
  # Optional if pipeline doesn't have any input parameters.
  pipeline_args:
    parameter_name: 'parameter_value' 
```

Regarding `pipeline_execution_mode`: Currently component in function `kfops.model.materialize_model` 
only supports `V2_COMPATIBLE` execution mode. More details on model materialization can be found 
on [Pipeline function](pipeline-function.md) page.

### Section `deployment`

Deployment related settings

```yaml
deployment:

  # When model is deployed, it will use this inference service name.
  inference_service_name: sklearn-iris

  # Path to file where your inference service function has been defined.
  # Note: Path is relative to root folder of your repository
  inference_service_function_path: config_files/deployment.py

  # Optional. Path to the location where inference test sample has been located.
  # Currently only supports JSON file format.
  # Sample will be used to check if newly deployed model responds with HTTP status 200.
  # Tested model is deployed as canary with 0% traffic. In case of non-200 status, it will stop deployment process.
  pre_deployment_test_sample_input_path: test_deployment/input.json

  # Kubernetes namespace into which production models will be deployed to.
  # Notice: namespace defined here has to already exist in cluster.
  production: 
    namespace: prod

  # Optional. Similar to production namespace above.
  # Kubernetes namespace into which production models will be deployed to.
  staging:
    namespace: staging
```

### Section `image_builder`

Deployment related settings

```yaml
# Optional. Required only if your Kubeflow Pipelines use custom images and they are 
# being built in the cluster as part of /build command
image_builder:

  # Registry name where your built image will be pushed. Examples:
  # * For Docker hub use your Docker hub profile name.
  # * For ECR use name in format aws_account_id.dkr.ecr.region.amazonaws.com
  container_registry_uri: my-registry

  # Optional flag required during development. Allows to push image into in-cluster insecure registry. 
  insecure: true

  # Specify images to be built during /build (or /build_run) step.
  # Refer to section "Container images builder" in Readme for details.
  images:
    - name: my_image_name
      dockerfile_folder_path: containers/my_image_name
      other_folders_path:
        - containers/lib

  # Optional. If not defined, default MinIO preinstalled with 
  # Kubeflow is used as a build context for Kaniko.
  # More details about Kaniko contexts: https://github.com/GoogleContainerTools/kaniko#kaniko-build-contexts
  minio:

    # Optional. By default context files are copied into MinIO bucket "image-build-artifacts" 
    # but can be overwritten using:
    context_files_bucket_name: different-bucket-name

    # Optional. By the default MinIO credentials are read from the cluster (minio-service.kubeflow.svc.cluster.local)
    # You can override these settings with options below:
    credentials:
      endpoint: YOUR_ENDPOINT (e.g. my-minio-service.my-namespace.svc.cluster.local)
      access_key: YOUR_ACCESS_KEY
      secret_key: YOUR_SECRET_KEY
```
