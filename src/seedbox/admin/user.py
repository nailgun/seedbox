import base64
from collections import OrderedDict

import yaml
import yaml.resolver
from flask import request, Response, flash, redirect
from flask_admin import expose
from flask_admin.actions import action
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import pki, kube, models
from .base import ModelView


class Dumper(yaml.SafeDumper):
    pass


def _dict_representer(dumper, data):
    return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())


Dumper.add_representer(OrderedDict, _dict_representer)


class UserView(ModelView):
    column_list = ['cluster', 'name', 'credentials', 'kubeconfig']
    list_template = 'admin/user_list.html'
    details_template = 'admin/user_details.html'
    form_excluded_columns = ['credentials']
    column_formatters = {
        'credentials': macro('render_credentials'),
        'kubeconfig': macro('render_kubeconfig'),
    }

    def _issue_creds(self, model):
        with self.session.no_autoflush:
            ca_creds = model.cluster.ca_credentials
        creds = models.CredentialsData()
        creds.cert, creds.key = pki.issue_certificate(model.name,
                                                      ca_cert=ca_creds.cert,
                                                      ca_key=ca_creds.key,
                                                      organizations=model.groups.split(','),
                                                      certify_days=365,
                                                      is_web_client=True)
        self.session.add(creds)
        model.credentials = creds

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_creds(model)

    @expose('/reissue-credentials', methods=['POST'])
    def reissue_creds_view(self):
        model = self.get_one(request.args.get('id'))
        self._issue_creds(model)
        self.session.add(model)
        self.session.commit()
        return_url = get_redirect_target() or self.get_url('.index_view')
        flash('The credentials successfully reissued', 'success')
        return redirect(return_url)

    @expose('/kubeconfig')
    def kubeconfig_view(self):
        user = self.get_one(request.args.get('id'))
        user_creds = user.credentials
        ca_creds = user.cluster.ca_credentials

        kubeconfig = kube.get_kubeconfig(user.cluster.name,
                                         user.cluster.k8s_apiserver_endpoint,
                                         ca_creds.cert,
                                         user.name,
                                         user_creds.cert,
                                         user_creds.key)
        return Response(kubeconfig, mimetype='text/x-yaml')

    @action('kubeconfig', 'Get kubeconfig')
    def kubeconfig_action(self, ids):
        clusters = {}
        users = {}

        for user in models.User.query.filter(models.User.id.in_(ids)):
            users[user.name] = user
            clusters[user.cluster.name] = user.cluster

        contexts = [{
            'name': user.name,
            'context': {
                'cluster': user.cluster.name,
                'user': user.name,
            },
        } for user in users.values()]

        clusters = [{
            'name': cluster.name,
            'cluster': {
                'server': cluster.k8s_apiserver_endpoint,
                'certificate-authority-data': base64.b64encode(cluster.ca_credentials.cert).decode('ascii'),
            },
        } for cluster in clusters.values()]

        users = [{
            'name': user.name,
            'user': {
                'client-certificate-data': base64.b64encode(user.credentials.cert).decode('ascii'),
                'client-key-data': base64.b64encode(user.credentials.key).decode('ascii'),
            },
        } for user in users.values()]

        config = OrderedDict([
            ('apiVersion', 'v1'),
            ('kind', 'Config'),
            ('clusters', clusters),
            ('users', users),
            ('contexts', contexts),
        ])

        return Response(yaml.dump(config, default_flow_style=False, Dumper=Dumper),
                        mimetype='text/x-yaml')
