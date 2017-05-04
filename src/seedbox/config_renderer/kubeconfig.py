import base64
from collections import OrderedDict

import yaml
import yaml.resolver


def render(users, default_user=None):
    clusters_map = {}
    users_map = {}

    for user in users:
        users_map[user.name] = user
        clusters_map[user.cluster.name] = user.cluster

    contexts = [{
        'name': user.name,
        'context': {
            'cluster': user.cluster.name,
            'user': user.name,
        },
    } for user in users_map.values()]

    clusters = [{
        'name': cluster.name,
        'cluster': {
            'server': cluster.k8s_apiserver_endpoint,
            'certificate-authority-data': base64.b64encode(cluster.ca_credentials.cert).decode('ascii'),
        },
    } for cluster in clusters_map.values()]

    users = [{
        'name': user.name,
        'user': {
            'client-certificate-data': base64.b64encode(user.credentials.cert).decode('ascii'),
            'client-key-data': base64.b64encode(user.credentials.key).decode('ascii'),
        },
    } for user in users_map.values()]

    config = OrderedDict([
        ('apiVersion', 'v1'),
        ('kind', 'Config'),
        ('clusters', clusters),
        ('users', users),
        ('contexts', contexts),
    ])

    if default_user:
        config['current-context'] = default_user.name

    return yaml.dump(config, default_flow_style=False, Dumper=Dumper)


class Dumper(yaml.SafeDumper):
    pass


def _dict_representer(dumper, data):
    return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())


Dumper.add_representer(OrderedDict, _dict_representer)
