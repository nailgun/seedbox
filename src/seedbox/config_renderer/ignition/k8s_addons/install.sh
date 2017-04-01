#!/bin/bash
set -e

baseurl="http://127.0.0.1:{{ config.k8s_apiserver_insecure_port }}/"

safeget() {
    curl --fail --silent --show-error $@
}

safepost() {
    curl --fail --silent --show-error -H 'Content-Type: application/yaml' --data-binary $@
}

echo "Waiting for Kubernetes API..."
until safeget "${baseurl}version"; do
    sleep 5
done

echo "K8S addon: ClusterRoleBinding for default ServiceAccount in kube-system namespace"
safepost @kube-system-default-sa.yaml "${baseurl}apis/rbac.authorization.k8s.io/v1alpha1/clusterrolebindings"

echo "K8S addon: DNS"
safepost @kube-dns-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"
safepost @kube-dns-svc.yaml "${baseurl}api/v1/namespaces/kube-system/services"
safepost @kube-dns-autoscaler-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"

echo "K8S addon: Heapster"
safepost @heapster-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"
safepost @heapster-svc.yaml "${baseurl}api/v1/namespaces/kube-system/services"

echo "K8S addon: Dashboard"
safepost @kube-dashboard-deployment.yaml "${baseurl}apis/extensions/v1beta1/namespaces/kube-system/deployments"
safepost @kube-dashboard-svc.yaml "${baseurl}api/v1/namespaces/kube-system/services"
