
## Container images builder

### About

Image building takes place when chatops command `/build` (or `/build_run`) has been executed in Pull Request comment. 

Note: the "build" command, apart from buidling docker container images also compiles Kubeflow Pipeline. 
The container image building is optional so if no images are being built, the command will go 
straight to Kubeflow Pipeline compilation.

Container builder uses [Kaniko](https://github.com/GoogleContainerTools/kaniko) to build images inside 
your Kubernetes cluster. Kaniko requires [build context](https://github.com/GoogleContainerTools/kaniko#kaniko-build-contexts)
and Kfops configures and uses MinIO that has been already installed together with Kubeflow.

The setup below assumes that during cluster setup `helm install` command was 
used with `kfops` namespace. Also, make sure you adapt your kaniko registry related 
settings accordingly (details below).

Kaniko Pods (and container images build by it) are executed in the same namespace as the workflows 
initiated by Github chatops commands. If building more than one image, they will be built in parallel and
after last built is finished, it will proceed with compiling the pipeline.

__Important notice:__ in the current version of Kfops package, it is required to configure `kaniko-manifest.yaml` per 
each repository that will build container images inside cluster. Notice that the content of this file will be identical for all
"connected" repositories.

### Configuring container builder Pod

Kaniko Kubernetes based configuration requires Pod manifest. This Pod Manifest should be put 
in `config_files/kaniko-manifest.yaml`. The Pod has to be modified to authenticate to your docker registry.

Steps: 

* Copy the `config_files_templates/kaniko-manifest.yaml` into `config_files/kaniko-manifest.yaml`

     Note: the `kaniko-manifest.yaml` has been copied and adapted from Kaniko documentation, section 
  [Running kaniko in a Kubernetes cluster](https://github.com/GoogleContainerTools/kaniko#running-kaniko-in-a-kubernetes-cluster).
  Make sure you don't remove necessary sections defined in the `kaniko-manifest.yaml` template.

* Depending on the docker registry that you use to store images, appropriate changes have to be made to `kaniko-manifest.yaml`.
  Simply, follow the details in Kaniko documentation, section 
  [Pushing to Different Registries](https://github.com/GoogleContainerTools/kaniko#pushing-to-different-registries).
  

See example setup in [Example Kaniko Pod setup](example_kaniko_setup.md).

#### Image building configuration

Main `config.yaml` contains `image_builder` section where you can configure how images are built.
Section `images` specifies what images should be built.
Each image requires:

* `name` - name that will be given to the container image
* `dockerfile_folder_path` - path to the folder where `Dockerfile` for the image is located

Optional argument `other_folders_path` specifies additional folders that should be copied to the container image 
(folder that can be shared between all containers).

Given following example files structure:

```
containers/
  ⊢ my_image_name/
    ⊢ Dockerfile
    ⊢ requirements.txt
  ⊢ my_second_image_name/
    ⊢ Dockerfile
    ⊢ requirements.txt    
containers_shared_library/ # Optional
  ⊢ my_file_shared_between_containers.py
```

your `images` section should be configured as follows:

```yaml
images:
   - name: my_image
     dockerfile_folder_path: containers/my_image_name
     other_folders_path:
       - containers_shared_library/
   - name: my_second_image
     dockerfile_folder_path: containers/my_second_image_name
     other_folders_path:
       - containers_shared_library/
```

Content of `containers/my_image_name` will be set as `CWD` folder during container build process.
For example, if it contains file `requirements.txt` then Dockerfile can reference it as follows: `ADD requirements.txt requirements.txt`

Content specified in `other_folders_path` will be copied into subfolders e.g.

```yaml
other_folders_path:
  - containers_shared_library
```
can be referenced in Dockerfile as `COPY containers_shared_library /mnt/containers_shared_library`

