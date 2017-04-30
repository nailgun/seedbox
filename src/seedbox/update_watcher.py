import re
import time
import json
import logging
import configparser

import requests

from seedbox import config

log = logging.getLogger(__name__)

coreos_channels = ('stable', 'beta', 'alpha')
coreos_version_url = 'https://{channel}.release.core-os.net/amd64-usr/current/version.txt'
quay_io_tags_url = 'https://quay.io/api/v1/repository/{repo_path}/tag/'
unstable_tag_regexps = [re.compile(r'[^a-zA-Z]' + w + r'[^a-zA-Z]') for w in ('rc', 'beta', 'alpha')]


def watch():
    while True:
        data = fetch()
        log.info('Current versions: %s', data)
        with open(config.update_state_file, 'w') as fp:
            json.dump(data, fp)
        log.info('Saved to %s', config.update_state_file)
        log.info('Waiting for %s seconds before next update', config.update_check_interval_sec)
        time.sleep(config.update_check_interval_sec)


def fetch():
    versions = {}

    coreos_versions = {}
    for coreos_channel in coreos_channels:
        try:
            coreos_versions[coreos_channel] = fetch_coreos(coreos_channel)
        except Exception:
            log.exception('Failed to fetch latest CoreOS version on %s channel', coreos_channel)
    versions['coreos'] = coreos_versions

    try:
        versions['etcd'] = fetch_from_quay(config.etcd_image)
    except Exception:
        log.exception('Failed to fetch latest etcd version')

    try:
        versions['hyperkube'] = fetch_from_quay(config.k8s_hyperkube_image)
    except Exception:
        log.exception('Failed to fetch latest hyperkube version')

    return versions


def fetch_coreos(channel):
    resp = requests.get(coreos_version_url.format(channel=channel))
    resp.raise_for_status()
    config = configparser.ConfigParser()
    config.read_string('[a]\n' + resp.content.decode('utf-8'))
    return config['a']['COREOS_VERSION']


def fetch_from_quay(image_url):
    quay_io_image_prefix = 'quay.io/'

    if not image_url.startswith(quay_io_image_prefix):
        raise Exception('Unsupported image URL', image_url)

    repo_path = image_url[len(quay_io_image_prefix):]
    resp = requests.get(quay_io_tags_url.format(repo_path=repo_path))
    resp.raise_for_status()

    tags = [(tag['name'], tag2version(tag['name'])) for tag in resp.json()['tags'] if is_stable_tag(tag['name'])]
    latest = tags[0]

    for tag in tags:
        if tag[1] > latest[1]:
            latest = tag

    return latest[0]


def tag2version(tag):
    from packaging import version
    return version.parse(tag)


def is_stable_tag(tag):
    for r in unstable_tag_regexps:
        if r.search(tag):
            return False
    return True
