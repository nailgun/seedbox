import os
import base64
import inspect
import urllib.parse
from jinja2 import Environment, ChoiceLoader, FileSystemLoader


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
        jinja = Environment(loader=self.get_template_loader(),
                            keep_trailing_newline=True,
                            autoescape=False)
        return jinja.get_template(name).render(self.get_template_context())

    def get_template_loader(self):
        template_roots = []

        cls = self.__class__
        while True:
            template_roots.append(os.path.dirname(inspect.getfile(cls)))
            cls = get_base_class(cls)
            if cls in (BaseIgnitionPackage, None):
                break

        return ChoiceLoader([FileSystemLoader(root) for root in template_roots])

    @staticmethod
    def to_data_url(data, mediatype='', b64=False):
        if b64:
            if not isinstance(data, bytes):
                data = data.encode('utf-8')
            return 'data:{};base64,{}'.format(mediatype, base64.b64encode(data).decode('ascii'))
        else:
            return 'data:{},{}'.format(mediatype, urllib.parse.quote(data))


def get_base_class(cls):
    for base in cls.__bases__:
        if issubclass(base, BaseIgnitionPackage):
            return base
    return None
