{{- define "tdse-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "tdse-service.labels" -}}
app.kubernetes.io/name: {{ include "tdse-service.name" . }}
app.kubernetes.io/part-of: tdse
app.kubernetes.io/managed-by: Helm
{{- end -}}
