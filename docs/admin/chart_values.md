## Helm chart values

[Helm chart overrides](https://helm.sh/docs/intro/using_helm/#customizing-the-chart-before-installing) are performed in the `./cluster_setup/values_override.yaml` file.

In the most basic format, your helm chart values override file should look like following:

```yaml
kubeflow_url: https://my-kubeflow.com
webhookDomain: https://my-cluster-domain.com # Or if the same location as pipelines: https://my-kubeflow.com
scm:
  github:
    githubRepoOwner: 'my-github-owner'
    githubPatUsername: 'my-github-personal-access-token-username'
repositoriesNames:
  - http://github.com/my-user/my-repo-name
```

### Parameters

__Kubeflow URL__

```yaml
kubeflow_url: <URL>
```
URL where your Kubeflow is installed. 
Your Kubeflow Pipelines should be accessible at http://<kubeflow-url>/pipelines

__Webhook domain__

```yaml
webhookDomain: <URL>
```

SCM (Source Code Management) system will send requests to your webhookDomain's eventEndpoint. 

For example, if webhookDomain is `https://example.com/` and eventEndpoint is `/kfops`
then requests will be sent to `https://example.com/kfops`.

__Event endpoint__

```yaml
eventEndpoint: '/kfops'
```
Endpoint which will be called by your SCM webhook (e.g. https://<your-domain>/kfops )
If not set - default is "/kfops"

__SCM settings__

Github specific settings:

```yaml
scm:
  github:
    githubRepoOwner: '<GITHUB REPO OWNER>'
    githubPatUsername: '<GITHUB PAT>'
```

where:

* `githubRepoOwner` is Github repository owner. Settings required for Github event webhooks and listener

* `githubPatUsername` is the username who created Github's "Personal access token"


__Repositories__

```yaml
repositoriesNames: []
  # - name: '<REPO NAME>'
  #- name: '<ANOTHER REPO NAME>'
```

List of reposities kfops should register webhook and listen to 
In format (e.g. for Github repository):` http://github.com/<repo-owner>/<repo-name>`

__Notice:__ The repository has to already exist on SCM server. Otherwise command `helm install`
will not be able to properly register the webhook. If your repository is not setup 
yet, you can leave the `[]` value. Once your repostory is accessible, fill it in 
and run `helm upgrade ...` command.

__Labels and annotations__

Optional labels and annotations for all resources created by kfops

```yaml 
labels:
  my: label
annotations:
  my: annotation
```