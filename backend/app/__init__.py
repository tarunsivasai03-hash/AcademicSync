"""
Flask application factory.
All extensions are initialised here; routes are registered via blueprints.
"""
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

load_dotenv()

from config import config_map
from app.extensions import db, migrate, jwt, bcrypt


# Path to the academic_system frontend folder (two levels up from this file)
_FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'academic_system')
)


def create_app(env: str = "default") -> Flask:
    app = Flask(__name__)

    # ── Load config ────────────────────────────────────────────────────────
    app.config.from_object(config_map[env])

    # Allow .env values to explicitly override config-class defaults
    app.config["SECRET_KEY"]     = os.getenv("SECRET_KEY")     or app.config["SECRET_KEY"]
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY") or app.config["JWT_SECRET_KEY"]

    # ── Ensure upload folder exists ────────────────────────────────────────
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Initialise extensions ──────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # Parse CORS origins — .env may set a comma-separated string; config.py may set a list
    cors_origins = app.config.get("CORS_ORIGINS", [])
    if isinstance(cors_origins, str):
        cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]

    _cors_kwargs = dict(
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    if "*" in cors_origins:
        # Wildcard origin — used for LAN/Wi-Fi dev testing.
        # browsers reject Access-Control-Allow-Credentials: true with origin *, so
        # we must omit supports_credentials here.
        CORS(app, origins="*", **_cors_kwargs)
    else:
        CORS(app, origins=cors_origins, supports_credentials=True, **_cors_kwargs)

    # ── JWT error handlers ─────────────────────────────────────────────────
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authentication required", "reason": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "Invalid token", "reason": reason}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return jsonify({"error": "Token has been revoked"}), 401

    # ── Global error handlers ──────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify({"error": "File too large. Maximum size is 16 MB."}), 413

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    # ── Serve frontend static files ────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(_FRONTEND_DIR, 'login.html')

    @app.route("/<path:filename>")
    def frontend_static(filename):
        return send_from_directory(_FRONTEND_DIR, filename)

    # ── Register blueprints ────────────────────────────────────────────────
    from app.routes.auth_routes import auth_bp
    from app.routes.student_routes import student_bp
    from app.routes.faculty_routes import faculty_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.common_routes import common_bp

    app.register_blueprint(auth_bp,    url_prefix="/api/auth")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(faculty_bp, url_prefix="/api/faculty")
    app.register_blueprint(admin_bp,   url_prefix="/api/admin")
    app.register_blueprint(common_bp,  url_prefix="/api")

    # ── Import all models so Flask-Migrate can detect them ─────────────────
    with app.app_context():
        from app.models import (         # noqa: F401  (side-effect import)
            user, course, assignment, submission,
            attendance, task, resource, notification, schedule,
        )

    return app
