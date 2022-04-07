import pytest
import yaml
from unittest.mock import patch, Mock, PropertyMock, call
from munch import munchify
from package.kfops.config import ConfigOverride
from package.kfops.handler import VersionControlHandler
from tempfile import NamedTemporaryFile

config_str = '''
repository:
  owner: my-repo-username
  name: kfops-sample
pipeline:
  name: Pipeline name
  description: Test description
  namespace: my-namespace
  experiment_name: Test experiment
  pipeline_path: package/tests/data/basic_pipeline.py
  pipeline_args:
    test_input: 'foo'
'''

config_str_with_deployment = config_str + '''
deployment:
  inference_service_name: sklearn-iris
'''

config_str_with_prod_namespace = config_str_with_deployment + '''
  production:
    namespace: my-production-namespace
'''

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.PipelineBuilder')
def test_vc_handler_build(pipeline_builder, messenger):
    pipeline_builder.return_value.build.return_value = {}
    client = Mock()
    TestVCManager = Mock()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str))
    test_handler = VersionControlHandler(
        client=client, command='build', pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()
    
    assert pipeline_builder.return_value.build.call_count == 1
    assert pipeline_builder.call_args[1]['config'] == c
    assert messenger.return_value.component_built.call_count == 1


@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.PipelineRunner')
def test_vc_handler_run_success(pipeline_runner, messenger):
    pipeline_runner.return_value.run_pipeline.return_value = munchify({'run_info': {'id': '123'}})
    pipeline_runner.return_value.wait_for_run_completion.return_value = munchify({'run_status': 'Succeeded', 'run_time': '1m'})
    client = Mock()
    TestVCManager = Mock()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str))
    test_handler = VersionControlHandler(
        client=client, command='run', 
        pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()
    
    assert pipeline_runner.return_value.run_pipeline.call_count == 1
    assert pipeline_runner.call_args[1]['config'] == c
    assert messenger.return_value.pipeline_run.call_count == 1
    assert messenger.return_value.pipeline_run_completed.call_count == 1

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.PipelineRunner')
def test_vc_handler_run_failure(pipeline_runner, messenger):
    pipeline_runner.return_value.run_pipeline.return_value = munchify({'run_info': {'id': '123'}})
    pipeline_runner.return_value.wait_for_run_completion.return_value = munchify({'run_status': 'Failed'})
    client = Mock()
    TestVCManager = Mock()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str))
    test_handler = VersionControlHandler(
        client=client, 
        command='run',
        pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()
    
    assert pipeline_runner.return_value.run_pipeline.call_count == 1
    assert pipeline_runner.call_args[1]['config'] == c
    assert messenger.return_value.pipeline_run.call_count == 1
    assert messenger.return_value.generic_error_message.call_count == 1

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.PipelineRunner')
def test_vc_handler_run_failure_could_not_find_version_id(pipeline_runner, messenger):
    client = Mock()
    TestVCManager = Mock()
    TestVCManager.return_value.extract_hidden_variables.return_value = {}

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str))
    test_handler = VersionControlHandler(
        client=client, command='run', 
        pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()

    assert pipeline_runner.return_value.run_pipeline.call_count == 1
    assert messenger.return_value.generic_error_message.call_count == 1
    assert 'Could not find pipeline to run' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.IsvcDeployer')
@patch('package.kfops.handler.VersionControlMessenger')
def test_vc_parses_command_params(messenger, isvc_deployer):
    client = Mock()
    TestVCManager = Mock()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str_with_prod_namespace))
    test_handler = VersionControlHandler(
        client=client, 
        command='deploy', command_params={'run-id': '123'},
        pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()

    isvc_deployer.assert_called_with('123', 'my-production-namespace', config=c, sample_input=None)


@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_run_id_not_found_error(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()
    TestVCManager.return_value.extract_hidden_variables.return_value = {}

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str))
    test_handler = VersionControlHandler(
        client=client, 
        command='deploy',
        pr_number='1', config=c,
        VCManager=TestVCManager)
    
    with pytest.raises(SystemExit):
        test_handler.exec_command()

    assert 'Could not find trained model.' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_namespace_not_found_error(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str_with_deployment))
    test_handler = VersionControlHandler(
        client=client, 
        command='deploy',
        pr_number='1', config=c,
        VCManager=TestVCManager)
    
    with pytest.raises(SystemExit):
        test_handler.exec_command()

    assert 'Namespace not defined' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_compare_pr_with_base_failure(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()
    TestVCManager.return_value.is_pr_diverged.return_value = True

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str_with_prod_namespace))
    test_handler = VersionControlHandler(
        client=client,
        command='deploy',
        pr_number='1', config=c,
        VCManager=TestVCManager)
    
    with pytest.raises(SystemExit):
        test_handler.exec_command()

    assert TestVCManager.return_value.is_pr_diverged.call_count == 1
    assert 'Your Pull Request is out of date with base branch' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_deploy_force_skips_pr_diverged_checking(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=yaml.safe_load(config_str_with_prod_namespace))
    test_handler = VersionControlHandler(
        client=client, 
        command='deploy', command_params={'force': True},
        pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()

    assert TestVCManager.return_value.is_pr_diverged.call_count == 0

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_deploy_invalid_sample_path(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    config = yaml.safe_load(config_str_with_prod_namespace)

    config['deployment']['pre_deployment_test_sample_input_path'] = 'invalid/path/sample.json'

    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)
    test_handler = VersionControlHandler(
        client=client,
        command='deploy', command_params={'force': True},
        pr_number='1', config=c,
        VCManager=TestVCManager)

    with pytest.raises(SystemExit):
        test_handler.exec_command()

    assert 'Invalid deployment settings' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_deploy_sample_input_is_not_json(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    config = yaml.safe_load(config_str_with_prod_namespace)

    with NamedTemporaryFile(suffix='.json') as f:
        with open(f.name, 'w') as fp:
            fp.write('{x=null}')

        config['deployment']['pre_deployment_test_sample_input_path'] = f.name

        c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)
        test_handler = VersionControlHandler(
            client=client, 
            command='deploy', command_params={'force': True},
            pr_number='1', config=c,
            VCManager=TestVCManager)

        with pytest.raises(SystemExit):
            test_handler.exec_command()

        assert 'Could not parse JSON file.' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_deploy_failure(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()

    isvc_deployer.return_value.error = 'Error message'

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    config = yaml.safe_load(config_str_with_prod_namespace)
    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)
    test_handler = VersionControlHandler(
        client=client,
        command='deploy', command_params={'force': True},
        pr_number='1', config=c,
        VCManager=TestVCManager)

    with pytest.raises(SystemExit):
        test_handler.exec_command()

    assert 'Error message' in messenger.return_value.generic_error_message.call_args[0][0]

@patch('package.kfops.handler.VersionControlMessenger')
@patch('package.kfops.handler.IsvcDeployer')
def test_vc_deploy_success(isvc_deployer, messenger):
    client = Mock()
    TestVCManager = Mock()
    TestVCManager.return_value.merge_pr.return_value = True, None
    TestVCManager.return_value.close_pr.return_value = True, None

    isvc_deployer.return_value.error = None

    messenger.return_value.generic_error_message.side_effect = SystemExit()

    config = yaml.safe_load(config_str_with_prod_namespace)
    c = ConfigOverride(validate_files=False, check_files_existence=False, config=config)
    test_handler = VersionControlHandler(
        client=client,
        command='deploy', command_params={'force': True},        
        pr_number='1', config=c,
        VCManager=TestVCManager)
    test_handler.exec_command()
    
    assert isvc_deployer.return_value.deploy.call_count == 1
    assert TestVCManager.return_value.add_label.call_count == 1