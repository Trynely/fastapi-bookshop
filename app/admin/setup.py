from sqladmin import Admin
from app.admin.registry import ADMIN_VIEWS
from app.core.db.postgres import db_helper
from app.admin.auth import authentication_backend

def init_admin(app, templates_path):
    admin = Admin(
        app=app,
        engine=db_helper.engine,
        authentication_backend=authentication_backend,
        templates_dir=str(templates_path),
    )

    for view in ADMIN_VIEWS:
        admin.add_view(view)

    return admin
