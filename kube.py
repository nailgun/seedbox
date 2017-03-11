import base64


KUBECONFIG_TEMPLATE = """apiVersion: v1
kind: Config
users:
- name: {user_name}
  user:
    client-certificate-data: {user_cert}
    client-key-data: {user_key}
clusters:
- name: {cluster_name}
  cluster:
    certificate-authority-data: {ca_cert}
    server: https://{apiserver_host}:443
contexts:
- context:
    cluster: {cluster_name}
    user: {user_name}
  name: default-context
current-context: default-context
"""


def get_kubeconfig(cluster_name, apiserver_host, ca_cert, user_name, user_cert, user_key):
    return KUBECONFIG_TEMPLATE.format(
        cluster_name=cluster_name,
        apiserver_host=apiserver_host,
        ca_cert=base64.b64encode(ca_cert).decode('ascii'),
        user_name=user_name,
        user_cert=base64.b64encode(user_cert).decode('ascii'),
        user_key=base64.b64encode(user_key).decode('ascii'),
    )
