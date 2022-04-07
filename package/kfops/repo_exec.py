"""
Run handler from repository

Usage:
    repo_exec <pull_request_comment>

Supported pull_request_comment commands:
    /run
    /build
    /build_run
    /deploy
    /staging_deploy

Supported optional pull_request_comment command parameters if command is run from PR comment:
    /deploy --run-id=<run_id> --force
    /staging_deploy --run-id=<run_id> --force
"""

import os
import sys
import logging
from kfp import Client

from .config import ConfigOverride
from .helpers import set_logger

PR_NUMBER = os.environ.get('PR_NUMBER')
RUN_ENV = os.environ.get('RUN_ENV')
KUBEFLOW_URL = os.environ.get('KUBEFLOW_URL')
WORKFLOW_NAMESPACE = os.environ.get('WORKFLOW_NAMESPACE')

def main():
    set_logger()
    logger = logging.getLogger('kfops')

    args = sys.argv[1:]
    if len(args) == 0:
        logger.error('Usage: repo_exec "<pull_request_comment>". \n' +\
            'Notice: Use double quotes if command contains spaces.\n' +\
            'Example: repo_exec "/deploy --run-id=123"')
        sys.exit(1)
    pr_comment = args[0]

    from .helpers import parse_pr_comment
    command, command_params = parse_pr_comment(pr_comment)

    config = ConfigOverride(namespace=WORKFLOW_NAMESPACE)

    pipelines_url = "%s/pipeline/" % KUBEFLOW_URL
    client = Client(ui_host=pipelines_url)

    from .handler import VersionControlHandler
    from .version_control_manager import GithubManager, DevelopmentDummyManager

    if RUN_ENV == 'development':
        manager = DevelopmentDummyManager
    else:
        manager = GithubManager

    github_handler = VersionControlHandler(
        client=client, 
        command=command, command_params=command_params,
        pr_number=PR_NUMBER, config=config,
        VCManager=manager)
    github_handler.exec_command()

if __name__ == '__main__':
    main()