import yaml
import os
import re
import pytest
from unittest.mock import patch, Mock, call
from requests.exceptions import HTTPError
from munch import munchify
from package.kfops.config import Config
from package.kfops.kserve_deployer import IsvcDeployer, read_function_from_file
from tempfile import NamedTemporaryFile
from kserve import V1beta1InferenceService


function_def = '''
def test_function():
    return True
'''

existing_inference_services = {
    'items': [
        {
            'metadata': {
                'name': 'test-inference-service',
                'namespace': 'default'
            },
        }
    ]
}

no_inference_services = {'items': []}

basic_config = {
    'deployment': {
        'inference_service_name': 'test-inference-service',
        'inference_service_function_path': 'dummpy.py',
    }
}

def dummy_func():
    return True

def valid_params_func(
    name='test-inference-service',
    storage_uri='s3://trained-models/FOO_RUN_ID/',
    canary_traffic_percent=0,
    namespace='default'
):
    return True


def test_read_function_from_file():
    with NamedTemporaryFile(suffix='.py') as f:
        f.write(bytes(function_def, 'utf-8'))
        f.seek(0)
        func = read_function_from_file(f.name, function_name='test_function')
        assert func() == True

def test_read_function_from_file_invalid_module_name():
    with pytest.raises(ModuleNotFoundError):
        read_function_from_file('invalid/path/function.py', function_name='test_function')

def test_read_function_from_file_invalid_function_name():
    with NamedTemporaryFile(suffix='.py') as f:
        f.write(bytes(function_def, 'utf-8'))
        f.seek(0)
        with pytest.raises(AttributeError):
            read_function_from_file(f.name, function_name='invalid_function_name')

@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
def test_check_isvc_exists(kfs, read_function_from_file):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    kfs.return_value.get.return_value = existing_inference_services
    read_function_from_file.return_value = dummy_func()

    deployer = IsvcDeployer(run_id='test-run-id', namespace='default', config=c)

    assert deployer.check_isvc_exists() == True

@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
def test_check_isvc_exists_no_isvc(kfs, read_function_from_file):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    kfs.return_value.get.return_value = no_inference_services
    read_function_from_file.return_value = dummy_func

    deployer = IsvcDeployer(run_id='test-run-id', namespace='default', config=c)

    assert deployer.check_isvc_exists() == False

@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
def test_invalid_isvc_function_parameters(kfs, read_function_from_file):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = dummy_func

    deployer = IsvcDeployer(run_id='test-run-id', namespace='default', config=c)

    with pytest.raises(TypeError):
        deployer.get_isvc()

@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
def test_valid_isvc_function_parameters(kfs, read_function_from_file):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = valid_params_func

    deployer = IsvcDeployer(run_id='test-run-id', namespace='default', config=c)

    assert deployer.get_isvc() == True

@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
@patch('package.kfops.kserve_deployer.IsvcDeployer.get_isvc')
def test_deploy_no_existing_isvc(isvc, kfs, read_function_from_file):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = valid_params_func

    deployer = IsvcDeployer(run_id='test-run-id', namespace='default', config=c)
    deployer.deploy()

    assert kfs.return_value.create.call_count == 1
    assert kfs.return_value.replace.call_count == 0

@patch('package.kfops.kserve_deployer.IsvcDeployer.wait_ready', return_value=None)
@patch('package.kfops.kserve_deployer.IsvcDeployer.check_isvc_exists', return_value=True)
@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
@patch('package.kfops.kserve_deployer.IsvcDeployer.get_isvc')
def test_deploy_replace_existing_isvc_no_sample_input(
    isvc, kfs, read_function_from_file, check_isvc_exists, wait_ready
):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = dummy_func    

    deployer = IsvcDeployer(run_id='test-run-id', namespace='default', config=c)
    deployer.deploy()

    assert kfs.return_value.create.call_count == 0
    assert kfs.return_value.replace.call_count == 2

    isvc.assert_has_calls([
        call(canary_traffic_percent=0),
        call(canary_traffic_percent=100)
    ])

@patch('package.kfops.kserve_deployer.requests')
@patch('package.kfops.kserve_deployer.IsvcDeployer.wait_ready', return_value=None)
@patch('package.kfops.kserve_deployer.IsvcDeployer.check_isvc_exists', return_value=True)
@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
@patch('package.kfops.kserve_deployer.IsvcDeployer.get_isvc')
def test_deploy_replace_existing_isvc_with_sample_input_http_error(
    get_isvc, kfs, read_function_from_file, check_isvc_exists, wait_ready, requests
):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = dummy_func   

    requests.post.side_effect = HTTPError('error msg')

    deployer = IsvcDeployer(
            run_id='test-run-id', namespace='default', config=c, 
            sample_input={"instances": [[1,2,3]]})
    deployer.deploy()

    assert kfs.return_value.create.call_count == 0
    assert kfs.return_value.replace.call_count == 1
    assert get_isvc.call_count == 1
    assert re.match(r'Error while testing newly deployed model.*error msg', deployer.error) is not None
    
@patch('package.kfops.kserve_deployer.requests')
@patch('package.kfops.kserve_deployer.IsvcDeployer.wait_ready', return_value=None)
@patch('package.kfops.kserve_deployer.IsvcDeployer.check_isvc_exists', return_value=True)
@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
@patch('package.kfops.kserve_deployer.IsvcDeployer.get_isvc')
def test_deploy_replace_existing_isvc_with_sample_input_status_error(
    get_isvc, kfs, read_function_from_file, check_isvc_exists, wait_ready, requests
):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = dummy_func   

    requests.post.return_value.status_code = 500 
    requests.post.return_value.text = 'error msg'

    deployer = IsvcDeployer(
            run_id='test-run-id', namespace='default', config=c, 
            sample_input={"instances": [[1,2,3]]})
    deployer.deploy()

    assert kfs.return_value.create.call_count == 0
    assert kfs.return_value.replace.call_count == 1
    assert get_isvc.call_count == 1
    assert 'status: 500.<br/>Response: <br/> error msg' in deployer.error 

@patch('package.kfops.kserve_deployer.requests')
@patch('package.kfops.kserve_deployer.IsvcDeployer.wait_ready', return_value=None)
@patch('package.kfops.kserve_deployer.IsvcDeployer.check_isvc_exists', return_value=True)
@patch('package.kfops.kserve_deployer.read_function_from_file')
@patch('package.kfops.kserve_deployer.KServeClient')
@patch('package.kfops.kserve_deployer.IsvcDeployer.get_isvc')
def test_deploy_replace_existing_isvc_with_sample_input_status_success(
    get_isvc, kfs, read_function_from_file, check_isvc_exists, wait_ready, requests
):
    c = Config(validate_files=False, check_files_existence=False, config=basic_config)
    read_function_from_file.return_value = dummy_func   

    requests.post.return_value.status_code = 200

    deployer = IsvcDeployer(
            run_id='test-run-id', namespace='default', config=c, 
            sample_input={"instances": [[1,2,3]]})
    deployer.deploy()

    assert kfs.return_value.create.call_count == 0
    assert kfs.return_value.replace.call_count == 2
    get_isvc.assert_has_calls([
        call(canary_traffic_percent=0),
        call(canary_traffic_percent=100)
    ])
    assert deployer.error == None
