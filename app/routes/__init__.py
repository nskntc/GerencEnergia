from .auth_routes import bp as auth_bp
from .admin_routes import bp as admin_bp
from .cliente_routes import bp as cliente_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(cliente_bp, url_prefix='/cliente')