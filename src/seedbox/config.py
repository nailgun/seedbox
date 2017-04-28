import os

dev_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

secret_key = os.environ.get('SECRET_KEY', '-')
database_uri = os.environ.get('DATABASE_URI', 'sqlite:///' + os.path.join(dev_root, 'test.db'))

default_coreos_channel = 'stable'
default_coreos_version = '1353.7.0'  # 'current' is also applicable
default_k8s_hyperkube_tag = 'v1.5.6_coreos.0'
k8s_hyperkube_image = 'quay.io/coreos/hyperkube'
default_k8s_pod_network = '10.2.0.0/16'
default_k8s_service_network = '10.3.0.0/24'
default_k8s_admission_control = 'NamespaceLifecycle,LimitRanger,ServiceAccount,ResourceQuota'
default_etcd_version = 3
default_boot_images_base_url = 'http://{}.release.core-os.net/amd64-usr/{}/'.format(default_coreos_channel,
                                                                                    default_coreos_version)

default_root_disk = '/dev/sda'
default_linux_consoles = 'tty0,ttyS0'

etcd_client_port = 2379
etcd_peer_port = 2380
etcd3_image_tag = 'v3.1.5'
k8s_apiserver_secure_port = 6443
k8s_apiserver_insecure_port = 8080
k8s_cluster_domain = 'cluster.local'

cluster_credentials_path = '/etc/ssl/cluster'
ca_cert_filename = 'ca.pem'
node_cert_filename = 'node.pem'
node_key_filename = 'node-key.pem'
ca_cert_path = cluster_credentials_path + '/' + ca_cert_filename
node_cert_path = cluster_credentials_path + '/' + node_cert_filename
node_key_path = cluster_credentials_path + '/' + node_key_filename

k8s_config_path = '/etc/kubernetes'  # don't change. hardcoded in kubelet-wrapper
k8s_secrets_path = k8s_config_path + '/secrets'
k8s_service_account_public_key_path = k8s_secrets_path + '/service-account.pub'
k8s_service_account_private_key_path = k8s_secrets_path + '/service-account.priv'
k8s_manifests_path = k8s_config_path + '/manifests'
k8s_kubeconfig_path = k8s_config_path + '/kubeconfig.yaml'
k8s_cni_conf_path = k8s_config_path + '/cni/net.d'

node_ca_certificates_path = '/usr/share/ca-certificates'

aci_proxy_ca_cert_path = '/etc/ssl/certs/aci-proxy-ca.pem'
