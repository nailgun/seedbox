import os

basedir = os.path.dirname(__file__)
cachedir = os.path.join(basedir, 'cache')

# TODO: move this to cluster config (model)
install_etc_hosts = True
k8s_runtime = 'docker'  # or 'rkt'
k8s_dns_service_ip = '10.3.0.10'

etcd_client_port = 2379
etcd_peer_port = 2380
ca_cert_path = '/etc/ssl/ca.pem'
node_cert_path = '/etc/ssl/node.pem'
node_key_path = '/etc/ssl/private/node-key.pem'
