import sys
import os
import yaml
import requests
import logging
from time import sleep
from typing import Callable, Optional, Dict
from requests.exceptions import HTTPError, ConnectTimeout, ConnectionError
from kserve import KServeClient
from kserve import V1beta1InferenceService

from .config import set_config, Config
default_config = set_config()

def read_function_from_file(file_path, function_name='inference_service_instance'):
    sys.path.insert(0, os.path.dirname(file_path))
    try:
        filename = os.path.basename(file_path)

        try:
            module = __import__(os.path.splitext(filename)[0])
        except ModuleNotFoundError as e:
            msg = 'Invalid deployment setup. Make sure config.yaml has ' +\
                  '"inference_service_function_path" set and it is pointing at file ' +\
                  'with function "inference_service_instance" implementation'
            raise ModuleNotFoundError(msg)

        try:
            func = getattr(module, function_name)
        except AttributeError as e:
            msg = 'Invalid deployment setup. Make sure deployment ' +\
                  'function in is called "inference_service_instance"'
            raise AttributeError(msg)
        return func
    finally:
        del sys.path[0]


class IsvcDeployer:
    def __init__(self, run_id: str, namespace: str, config: Config = default_config,
                 sample_input: Optional[Dict] = None):
        self.logger = logging.getLogger('kfops')
        self.config = config                 
        self.isvc_func = read_function_from_file(
            self.config.deployment.inference_service_function_path)
        self.inference_service_name = self.config.deployment.inference_service_name

        self.run_id = run_id
        self.namespace = namespace
        self.sample_input = sample_input

        self._error = None
        self.kfs = KServeClient()

    @property
    def error(self):
        return self._error

    def get_isvc(self, canary_traffic_percent=None):
        try:
            isvc = self.isvc_func(
                name=self.inference_service_name,
                storage_uri='s3://trained-models/%s/' % self.run_id,
                canary_traffic_percent=canary_traffic_percent,
                namespace=self.namespace)
            return isvc
        except TypeError as e:
            error_msg = 'Invalid deployment setup. Make sure your function ' +\
                        '"inference_service_instance" has valid parameters. Exception details: %s'
            raise TypeError(error_msg % e)

    def deploy(self):
        if self.check_isvc_exists():
            self.replace_isvc()
        else:
            isvc = self.get_isvc()
            res = self.kfs.create(isvc, namespace=self.namespace)
            self.wait_ready()

    def replace_isvc(self):
        isvc = self.get_isvc(canary_traffic_percent=0)
        res = self.kfs.replace(self.inference_service_name, isvc)
        self.wait_ready()

        if self.error:
            return

        if self.sample_input:
            self.logger.info('Testing endpoint with sample input: %s' % self.sample_input)

            revision = self.get_latest_revision()
            url = 'http://%s-private.%s.svc.cluster.local/v1/models/%s:predict' % \
                (revision, self.namespace, self.inference_service_name)

            self.logger.info('Test sample input on revision: %s. Endpoint: %s' % (revision, url))

            try:
                resp = requests.post(url, json=self.sample_input)
            except (ConnectionError, ConnectTimeout, HTTPError) as e:
                self._error = 'Error while testing newly deployed model with ' +\
                    'sample data. Exception raised: %s' % e

            if self.error:
                return

            if resp.status_code == 200:
                isvc = self.get_isvc(canary_traffic_percent=100)
                res = self.kfs.replace(self.inference_service_name, isvc)
                self.wait_ready()
            else:
                self._error = 'New model is deployed (with traffic 0%) ' +\
                    'but test sample failed with status: ' +\
                    '%s.<br/>Response: <br/> %s' % (resp.status_code, resp.text)
        else:
            isvc = self.get_isvc(canary_traffic_percent=100)
            res = self.kfs.replace(self.inference_service_name, isvc)
            self.wait_ready()

    def wait_ready(self):
        sleep(10)
        try:
            self.kfs.wait_isvc_ready(
                name=self.inference_service_name, namespace=self.namespace)
        except RuntimeError as r:
            kfs_get = self.kfs.get(
                name=self.inference_service_name, namespace=self.namespace)
            status = yaml.safe_dump(kfs_get['status'])
            # TODO: (In beta release) Add event watch and report it as well
            self._error = 'Error: Timed out waiting for deployment becoming ready. ' +\
                          'InferenceService Status: <br/> <code>%s</code>' % status

    def check_isvc_exists(self):
        try:
            isvcs = self.kfs.get(namespace=self.namespace)
        except RuntimeError as e:
            raise Exception('Error while probing for inference services. Make sure you ' +
                            'created deployment namespaces. Refer to documentation for details.')
        existing_isvcs = [i.get('metadata', {}).get('name') for i in isvcs['items']]
        return self.inference_service_name in existing_isvcs

    def get_latest_revision(self):
        isvc = self.kfs.get(self.inference_service_name, namespace=self.namespace)
        return isvc.get('status', {}).get(
            'components', {}).get('predictor', {}).get('latestCreatedRevision')
