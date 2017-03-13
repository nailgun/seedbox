from flask_admin import Admin
from flask_admin.contrib.fileadmin import FileAdmin

from seedbox import config, models
from .cluster import ClusterView
from .node import NodeView
from .user import UserView
from .credentials_data import CredentialsDataView


admin = Admin(name='seedbox', template_mode='bootstrap3')
admin.add_view(ClusterView(models.Cluster, models.db.session))
admin.add_view(NodeView(models.Node, models.db.session))
admin.add_view(UserView(models.User, models.db.session))
admin.add_view(CredentialsDataView(models.CredentialsData, models.db.session))
admin.add_view(FileAdmin(config.cachedir, '/cache/', name='Image cache'))
