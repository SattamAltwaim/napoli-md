"""Application factory for the Flask REST API."""

import os
from pathlib import Path

from flask import Flask, current_app, jsonify
from flask_cors import CORS

from .data_loader import DataNotFoundError, TrajectoryRepository, UnknownSystemError


DEFAULT_DATA_ROOT = (
    Path(__file__).resolve().parents[1]
    / "frontend"
    / "public"
    / "data"
    / "simulated_trajectory_8cgk_6UQ"
)


def get_repository():
    data_root = Path(current_app.config["DATA_ROOT"]).resolve()
    repo = current_app.extensions.get("trajectory_repository")

    if repo is None or repo.data_root != data_root:
        repo = TrajectoryRepository(data_root)
        current_app.extensions["trajectory_repository"] = repo

    return repo


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATA_ROOT=Path(os.environ.get("NAPOLI_DATA_ROOT", DEFAULT_DATA_ROOT)).resolve(),
        MAX_CONTENT_LENGTH=200 * 1024 * 1024,
    )

    if config:
        app.config.update(config)

    CORS(app)

    from .routes.data import bp as data_bp
    from .routes.systems import bp as systems_bp
    from .routes.upload import bp as upload_bp

    app.register_blueprint(systems_bp, url_prefix="/api")
    app.register_blueprint(data_bp, url_prefix="/api")
    app.register_blueprint(upload_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "dataRoot": str(app.config["DATA_ROOT"])})

    @app.errorhandler(UnknownSystemError)
    def handle_unknown_system(error):
        return jsonify({"error": str(error)}), 404

    @app.errorhandler(DataNotFoundError)
    def handle_data_not_found(error):
        return jsonify({"error": str(error)}), 404

    return app

