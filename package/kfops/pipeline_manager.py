from datetime import datetime
from tempfile import NamedTemporaryFile

import kfp
from kfp import dsl
from kfp.compiler.main import compile_pyfile

from .config import set_config
default_config = set_config()

from .config import Config
from .image_builder import ImageBuilder


class PipelineRunner:
    def __init__(self, client, config: Config = default_config):
        self.config = config
        self.client = client

    def run_pipeline(self, pipeline_version_id):
        experiments = self.client.list_experiments(
            namespace=self.config.pipeline.namespace,
            #TODO: Switch to pagination
            page_size=1000 
        ).experiments

        if experiments:
            namespace_experiments = [e.name for e in experiments]
        else:
            namespace_experiments = []
        experiment_name = self.config.pipeline.experiment_name

        if experiment_name not in namespace_experiments:
            self.client.create_experiment(
                experiment_name,
                description=self.config.pipeline.description,
                namespace=self.config.pipeline.namespace)

        experiment = self.client.get_experiment(
            experiment_name=experiment_name,
            namespace=self.config.pipeline.namespace)

        run_params = self.config.pipeline.get('pipeline_args') or {}
        if not run_params.get('version_id'):
            run_params['version_id'] = pipeline_version_id

        run_info = self.client.run_pipeline(
            experiment_id=experiment.id,
            job_name='%s (%s)' % (self.config.pipeline.name, experiment_name),
            version_id=pipeline_version_id,
            params=run_params)

        return {
            'url': '%s/#/runs/details/%s' % (
                self.client._get_url_prefix(), run_info.id),
            'run_info': run_info,
            'run_params': run_params
        }

    def wait_for_run_completion(self, run_id):
        # TODO: Improve timeout handling
        run_info = self.client.wait_for_run_completion(run_id, timeout=60 * 60 * 24 * 7)
        run_time = (run_info.run.finished_at - run_info.run.created_at).seconds

        if run_time > 60:
            run_time = '%s min(s)' % (run_time // 60)
        else:
            run_time = '%s seconds' % run_time

        return {'run_time': run_time, 'run_status': run_info.run.status}


class PipelineBuilder:
    def __init__(self, client, config: Config = default_config):
        self.config = config
        self.client = client

    def build(self):
        self.pipeline_id = self.client.get_pipeline_id(name=self.config.pipeline.name)
        self.compiled_output_file = None

        try:
            self._compile_pipeline()
            uploaded_pipeline = self._upload_kubeflow()
            self._build_images(uploaded_pipeline['version_id'])
            return uploaded_pipeline
        finally:
            self.compiled_output_file.close()

    def _build_images(self, image_tag: str):
        if self.config.image_builder:
            ib = ImageBuilder(self.config)
            ib.build_images(image_tag)

    def _compile_pipeline(self):
        self.compiled_output_file = NamedTemporaryFile(
            suffix='.zip')

        execution_mode = self.config.pipeline.pipeline_execution_mode
        execution_mode_mapping = {
            'V1_LEGACY': kfp.dsl.PipelineExecutionMode.V1_LEGACY, 
            'V2_COMPATIBLE': kfp.dsl.PipelineExecutionMode.V2_COMPATIBLE,
            'V2_ENGINE': kfp.dsl.PipelineExecutionMode.V2_ENGINE
        }

        try:
            compile_pyfile(
                pyfile=self.config.pipeline.pipeline_path,
                function_name=self.config.pipeline.pipeline_function_name
                if self.config.pipeline.get('pipeline_function_name') else None,
                output_path=self.compiled_output_file.name,
                type_check=True,
                mode=execution_mode_mapping[execution_mode])
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError('Invalid pipeline function setup. Check your config.yaml : %s' % e)

    def _upload_kubeflow(self):
        if self.pipeline_id:
            version_info = self.client.upload_pipeline_version(
                self.compiled_output_file.name,
                pipeline_name=self.config.pipeline.name,
                pipeline_version_name='Version %s' % datetime.now().strftime('%d %h %H:%M:%s, %Y'))

            return {
                'url': '%s/#/pipelines/details/%s/version/%s' % (
                    self.client._get_url_prefix(), self.pipeline_id,
                    version_info.id),
                'pipeline_id': self.pipeline_id,
                'version_id': version_info.id,
                'info': version_info
            }
        else:
            pipeline_info = self.client.upload_pipeline(
                self.compiled_output_file.name,
                pipeline_name=self.config.pipeline.name,
                description=self.config.pipeline.description)

            return {
                'url': '%s/#/pipelines/details/%s' % (
                    self.client._get_url_prefix(), pipeline_info.id),
                'pipeline_id': pipeline_info.id,
                'version_id': pipeline_info.default_version.id,
                'info': pipeline_info
            }
