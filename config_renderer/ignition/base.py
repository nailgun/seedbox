import base64
import urllib.parse


class BaseIgnitionPackage(object):
    name = None
    template_context = {}

    def get_files(self):
        return ()

    def get_units(self):
        return ()

    def get_unit(self, name, enable=False, dropins=None):
        if dropins:
            return {
                'name': name,
                'enable': enable,
                'dropins': [{
                    'name': dropin,
                    'contents': self.render_template(dropin),
                } for dropin in dropins],
            }
        else:
            return {
                'name': name,
                'enable': enable,
                'contents': self.render_template(name),
            }

    def get_template_context(self):
        return self.template_context

    def render_template(self, name):
        from config_renderer import jinja
        return jinja.get_template(self.name + '/' + name).render(self.get_template_context())

    @staticmethod
    def to_data_url(data, mediatype='', b64=False):
        if b64:
            if not isinstance(data, bytes):
                data = data.encode('utf-8')
            return 'data:{};base64,{}'.format(mediatype, base64.b64encode(data).decode('ascii'))
        else:
            return 'data:{},{}'.format(mediatype, urllib.parse.quote(data))
