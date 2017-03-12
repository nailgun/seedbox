import os
import logging

import filelock
import requests
from flask import Flask, Response, request, abort, send_file

from seedbox import config, models, config_renderer
from seedbox.admin import admin


log = logging.getLogger(__name__)


app = Flask(__name__, template_folder='admin/templates')
app.secret_key = config.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = config.database_uri
models.db.app = app
models.db.init_app(app)
admin.init_app(app)

ipxe_response = """#!ipxe
kernel /image/{coreos_channel}/{coreos_version}/coreos_production_pxe.vmlinuz coreos.config.url={base_url}ignition {kernel_args}
initrd /image/{coreos_channel}/{coreos_version}/coreos_production_pxe_image.cpio.gz
boot
"""


def get_node(request_type):
    node_ip = request.remote_addr
    log.info('%s request from %s', request_type, node_ip)

    node = models.Node.query.filter_by(ip=node_ip).first()
    if node is None:
        log.error('Node %s is unknown', node_ip)
        abort(403)

    return node


@app.route('/ipxe')
def ipxe_boot():
    node = get_node('iPXE boot')
    kernel_args = ' '.join(config_renderer.kernel.get_kernel_arguments(node))
    response = ipxe_response.format(coreos_channel=node.coreos_channel,
                                    coreos_version=node.coreos_version,
                                    base_url=request.url_root,
                                    kernel_args=kernel_args)
    return Response(response, mimetype='text/plain')


@app.route('/ignition')
def ignition():
    node = get_node('Ignition config')
    response = config_renderer.ignition.render(node, 'indent' in request.args)
    return Response(response, mimetype='application/json')


@app.route('/image/<channel>/<version>/<filename>')
def image(channel, version, filename):
    get_node('Image download')

    dirpath = os.path.join(config.cachedir, channel, version)
    filepath = os.path.join(dirpath, filename)

    os.makedirs(dirpath, exist_ok=True)

    lock = filelock.FileLock(filepath + '.lock')
    with lock:
        if not os.path.exists(filepath):
            source_url = 'https://{}.release.core-os.net/amd64-usr/{}/{}'.format(channel, version, filename)
            resp = requests.get(source_url, stream=True)
            if resp.status_code == 404:
                abort(404)
            resp.raise_for_status()

            with open(filepath + '.partial', 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk)
            os.rename(filepath + '.partial', filepath)

        os.remove(filepath + '.lock')

    return send_file(filepath)


@app.route('/credentials/<cred_type>.pem')
def credentials(cred_type):
    node = get_node('Credentials download')

    if not node.cluster.allow_unsafe_credentials_transfer and request.environ['wsgi.url_scheme'] != 'https':
        abort(400)

    if cred_type == 'ca':
        return Response(node.cluster.ca_credentials.cert, mimetype='text/plain')

    if cred_type == 'node':
        return Response(node.credentials.cert, mimetype='text/plain')

    if cred_type == 'node-key':
        return Response(node.credentials.key, mimetype='text/plain')

    abort(404)


@app.route('/report', methods=['POST'])
def report():
    node = get_node('Provision report')

    node.current_config_version = request.args.get('version')
    if node.current_config_version is None:
        abort(400)

    ignition_config = request.get_json()
    if ignition_config is None:
        abort(400)

    node.current_ignition_config = request.data

    models.db.session.add(node)
    models.db.session.commit()

    return Response('ok', mimetype='application/json')


if __name__ == '__main__':
    app.run('0.0.0.0')
