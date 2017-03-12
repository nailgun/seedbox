from flask import request, flash, redirect
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import pki, models
from .base import ModelView


class ClusterView(ModelView):
    column_list = ['name', 'ca_credentials']
    list_template = 'admin/cluster_list.html'
    details_template = 'admin/cluster_details.html'
    form_excluded_columns = ['ca_credentials', 'nodes', 'users']
    column_formatters = {
        'ca_credentials': macro('render_ca_credentials'),
    }
    form_choices = {
        'k8s_runtime': [
            (str(models.Runtime.docker.value), 'Docker'),
            (str(models.Runtime.rkt.value), 'rkt'),
        ]
    }

    def _issue_ca_creds(self, model):
        ca = models.CredentialsData()
        ca.cert, ca.key = pki.create_ca_certificate(model.name,
                                                    certify_days=10000)
        self.session.add(ca)
        model.ca_credentials = ca

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_ca_creds(model)
        else:
            model.nodes.update({models.Node.target_config_version: models.Node.target_config_version + 1})

    @expose('/reissue-ca-credentials', methods=['POST'])
    def reissue_ca_creds_view(self):
        model = self.get_one(request.args.get('id'))
        model.nodes.update({models.Node.target_config_version: models.Node.target_config_version + 1})
        self._issue_ca_creds(model)
        self.session.add(model)
        self.session.commit()
        return_url = get_redirect_target() or self.get_url('.index_view')
        flash('The credentials successfully reissued', 'success')
        return redirect(return_url)
