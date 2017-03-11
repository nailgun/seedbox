import os

basedir = os.path.dirname(__file__)
cachedir = os.path.join(basedir, 'cache')

# TODO: move this to cluster config (model)
install_etc_hosts = True
k8s_runtime = 'docker'  # or 'rkt'
k8s_pod_network = '10.2.0.0/16'
k8s_service_ip_range = '10.3.0.0/24'
k8s_dns_service_ip = '10.3.0.10'
k8s_hyperkube_tag = 'v1.5.2_coreos.0'

# TODO: move this to node config
root_disk = '/dev/sda'
root_partition = '/dev/sda1'

etcd_client_port = 2379
etcd_peer_port = 2380
k8s_apiserver_insecure_port = 8080
k8s_cluster_domain = 'cluster.local'
cluster_credentials_path = '/etc/ssl/cluster'
ca_cert_path = cluster_credentials_path + '/ca.pem'
node_cert_path = cluster_credentials_path + '/node.pem'
node_key_path = cluster_credentials_path + '/node-key.pem'
