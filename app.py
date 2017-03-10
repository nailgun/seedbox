import logging
import urllib.parse
from flask import Flask, Response, request, abort

import kube
import config
import models
from admin import admin

log = logging.getLogger(__name__)


app = Flask(__name__)
app.secret_key = '-'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
models.db.app = app
models.db.init_app(app)
admin.init_app(app)

node_boot_args = {
    'secret': urllib.parse.quote(config.boot_secret),
    'uuid': '${uuid}',
    'serial': '${serial}',
    'mac': '${net0/mac:hexhyp}',
    'domain': '${domain}',
    'hostname': '${hostname}',
}

node_boot_string = '&'.join('{}={}'.format(k, v) for k, v in node_boot_args.items())

boot_chain_response = """#!ipxe
chain /boot/ipxe?{node_boot_string}
"""

boot_response = """#!ipxe
kernel {coreos_base_url}coreos_production_pxe.vmlinuz coreos.config.url={base_url}boot/ignition?{node_boot_string} coreos.first_boot=yes console=tty0 console=ttyS0 coreos.autologin
initrd {coreos_base_url}coreos_production_pxe_image.cpio.gz
boot
"""


def get_node(request_type, require_args=True):
    node_ip = request.remote_addr
    log.info('%s request from %s', request_type, node_ip)

    if request.args.get('secret') != config.boot_secret:
        log.info('Invalid boot secret from %s', node_ip)
        abort(401)

    if not all(key in request.args for key in node_boot_args):
        if require_args:
            log.error('%s request without required parameters from %s', request_type, node_ip)
            abort(400)
        else:
            return None

    node = models.Node.query.filter_by(ip=node_ip).first()
    if node is None:
        log.error('Node %s is unknown', node_ip)
        abort(403)

    return node


@app.route('/boot/ipxe')
def ipxe_boot():
    node = get_node('iPXE boot', require_args=False)
    if node is None:
        response = boot_chain_response.format(node_boot_string=node_boot_string)
    else:
        cluster = node.cluster
        response = boot_response.format(node_boot_string=node_boot_string,
                                        coreos_base_url=cluster.coreos_base_url,
                                        base_url=request.url_root)
    return Response(response, mimetype='text/plain')


@app.route('/boot/ignition')
def ignition():
    node = get_node('Ignition config')
    response = kube.get_coreos_kube_ignition(node)
    return Response(response, mimetype='application/json')


if __name__ == '__main__':
    app.run('0.0.0.0')
