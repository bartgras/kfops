import sys
from abc import ABC, abstractmethod
import logging
from typing import Dict, Optional
from .version_control_manager import VersionControlManager


class PipelineError(Exception):
    pass


class Messenger(ABC):
    def __init__(self):
        self.logger = logging.getLogger('kfops')

    @abstractmethod
    def generic_message(self, message: str) -> None:
        'Generic INFO type message'
        pass
    
    @abstractmethod
    def generic_error_message(self, message: str) -> None:
        'Generify ERROR type message'
        pass

    @abstractmethod
    def component_built(self, pipeline_info: Dict, build_only) -> None:
        'Component built message'
        pass

    @abstractmethod
    def pipeline_run(self, run_data: Dict) -> None:
        'Pipeline run message'
        pass

    @abstractmethod
    def pipeline_run_completed(self, run_id: str, run_time: str) -> None:
        'Pipeline run completed message'
        pass


class TerminalMessenger(Messenger):
    def __init__(self):
        super().__init__()
        
    def generic_message(self, message: str) -> None:
        self.logger.info(message)

    def generic_error_message(self, message: str) -> None:
        self.logger.exception(message)
        raise PipelineError(message)

    def component_built(self, pipeline_info: Dict, build_only) -> None:
        self.logger.info('Pipeline compiled successfully.')
        msg = 'Compiled pipeline url: {url}'
        self.logger.info(msg.format(url=pipeline_info['url']))
        if build_only:
            msg = 'Run pipeline is with "kfc run --version-id {version_id}" command.'
            self.logger.info(msg.format(version_id=pipeline_info['version_id']))

    def pipeline_run(self, run_data: Dict) -> None:
        msg = 'Pipeline run started. Details: {url}'
        self.logger.info(msg.format(url=run_data['url']))

        run_params = run_data.get('run_params')
        if run_params:
            params = ['%s:%s' % (k, v) for k, v in run_params.items()]
            self.logger.info("Run parameters:\n", "\n".join(params))

    def pipeline_run_completed(self, run_id: str, run_time: str) -> None:
        msg = 'Pipeline run successfully completed after {run_time}.\nRun ID: {run_id}'
        self.logger.info(msg.format(run_id=run_id, run_time=run_time))



pipeline_build_template = '''
Pipeline compiled successfully. <a href="{url}" target="_blank">Details</a><br/>
<!-- KFOPS_VERSION_ID={version_id} -->
'''

pipeline_run_template = '''
Pipeline run started. <a href="{url}" target="_blank">Details</a>{run_params}
Wait for completion message.
'''

pipeline_run_completed_template = '''
Pipeline run successfully completed after {run_time}.\n
* Type: <code>&#47;deploy</code> to deploy to production model from last pipeline run (in this PR).
* Type: <code>&#47;deploy --run-id={run_id}</code> to deploy to production this particular pipeline run.
* Type: <code>&#47;staging_deploy</code> to deploy to staging model from last pipeline run (in this PR).
* Type: <code>&#47;staging_deploy --run-id={run_id}</code> to deploy to staging this particular pipeline run.\n
<b>Note:</b> Sucessful deployment to production will automatically merge your code with base branch and close the Pull request.
<!-- KFOPS_RUN_ID={run_id} -->
'''


class VersionControlMessenger(Messenger):
    def __init__(self, issue_number: int, vc_manager: VersionControlManager) -> None:
        super().__init__()
        self.issue_number = issue_number
        self.vc_manager = vc_manager

    def generic_message(self, message: str) -> None:
        self.logger.debug(message)
        self.vc_manager.create_comment(message)

    def generic_error_message(self, message: str) -> None:
        self.logger.error(message)
        self.vc_manager.create_comment(message)
        sys.exit(1)

    def component_built(self, pipeline_info: Dict, build_only) -> None:
        body = pipeline_build_template.format(
            url=pipeline_info['url'],
            version_id=pipeline_info['version_id'])

        if build_only:
            body += '<br/>Type: <code>&#47;run</code> to run the compiled pipeline.'

        self.logger.debug(body)
        self.vc_manager.create_comment(body)        

    def pipeline_run(self, run_data: Dict) -> None:
        run_params = run_data.get('run_params')
        if run_params:
            table_template = '\n<table><tr><td>Parameter name</td><td>Parameter value</td></tr>%s</table>\n'
            table_rows = ''.join(['<tr><td>%s</td><td>%s</td></tr>' % (k, v) for k, v in run_params.items()])
            run_params = table_template % table_rows
        else:
            run_params = ''

        body = pipeline_run_template.format(
            url=run_data['url'],
            run_params=run_params)

        self.logger.debug(body)
        self.vc_manager.create_comment(body)                    

    def pipeline_run_completed(self, run_id: str, run_time: str) -> None:
        body = pipeline_run_completed_template.format(
            run_time=run_time,
            run_id=run_id)
        self.logger.debug(body)
        self.vc_manager.create_comment(body)        
