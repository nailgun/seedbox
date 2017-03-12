from flask import request, Response
from flask_admin import expose
from flask_admin.model.template import macro

from seedbox import pki
from .base import ModelView


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
