import re
import json
import sys
import logging

def set_logger():
    """
    Configure logger. By default outputed to stdout. 
    Error level and above are outputed to stderr.
    """
    logger = logging.getLogger('kfops')

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    info_handler = logging.StreamHandler(stream=sys.stdout)
    info_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    info_handler.setFormatter(formatter)
    logger.addHandler(info_handler)            

    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.addFilter(lambda record: record.levelno > logging.INFO)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

def convert_parameters_to_dict(parameters):
    '''
    Convert parameters in format a.b.c=d to a dict {'a': {'b': {'c': d}}}
    '''
    d = {}
    for p in parameters:
        if '=' not in p:
            raise ValueError('Parameter %s has invalid format. Use format key=value or key.sub_key=value')        
        k, v = p.split('=')
        k = k.split('.')
        d = dict_set(d, k, v)
    return d

def dict_set(d, keys, value):
    if len(keys) == 1:
        d[keys[0]] = value
    else:
        d[keys[0]] = dict_set(d.get(keys[0], {}), keys[1:], value)
    return d

def merge_parameters(params_list):
    '''
    Converts list of command parameters into dict. 
    If option has argument, it is added to dict as value
    '''
    params = {}
    for i, p in enumerate(params_list):
        if '=' in p:
            k, v = p.split('=')
            params[k.replace('--', '')] = v
        elif i < len(params_list)-1 and '--' in p and '--' not in params_list[i + 1]:
            params[p.replace('--', '')] = params_list[i + 1]
        elif '--' in p:
            params[p.replace('--', '')] = True
    return params

def parse_pr_comment(comment):
    '''
    Parse comment sent from Pull Request
    '''
    comment = comment.replace('\r', '')
    
    commands = ['build_run', 'build', 'run', 'staging_deploy', 'deploy']

    pattern = re.compile(r"^.*?(:?%s)(:?\s|\r?\n?|.+?)$" % "|".join(['/' + c for c in commands]), re.MULTILINE)
    command, command_params = re.findall(pattern, comment)[0]
    command_params = command_params.strip().split()
    params_dict = merge_parameters(command_params)
    command = command.replace('/', '')

    return command, params_dict
