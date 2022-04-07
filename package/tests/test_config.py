import os
import pytest
import yaml
import tempfile
from tempfile import NamedTemporaryFile

from package.kfops.config import ConfigOverride, InvalidConfigException

base_conf_str = '''
repository:
  owner: my-repo-username
  name: kfops-sample
'''

def test_config_yaml_validation():
    schema_file_path = os.path.join(os.getcwd(), 'package/kfops/config_schema.yaml')

    with pytest.raises(InvalidConfigException, match=r".*Validation errors.*"):
        with tempfile.NamedTemporaryFile(suffix='.yaml') as tmpf:
            with open(tmpf.name, 'w') as f:
                f.write(base_conf_str)

            ConfigOverride(
                validate_files=True, 
                check_files_existence=False,
                config_file_path=tmpf.name, 
                config_schema_path=schema_file_path)

def test_pipeline_config():
    config_str = '''
    pipeline:
      name: pipeline name
      description: pipeline description
      namespace: namespace
      experiment_name: experiment
      pipeline_path: my/path/func.py
      pipeline_function_name: func_name
      pipeline_args:
        parameter_foo: bar
    '''
    config = yaml.safe_load(config_str)
    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)
    assert c.pipeline.name == 'pipeline name'
    assert c.pipeline.description == 'pipeline description'
    assert c.pipeline.namespace == 'namespace'
    assert c.pipeline.experiment_name == 'experiment'
    assert c.pipeline.pipeline_path == 'my/path/func.py'
    assert c.pipeline.pipeline_function_name == 'func_name'
    assert c.pipeline.pipeline_args == {'parameter_foo': 'bar'}
    assert c.pipeline.pipeline_execution_mode == 'V2_COMPATIBLE'

def test_invalid_pipeline_execution_mode():
    config_str = '''
    pipeline:
      pipeline_execution_mode: INVALID
    '''
    config = yaml.safe_load(config_str)
    with pytest.raises(InvalidConfigException, match=r".*Invalid Kubeflow Pipelines execution mode.*"):
        c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)


def test_deployment_config():
    config_str = '''
    deployment:
      inference_service_name: inference
      inference_service_function_path: config_files/deployment.py
      # Optional, use test data and check if newly deployed model responds with HTTP status 200. Stop deployment if status is not 200.
      pre_deployment_test_sample_input_path: test_deployment/input.json
      production:
        namespace: prod
    '''
    config = yaml.safe_load(config_str)
    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)

    assert c.deployment.inference_service_name == 'inference'
    assert c.deployment.inference_service_function_path == 'config_files/deployment.py'
    assert c.deployment.pre_deployment_test_sample_input_path == 'test_deployment/input.json'
    assert c.deployment.production.namespace == 'prod'


def test_default_image_builder_config():
    config_str = '''
    image_builder:
      container_registry_uri: registry
    '''
    config = yaml.safe_load(config_str)
    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)
    assert c.image_builder.insecure is False
    assert c.image_builder.minio.context_files_bucket_name == 'image-build-artifacts'
    assert c.image_builder.minio.credentials is None

def test_image_builder_config():
    config_str = '''
    image_builder:
      container_registry_uri: registry
      insecure: true
      images:
      - name: image1
        dockerfile_folder_path: containers/image1
        other_folders_path:
          - containers/lib
      - name: test2
        dockerfile_folder_path: containers/image1
        other_folders_path:
          - lib
      minio:
        context_files_bucket_name: bucket-name
        credentials:
          endpoint: endpoint
          access_key: access_key
          secret_key: secret_key    
    '''
    config = yaml.safe_load(config_str)
    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)

    assert c.image_builder.container_registry_uri == 'registry'
    assert c.image_builder.insecure is True
    assert len(c.image_builder.images) == 2

    images = c.image_builder.images
    assert images[0].name == 'image1'
    assert images[0].dockerfile_folder_path == 'containers/image1'
    assert images[0].other_folders_path == ['containers/lib']

    minio = c.image_builder.minio
    assert minio.context_files_bucket_name == 'bucket-name'
    assert minio.credentials.endpoint == 'endpoint'
    assert minio.credentials.access_key == 'access_key'
    assert minio.credentials.secret_key == 'secret_key'


config_str = '''
pipeline:
  name: pipeline name
  description: pipeline description
  namespace: namespace
  experiment_name: experiment
  pipeline_path: my/path/func.py
  pipeline_function_name: func_name
  pipeline_args:
    parameter_foo: bar
'''

def test_args_override():
    config = yaml.safe_load(config_str)
    args_override = [
        'name=new name',
        'description=new description',
        'namespace=new-namespace',
        'experiment_name=new experiment name',
        'pipeline_path=new/path/func.py',
        'pipeline_function_name=new_func_name',
        'pipeline_args.parameter_foo=bar',
        'pipeline_args.parameter_foo2=bar2',
    ]
    config = yaml.safe_load(config_str)
    c = ConfigOverride(
      args_override=args_override, validate_files=False, 
      check_files_existence=False, config=config)

    assert c.pipeline.name == 'new name'
    assert c.pipeline.description == 'new description'
    assert c.pipeline.namespace == 'new-namespace'
    assert c.pipeline.experiment_name == 'new experiment name'
    assert c.pipeline.pipeline_path == 'new/path/func.py'
    assert c.pipeline.pipeline_function_name == 'new_func_name'
    assert c.pipeline.pipeline_args == {'parameter_foo': 'bar', 'parameter_foo2': 'bar2'}

def test_config_file_override():
    config = yaml.safe_load(config_str)
    config_override_str = '''
    pipeline:
      name: new name
      description: new description
      namespace: new-namespace
      experiment_name: new experiment name
      pipeline_path: new/path/func.py
      pipeline_function_name: new_func_name
      pipeline_args:
        parameter_foo: bar
        parameter_foo2: bar2
    '''

    with NamedTemporaryFile(suffix='yaml') as temp_file:
        with open(temp_file.name, 'w') as f:
            f.write(config_override_str)

        c = ConfigOverride(
          config_file_path_override=temp_file.name, validate_files=False, 
          check_files_existence=False, config=config)

        assert c.pipeline.name == 'new name'
        assert c.pipeline.description == 'new description'
        assert c.pipeline.namespace == 'new-namespace'
        assert c.pipeline.experiment_name == 'new experiment name'
        assert c.pipeline.pipeline_path == 'new/path/func.py'
        assert c.pipeline.pipeline_function_name == 'new_func_name'
        assert c.pipeline.pipeline_args == {'parameter_foo': 'bar', 'parameter_foo2': 'bar2'}