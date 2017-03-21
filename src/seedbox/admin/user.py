from flask import request, abort, Response, flash, redirect
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import config, pki, kube, models
from .base import ModelView


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
                                                      certify_days=365)
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
        return Response(kubeconfig, mimetype='text/plain')
