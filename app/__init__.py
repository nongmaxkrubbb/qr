from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # เพิ่ม ProxyFix เพื่อให้ Flask รองรับ URL สาธารณะเวลาใช้ Cloudflare/Ngrok
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    app.config.from_object('config.Config')

    from app.database import init_app
    init_app(app)

    from app.routes.user_routes import user_bp
    from app.routes.admin_routes import admin_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    return app
