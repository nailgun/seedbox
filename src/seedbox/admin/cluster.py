from flask import request, flash, redirect
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import pki, models
from .base import ModelView


class ClusterView(ModelView):
    column_list = ['name', 'ca_credentials', 'info']
    list_template = 'admin/cluster_list.html'
    details_template = 'admin/cluster_details.html'
    form_excluded_columns = ['ca_credentials', 'nodes', 'users', 'service_account_keypair']
    column_formatters = {
        'ca_credentials': macro('render_ca_credentials'),
        'info': macro('render_info'),
    }
    column_labels = {
        'ca_credentials': "CA credentials",
        'etcd_version': "etcd version",
        'suppose_etcd_cluster_exists': "Suppose etcd cluster already exists",
        'manage_etc_hosts': "Manage /etc/hosts",
        'allow_insecure_provision': "Allow insecure node provisioning",
        'apiservers_audit_log': "Enable audit log on Kubernetes apiservers",
        'apiservers_swagger_ui': "Enable Swagger-UI on Kubernetes apiservers",
        'explicitly_advertise_addresses': "Explicitly advertise addresses",
        'k8s_pod_network': "Kubernetes pod network CIDR",
        'k8s_service_network': "Kubernetes service network CIDR",
        'k8s_hyperkube_tag': "Kubernetes hyperkube image tag",
        'k8s_cni': "Use CNI in Kubernetes cluster",
        'boot_images_base_url': "Base HTTP URL of CoreOS images",
        'aci_proxy_url': "ACI proxy URL",
        'aci_proxy_ca_cert': "ACI proxy CA certificate (PEM)",
    }
    column_descriptions = {
        'name': "Human readable cluster name. Don't use spaces.",
        'etcd_version': "2 or 3.",
        'suppose_etcd_cluster_exists': "This will set `initial-cluster-state` to `existing` for newly provisioned "
                                       "etcd members. Use it to add etcd members to existing cluster.",
        'manage_etc_hosts': "If this is set, /etc/hosts on each node will be populated with FQDNs and IPs of all "
                            "cluster nodes. Useful for virtual environments.",
        'allow_insecure_provision': "Allow nodes to download CoreOS Ignition config and credentials via "
                                    "non-encrypted connection. Useful for virtual environments.",
        'explicitly_advertise_addresses': "If this is set, cluster components will explicitly advertise "
                                          "node IP as it set in seedbox. Useful for virtual environments.",
        'boot_images_base_url': "Will speedup PXE boot if set to location in your datacenter.",
        'aci_proxy_url': "Docker and rkt will use this proxy to download container images.",
        'aci_proxy_ca_cert': "Docker and rkt download images via HTTPS. If your proxy intercepts "
                             "HTTPS connections you should add proxy CA certificate here. It will be "
                             "added to system root CA certificates on each node.",
    }

    def _issue_creds(self, model):
        ca = models.CredentialsData()
        ca.cert, ca.key = pki.create_ca_certificate(model.name,
                                                    certify_days=10000)
        self.session.add(ca)
        model.ca_credentials = ca

        service_account_keypair = models.CredentialsData()
        service_account_keypair.cert, service_account_keypair.key = pki.generate_rsa_keypair()
        self.session.add(service_account_keypair)
        model.service_account_keypair = service_account_keypair

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_creds(model)
        else:
            model.nodes.update({models.Node.target_config_version: models.Node.target_config_version + 1})

    @expose('/reissue-ca-credentials', methods=['POST'])
    def reissue_ca_creds_view(self):
        model = self.get_one(request.args.get('id'))
        model.nodes.update({models.Node.target_config_version: models.Node.target_config_version + 1})
        self._issue_creds(model)
        self.session.add(model)
        self.session.commit()
        return_url = get_redirect_target() or self.get_url('.index_view')
        flash('The credentials successfully reissued', 'success')
        return redirect(return_url)
