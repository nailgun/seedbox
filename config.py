import os

basedir = os.path.dirname(__file__)
cachedir = os.path.join(basedir, 'cache')

# used to distigush unkown hosts and non-configured hosts
boot_secret = '123'
