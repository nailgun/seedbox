import json

from flask import request, Response
from flask_admin import expose
from flask_admin.model.template import macro

from .base import ModelView
from seedbox import ignition_parser


class ProvisionView(ModelView):
    column_list = ['applied_at', 'config_version', 'data']
    column_details_list = ['applied_at', 'config_version', 'data']
    column_default_sort = ('applied_at', True)
    list_template = 'admin/provision_list.html'
    details_template = 'admin/provision_details.html'
    column_formatters = {
        'data': macro('render_data'),
    }

    def get_query(self):
        query = super().get_query()
        node_id = request.args.get('node_id')
        if node_id:
            query = query.filter_by(node_id=node_id)
        return query

    @expose('/ipxe')
    def raw_ipxe_view(self):
        provision = self.get_one(request.args.get('id'))
        return Response(provision.ipxe_config, mimetype='text/plain')

    @expose('/ignition.json')
    def raw_ignition_view(self):
        provision = self.get_one(request.args.get('id'))
        data = json.loads(provision.ignition_config)
        data = json.dumps(data, indent=2)
        return Response(data, mimetype='application/json')

    @expose('/ignition.tar.gz')
    def ignition_filesystem_view(self):
        provision = self.get_one(request.args.get('id'))
        tgz_data = ignition_parser.render_ignition_tgz(json.loads(provision.ignition_config))
        return Response(tgz_data, mimetype='application/tar+gzip')

    def is_visible(self):
        return False
