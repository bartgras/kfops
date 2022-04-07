import yaml
import os
import pytest
from unittest.mock import patch, Mock, call
from munch import munchify
import re

from package.kfops.config import Config
from package.kfops.s3 import MinioManager, tar_filter

@patch('package.kfops.s3.v1_api')
@patch('package.kfops.s3.Minio')
def test_minio_creds_from_cluster(minio, v1_api):
    v1_api.read_namespaced_secret.return_value = munchify({
        'data': {
            'accesskey': 'azhzX2FjY2Vzc19rZXk=',
            'secretkey': 'azhzX3NlY3JldF9rZXk=',
        }
    })
    
    config_str = '''
    image_builder:
      container_registry_uri: registry
    '''
    config = yaml.safe_load(config_str)
    c = Config(validate_files=False, check_files_existence=False, config=config)
    minio_manager = MinioManager(bucket='bucket', config=c)
    assert minio_manager.get_minio_creds() == ('k8s_access_key', 'k8s_secret_key', \
        'minio-service.kubeflow.svc.cluster.local')

@patch('package.kfops.s3.v1_api')
@patch('package.kfops.s3.Minio')
def test_minio_creds_from_config(minio, v1_api):
    config_str = '''
    image_builder:
      minio:
        context_files_bucket_name: bucket-name
        credentials:
          endpoint: endpoint
          access_key: access_key
          secret_key: secret_key    
    '''
    config = yaml.safe_load(config_str)  
    c = Config(validate_files=False, check_files_existence=False, config=config)
    minio_manager = MinioManager(bucket='bucket', config=c)
    assert minio_manager.get_minio_creds() == ('access_key', 'secret_key', 'endpoint')

@patch('package.kfops.s3.MinioManager._get_cluster_minio_creds', return_value=('access_key', 'secret_key', 'endpoint'))
@patch('package.kfops.s3.Minio')
@patch('package.kfops.s3.tarfile')
def test_tgz_upload_folders(tarfile, minio, minio_manager):
    config_str = '''
    image_builder:
      minio:
        credentials:
          endpoint: endpoint
          access_key: access_key
          secret_key: secret_key    
    '''
    config = yaml.safe_load(config_str)  
    c = Config(validate_files=False, check_files_existence=False, config=config)
    minio_manager = MinioManager(bucket='bucket', config=c)
    res = minio_manager.tgz_upload_folders('path/to/folder', ['path2/subfolder2', 'path3/subfolder3'])
    assert res.endswith('.tar.gz')
    assert minio.return_value.fput_object.call_count == 1
    assert minio.return_value.fput_object.call_args[0][0] == 'bucket'
    assert minio.return_value.fput_object.call_args[0][1].endswith('.tar.gz')
    assert '/' not in minio.return_value.fput_object.call_args[0][1]
    assert re.match(r'/.*/.*\.tar\.gz', minio.return_value.fput_object.call_args[0][2]) is not None

    assert tarfile.open.call_count == 1
    assert tarfile.open.return_value.__enter__.return_value.add.call_count == 3
    tarfile.open.return_value.__enter__.return_value.add.assert_has_calls([
        call('path/to/folder', arcname='', filter=tar_filter),
        call('path2/subfolder2', arcname='subfolder2', filter=tar_filter),
        call('path3/subfolder3', arcname='subfolder3', filter=tar_filter),
    ])

