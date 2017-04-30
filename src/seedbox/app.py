import logging

from flask import Flask, Response, request, abort, redirect
from flask_migrate import Migrate

from seedbox import config, models, config_renderer
from seedbox.admin import admin


log = logging.getLogger(__name__)


app = Flask(__name__, template_folder='admin/templates')
app.secret_key = config.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = config.database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
models.db.app = app
models.db.init_app(app)
migrate = Migrate(app, models.db, directory='seedbox/migrations')
admin.init_app(app)


def get_node(node_ip):
    node = models.Node.query.filter_by(ip=node_ip).first()
    if node is None:
        log.error('Node %s is unknown', node_ip)
        return abort(403)
    return node


@app.before_request
def check_admin_secure():
    if request.path.startswith(config.admin_base_url + '/'):
        response = ensure_secure_request()
        if response is not None:
            return response


def route(rule, request_name, secure=True, **route_kwargs):
    def decorator(func):
        def wrapped(*args, **kwargs):
            node_ip = request.remote_addr
            log.info('%s request from %s', request_name, node_ip)
            if secure:
                response = ensure_secure_request()
                if response is not None:
                    return response
            node = get_node(node_ip)
            return func(node, *args, **kwargs)

        wrapped.__name__ = func.__name__
        return app.route(rule, **route_kwargs)(wrapped)
    return decorator


def ensure_secure_request():
    is_request_secure = request.environ['wsgi.url_scheme'] == 'https'
    if not is_request_secure and not config.allow_insecure_transport:
        if request.method in ('POST', 'PUT', 'PATCH'):
            # request body already sent in insecure manner
            # return error in this case to notify cluster admin
            return abort(400)
        else:
            return redirect(request.url.replace('http://', 'https://', 1))


@route('/ipxe', 'iPXE boot', secure=False)
def ipxe_boot(node):
    response = config_renderer.ipxe.render(node, request.url_root)
    return Response(response, mimetype='text/plain')


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

    return abort(404)


@route('/report', 'Provision report', methods=['POST'])
def report(node):
    if not node.maintenance_mode:
        node.active_config_version = request.args.get('version')
        if node.active_config_version is None:
            return abort(400)

        ignition_config = request.get_json()
        if ignition_config is None:
            return abort(400)

        node.active_ignition_config = request.data

    node.wipe_root_disk_next_boot = False

    models.db.session.add(node)

    if node.cluster.are_etcd_nodes_configured:
        node.cluster.assert_etcd_cluster_exists = True
        models.db.session.add(node.cluster)

    models.db.session.commit()
    return Response('ok', mimetype='application/json')


@app.route('/addons/<cluster_name>/<addon_name>-<addon_version>.tar.gz')
def k8s_addons_helm_chart(cluster_name, addon_name, addon_version):
    # TODO: not ready for multitenancy
    cluster = models.Cluster.query.filter_by(name=cluster_name).first()
    if cluster is None:
        return abort(404)

    try:
        addon = config_renderer.charts.addons[addon_name][addon_version]
    except KeyError:
        return abort(404)

    return Response(config_renderer.charts.render_addon_tgz(cluster, addon),
                    mimetype='application/tar+gzip')
