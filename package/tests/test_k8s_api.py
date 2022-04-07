import yaml
import os
import pytest
from unittest.mock import patch, Mock, call
from munch import munchify
import re

from package.kfops.config import Config
from package.kfops.k8s_api import create_pod, report_pod_status, PodStatusException

pod_manifest = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "name": "test-pod",
        "labels": {
            "app": "test-pod",
            "image_name": "test-image"
        }
    },
    "spec": {
        "containers": [
            {
                "name": "test-pod",
                "image": "test-image",
            }
        ]
    }
}

created_pod_status_success = {
    "status": {
        "phase": "Succeeded",
    }
}

created_pod_manifest = dict({**pod_manifest, **created_pod_status_success})


@patch('package.kfops.k8s_api.v1_api.read_namespaced_pod', return_value=munchify(created_pod_manifest))
@patch('package.kfops.k8s_api.v1_api.create_namespaced_pod', return_value=munchify(pod_manifest))
def test_create_pod(v1_api_create, v1_api_read):
    namespace = 'test-namespace'
    created_pod = create_pod(pod_manifest, namespace)
    v1_api_read.assert_called_once_with(name='test-pod', namespace=namespace)
    assert created_pod == 'test-pod'


@patch('package.kfops.k8s_api.v1_api.read_namespaced_pod', return_value=munchify(created_pod_manifest))
def test_report_pod_status_success(v1_api_read): 
    namespace = 'test-namespace'
    pod_name = 'test-pod'
    results = []
    report_pod_status(pod_name, namespace, results)
    assert results == [[None, True]]

created_pod_status_failure = {
    "status": {
        "phase": "Failed",
    }
}

pod_manifest_failure = dict({**pod_manifest, **created_pod_status_failure})

@patch('package.kfops.k8s_api.v1_api.read_namespaced_pod_log', return_value='Error from pod')
@patch('package.kfops.k8s_api.v1_api.read_namespaced_pod', return_value=munchify(pod_manifest_failure))
def test_report_pod_status_failure(v1_api_read, v1_api_read_log):
    namespace = 'test-namespace'
    pod_name = 'test-pod'
    results = []

    report_pod_status(pod_name, namespace, results)
    assert results[0][1] == False
    assert results[0][0] == 'Failed while building container image: test-image\nLogs:\nError from pod'