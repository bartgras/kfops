import yaml
import os
from munch import munchify
from pykwalify.core import Core, log as pykwalify_log
from pykwalify.errors import SchemaError
from collections import namedtuple
import logging

from .helpers import convert_parameters_to_dict


class InvalidConfigException(Exception):
    pass


class ConfigMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


Image = namedtuple('Image', [
    'name',
    'dockerfile_folder_path',
    'other_folders_path'
])


MinioConfig = namedtuple('MinioConfig', [
    'context_files_bucket_name',
    'credentials'
])


class ImageBuilderConfig:
    def __init__(self, image_builder_config):
        self.conf = image_builder_config

    @property
    def container_registry_uri(self):
        return self.conf.get('container_registry_uri')

    @property
    def insecure(self):
        return self.conf.get('insecure', False)

    @property
    def images(self):
        images = []
        for container_image in self.conf.get('images', []):
            images.append(Image(
                name=container_image['name'],
                dockerfile_folder_path=container_image['dockerfile_folder_path'],
                other_folders_path=container_image.get('other_folders_path', [])
            ))
        return images

    @property
    def minio(self):
        mc = self.conf.get('minio', {})
        return MinioConfig(
            context_files_bucket_name=mc.get('context_files_bucket_name') or 'image-build-artifacts',
            credentials=munchify(mc['credentials']) if mc.get('credentials') else None
        )


class Config(object, metaclass=ConfigMeta):
    '''
    Wraps main "config.yaml" settings into a class. Provides sensible defaults.
    Note, additional (field requirement validation) is performed using "config_schema.yaml".
    '''
    def __init__(
        self, validate_files=True, check_files_existence=True,
        config=None, config_file_path=None,
        config_schema_path=None, namespace=None
    ):
        self.logger = logging.getLogger('kfops')

        if config_file_path and config:
            raise InvalidConfigException('Either pass config dict or config file path.')

        self.config_file_path = config_file_path if config_file_path \
            else "./config_files/config.yaml"

        if check_files_existence:
            self.check_config_files_existence()


        if not config:
            self.config = self.load_config_from_file()
        else:
            self.config = config

        if config_schema_path:
            self.schema_file = config_schema_path
        else:
            package_path = os.path.dirname(os.path.realpath(__file__))
            self.schema_file = os.path.join(package_path, 'config_schema.yaml')

        if validate_files:
            self.validate_config_files()
        
        self._workflow_namespace = namespace

        self.set_pipeline()

    def check_config_files_existence(self):
        def check_project_files(rel_path):
            if not os.path.exists(os.path.join(project_path, rel_path)):
                msg = 'Missing config file in %s, Check documentation for details.' % rel_path
                raise InvalidConfigException(msg)

        project_path = os.getcwd()

        check_project_files('config_files/config.yaml')
        check_project_files('config_files/kaniko-manifest.yaml')

    def validate_config_files(self):
        c = Core(source_file=self.config_file_path, schema_files=[self.schema_file])
        pykwalify_log.disabled = True
        c.validate(raise_exception=False)

        if c.validation_errors:
            msg = 'Invalid config.yaml. Validation errors:\n-%s' % '\n- '.join(c.validation_errors)
            raise InvalidConfigException(msg)

    def load_config_from_file(self, config_file_path=None):
        try:
            with open(config_file_path or self.config_file_path, 'r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as exc:
            self.logger.exception(exc)
            raise

    def set_pipeline(self):
        self._pipeline = munchify(self.config.get('pipeline', {}))

        execution_mode = self._pipeline.get('pipeline_execution_mode')
        if execution_mode and execution_mode not in ['V1_LEGACY', 'V2_COMPATIBLE', 'V2_ENGINE']:
            msg = 'Invalid Kubeflow Pipelines execution mode. ' \
                'Valid choices are: V1_LEGACY, V2_COMPATIBLE, V2_ENGINE'
            raise InvalidConfigException(msg)
        else:
            self._pipeline['pipeline_execution_mode'] = 'V2_COMPATIBLE'

    @property
    def pipeline(self):
        return self._pipeline

    @property
    def repository(self):
        return munchify(self.config['repository'])

    @property
    def deployment(self):
        return munchify(self.config['deployment']) if self.config.get('deployment') else None

    @property
    def workflow_namespace(self):
        if self._workflow_namespace:
            return self._workflow_namespace
        else:
            return 'kfops'

    @property
    def image_builder(self):
        if self.config.get('image_builder'):
            return ImageBuilderConfig(self.config['image_builder'])


class ConfigOverride(Config):
    def __init__(self, args_override=None, config_file_path_override=None, *args, **kwargs):
        self.args_override = args_override
        self.config_file_path_override = config_file_path_override
        super().__init__(*args, **kwargs)

        if self.config_file_path_override:
            self.override_from_file()

        if self.args_override:
            self.override_from_args()

    def override_from_file(self):
        self.logger.debug('Config file path override: %s' % self.config_file_path_override)
        override = self.load_config_from_file(self.config_file_path_override)
        if override.get('pipeline'):
            p = self.pipeline
            p.update(override['pipeline'])
            self._pipeline = munchify(p)

    def override_from_args(self):
        override = convert_parameters_to_dict(self.args_override)
        p = self.pipeline
        p.update(override)
        self._pipeline = munchify(p)


def set_config():
    # Hack for unit tests
    try:
        return ConfigOverride()
    except:
        return None