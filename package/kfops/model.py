import kfp
from kfp.onprem import use_k8s_secret
from kubernetes.client.models import V1EnvVar

def materialize_model(model):
    # TODO: Change URL to component pointing at file in kfops repo
    materialize_model_op = kfp.components.load_component_from_url(
        'https://gist.githubusercontent.com/bartgras/203f1329dad7a8d83a5b04371c5a4fed/raw/b1c6f668f0b880f8202d3f6abde047b6714295b0/component.yaml')

    task = materialize_model_op(model=model)

    task.apply(
        use_k8s_secret(
            secret_name='mlpipeline-minio-artifact',
            k8s_secret_key_to_env={
                'secretkey': 'MINIO_SECRET_KEY',
                'accesskey': 'MINIO_ACCESS_KEY'
            },
        )
    )
    env_run_id = V1EnvVar(name='RUN_ID', value=kfp.dsl.RUN_ID_PLACEHOLDER)
    task.add_env_variable(env_run_id)

    return task
