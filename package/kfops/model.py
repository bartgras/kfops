import kfp
from kfp.onprem import use_k8s_secret
from kubernetes.client.models import V1EnvVar

def materialize_model(model):
    materialize_model_op = kfp.components.load_component_from_url(
        'https://raw.githubusercontent.com/bartgras/kfops/18c4c48af714fde8dd8ee324f49f757e05a9fb6d/components/materialize_model_component.yaml')

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
