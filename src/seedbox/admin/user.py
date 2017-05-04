from flask import request, Response, flash, redirect, abort
from flask_admin import expose
from flask_admin.form import rules
from flask_admin.actions import action
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import pki, models, config_renderer, exceptions
from .base import ModelView


class UserView(ModelView):
    column_list = ['cluster', 'name', 'credentials', 'kubeconfig']
    list_template = 'admin/user_list.html'
    details_template = 'admin/user_details.html'
    form_excluded_columns = [
        'credentials',
    ]
    column_formatters = {
        'credentials': macro('render_credentials'),
        'kubeconfig': macro('render_kubeconfig'),
    }
    column_labels = {
        'ssh_key': 'SSH key',
        'k8s_groups': 'Kubernetes groups',
    }
    column_descriptions = {
        'name': 'Will be used as CommonName in TLS certificate.',
        'k8s_groups': 'Will be added as Organization(s) in TLS certificate. (Separate by comma.)',
        'ssh_key': 'This key will be authorized on all nodes of the cluster (as `core` user).',
    }
    form_rules = [
        rules.Field('cluster'),
        rules.Field('name'),
        rules.Field('k8s_groups'),
        rules.Field('ssh_key'),
    ]

    def _issue_creds(self, model):
        with self.session.no_autoflush:
            ca_creds = model.cluster.ca_credentials
        creds = models.CredentialsData()
        if model.k8s_groups:
            orgs = model.k8s_groups.split(',')
        else:
            orgs = []
        creds.cert, creds.key = pki.issue_certificate(model.name,
                                                      ca_cert=ca_creds.cert,
                                                      ca_key=ca_creds.key,
                                                      organizations=orgs,
                                                      certify_days=365,
                                                      is_web_client=True)
        self.session.add(creds)
        model.credentials = creds

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_creds(model)

    def after_model_delete(self, model):
        models.CredentialsData.query.filter_by(id=model.credentials_id).delete()

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
        return Response(render_kubeconfig([user]), mimetype='text/x-yaml')

    @action('kubeconfig', 'Get kubeconfig')
    def kubeconfig_action(self, ids):
        users = models.User.query.filter(models.User.id.in_(ids))
        return Response(render_kubeconfig(users), mimetype='text/x-yaml')


def render_kubeconfig(users):
    try:
        default_user = None
        if len(users) == 1:
            default_user = users[0]

        return config_renderer.kubeconfig.render(users, default_user=default_user)
    except exceptions.K8sNoClusterApiserver:
        return abort(404, 'No node with k8s apiserver.')
