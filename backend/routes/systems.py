"""System discovery endpoints."""

from flask import Blueprint, jsonify

from ..app import get_repository


bp = Blueprint("systems", __name__)


@bp.get("/systems")
def list_systems():
    repo = get_repository()
    return jsonify(repo.systems())


@bp.get("/systems/<system_id>")
def get_system(system_id):
    repo = get_repository()
    return jsonify(repo.system(system_id))
