import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from munch import munchify
from package.kfops.config import Config
from package.kfops.pipeline_manager import PipelineRunner
from package.tests.test_pipeline_builder import config_str, basic_config, pipeline_function_file
from kfp import Client

list_experiments_response = {
    'experiments': [
        {
            'created_at': datetime.now(),
            'description': None,
            'id': '<old-experiment-id>',
            'name': 'Experiment 1',
        },
    ],
    'next_page_token': None,
    'total_size': 1
}

new_experiment_id = '<experiment-id>'
create_experiment_response = {
    'created_at': datetime.now(),
    'description': 'Test description',
    'id': new_experiment_id,
    'name': 'Test experiment',
}

get_experiment_response = {
    'created_at': datetime.now(),
    'description': 'Test description',
    'id': new_experiment_id,
    'name': 'Test experiment',
}

run_id = '<run-id>'
run_pipeline_response = {
    'created_at': datetime.now(),
    'description': None,
    'error': None,
    'id': run_id,
    'metrics': None,
    'name': 'Test job name',
    'service_account': 'default-editor',
    'status': None
}

wait_for_run_completion_response = {
    'pipeline_runtime': {'pipeline_manifest': None,},
    'run': {
        'created_at': datetime.now() - timedelta(seconds=30), 
        'description': None,
        'error': None,
        'finished_at': datetime.now(),
        'id': run_id,
        'metrics': None,
        'name': 'Test job name',
        'service_account': 'default-editor',
        'status': 'Succeeded', # 'Failed' or 'Succeeded'
        'storage_state': None}
}

@pytest.mark.parametrize('basic_config', [(pipeline_function_file, config_str)], indirect=True)
def test_successful_run_no_experiment(basic_config, pipeline_function_file):
    client = Mock()
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.list_experiments.return_value = munchify(list_experiments_response)
    client.create_experiment.return_value = munchify(create_experiment_response)
    client.get_experiment.return_value = munchify(get_experiment_response)
    client.run_pipeline.return_value = munchify(run_pipeline_response)

    pipeline_runner = PipelineRunner(client, basic_config)
    version_id = '<version-id>'
    result = pipeline_runner.run_pipeline(pipeline_version_id=version_id)

    assert result['url'] == 'http://example.com/pipeline/#/runs/details/%s' % run_id
    assert result['run_info'] == munchify(run_pipeline_response)
    assert result['run_params'] == {'version_id': '<version-id>', 'test_input': 'foo'}

    client.list_experiments.assert_called_once_with(
        namespace='my-namespace',
        page_size=1000)

    client.create_experiment.assert_called_once_with(
        'Test experiment',
        description='Test description',
        namespace='my-namespace')

    client.get_experiment.assert_called_once_with(
        experiment_name='Test experiment',
        namespace='my-namespace')

    client.run_pipeline.assert_called_once_with(
        experiment_id=new_experiment_id,
        job_name='Pipeline name (Test experiment)',
        version_id=version_id,
        params={'version_id': '<version-id>', 'test_input': 'foo'})

@pytest.mark.parametrize('basic_config', [(pipeline_function_file, config_str)], indirect=True)
def test_successful_run_experiment_exists(basic_config, pipeline_function_file):
    client = Mock()
    client._get_url_prefix.return_value = 'http://example.com/pipeline'

    list_experiments_response['experiments'].append({
            'created_at': datetime.now(),
            'description': 'Test descripton',
            'id': new_experiment_id,
            'name': 'Test experiment',
    })

    client.list_experiments.return_value = munchify(list_experiments_response)
    client.get_experiment.return_value = munchify(get_experiment_response)
    client.run_pipeline.return_value = munchify(run_pipeline_response)

    pipeline_runner = PipelineRunner(client, basic_config)
    version_id = '<version-id>'
    result = pipeline_runner.run_pipeline(pipeline_version_id=version_id)

    assert result['url'] == 'http://example.com/pipeline/#/runs/details/%s' % run_id
    assert result['run_info'] == munchify(run_pipeline_response)
    assert result['run_params'] == {'version_id': '<version-id>', 'test_input': 'foo'}

    client.create_experiment.call_count == 0
    client.list_experiments.call_count == 1
    client.get_experiment.call_count == 1
    client.run_pipeline.call_count == 1

@pytest.mark.parametrize('basic_config', [(pipeline_function_file, config_str)], indirect=True)
def test_wait_for_run_completion(basic_config, pipeline_function_file):
    client = Mock()
    client._get_url_prefix.return_value = 'http://example.com/pipeline'
    client.wait_for_run_completion.return_value = munchify(wait_for_run_completion_response)

    pipeline_runner = PipelineRunner(client, basic_config)

    result = pipeline_runner.wait_for_run_completion(run_id)

    assert result['run_time'] == '30 seconds'
    assert result['run_status'] == 'Succeeded'
