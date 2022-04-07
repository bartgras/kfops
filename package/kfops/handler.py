import os
import sys
import re
import yaml
import json
from kfp import Client
from shutil import copyfile

from .config import set_config, Config
default_config = set_config()

from .pipeline_manager import PipelineBuilder, PipelineRunner
from typing import Dict, Optional

from .kserve_deployer import IsvcDeployer
from .messengers import TerminalMessenger, VersionControlMessenger
from .version_control_manager import GithubManager


class BaseHandler:
    def __init__(self, client: Client, command: str, command_params: Dict = {}, config: Config = default_config) -> None:
        self.command = command
        self.command_params = command_params
        self.client = client
        self.config = config
        self.messenger = None
        if type(self) == BaseHandler:
            print('Do not instantiate BaseHandler directly, use child classes instead.')
            exit(0)

    def exec_command(self):
        if self.command == 'build':
            self.build()
        elif self.command == 'run':
            self.run()
        elif self.command == 'build_run':
            self.build_run()
        elif self.command == 'deploy' or self.command == 'staging_deploy':
            environment = 'production' if self.command == 'deploy' else 'staging'
            self.deploy(environment=environment)

    def build(self, build_only=True):
        pb = PipelineBuilder(client=self.client, config=self.config)
        pipeline_info = pb.build()
        self.messenger.component_built(pipeline_info, build_only=build_only)
        return pipeline_info

    def build_run(self):
        pipeline_info = self.build(build_only=False)
        self.run(version_id=pipeline_info['version_id'])

    def _run(self, version_id):
        self.pipeline_runner = PipelineRunner(client=self.client, config=self.config)
        run_data = self.pipeline_runner.run_pipeline(pipeline_version_id=version_id)
        self.messenger.pipeline_run(run_data=run_data)
        return run_data
    
    def run(self, version_id=None):
        raise NotImplementedError

    def _wait_completed(self, run_data):
        run_id = run_data['run_info'].id
        results = self.pipeline_runner.wait_for_run_completion(run_id)

        if results['run_status'] == 'Failed':
            self.messenger.generic_error_message('Kubeflow pipeline run failed. Check run for defails.')
        else:
            self.messenger.pipeline_run_completed(run_id=run_id, run_time=results['run_time'])


class TerminalHandler(BaseHandler):
    def __init__(self, client: Client, command: str, command_params: Dict = {}, config: Config = default_config) -> None:
        super().__init__(client, command, command_params, config)
        self.messenger = TerminalMessenger()

    def run(self, version_id: Optional[str] = None):
        vid = version_id if version_id else self.command_params.get('version-id')
        if not vid:
            self.messenger.generic_error_message('Missing --version-id')

        run_data = self._run(vid)

        if self.command_params.get('wait-until-complete'):
            self._wait_completed(run_data)


class VersionControlHandler(BaseHandler):
    def __init__(
        self, client: Client, command: str, 
        pr_number: int, VCManager: 'VersionControlManager',
        command_params: Dict = {},
        config: Config = default_config
    ) -> None:

        super().__init__(client, command, command_params, config)
        self.pr_number = pr_number

        self.vc_manager = VCManager(self.pr_number)        
        self.messenger = VersionControlMessenger(
            issue_number=self.pr_number,
            vc_manager=self.vc_manager)

    def run(self, version_id: Optional[str] = None):
        if not version_id:
            version_id = self._extract_vars('VERSION_ID')

            if not version_id:
                self.messenger.generic_error_message(
                    'Could not find pipeline to run. Did you run /build?')

        run_data = self._run(version_id)
        self._wait_completed(run_data)

    def _compare_pr_with_base(self, environment: str):
        if environment != 'production':
            return

        if self.vc_manager.is_pr_diverged():
            self.messenger.generic_error_message(
                '<b>Your Pull Request is out of date with base branch</b><br/>' +\
                'There are changes on the base branch which are not present on current ' +\
                'branch. It is recommended to pull these changes and retrain your model before ' +\
                'deployment. You can ignore that warning with command: ' +\
                '<code>&#47;deploy --force</code>')

    def _extract_vars(self, var_name):
        extracted_vars = self.vc_manager.extract_hidden_variables(
            variables=['VERSION_ID', 'RUN_ID'], prefix='KFOPS')
        return extracted_vars.get(var_name)

    def deploy(self, environment: str):
        run_id = self.command_params.get('run-id')

        if not run_id:
            run_id = self._extract_vars('RUN_ID')

        if not run_id:
            self.messenger.generic_error_message(
                'Could not find trained model. Have you already /build and /run (or /build_run)?')

        if not self.config.deployment:
            self.messenger.generic_error_message(
                'Could not find deployment settings in config.yaml. Stopping deployment.')

        # TODO: Check if RUN ID extist in Kubeflow and report error if doesn't
        namespace = self.config.deployment.get(environment, {}).get('namespace')
        if not namespace:
            self.messenger.generic_error_message(
                'Namespace not defined in deployment settings (config.yaml). Stopping deployment.')

        if not self.command_params.get('force'):
            self._compare_pr_with_base(environment)

        sample_input_path = self.config.deployment.get(
            'pre_deployment_test_sample_input_path')
        if sample_input_path:
            try:
                with open(sample_input_path, 'r') as f:
                    sample_input = json.load(f)
            except FileNotFoundError as e:
                self.messenger.generic_error_message(
                    'Invalid deployment settings. Check pre_deployment_test_sample_input_path in config.yaml. ' +
                    'Stopping deployment. Exception details: %s' % e)
            except json.decoder.JSONDecodeError as e:
                self.messenger.generic_error_message(
                    'Invalid deployment settings. Could not parse JSON file.' +
                    'Check pre_deployment_test_sample_input_path in config.yaml. ' +
                    'Stopping deployment. Exception details: %s' % e)
        else:
            sample_input = None

        deployer = IsvcDeployer(run_id, namespace, config=self.config, sample_input=sample_input)
        deployer.deploy()
        if deployer.error:
            self.messenger.generic_error_message(deployer.error)
        else:
            self.messenger.generic_message(
                'Model from RUN_ID: %s has been successfuly deployed to namespace: %s' %
                (run_id, namespace))
            
            self.vc_manager.add_label('Deployed-to-%s' % namespace)
            
            if environment == 'production':
                if not self.vc_manager.is_pr_mergeable():
                    self.messenger.generic_error_message('PR is not mergeable. Fix merge conflicts and try again.')

                merge_ok, err = self.vc_manager.merge_pr()
                if not merge_ok:
                    self.messenger.generic_error_message('Failed while trying to merge PR: %s' % err)

                close_pr_ok, err = self.vc_manager.close_pr()
                if not close_pr_ok:
                    self.messenger.generic_error_message('Failed while trying to close PR: %s' % err)
