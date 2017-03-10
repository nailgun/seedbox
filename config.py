import os

basedir = os.path.dirname(__file__)
cachedir = os.path.join(basedir, 'cache')

etcd_client_port = 2379
etcd_peer_port = 2380
credentials_path = '/etc/ssl/private'
