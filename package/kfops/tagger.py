from .config import set_config, InvalidConfigException
default_config = set_config()

def versioned_image(image_name: str) -> str:
    '''
    Return full versioned image name in format REGISTRY/IMAGE_NAME:TAG where:

    * REGISTRY part is automatically read from `config.yaml`.

    * IMAGE_NAME: `image_name` should be defined in `config.yaml` 
      (location: `image_builder.images[*].name`)

    * TAG is a Argo Workflow template parameter and it's going to be substituted 
      during Kubeflow Pipeline compilation to Version ID of compiled Kubeflow Pipeline.
    '''

    container_registry_uri = default_config.image_builder.container_registry_uri
    if not container_registry_uri:
        message = 'Missing image_builder.container_registry_uri in settings (file config.yaml).'
        raise InvalidConfigException(message)

    images = default_config.image_builder.images
    if image_name not in [i.name for i in images]:
        message = 'Image name "%s" not found in config.yaml image_builder.images[*].name'
        raise InvalidConfigException(message)

    return "%s/%s:{{workflow.parameters.version_id}}" % (container_registry_uri, image_name)
