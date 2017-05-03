import json
import logging

from flask import request, flash, redirect
from flask_admin import expose
from flask_admin.form import rules
from flask_admin.helpers import get_redirect_target
from flask_admin.model.template import macro

from seedbox import pki, models, config_renderer, config
from .base import ModelView

log = logging.getLogger()


class ClusterView(ModelView):
    column_list = ['name', 'ca_credentials', 'is_configured', 'assert_etcd_cluster_exists', 'info']
    list_template = 'admin/cluster_list.html'
    details_template = 'admin/cluster_details.html'
    form_excluded_columns = [
        'ca_credentials',
        'nodes',
        'users',
        'k8s_service_account_public_key',
        'k8s_service_account_private_key',
    ]
    column_formatters = {
        'ca_credentials': macro('render_ca_credentials'),
        'info': macro('render_info'),
    }
    column_labels = {
        'ca_credentials': "CA credentials",
        'etcd_image_tag': "etcd image tag",
        'assert_etcd_cluster_exists': "Assert etcd cluster already exists",
        'etcd_nodes_dns_name': "DNS name of any etcd node",
        'install_dnsmasq': "Install dnsmasq on cluster nodes",
        'k8s_apiservers_audit_log': "Enable audit log on apiservers",
        'k8s_apiservers_swagger_ui': "Enable Swagger-UI on apiservers",
        'dnsmasq_static_records': "Add static records to dnsmasq",
        'explicitly_advertise_addresses': "Explicitly advertise addresses",
        'k8s_pod_network': "Pod network CIDR",
        'k8s_service_network': "Service network CIDR",
        'k8s_hyperkube_tag': "Hyperkube image tag",
        'k8s_cni': "Use CNI",
        'k8s_apiservers_dns_name': "DNS name of any master node",
        'k8s_is_rbac_enabled': "Enable RBAC",
        'k8s_admission_control': "Admission control",
        'custom_coreos_images_base_url': "Custom base HTTP URL of CoreOS images",
        'aci_proxy_url': "ACI proxy URL",
        'aci_proxy_ca_cert': "ACI proxy CA certificate (PEM)",
        'coreos_channel': 'CoreOS channel',
        'coreos_version': 'CoreOS version',
    }
    column_descriptions = {
        'name': "Human readable cluster name. Don't use spaces.",
        'assert_etcd_cluster_exists': "This will set `initial-cluster-state` to `existing` for newly provisioned "
                                      "etcd members. Use it to add etcd members to existing cluster.",
        'etcd_nodes_dns_name': "Must be round-robin DNS record. If this is set it will be used by "
                               "all components to access etcd instead of hardcoded node list. You can "
                               "add/remove nodes at any time just by updating DNS record.",
        'install_dnsmasq': "If this is set, dnsmasq will be run on each node for resolving cluster.local zone "
                           "using k8s DNS and for DNS caching.",
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
        'custom_coreos_images_base_url': "coreos_production_pxe.vmlinuz and coreos_production_pxe_image.cpio.gz. It "
                                         "will be used instead of default if set.",
        'coreos_channel': 'stable, beta or alpha',
    }
    form_rules = [
        rules.Field('name'),
        rules.Field('install_dnsmasq'),
        rules.FieldSet([
            'etcd_image_tag',
            'assert_etcd_cluster_exists',
            'etcd_nodes_dns_name',
        ], 'etcd'),
        rules.FieldSet([
            'k8s_apiservers_audit_log',
            'k8s_apiservers_swagger_ui',
            'k8s_pod_network',
            'k8s_service_network',
            'k8s_hyperkube_tag',
            'k8s_cni',
            'k8s_apiservers_dns_name',
            'k8s_is_rbac_enabled',
            'k8s_admission_control',
        ], 'Kubernetes'),
        rules.FieldSet([
            'coreos_channel',
            'coreos_version',
            'custom_coreos_images_base_url',
            'aci_proxy_url',
            'aci_proxy_ca_cert',
        ], 'Images'),
        rules.FieldSet([
            'dnsmasq_static_records',
            'explicitly_advertise_addresses',
        ], 'Testing environment'),
    ]

    def _issue_creds(self, model):
        ca = models.CredentialsData()
        ca.cert, ca.key = pki.create_ca_certificate(model.name,
                                                    certify_days=10000)
        self.session.add(ca)
        model.ca_credentials = ca
        model.k8s_service_account_public_key, model.k8s_service_account_private_key = pki.generate_rsa_keypair()

    def on_model_change(self, form, model, is_created):
        if is_created:
            self._issue_creds(model)
        else:
            model.nodes.update({models.Node.target_config_version: models.Node.target_config_version + 1})

    def after_model_delete(self, model):
        models.CredentialsData.query.filter_by(id=model.ca_credentials_id).delete()

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

    @expose('/reset-state', methods=['POST'])
    def reset_state(self):
        model = self.get_one(request.args.get('id'))
        model.nodes.update({
            models.Node.target_config_version: 1,
            models.Node.active_config_version: 0,
            models.Node.wipe_root_disk_next_boot: config.default_wipe_root_disk_next_boot,
        })
        model.assert_etcd_cluster_exists = False
        self.session.add(model)
        self.session.commit()
        return_url = get_redirect_target() or self.get_url('.index_view')
        flash('The cluster state has been successfully reset', 'success')
        return redirect(return_url)

    @property
    def latest_component_versions(self):
        try:
            with open(config.update_state_file, 'r') as fp:
                return json.load(fp)
        except Exception:
            log.exception('Failed to load component versions file')
            return {}
