# Kfops

## Introduction

Read the high-level introductory [article](https://medium.com/@bartgras/simplified-mlops-for-kubeflow-with-kfops-785e36a6c5f4).

### Getting started & article tldr;

Kfops is an opinionated [Kubeflow](https://www.kubeflow.org/) "wrapper" to manage your 
pipelines and model deployment with the use of dedicated python package and chatops commands. 
It simplifies and standardizes the Kubeflow-based ML model lifecycle by enforcing the
"single repository per  ML model" rule and the explicit way how it should be configured.
Commands like `/build`, `/build_run` and `/deploy` are executed in the context of the Pull Request.

__Notice:__ Kfops requires "full" Kubeflow deployment (version >= 1.3) and 
[KServe](https://kserve.github.io/website/) to serve models. Check other requirements 
in the [Administrator's guide](admin/intro.md).

For details, check:

* [Commands reference](commands.md)
* [Where does Kfops fit in the MLOps lifecycle](mlops_lifecycle.md)
* [Design goals and features](features.md)

## Installation steps

Refer to [Installation steps](install.md) for details.