from flask import request, flash, redirect
from flask_admin import expose
from flask_admin.form import rules
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import pki, models, config_renderer
from .base import ModelView


class ClusterView(ModelView):
    column_list = ['name', 'ca_credentials', 'info']
    list_template = 'admin/cluster_list.html'
    details_template = 'admin/cluster_details.html'
    form_excluded_columns = [
        'ca_credentials',
        'nodes',
        'users',
        'service_account_keypair',
    ]
    column_formatters = {
        'ca_credentials': macro('render_ca_credentials'),
        'info': macro('render_info'),
    }
    column_labels = {
        'ca_credentials': "CA credentials",
        'etcd_image_tag': "etcd image tag",
        'suppose_etcd_cluster_exists': "Suppose etcd cluster already exists",
        'etcd_nodes_dns_name': "DNS name of any etcd node",
        'install_dnsmasq': "Install dnsmasq on cluster nodes",
        'allow_insecure_provision': "Allow insecure node provisioning",
        'apiservers_audit_log': "Enable audit log on apiservers",
        'apiservers_swagger_ui': "Enable Swagger-UI on apiservers",
        'dnsmasq_static_records': "Add static records to dnsmasq",
        'explicitly_advertise_addresses': "Explicitly advertise addresses",
        'k8s_pod_network': "Pod network CIDR",
        'k8s_service_network': "Service network CIDR",
        'k8s_hyperkube_tag': "Hyperkube image tag",
        'k8s_cni': "Use CNI",
        'k8s_apiservers_dns_name': "DNS name of any master node",
        'k8s_is_rbac_enabled': "Enable RBAC",
        'k8s_admission_control': "Admission control",
        'boot_images_base_url': "Base HTTP URL of CoreOS images",
        'aci_proxy_url': "ACI proxy URL",
        'aci_proxy_ca_cert': "ACI proxy CA certificate (PEM)",
    }
    column_descriptions = {
        'name': "Human readable cluster name. Don't use spaces.",
        'suppose_etcd_cluster_exists': "This will set `initial-cluster-state` to `existing` for newly provisioned "
                                       "etcd members. Use it to add etcd members to existing cluster.",
        'etcd_nodes_dns_name': "Must be round-robin DNS record. If this is set it will be used by "
                               "all components to access etcd instead of hardcoded node list. You can "
                               "add/remove nodes at any time just by updating DNS record.",
        'install_dnsmasq': "If this is set, dnsmasq will be run on each node for resolving cluster.local zone "
                           "using k8s DNS and for DNS caching.",
        'allow_insecure_provision': "Allow nodes to download CoreOS Ignition config and credentials via "
                                    "non-encrypted connection.",
        'dnsmasq_static_records': "Hosts' dnsmasq will serve cluster nodes' FQDNs and cluster components "
                                  "like etcd and apiserver.",
        'explicitly_advertise_addresses': "If this is set, cluster components will explicitly advertise "
                                          "node IP as it set in seedbox.",
        'k8s_apiservers_dns_name': "Must be round-robin DNS record. If this is set it will be used by "
                                   "all components to access apiserver instead of hardcoded node list. You can "
                                   "add/remove nodes at any time just by updating DNS record.",
        'k8s_is_rbac_enabled': "Set kube-apiserver authentication mode to RBAC. Otherwise it will be AlwaysAllow.",
        'k8s_admission_control': "Ordered list of plug-ins to do admission control of resources into cluster.",
        'aci_proxy_url': "Docker and rkt will use this proxy to download container images.",
        'aci_proxy_ca_cert': "Docker and rkt download images via HTTPS. If your proxy intercepts "
                             "HTTPS connections you should add proxy CA certificate here. It will be "
                             "added to system root CA certificates on each node.",
    }
    form_rules = [
        rules.Field('name'),
        rules.Field('install_dnsmasq'),
        rules.FieldSet([
            'etcd_image_tag',
            'suppose_etcd_cluster_exists',
            'etcd_nodes_dns_name',
        ], 'etcd'),
        rules.FieldSet([
            'apiservers_audit_log',
            'apiservers_swagger_ui',
            'k8s_pod_network',
            'k8s_service_network',
            'k8s_hyperkube_tag',
            'k8s_cni',
            'k8s_apiservers_dns_name',
            'k8s_is_rbac_enabled',
            'k8s_admission_control',
        ], 'Kubernetes'),
        rules.FieldSet([
            'boot_images_base_url',
            'aci_proxy_url',
            'aci_proxy_ca_cert',
        ], 'Images'),
        rules.FieldSet([
            'dnsmasq_static_records',
            'allow_insecure_provision',
            'explicitly_advertise_addresses',
        ], 'Virtual environment'),
    ]

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

    @property
    def k8s_addons_dict(self):
        return config_renderer.charts.addons
