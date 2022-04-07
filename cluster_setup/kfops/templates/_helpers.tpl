{{- define "name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "chartName" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "selectorLabels" -}}
app.kubernetes.io/name: {{ include "name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "labels" -}}
helm.sh/chart: {{ include "chartName" . }}
{{ include "selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "additionalLabels" -}}
{{- range $key, $value := .Values.labels -}}
{{ $key }}: {{ $value }}
{{- end }}
{{- end }}

{{- define "annotations" -}}
{{- if .Values.annotations -}}
annotations:
{{- range $key, $value := .Values.annotations -}}
  {{ $key }}: {{ $value }}
{{- end -}}
{{- end -}}
{{- end -}}


{{- define "kfops.devVolumes" -}}
{{- if .Values.development.developmentVolumeMount }}
{{- range .Values.development.developmentVolumeMount }}
- name: {{ .name }}
  mountPath: {{ .mountPath }}
{{- end }}
{{- end }}
{{- end }}


{{- define "workflow.Envs" -}}
- name: KUBEFLOW_URL
  valueFrom:
    configMapKeyRef:
      name: kfops-vars
      key: KUBEFLOW_URL
- name: WORKFLOW_NAMESPACE
  valueFrom:
    configMapKeyRef:
      name: kfops-vars
      key: WORKFLOW_NAMESPACE      
{{ if .Values.scm.github -}}
- name: GITHUB_TOKEN
  valueFrom:
    secretKeyRef:
      name: scm-access-webhook-token
      key: token
- name: GITHUB_PAT_USERNAME
  valueFrom:
    configMapKeyRef:
      name: kfops-vars
      key: GITHUB_PAT_USERNAME            
{{- else if .Values.scm.gitlab }}
# Define for Gitlab
{{- end }}


{{- if eq .Values.environment "development" -}}
- name: RUN_ENV
  value: development
{{- end }}
{{- end }}


{{- define  "eventSource.scm" }}
{{- if .Values.scm.github }}
github:
  kfops:
    repositories:
      - owner: {{ .Values.scm.github.githubRepoOwner }} 
        names:
          {{- range .Values.repositoriesNames }}
          - {{ .name | quote }}
          {{- end }}
    webhook:
      endpoint: {{ .Values.eventEndpoint }}
      port: "12000"
      method: POST
      url: {{ required "Value 'webhookDomain' is required." .Values.webhookDomain }}
    events: 
      - issue_comment 
    apiToken:
      name: scm-access-webhook-token
      key: token
    insecure: false
    active: true
    contentType: json
{{- else if .Values.scm.gitlab }}
gitlab: {}
# Define for Gitlab
{{- end }}
{{- end }}


{{- define "configMap.values" -}}
KUBEFLOW_URL: {{ required "Value 'kubeflow_url' is required." .Values.kubeflow_url }}
WORKFLOW_NAMESPACE: {{ .Release.Namespace }}
{{- if .Values.scm.github }}
GITHUB_PAT_USERNAME: {{ .Values.scm.github.githubPatUsername }}
{{- else if .Values.scm.gitlab }}
gitlab: {}
# Define for Gitlab
{{- end }}
{{- end }}


{{- define "sensor.parameters" }}
{{- if .Values.scm.github }}
- src:
    dependencyName: kfops-dep
    dataKey: body.comment.body
  dest: spec.arguments.parameters.0.value 
- src:
    dependencyName: kfops-dep
    dataKey: body.issue.number
  dest: spec.arguments.parameters.1.value
- src:
    dependencyName: kfops-dep
    dataKey: body.repository.owner.login
  dest: spec.arguments.parameters.2.value
- src:
    dependencyName: kfops-dep
    dataKey: body.repository.name
  dest: spec.arguments.parameters.3.value
{{- else if .Values.scm.gitlab }}
# Define for Gitlab
{{- end }}
{{- end }}


{{- define "sensor.filterPath" }}
{{- if .Values.scm.github }}
path: body.comment.body
{{- else if .Values.scm.gitlab }}
# Define for Gitlab
{{- end }}
{{- end }}