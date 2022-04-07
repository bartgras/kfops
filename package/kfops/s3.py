import tarfile
import tempfile
import os
import base64
from minio import Minio

from .config import set_config, Config
default_config = set_config()

from .k8s_api import v1_api

def tar_filter(f):
    exclude_files = ['__pycache__']
    for ef in exclude_files:
        if ef in f.name:
            return None
    return f


class MinioManager:
    def __init__(self, bucket, config: Config = default_config):
        self.config = config
        self.client = self._get_client()
        self.bucket = bucket
        self._ensure_bucket_exists()

    def _get_client(self):
        access_key, secret_key, endpoint = self.get_minio_creds()
        return Minio(endpoint, access_key, secret_key, secure=False)

    def get_minio_creds(self):
        mc = self.config.image_builder.minio.credentials
        if mc:
            return mc['access_key'], mc['secret_key'], mc['endpoint']
        else:
            return self._get_cluster_minio_creds()

    def _get_cluster_minio_creds(self):
        def read_data(key):
            return base64.b64decode(secret.data[key]).decode()

        secret = v1_api.read_namespaced_secret('mlpipeline-minio-artifact', namespace='kubeflow')
        endpoint = 'minio-service.kubeflow.svc.cluster.local'
        return read_data('accesskey'), read_data('secretkey'), endpoint

    def _ensure_bucket_exists(self):
        found = self.client.bucket_exists(self.bucket)
        if not found:
            self.client.make_bucket(self.bucket)

    def tgz_upload_folders(self, dockerfile_folder_path, other_folders_path=[]):
        try:
            tmp_file = tempfile.NamedTemporaryFile(suffix='.tar.gz')
            with tarfile.open(tmp_file.name, "w:gz") as tar:

                tar.add(dockerfile_folder_path, arcname='', filter=tar_filter)

                for folder_path in other_folders_path:
                    tar.add(folder_path, arcname=os.path.basename(folder_path), filter=tar_filter)

            filename = os.path.split(tmp_file.name)[1]
            self.client.fput_object(self.bucket, filename, tmp_file.name)
            return filename
        finally:
            tmp_file.close()

    def copy(self, src):
        filename = os.path.split(src)[1]
        self.client.fput_object(self.bucket, filename, src)
