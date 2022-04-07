import os
import sys
import yaml
import uuid
import logging
from typing import Type, Callable, List, Optional
from threading import Thread

from .config import set_config, Config, InvalidConfigException
default_config = set_config()

from .k8s_api import create_pod, report_pod_status
from .s3 import MinioManager


class ImageBuilderException(Exception):
    pass

class ImageBuilder:
    '''
    Loads from config.yaml images to be built, prepares pod manifest and uses 
    Kaniko (https://github.com/GoogleContainerTools/) to build (in parallel) and push 
    them to the repository.
    '''
    def __init__(self, config: Config = default_config, kaniko_manifest_path: Optional[str] = None) -> None:
        self.config = config
        self.minio_context_files_bucket_name = self.config.image_builder.minio.context_files_bucket_name
        self.cluster_namespace = self.config.workflow_namespace

    def build_images(self, images_tag: str = None) -> None:
        build_threads: List = []

        if not images_tag:
            images_tag = uuid.uuid4().hex
        results = []
        for image in self.config.image_builder.images:
            pod_manifest = self.prepare_pod_manifest(image, images_tag)
            pod_name = create_pod(pod_manifest, self.cluster_namespace)
            t = Thread(target=report_pod_status, args=(pod_name, self.cluster_namespace, results))
            t.start()
            build_threads.append(t)
        [i.join() for i in build_threads]
        
        for r in results:
            if not r[1]:
                raise ImageBuilderException(r[0])
        return results

    def prepare_pod_manifest(self, image, images_tag: str = None) -> List:
        mm = MinioManager(bucket=self.minio_context_files_bucket_name)
        minio_tgz_path = mm.tgz_upload_folders(
            dockerfile_folder_path=image.dockerfile_folder_path,
            other_folders_path=image.other_folders_path or [])

        kaniko_builder = KanikoManifestBuilder(
            minio_tgz_path, image.name, images_tag, self.config)

        return kaniko_builder.build()


class KanikoManifestBuilder:
    '''
    Loads the kaniko YAML manifest file and configures it with other required 
    from config.yaml and input parameters.
    Returns the modified manifest in json format.

    Parameters:
        filename: Kaniko context file path that contains the dockerfile and other files 
                  required for building the image.
        image_name: Name of the image to be built. Read automatically from the config 
                    file (image_builder.images[*].name).
        image_tag: Tag of the image to be built.
        config: Main config object.
    '''
    def __init__(self, filename, image_name, image_tag, 
        config: Config = default_config, 
        kaniko_manifest_path: Optional[str] = None,
        ) -> None:
        self.logger = logging.getLogger('kfops')
        self.config = config
        self.filename = filename
        self.image_name = image_name
        self.image_tag = image_tag

        self.container_registry_uri = self.config.image_builder.container_registry_uri
        self.minio_context_files_bucket_name = self.config.image_builder.minio.context_files_bucket_name
        self.insecure_registry = self.config.image_builder.insecure

        if kaniko_manifest_path:
            self.kaniko_manifest_path = kaniko_manifest_path
        else:
            self.kaniko_manifest_path = os.path.join(
                os.getcwd(), 'config_files/kaniko-manifest.yaml')

        with open(self.kaniko_manifest_path, 'r') as f:
            try:
                self.pod = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                self.logger.exception(exc)
                raise

    def build(self):
        self.inject_init_container()
        self.configure_main_container()
        return self.pod

    def inject_init_container(self):
        if not self.pod['spec'].get('initContainers'):
            self.pod['spec']['initContainers'] = []
        
        commands = '''
        mc alias set minio $MINIO_SERVER_HOST $MINIO_SERVER_ACCESS_KEY $MINIO_SERVER_SECRET_KEY;
        mc cp minio/%s/%s /context;
        '''
        init_container_args = [commands % (self.minio_context_files_bucket_name, self.filename)]

        mm = MinioManager(bucket=self.minio_context_files_bucket_name)
        access_key, secret_key, endpoint = mm.get_minio_creds()
        init_container_env = [
            {'name': 'MINIO_SERVER_HOST', 'value': "http://%s:9000" % endpoint},
            {'name': 'MINIO_SERVER_ACCESS_KEY', 'value': access_key},
            {'name': 'MINIO_SERVER_SECRET_KEY', 'value': secret_key},
        ]

        self.pod['spec']['initContainers'].append({
            'name': 'pull-context-file',
            'image': 'minio/mc:latest',
            'command': ['sh', '-c'],
            'volumeMounts': [
                {
                    'mountPath': '/context',
                    'name': 'context-folder'
                }
            ],
            'env': init_container_env,
            'args':init_container_args
        })

        if not self.pod['spec'].get('volumes'):
            self.pod['spec']['volumes'] = []

        self.pod['spec']['volumes'].append({
                'name': 'context-folder',
                'emptyDir': {}
        })

        return self.pod

    def configure_main_container(self):
        container_position = [i for i, p in enumerate(self.pod['spec']['containers'])
                             if p.get('image') and 'gcr.io/kaniko-project/executor' in p.get('image')]

        if len(container_position) == 0:
            raise InvalidConfigException('Kaniko container "cluster-image-builder" not found. ' +
                'Make sure your kaniko pod YAML contains container with that name ' +
                'and kaniko image (e.g. gcr.io/kaniko-project/executor:latest).')

        if not self.pod['spec']['containers'][container_position[0]].get('volumeMounts'):
            self.pod['spec']['containers'][container_position[0]]['volumeMounts'] = []
        
        volume_mounts = self.pod['spec']['containers'][container_position[0]]['volumeMounts']
        volume_mounts.append({
            'name': 'context-folder',
            'mountPath': '/context'
        })

        image = "%s/%s:%s" % (self.container_registry_uri, self.image_name, self.image_tag)

        pod_args_overwite = [
            "--dockerfile=Dockerfile",
            '--cache=true',
            '--verbosity=debug',
            "--context=tar:///context/%s" % self.filename,
            "--destination=%s" % image
        ]
        if self.insecure_registry:
            pod_args_overwite.append('--insecure')

        pod_labels = self.pod['metadata'].get('labels')
        if pod_labels:
            self.pod['metadata']['labels']['image_name'] = self.image_name
        else:
            self.pod['metadata']['labels'] = {'image_name': self.image_name}
        
        if not self.pod['spec']['containers'][container_position[0]].get('args'):
            self.pod['spec']['containers'][container_position[0]]['args'] = []

        self.pod['spec']['containers'][container_position[0]]['args'] = pod_args_overwite



    
