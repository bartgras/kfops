## Pipeline function

### Write pipeline function

Refer to [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/) on details how to
implement the pipeline.

__Important:__ Kfops executes pipeline function using Kubeflow Pipelines v1.7.0 
(`pip install kfp==1.7.0`). Make sure your function satisfies this requirement.

Remember that [execution mode](https://www.kubeflow.org/docs/components/pipelines/sdk-v2/v2-compatibility/) 
defined in your `config.yaml` should match the mode used in pipeline function definition.
By default execution mode is set to `V2_COMPATIBLE`.

The model saving step has to be defined explicitly in the pipeline code.

### Save ML model from the pipeline

The Python `kfops` module contains convenience function `materialize_model` to simplify the 
process of saving the model to MinIO bucket. 
The function requires your pipeline is written using v2 execution mode and 
can be imported using: `from kfops.model import materialize_model`.

Example below saves the model directly from the pipeline's "train" task:

```python
import kfp
from kfops.model import materialize_model
from kfp.v2.dsl import component, Output, Model

@component
def train(model: Output[Model]): # Important: Make sure the variable name is 'model'

    # ... Here are all the steps required to train the model ...

    # Save the model to the temporary file
    import os
    import pickle
    from distutils.dir_util import copy_tree
    os.mkdir('/tmp/models')
    with open('/tmp/models/model.pickle', 'wb') as f:
        pickle.dump(my_trained_model, f)

    # Copy saved file to the "Output".
    # Notice: No matter if your model is single or multiple files, make sure 
    # you are copying folder, not the file itself.
    copy_tree('/tmp/models/', model.path)

# Pipeline
@kfp.v2.dsl.pipeline(name='Example_pipeline')
def example_pipeline(version_id: 'str'):
    train_model_task = train()
    materialize_model_task = materialize_model(model=train_model_task.outputs['model'])
    # Notice: It is important to disable cache for that task
    materialize_model_task.execution_options.caching_strategy.max_cache_staleness = "P0D"
```

Notice that if the container image used by your pipeline step does not have Python with
`kfops` package installed, you will need to reproduce it manually. 
Refer to project's code, file `package/kfops/model.py`, for details.

Materialized model is copied to MinIO bucket: `s3://trained_models/<pipeline_run_id>/`
where `pipeline_run_id` is ID of pipeline run that "produced" the model.


### Synchronize container image tag with compiled Kubeflow Pipeline

When your container images are being built by Kaniko, they have to have an image tag.
In simple case they could always be marked with tag `latest` but if you want to make sure 
your pipelines are reproducible, backwards and forward compatible, then the container 
image tag should match the compiled Kubeflow Pipeline.

To make the synchronization working, first the pipeline is built and
then the ID (Kubeflow pipeline version ID) of compiled pipeline is used
as a tag of the built container image.

Each compiled pipeline has to have input parameter "version_id" that
when filled in with pipeline ID will execute container images with matching tag. 
Simply put, during pipeline run, "Version ID" of the compiled Kubeflow Pipeline 
is used as an image tag.

Kfops simplifies this setup with the `versioned_image` function that can be used 
inside your pipeline function definition as follows:

```python
from kfops.tagger import versioned_image

my_op = kfp.components.create_component_from_func(
    func=my_pipeline_function, 
    base_image=versioned_image('<IMAGE NAME>')
)
```

Where `<IMAGE NAME>` is the image name defined in `config.yaml`' file, section `image_builder.images`:

```yaml
image_builder:
  container_registry_uri: <YOUR REGISTRY URI>
  images:
    - name: <IMAGE NAME>
```    

The image tag (Kubeflow Pipelines Version ID) has to be passed into pipeline.
This requires simple change in your pipeline function code with `version_id` passed on the input:

```python
@kfp.dsl.pipeline(name='My pipeline')
def my_pipeline(version_id: 'str'):
  ...
```  

### Pull images from private docker registry

__Note:__ this section is not directly related to Kfops but might save you time 
when composing your pipeline.

The Kfops with Kaniko allows you to push images to private registry but additional changes 
have to be made in order to pull those images into your Kubeflow pipeline.

Steps:

* Create docker registry secret in a namespace where pipeline is going to be executed. Refer to 
  [Kubernetes documentation](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/) for details.
  The secret has to be created per each namespace in which your pipeline is going to be executed.
  With Kfops, the Kubeflow pipeline is always executed in a single namespace, 
  configured with `pipeline.namespace` parameter in `config.yaml` file.
	
* Add `set_image_pull_secrets` function to the Kubeflow Pipeline with secret you just created. Check example
  [here](https://github.com/kubeflow/pipelines/blob/dec03067ca1f89f1ca23c7397830d60201448fa6/samples/core/imagepullsecrets/imagepullsecrets.py)
  for details.