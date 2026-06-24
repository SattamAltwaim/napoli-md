"""Upload and job endpoints.

The bundled project does not include the processing engine described by the
original backend README, so upload endpoints are intentionally inert.
"""

from flask import Blueprint, jsonify


bp = Blueprint("upload", __name__)


@bp.post("/upload")
def upload():
    return jsonify({"error": "Upload processing is not available in this bundled Flask backend."}), 501


@bp.get("/status/<job_id>")
def status(job_id):
    return jsonify({"jobId": job_id, "status": "unavailable", "progress": 0})


@bp.get("/jobs")
def jobs():
    return jsonify([])

