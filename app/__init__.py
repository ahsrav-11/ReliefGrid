import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login = LoginManager()
login.login_view = "auth.login_view"
csrf = CSRFProtect()


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        # SQLite by default; set DATABASE_URL (e.g. postgresql://user:pw@host/db) to switch with no code change.
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///reliefgrid.db"),
    )
    if config:
        app.config.update(config)
    db.init_app(app)
    login.init_app(app)
    csrf.init_app(app)

    from .blueprints import auth, core, admin, requests_bp, allocation, delivery
    for m in (auth, core, admin, requests_bp, allocation, delivery):
        app.register_blueprint(m.bp)

    @app.context_processor
    def inject_unread():
        from flask_login import current_user
        from .models import Notification
        if current_user.is_authenticated:
            return {"unread": Notification.query.filter_by(user_id=current_user.id, read=False).count()}
        return {"unread": 0}

    with app.app_context():
        db.create_all()
    return app
