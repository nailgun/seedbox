#!/bin/bash
set -e

baseurl="http://127.0.0.1:{{ config.k8s_apiserver_insecure_port }}/"

strictget() {
    curl --fail --silent --show-error $@
}

strictpost() {
    curl --fail --silent --show-error -H 'Content-Type: application/yaml' --data-binary $@
}

echo "Waiting for Kubernetes API..."
until strictget "${baseurl}version"; do
    sleep 5
done

echo "K8S addon: ClusterRoleBinding for default ServiceAccount in kube-system namespace"
strictpost @kube-system-default-sa.yaml "${baseurl}apis/rbac.authorization.k8s.io/v1alpha1/clusterrolebindings"

echo "K8S addon: DNS"
strictpost @kube-dns-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"
strictpost @kube-dns-svc.yaml "${baseurl}api/v1/namespaces/kube-system/services"
strictpost @kube-dns-autoscaler-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"

echo "K8S addon: Heapster"
strictpost @heapster-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"
strictpost @heapster-svc.yaml "${baseurl}api/v1/namespaces/kube-system/services"

echo "K8S addon: Dashboard"
strictpost @kube-dashboard-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"
strictpost @kube-dashboard-svc.yaml "${baseurl}api/v1/namespaces/kube-system/services"
