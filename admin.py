import json
from flask import request, abort, Response, flash, redirect
from flask_admin import Admin, expose
from flask_admin.model.template import macro
from flask_admin.helpers import get_redirect_target
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.contrib.sqla import ModelView as BaseModelView

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
        apiserver_node = models.Node.query.filter_by(cluster_id=user.cluster_id,
                                                     is_k8s_apiserver_lb=True).first()
        apiserver_port = config.k8s_apiserver_lb_port
        if apiserver_node is None:
            apiserver_node = models.Node.query.filter_by(cluster_id=user.cluster_id,
                                                         is_k8s_apiserver=True).first()
            apiserver_port = config.k8s_apiserver_secure_port
            if apiserver_node is None:
                abort(400)

        kubeconfig = kube.get_kubeconfig(user.cluster.name,
                                         apiserver_node.fqdn,
                                         apiserver_port,
                                         ca_creds.cert,
                                         user.name,
                                         user_creds.cert,
                                         user_creds.key)
        return Response(kubeconfig, mimetype='text/plain')


class CredentialsDataView(ModelView):
    column_list = ['cert', 'key']
    list_template = 'admin/credentials_list.html'
    details_template = 'admin/credentials_details.html'
    column_formatters = {
        'cert': macro('render_cert'),
        'key': macro('render_key'),
    }

    @expose('/cert.pem')
    def cert_view(self):
        creds = self.get_one(request.args.get('id'))
        return Response(creds.cert, mimetype='text/plain')

    @expose('/key.pem')
    def key_view(self):
        creds = self.get_one(request.args.get('id'))
        return Response(creds.key, mimetype='text/plain')

    @expose('/cert.txt')
    def cert_text_view(self):
        creds = self.get_one(request.args.get('id'))
        info = pki.get_certificate_text(creds.cert)
        return Response(info, mimetype='text/plain')

    def is_visible(self):
        return False


admin = Admin(name='Cluster manager', template_mode='bootstrap3')
admin.add_view(ClusterView(models.Cluster, models.db.session))
admin.add_view(NodeView(models.Node, models.db.session))
admin.add_view(UserView(models.User, models.db.session))
admin.add_view(CredentialsDataView(models.CredentialsData, models.db.session))
admin.add_view(FileAdmin(config.cachedir, '/cache/', name='Image cache'))
