import time
import yaml
from kubernetes import config, client, utils
from kubernetes.client.configuration import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from typing import List, Dict


class PodStatusException(Exception):
    pass


def setup_k8s_api():
    try:
        config.load_kube_config()
    except config.config_exception.ConfigException:
        config.load_incluster_config()

    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    return client

k8s_client = setup_k8s_api()
v1_api = k8s_client.api.core_v1_api.CoreV1Api()

def create_pod(pod_manifest, namespace):
    resp = v1_api.create_namespaced_pod(body=pod_manifest, namespace=namespace)

    generated_name = resp.metadata.name

    while True:
        try:
            resp = v1_api.read_namespaced_pod(name=generated_name, namespace=namespace)
        except ApiException as e:
            pass

        if resp.status.phase != 'Pending':
            break
        time.sleep(1)
    return resp.metadata.name

def report_pod_status(pod_name, namespace, results):
    while True:
        try:
            resp = v1_api.read_namespaced_pod(name=pod_name, namespace=namespace)

            if resp.status.phase == 'Succeeded':
                results.append([None, True])
                break

            if resp.status.phase == 'Failed':
                image_name = resp.metadata.labels.get('image_name')

                logs = v1_api.read_namespaced_pod_log(pod_name, namespace)

                message = 'Failed while building container image: %s' % image_name

                if logs:
                    message += '\nLogs:\n%s' % logs

                results.append([message, False])
                break

        #TODO: Improve exception handling
        except Exception as e:
            results.append([e, False])
