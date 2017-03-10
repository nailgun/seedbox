import os
import json
from jinja2 import Environment, FileSystemLoader


jinja = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')), autoescape=False)


def render(node, url_root, indent=False):
    cfg = {
        'ignition': {
            'version': '2.0.0',
            'config': {},
        },
        'storage': {},
        'networkd': {},
        'passwd': {},
        'systemd': {
            'units': [],
        },
    }

    unit_cfg = {
        'name': 'provision-report.service',
        'enable': True,
        'contents': jinja.get_template('services/provision-report.service').render(node=node, url_root=url_root)
    }

    cfg['systemd']['units'].append(unit_cfg)

    if indent:
        return json.dumps(cfg, indent=2)
    else:
        return json.dumps(cfg, separators=(',', ':'))
