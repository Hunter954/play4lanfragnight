import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def bootstrap_database():
    """Cria tabelas e registros mínimos quando o banco estiver vazio."""
    from .models import User, SiteSetting

    db.create_all()

    if not User.query.filter_by(email='admin@play4lan.local').first():
        admin = User(
            name='Administrador',
            email='admin@play4lan.local',
            password_hash=generate_password_hash('123456'),
            is_admin=True,
            phone='5545999999999',
        )
        db.session.add(admin)

    default_settings = {
        'site_name': 'Play4Lan FragNight',
        'hero_title': 'Reserve sua máquina para o próximo FragNight',
        'hero_subtitle': 'Escolha seu setup como no cinema, pague online e confirme sua vaga.',
        'support_whatsapp': '',
        'pix_label': 'Mercado Pago',
        'mp_access_token': '',
        'mp_public_key': '',
        'zapi_instance_id': '',
        'zapi_instance_token': '',
        'zapi_client_token': '',
    }

    secret_keys = {'mp_access_token', 'zapi_instance_id', 'zapi_instance_token', 'zapi_client_token'}
    for key, value in default_settings.items():
        if not SiteSetting.query.filter_by(key=key).first():
            SiteSetting.set(key, value, is_secret=key in secret_keys)

    db.session.commit()


def create_app():
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    database_url = os.getenv('DATABASE_URL', 'sqlite:///play4lan.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/data/uploads')
    app.config['APP_BASE_URL'] = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        bootstrap_database()

    from .routes import site_bp, auth_bp, admin_bp, payment_bp
    app.register_blueprint(site_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(payment_bp, url_prefix='/payments')

    @app.context_processor
    def inject_globals():
        from .models import SiteSetting, FragNightEvent
        settings = SiteSetting.get_dict()
        active_event = FragNightEvent.query.filter_by(is_active=True).order_by(FragNightEvent.event_date.asc()).first()
        return {'site_settings': settings, 'active_event_global': active_event}

    return app
