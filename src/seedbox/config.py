import os

app_root = os.path.dirname(os.path.dirname(__file__))
dev_root = os.path.dirname(os.path.dirname(app_root))

secret_key = os.environ.get('SECRET_KEY', '-')
allow_insecure_transport = os.environ.get('ALLOW_INSECURE_TRANSPORT', '1').lower() in ('1', 'true', 'yes')
admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
database_uri = os.environ.get('DATABASE_URI', 'sqlite:///' + os.path.join(dev_root, 'test.db'))
reverse_proxy_count = int(os.environ.get('REVERSE_PROXY_COUNT', 0))

update_check_interval_sec = 24 * 60 * 60  # 24 hours
update_state_file = os.environ.get('UPDATE_STATE_FILE', '/tmp/seedbox.json')

admin_base_url = '/admin'

default_coreos_channel = 'stable'
default_coreos_version = '1353.7.0'  # 'current' is also applicable
default_coreos_images_base_url = 'http://{channel}.release.core-os.net/amd64-usr/{version}/'
etcd_image = 'quay.io/coreos/etcd'
default_etcd_image_tag = 'v3.1.7'
k8s_hyperkube_image = 'quay.io/coreos/hyperkube'
default_k8s_hyperkube_tag = 'v1.6.2_coreos.0'
default_k8s_pod_network = '10.2.0.0/16'
default_k8s_service_network = '10.3.0.0/24'
default_k8s_admission_control = 'NamespaceLifecycle,LimitRanger,ServiceAccount,DefaultStorageClass,ResourceQuota'

default_root_disk = '/dev/sda'
default_linux_consoles = 'tty0,ttyS0'
default_wipe_root_disk_next_boot = True
persistent_dir_path = '/mnt/persistent'

etcd_client_port = 2379
etcd_peer_port = 2380
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
k8s_kube_proxy_config_path = k8s_config_path + '/kube-proxy-config.yaml'
k8s_cni_conf_path = k8s_config_path + '/cni/net.d'
k8s_kube_proxy_user_name = 'system:kube-proxy'

node_ca_certificates_path = '/usr/share/ca-certificates'

aci_proxy_ca_cert_path = '/etc/ssl/certs/aci-proxy-ca.pem'
