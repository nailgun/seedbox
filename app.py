import os
import logging
import requests
import filelock
from flask import Flask, Response, request, abort, send_file

import config
import models
import config_renderer
from admin import admin

log = logging.getLogger(__name__)


app = Flask(__name__)
app.secret_key = '-'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
models.db.app = app
models.db.init_app(app)
admin.init_app(app)

ipxe_response = """#!ipxe
kernel /boot/image/{coreos_channel}/{coreos_version}/coreos_production_pxe.vmlinuz coreos.config.url={base_url}boot/ignition {kernel_args}
initrd /boot/image/{coreos_channel}/{coreos_version}/coreos_production_pxe_image.cpio.gz
boot
"""


def get_node(request_type, require_args=False):
    node_ip = request.remote_addr
    log.info('%s request from %s', request_type, node_ip)

    node = models.Node.query.filter_by(ip=node_ip).first()
    if node is None:
        log.error('Node %s is unknown', node_ip)
        abort(403)

    return node


@app.route('/boot/ipxe')
def ipxe_boot():
    node = get_node('iPXE boot')
    kernel_args = ' '.join(config_renderer.kernel.get_kernel_arguments(node))
    response = ipxe_response.format(coreos_channel=node.coreos_channel,
                                    coreos_version=node.coreos_version,
                                    base_url=request.url_root,
                                    kernel_args=kernel_args)
    return Response(response, mimetype='text/plain')


@app.route('/boot/ignition')
def ignition():
    node = get_node('Ignition config')
    response = config_renderer.ignition.render(node, request.url_root, 'indent' in request.args)
    return Response(response, mimetype='application/json')


@app.route('/boot/image/<channel>/<version>/<filename>')
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


# TODO: ensure connection is encrypted
@app.route('/credentials/<cred_type>.pem')
def credentials(cred_type):
    node = get_node('Credentials download')
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
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400)

    if 'config_version' in data:
        node.current_config_version = data['config_version']
        models.db.session.add(node)
        models.db.session.commit()

    return Response('ok', mimetype='application/json')


if __name__ == '__main__':
    app.run('0.0.0.0')
