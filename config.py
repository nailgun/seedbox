import os

basedir = os.path.dirname(__file__)
cachedir = os.path.join(basedir, 'cache')

# used to distigush unkown hosts and non-configured hosts
boot_secret = '123'

etcd_client_port = 2379
etcd_peer_port = 2380
