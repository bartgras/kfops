"""
Build/Run experiment from command line.

Usage:
    kfc build --kubeflow-url=<url> [--set <key-val>...]
        [-n NAMESPACE|--namespace NAMESPACE] 
        [-o PATH|--config-override PATH]
    kfc build_run --kubeflow-url=<url> [--set <key-val>...] 
        [-n NAMESPACE|--namespace NAMESPACE] 
        [-o PATH|--config-override PATH] [-w|--wait-until-complete]
    kfc run --kubeflow-url=<url> --version-id VERSION_ID [--set <key-val>...] 
        [-n NAMESPACE|--namespace NAMESPACE] 
        [-o PATH|--config-override PATH] [-w|--wait-until-complete]
    kfc [-h | --help]

Options:
    --kubeflow-url=<url>                  Location of your Kubeflow installation.
    -n NAMESPACE, --namespace NAMESPACE   Kubernetes namespace where Kfops has been setup. If not provided, 
                                          defaults to "kfops".
    --version-id VERSION_ID               Version ID of the previously built pipeline.
    -w --wait-until-complete              Keeps the script running until run finished or failed.
    -o PATH, --config-override PATH       Path to a config file that overrides "pipeline" options from 
                                          default config.yaml settings.
    --set                                 Override "pipeline" options directly from the command line. Accepts 
                                          multiple key-value pairs.
                                          e.g. --set experiment_name=my-experiment pipeline_args.parameter1=value1
                                          Note that --set takes precedence over --config-override.

Options:
    -h --help                             Show this help message and exit
"""

import os
from docopt import docopt
from kfp import Client

from .config import ConfigOverride, Config
import logging
from .helpers import set_logger
logger = logging.getLogger('kfops')

def init_config():
    '''
    Initializes singleton config object that is going to be used throughout the application.
    '''
    args = docopt(__doc__)
    args_override = args['<key-val>'] if args['--set'] and len(args['<key-val>']) > 0 else []

    config_file_path_override = args['--config-override'] if args['--config-override'] else None

    params = {
        'args_override': args_override, 'config_file_path_override': config_file_path_override
    }

    if args.get('--namespace'):
        params['namespace'] = args.get('--namespace')

    ConfigOverride(**params)

def adapt_args(args):
    'Modifies docopt args to conform with handler inputs'
    valid_commands = ['build', 'build_run', 'run']

    command = [i for i in args if args[i] and i in valid_commands]
    if len(command) == 0:
        logger.error('Invalid command')
        exit(1)
    command = command[0]

    command_params = {k.replace('--', ''):v for k, v in args.items()}
    return command, command_params

def main():
    set_logger()
    init_config()

    # Hack, singleton config has to be initialized before importing other modules
    from .handler import TerminalHandler

    args = docopt(__doc__)

    if not any(args.values()):
        print("Type --help for usage details")
        exit(1)

    pipelines_url = "%s/pipeline/" % args['--kubeflow-url']
    client = Client(ui_host=pipelines_url)

    command, command_params = adapt_args(args)
    handler = TerminalHandler(client=client, command=command, command_params=command_params)
    handler.exec_command()

if __name__ == '__main__':
    main()
