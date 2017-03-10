from flask import request, abort, Response
from flask_admin import Admin, expose
from flask_admin.model.template import macro
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView as BaseModelView, form

import pki
import kube
import config
import models


class ModelView(BaseModelView):
    can_view_details = True


class ClusterView(ModelView):
    column_list = ['name', 'ca_credentials']
    list_template = 'admin/cluster_list.html'
    details_template = 'admin/cluster_details.html'
    form_excluded_columns = ['ca_credentials', 'nodes', 'users']
    column_formatters = {
        'ca_credentials': macro('render_ca_credentials'),
    }

    def on_model_change(self, form, model, is_created):
        if not is_created:
            return
        ca = models.CredentialsData()
        ca.cert, ca.key = pki.create_ca_certificate(model.name,
                                                    certify_days=10000)
        self.session.add(ca)
        model.ca_credentials = ca


class NodeView(ModelView):
    column_list = ['cluster', 'fqdn', 'ip', 'credentials']
    list_template = 'admin/node_list.html'
    details_template = 'admin/node_details.html'
    form_excluded_columns = ['credentials']
    column_formatters = {
        'credentials': macro('render_credentials'),
    }

    def on_model_change(self, form, model, is_created):
        if not is_created:
            return
        with self.session.no_autoflush:
            ca_creds = model.cluster.ca_credentials
        creds = models.CredentialsData()
        creds.cert, creds.key = pki.create_certificate(model.fqdn,
                                                       ips=[model.ip],
                                                       fqdns=[model.fqdn],
                                                       ca_cert=ca_creds.cert,
                                                       ca_key=ca_creds.key,
                                                       certify_days=10000)
        self.session.add(creds)
        model.credentials = creds


class UserView(ModelView):
    column_list = ['cluster', 'name', 'credentials', 'kubeconfig']
    list_template = 'admin/user_list.html'
    details_template = 'admin/user_details.html'
    form_excluded_columns = ['credentials']
    column_formatters = {
        'credentials': macro('render_credentials'),
        'kubeconfig': macro('render_kubeconfig'),
    }

    def on_model_change(self, form, model, is_created):
        if not is_created:
            return
        with self.session.no_autoflush:
            ca_creds = model.cluster.ca_credentials
        creds = models.CredentialsData()
        creds.cert, creds.key = pki.create_certificate(model.name,
                                                       ips=[],
                                                       fqdns=[],
                                                       ca_cert=ca_creds.cert,
                                                       ca_key=ca_creds.key,
                                                       certify_days=365)
        self.session.add(creds)
        model.credentials = creds

    @expose('/kubeconfig', methods=['GET'])
    def kubeconfig_view(self):
        user = self.get_one(request.args.get('id'))
        user_creds = user.credentials
        ca_creds = user.cluster.ca_credentials
        apiserver_node = models.Node.query.filter_by(cluster_id=user.cluster_id,
                                                     is_k8s_apiserver_lb=True).first()
        if apiserver_node is None:
            apiserver_node = models.Node.query.filter_by(cluster_id=user.cluster_id,
                                                         is_k8s_apiserver=True).first()
            if apiserver_node is None:
                abort(400)

        kubeconfig = kube.get_kubeconfig(user.cluster.name, apiserver_node.fqdn, ca_creds.cert, user.name, user_creds.cert, user_creds.key)
        return Response(kubeconfig, mimetype='text/plain')


class CredentialsDataView(ModelView):
    column_list = ['id', 'cert', 'key', 'info']
    list_template = 'admin/credentials_list.html'
    details_template = 'admin/credentials_details.html'
    column_formatters = {
        'cert': macro('render_cert'),
        'key': macro('render_key'),
        'info': macro('render_cert_info'),
    }

    @expose('/cert.pem', methods=['GET'])
    def cert_view(self):
        creds = self.get_one(request.args.get('id'))
        return Response(creds.cert, mimetype='text/plain')

    @expose('/key.pem', methods=['GET'])
    def key_view(self):
        creds = self.get_one(request.args.get('id'))
        return Response(creds.key, mimetype='text/plain')

    @expose('/cert.txt', methods=['GET'])
    def cert_info_view(self):
        creds = self.get_one(request.args.get('id'))
        info = pki.get_certificate_info(creds.cert)
        return Response(info, mimetype='text/plain')


admin = Admin(name='Cluster manager', template_mode='bootstrap3')
admin.add_view(ClusterView(models.Cluster, models.db.session))
admin.add_view(NodeView(models.Node, models.db.session))
admin.add_view(UserView(models.User, models.db.session))
admin.add_view(CredentialsDataView(models.CredentialsData, models.db.session))
admin.add_view(FileAdmin(config.cachedir, '/cache/', name='Cache'))
