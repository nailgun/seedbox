import json

from flask import request, abort, Response, flash, redirect
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import config, pki, models, config_renderer
from .base import ModelView


class NodeView(ModelView):
    column_list = [
        'cluster',
        'fqdn',
        'ip',
        'credentials',
        'ignition_config',
    ]
    list_template = 'admin/node_list.html'
    details_template = 'admin/node_details.html'
    form_excluded_columns = [
        'credentials',
        'target_config_version',
        'active_config_version',
        'active_ignition_config',
    ]
    column_formatters = {
        'credentials': macro('render_credentials'),
        'ignition_config': macro('render_ignition_config'),
    }
    inline_models = [models.Mountpoint]

    def _issue_creds(self, model):
        with self.session.no_autoflush:
            ca_creds = model.cluster.ca_credentials
        creds = models.CredentialsData()

        if model.is_k8s_apiserver:
            san_dns = [
                'kubernetes',
                'kubernetes.default',
                'kubernetes.default.svc',
                'kubernetes.default.svc.' + config.k8s_cluster_domain,
            ]
            san_ips = [model.cluster.k8s_apiserver_service_ip]
        else:
            san_dns = []
            san_ips = []

        san_dns.append(model.fqdn)
        san_ips.append(model.ip)

        creds.cert, creds.key = pki.issue_certificate('system:node:' + model.fqdn,
                                                      ca_cert=ca_creds.cert,
                                                      ca_key=ca_creds.key,
                                                      organizations=['system:nodes'],
                                                      san_dns=san_dns,
                                                      san_ips=san_ips,
                                                      certify_days=10000,
                                                      is_web_server=True,
                                                      is_web_client=True)
        self.session.add(creds)
        model.credentials = creds

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_creds(model)
            model.active_ignition_config = ''
        else:
            model.target_config_version += 1

    @expose('/reissue-credentials', methods=['POST'])
    def reissue_creds_view(self):
        model = self.get_one(request.args.get('id'))
        model.target_config_version += 1
        self._issue_creds(model)
        self.session.add(model)
        self.session.commit()
        return_url = get_redirect_target() or self.get_url('.index_view')
        flash('The credentials successfully reissued', 'success')
        return redirect(return_url)

    @expose('/active-ignition.json')
    def active_ignition_config_view(self):
        node = self.get_one(request.args.get('id'))
        if not node.active_ignition_config:
            abort(404)

        data = json.loads(node.active_ignition_config)
        data = json.dumps(data, indent=2)
        return Response(data, mimetype='application/json')

    @expose('/target-ignition.json')
    def target_ignition_config_view(self):
        node = self.get_one(request.args.get('id'))
        response = config_renderer.ignition.render(node, indent=True)
        return Response(response, mimetype='application/json')
