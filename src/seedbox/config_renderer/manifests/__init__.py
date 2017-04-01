import os

from jinja2 import Environment, FileSystemLoader

from seedbox import config

basedir = os.path.dirname(__file__)


def render_yaml(cluster, filename):
    jinja_env = Environment(loader=FileSystemLoader(basedir),
                            keep_trailing_newline=True,
                            autoescape=False)
    return jinja_env.get_template(filename).render({
        'config': config,
        'cluster': cluster,
    })
