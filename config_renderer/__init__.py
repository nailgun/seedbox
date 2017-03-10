import os
from flask import request
from jinja2 import Environment, FileSystemLoader

import config
from . import kernel
from . import ignition

jinja = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    keep_trailing_newline=True,
    autoescape=False,
)


def render_template(template_name, node):
    context = {
        'node': node,
        'cluster': node.cluster,
        'url_root': request.url_root,
        'config': config,
    }

    return jinja.get_template(template_name).render(context)
