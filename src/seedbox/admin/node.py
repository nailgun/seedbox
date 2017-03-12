import json

from flask import request, abort, Response, flash, redirect
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import config, pki, models
from .base import ModelView


class NodeView(ModelView):
    column_list = [
        'cluster',
        'fqdn',
        'ip',
        'is_ready',
        'credentials',
        'current_ignition_config',
    ]
    list_template = 'admin/node_list.html'
    details_template = 'admin/node_details.html'
    form_excluded_columns = [
        'credentials',
        'target_config_version',
        'current_config_version',
        'current_ignition_config',
    ]
    column_formatters = {
        'credentials': macro('render_credentials'),
        'current_ignition_config': macro('render_current_ignition_config'),
    }

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

        creds.cert, creds.key = pki.issue_certificate(model.fqdn,
                                                      ca_cert=ca_creds.cert,
                                                      ca_key=ca_creds.key,
                                                      san_dns=san_dns,
                                                      san_ips=san_ips,
                                                      certify_days=10000)
        self.session.add(creds)
        model.credentials = creds

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_creds(model)
            model._coreos_channel = ''
            model._coreos_version = ''
            model.current_ignition_config = ''
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

    @expose('/ignition.json')
    def current_ignition_config_view(self):
        node = self.get_one(request.args.get('id'))
        if not node.current_ignition_config:
            abort(404)

        data = json.loads(node.current_ignition_config)
        data = json.dumps(data, indent=2)
        return Response(data, mimetype='application/json')
