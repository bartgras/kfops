import yaml
import re
import pytest
from datetime import datetime
from unittest.mock import patch, Mock, call
from munch import munchify
from package.kfops.config import Config, ConfigOverride
from package.kfops.pipeline_manager import PipelineBuilder
from kfp import Client
from tempfile import NamedTemporaryFile

pipeline_function_template = '''
from kfp import dsl, components

def do_nothing(test_input: str):
    return test_input

do_nothing_op = components.create_component_from_func(
    func=do_nothing, base_image='python:3.8'
)

@dsl.pipeline(name='Basic pipeline')
def example_pipeline(test_input: str):
    do_nothing_task = do_nothing_op(test_input)
'''

config_str = '''
pipeline:
  name: Pipeline name
  description: Test description
  namespace: my-namespace
  experiment_name: Test experiment
  pipeline_path: package/tests/data/basic_pipeline.py
  pipeline_args:
    test_input: 'foo' 
'''

config_str_with_image_builder = '''
pipeline:
  name: Pipeline name
  description: Test description
  namespace: my-namespace
  experiment_name: Test experiment
  pipeline_path: package/tests/data/basic_pipeline.py
  pipeline_args:
    test_input: 'foo' 
image_builder:
  container_registry_uri: registry.example.com
  images:
    - name: image_test
      dockerfile_folder_path: containers/image1
'''

@pytest.fixture
def pipeline_function_file():
    temp_file = NamedTemporaryFile(suffix='.py')
    with open(temp_file.name, 'w') as f:
        f.write(pipeline_function_template)
    yield temp_file
    temp_file.close()

@pytest.fixture
def basic_config(pipeline_function_file, config_str=config_str):
    return ConfigOverride(
        validate_files=False, check_files_existence=False, config=yaml.load(config_str),
        args_override=['pipeline_path=%s' % pipeline_function_file.name])  

@pytest.fixture
def basic_config_with_image_builder(pipeline_function_file):
    return ConfigOverride(
        validate_files=False, check_files_existence=False, 
        config=yaml.load(config_str_with_image_builder),
        args_override=['pipeline_path=%s' % pipeline_function_file.name])

def test_pipeline_builder_build_fails_with_invalid_pipeline_function_setup():
    client = Mock()
    client.get_pipeline_id.return_value = None
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.upload_pipeline.return_value = munchify(upload_pipeline_response)

    config = ConfigOverride(
      validate_files=False, check_files_existence=False, config=yaml.load(config_str),
      args_override=['pipeline_path=invalid/path/to/pipeline/function_file.py'])
    pipeline_builder = PipelineBuilder(client, config=config)
    with pytest.raises(ModuleNotFoundError, match=r"Invalid pipeline function setup. .* No module named 'function_file'"):
        pipeline_builder.build()

upload_pipeline_response = {
  'default_version': {
    'code_source_url': None,
    'created_at': datetime.now(),
    'description': None,
    'id': '4484d1ae-5639-46eb-9010-acc50f392e65',
    'name': 'Test pipeline example',
    'package_url': None,
  },
  'id': '4484d1ae-5639-46eb-9010-acc50f392e65',
  'url': 'http://example.com/pipeline/#/pipelines/details/4484d1ae-5639-46eb-9010-acc50f392e65',
  'name': 'Pipeline name',
  'description': 'Test description',
  'error': None,
}


@pytest.mark.parametrize('basic_config', [(pipeline_function_file, config_str)], indirect=True)
def test_pipeline_build_succeeds_no_previous_builds(basic_config, pipeline_function_file):
    client = Mock()
    client.get_pipeline_id.return_value = None
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.upload_pipeline.return_value = munchify(upload_pipeline_response)

    pipeline_builder = PipelineBuilder(client, config=basic_config)
    response = pipeline_builder.build()

    assert client.upload_pipeline.call_args[0][0].endswith('.zip')
    assert client.upload_pipeline.call_args[1]['pipeline_name'] == 'Pipeline name'
    assert client.upload_pipeline.call_args[1]['description'] == 'Test description'

    assert response['url'] == 'http://example.com/pipeline/#/pipelines/details/4484d1ae-5639-46eb-9010-acc50f392e65'
    assert response['pipeline_id'] == '4484d1ae-5639-46eb-9010-acc50f392e65'
    assert response['version_id'] == '4484d1ae-5639-46eb-9010-acc50f392e65'
    assert response['info'] == upload_pipeline_response

upload_pipeline_version_response = {
  'code_source_url': None,
  'created_at': datetime.now(),
  'description': None,
  'id': '8f704777-1cf3-449b-967e-3486c49be2de',
  'name': 'Version 2 Dev 14:10:1638166257, 2021',
  'package_url': None,
  'resource_references': [{
    'key': {
      'id': '4484d1ae-5639-46eb-9010-acc50f392e65',
      'type': 'PIPELINE'
    },
    'name': None,
    'relationship': 'OWNER'
  }]
}

@pytest.mark.parametrize('pipeline_function_file', [pipeline_function_template], indirect=True)
def test_pipeline_build_succeeds_previous_build_exists(pipeline_function_file, basic_config):
    client = Mock()
    client.get_pipeline_id.return_value = '4484d1ae-5639-46eb-9010-acc50f392e65'
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.upload_pipeline_version.return_value = munchify(upload_pipeline_version_response)

    pipeline_builder = PipelineBuilder(client, config=basic_config)
    response = pipeline_builder.build()

    assert client.upload_pipeline_version.call_args[0][0].endswith('.zip')
    assert client.upload_pipeline_version.call_args[1]['pipeline_name'] == 'Pipeline name'
    assert re.match(r'Version .*', client.upload_pipeline_version.call_args[1]['pipeline_version_name']) is not None

    assert response['url'] == 'http://example.com/pipeline/#/pipelines/details/4484d1ae-5639-46eb-9010-acc50f392e65/version/8f704777-1cf3-449b-967e-3486c49be2de'
    assert response['pipeline_id'] == '4484d1ae-5639-46eb-9010-acc50f392e65'
    assert response['version_id'] == '8f704777-1cf3-449b-967e-3486c49be2de'
    assert response['info'] == upload_pipeline_version_response

@patch('package.kfops.pipeline_manager.ImageBuilder')
def test_pipeline_builder_calls_image_builder(image_builder, basic_config_with_image_builder):
    client = Mock()  
    client.get_pipeline_id.return_value = None
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.upload_pipeline.return_value = munchify(upload_pipeline_response)

    pipeline_builder = PipelineBuilder(client, config=basic_config_with_image_builder)
    response = pipeline_builder.build()

    assert image_builder.call_count == 1
    assert image_builder.return_value.build_images.call_args[0][0] == '4484d1ae-5639-46eb-9010-acc50f392e65'

def test_pipeline_build_fails_with_syntax_error_in_pipeline_function():
    client = Mock()
    client.get_pipeline_id.return_value = None
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.upload_pipeline.return_value = munchify(upload_pipeline_response)

    with NamedTemporaryFile(suffix='.py') as temp_file:
        with open(temp_file.name, 'w') as f:
            f.write('typo')
    
        config = ConfigOverride(
            validate_files=False, check_files_existence=False, config=yaml.load(config_str),
            args_override=['pipeline_path=%s' % temp_file.name])  

        pipeline_builder = PipelineBuilder(client, config=config)
        with pytest.raises(NameError):
            pipeline_builder.build()
