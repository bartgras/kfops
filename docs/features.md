## Design goals & features

The introductory article can give you a better understanding of what Kfops is, how, and what it's trying to solve.
The following list contains additional, some of them being more technical, design goals:

* Rely on "traditional" software development lifecycle best practices.

* Try to be self-sufficient and limit the number of services outside the Kubernetes cluster (e.g., build container images inside the cluster).

* Try to utilize services already installed with Kubeflow.

* Centralize the setup of the most important settings in a single configuration file. More details in [here](user/config).

* Support ["day-2"](https://dzone.com/articles/defining-day-2-operations) operations, where your model has been built and now it has to be maintained and improved. Keep in mind that "day-2" improvements are not only improvements to the model itself but to the whole system like e.g., pipeline, preprocessing, containers or modules/packages used.

* Works best if used with Kubeflow "Team profile": basically, Kubeflow profile (namespace) that is being used to build/run is a "project profile" that other team users should be granted access to. Team profile should have permissions to e.g. access data from the S3 bucket that you are comfortable sharing with all project participants.

* Improve experiment reproducibility by [synchronizing image tags](./admin/image_builder.md#synchronizing-container-image-tag-with-compiled-kubeflow-pipeline) with compiled Kubeflow Pipeline version ID or using Kubeflow Pipeline run ID as the trained model filename.

* Assume that Kubefow Pipelines itself should handle data validation, model evaluation, and validation tasks.

__Other features not mentioned in the introductory article:__

* In-cluster images builder builds images in parallel.

* During model deployment:

	* By default, it will stop deployment if Pull Request is out of date with the base branch. It can be ignored with `/deploy --force` flag.

	* If successfully deployed, it labels PR with "Deployed-to-production" (or "Deployed-to-staging") and removes that label from any PR that had it set previously.

	* Deployment to production will automatically close PR and merge it with the main branch.

