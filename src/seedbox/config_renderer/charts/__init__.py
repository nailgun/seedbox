import io
import os
import tarfile

from jinja2 import Environment, FileSystemLoader

from seedbox import config

basedir = os.path.dirname(__file__)


def render_tgz(cluster, chart_name):
    chart_path = os.path.join(basedir, chart_name)
    if not os.path.exists(chart_path):
        raise ChartNotExist(chart_name)

    tgz_fp = io.BytesIO()
    with tarfile.open(fileobj=tgz_fp, mode='w:gz') as tgz:
        tgz.add(os.path.join(chart_path, 'Chart.yaml'), os.path.join(chart_name, 'Chart.yaml'))
        tgz.add(os.path.join(chart_path, 'templates'), os.path.join(chart_name, 'templates'))

        values_data = render_values(cluster, chart_name).encode('utf-8')
        values_info = tarfile.TarInfo(os.path.join(chart_name, 'values.yaml'))
        values_info.size = len(values_data)
        tgz.addfile(values_info, io.BytesIO(values_data))

    return tgz_fp.getvalue()


def render_values(cluster, chart_name):
    chart_path = os.path.join(basedir, chart_name)
    jinja_env = Environment(loader=FileSystemLoader(chart_path),
                            keep_trailing_newline=True,
                            autoescape=False)
    return jinja_env.get_template('values.yaml').render({
        'config': config,
        'cluster': cluster,
    })


class ChartNotExist(Exception):
    pass
