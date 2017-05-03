from flask_admin import Admin

from seedbox import models, config
from .cluster import ClusterView
from .node import NodeView
from .user import UserView
from .credentials_data import CredentialsDataView
from .provision import ProvisionView


admin = Admin(name='seedbox', url=config.admin_base_url, template_mode='bootstrap3')
admin.add_view(ClusterView(models.Cluster, models.db.session))
admin.add_view(NodeView(models.Node, models.db.session))
admin.add_view(UserView(models.User, models.db.session))
admin.add_view(CredentialsDataView(models.CredentialsData, models.db.session))
admin.add_view(ProvisionView(models.Provision, models.db.session))
