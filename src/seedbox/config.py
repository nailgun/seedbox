import os

dev_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

secret_key = '-'
cachedir = os.path.join(dev_root, 'tmp', 'cache')
database_uri = 'sqlite:///' + os.path.join(dev_root, 'test.db')

etcd_client_port = 2379
etcd_peer_port = 2380
k8s_apiserver_lb_port = 433
k8s_apiserver_secure_port = 6443
k8s_apiserver_insecure_port = 8080
k8s_cluster_domain = 'cluster.local'

cluster_credentials_path = '/etc/ssl/cluster'
ca_cert_path = cluster_credentials_path + '/ca.pem'
node_cert_path = cluster_credentials_path + '/node.pem'
node_key_path = cluster_credentials_path + '/node-key.pem'

k8s_config_path = '/etc/kubernetes'  # don't change. hardcoded in kubelet-wrapper
k8s_manifests_path = k8s_config_path + '/manifests'
k8s_kubeconfig_path = k8s_config_path + '/kubeconfig.yaml'
k8s_cni_path = k8s_config_path + '/cni'
k8s_cni_conf_path = k8s_cni_path + '/net.d'

node_host_rkt_path = '/opt/bin/host-rkt'
node_ca_certificates_path = '/usr/share/ca-certificates'
