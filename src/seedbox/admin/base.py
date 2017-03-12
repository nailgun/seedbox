from flask_admin.contrib.sqla import ModelView as BaseModelView


class ModelView(BaseModelView):
    can_view_details = True
