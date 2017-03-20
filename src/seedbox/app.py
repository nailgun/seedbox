import os
import logging

import filelock
import requests
from flask import Flask, Response, request, abort, send_file, redirect
from flask_migrate import Migrate

from seedbox import config, models, config_renderer
from seedbox.admin import admin


log = logging.getLogger(__name__)


app = Flask(__name__, template_folder='admin/templates')
app.secret_key = config.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = config.database_uri
models.db.app = app
models.db.init_app(app)
migrate = Migrate(app, models.db)
admin.init_app(app)


def get_node(node_ip):
    node = models.Node.query.filter_by(ip=node_ip).first()
    if node is None:
        log.error('Node %s is unknown', node_ip)
        abort(403)
    return node


def route(rule, request_name, secure=True, **route_kwargs):
    def decorator(func):
        def wrapped(*args, **kwargs):
            node_ip = request.remote_addr
            log.info('%s request from %s', request_name, node_ip)
            node = get_node(node_ip)

            is_request_secure = request.environ['wsgi.url_scheme'] == 'https'
            if secure and not is_request_secure and not node.cluster.allow_insecure_provision:
                if request.method in ('POST', 'PUT', 'PATCH'):
                    # request body already sent in insecure manner
                    # return error in this case to notify cluster admin
                    abort(400)
                else:
                    return redirect(request.url.replace('http://', 'https://', 1))

            return func(node, *args, **kwargs)

        wrapped.__name__ = func.__name__
        return app.route(rule, **route_kwargs)(wrapped)
    return decorator


@route('/ipxe', 'iPXE boot', secure=False)
def ipxe_boot(node):
    response = config_renderer.ipxe.render(node, request.url_root)
    return Response(response, mimetype='text/plain')


@route('/image/<channel>/<version>/<filename>', 'Image download', secure=False)
def image(node, channel, version, filename):
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


@route('/ignition', 'Ignition config')
def ignition(node):
    response = config_renderer.ignition.render(node, 'indent' in request.args)
    return Response(response, mimetype='application/json')


@route('/credentials/<cred_type>.pem', 'Credentials download')
def credentials(node, cred_type):
    if cred_type == 'ca':
        return Response(node.cluster.ca_credentials.cert, mimetype='text/plain')

    if cred_type == 'node':
        return Response(node.credentials.cert, mimetype='text/plain')

    if cred_type == 'node-key':
        return Response(node.credentials.key, mimetype='text/plain')

    abort(404)


@route('/report', 'Provision report', methods=['POST'])
def report(node):
    node.active_config_version = request.args.get('version')
    if node.active_config_version is None:
        abort(400)

    ignition_config = request.get_json()
    if ignition_config is None:
        abort(400)

    node.active_ignition_config = request.data

    models.db.session.add(node)
    models.db.session.commit()

    return Response('ok', mimetype='application/json')
