import yaml
import os
import pytest
from unittest.mock import patch, Mock
from package.kfops.config import Config, InvalidConfigException
from package.kfops.image_builder import ImageBuilder, KanikoManifestBuilder, ImageBuilderException

from tempfile import NamedTemporaryFile

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

@patch('package.kfops.image_builder.create_pod')
@patch('package.kfops.k8s_api.v1_api')
@patch('package.kfops.image_builder.ImageBuilder.prepare_pod_manifest')
def test_build_images_in_threads_success(prepare_pod_manifests, k8s_api, create_pod):
    prepare_pod_manifests.return_value = 'Pod'
    k8s_api.read_namespaced_pod.return_value.status.phase = 'Succeeded'
    create_pod.return_value = 'Pod name'

    c = Config(validate_files=False, check_files_existence=False, config=config, namespace='my-namespace')
    ib = ImageBuilder(config=c)
    images = ib.build_images(images_tag='asdf')
    
    assert create_pod.call_count == 2
    create_pod.assert_called_with('Pod', 'my-namespace')
    assert images == [[None, True], [None, True]]

@patch('package.kfops.image_builder.create_pod')
@patch('package.kfops.k8s_api.v1_api')
@patch('package.kfops.image_builder.ImageBuilder.prepare_pod_manifest')
def test_build_images_in_threads_error(prepare_pod_manifests, k8s_api, create_pod):
    prepare_pod_manifests.return_value = 'Pod'
    k8s_api.read_namespaced_pod.return_value.status.phase = 'Failed'
    create_pod.return_value = 'Pod name'

    c = Config(validate_files=False, check_files_existence=False, config=config, namespace='my-namespace')
    ib = ImageBuilder(config=c)

    with pytest.raises(ImageBuilderException, match=r'Failed while building container image.*'):
        images = ib.build_images(images_tag='asdf')

kaniko_manifest = '''
apiVersion: v1
kind: Pod
metadata:
  generateName: cluster-image-builder-
  labels:
    name: cluster-image-builder
  #Note: Namespace is applied automatically during Pod creation
spec:
  containers:  
  - name: cluster-image-builder
    image: gcr.io/kaniko-project/executor:latest
    volumeMounts:
    - name: dockerfile-storage
      mountPath: /cache
  restartPolicy: Never
  volumes:
  - name: dockerfile-storage
    persistentVolumeClaim:
      claimName: dockerfile-claim
'''

@patch('package.kfops.image_builder.MinioManager')
def test_configure_kaniko_manifest(minio_manager):
    c = Config(validate_files=False, check_files_existence=False, config=config)

    minio_manager.return_value.get_minio_creds.return_value = ['access_key', 'secret_key', 'endpoint']

    with NamedTemporaryFile(suffix='yaml') as temp_file:
        with open(temp_file.name, 'w') as f:
            f.write(kaniko_manifest)

        kaniko_builder = KanikoManifestBuilder(
          filename='context.tgz', image_name='image1', image_tag='image1-tag',
          config=c, kaniko_manifest_path=temp_file.name)

        manifest = kaniko_builder.build()

        assert manifest['spec']['containers'][0]['args'] == [
            "--dockerfile=Dockerfile",
            '--cache=true',
            '--verbosity=debug',
            "--context=tar:///context/context.tgz",
            "--destination=registry/image1:image1-tag",
            "--insecure"]
        assert manifest['metadata']['labels']['image_name'] == 'image1'

        init_container_commands = '''
            mc alias set minio $MINIO_SERVER_HOST $MINIO_SERVER_ACCESS_KEY $MINIO_SERVER_SECRET_KEY;
            mc cp minio/bucket-name/context.tgz /context;
            '''

        assert 'minio/bucket-name/context.tgz /context' in manifest['spec']['initContainers'][0]['args'][0]

        manifest_env = manifest['spec']['initContainers'][0]['env']
        assert len(manifest_env) == 3
        assert [i['name'] for i in manifest_env if i.get('name') == 'MINIO_SERVER_HOST'] == ['MINIO_SERVER_HOST']
        assert [i['value'] for i in manifest_env if i.get('name') == 'MINIO_SERVER_ACCESS_KEY'] == ['access_key']
        assert [i['value'] for i in manifest_env if i.get('name') == 'MINIO_SERVER_SECRET_KEY'] == ['secret_key']

        assert manifest['spec']['initContainers'][0]['command'] == ['sh', '-c']
        assert manifest['spec']['initContainers'][0]['image'] == 'minio/mc:latest'
        assert manifest['spec']['initContainers'][0]['volumeMounts'][0]['mountPath'] == '/context'
        assert manifest['spec']['initContainers'][0]['volumeMounts'][0]['name'] == 'context-folder'

        assert manifest['spec']['containers'][0]['volumeMounts'][0]['mountPath'] == '/cache'
        assert manifest['spec']['containers'][0]['volumeMounts'][0]['name'] == 'dockerfile-storage'

        assert manifest['spec']['containers'][0]['volumeMounts'][1]['mountPath'] == '/context'
        assert manifest['spec']['containers'][0]['volumeMounts'][1]['name'] == 'context-folder'

        assert manifest['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] == 'dockerfile-claim'

        assert manifest['spec']['volumes'][1]['name'] == 'context-folder'
        assert manifest['spec']['volumes'][1]['emptyDir'] == {}

invalid_pod_kaniko_manifest = '''
apiVersion: v1
kind: Pod
metadata:
  generateName: cluster-image-builder-
spec:
  containers:  
  - name: some
'''

@patch('package.kfops.image_builder.MinioManager')
def test_missing_kaniko_image_in_kaniko_manifest(minio_manager):
    c = Config(validate_files=False, check_files_existence=False, config=config)

    minio_manager.return_value.get_minio_creds.return_value = ['access_key', 'secret_key', 'endpoint']

    with NamedTemporaryFile(suffix='yaml') as temp_file:
        with open(temp_file.name, 'w') as f:
            f.write(invalid_pod_kaniko_manifest)
        
        kaniko_builder = KanikoManifestBuilder(
          filename='context.tgz', image_name='image1', image_tag='image1-tag',
          config=c, kaniko_manifest_path=temp_file.name)

        with pytest.raises(InvalidConfigException, match=r'Kaniko container "cluster-image-builder" not found.'):
            kaniko_builder.build()
