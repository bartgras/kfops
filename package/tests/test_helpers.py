import pytest
from package.kfops.helpers import convert_parameters_to_dict, parse_pr_comment

def test_convert_parameters_to_dict():
    assert convert_parameters_to_dict(['pipeline_name=name', 'pipeline_args.p1=v1', 'pipeline_args.p2=v2']) == \
        {'pipeline_name': 'name', 'pipeline_args': {'p1': 'v1', 'p2': 'v2'}}
    assert convert_parameters_to_dict(['pipeline.name.key1=val1', 'pipeline.name.key2=val2']) == \
        {'pipeline': {'name': {'key1': 'val1', 'key2': 'val2'}}}

@pytest.mark.parametrize('comment, expected_command, expected_params', [
    ('/build_run', 'build_run', {}),
    (' /build_run ', 'build_run', {}),
    ('/build_run \ncomment in next line', 'build_run', {}),
    ('/build_run \r\ncomment in next line', 'build_run', {}),
    ('/deploy --run-id=123 --force', 'deploy', {'run-id': '123', 'force': True}),
    ('/deploy --force --run-id 123', 'deploy', {'run-id': '123', 'force': True}),
    ('/deploy --force --run-id 123 --force', 'deploy', {'run-id': '123', 'force': True}),
    ('First line\n/deploy --run-id=123\nLast line', 'deploy', {'run-id': '123'}),
    ('First line\r\n/deploy --run-id=123\r\nLast line', 'deploy', {'run-id': '123'}),
])
def test_parse_pr_comment(comment, expected_command, expected_params):
    command, params = parse_pr_comment(comment)
    assert command == expected_command
    assert params == expected_params
