"""Data retrieval endpoints for system analysis payloads."""

from flask import Blueprint, jsonify, request

from ..app import get_repository


bp = Blueprint("data", __name__)


def atom_pair_params_from_query():
    keys = ["resName1", "resNum1", "chain1", "resName2", "resNum2", "chain2"]
    return {key: request.args.get(key) for key in keys if request.args.get(key) is not None}


def interaction_types_from_request():
    values = request.args.getlist("interaction_types")
    if len(values) == 1 and "," in values[0]:
        values = [item.strip() for item in values[0].split(",")]
    return [value for value in values if value]


@bp.get("/systems/<system_id>/interactions")
def interactions(system_id):
    return jsonify(get_repository().interactions(system_id))


@bp.get("/systems/<system_id>/area")
def area(system_id):
    return jsonify(get_repository().area(system_id))


@bp.get("/systems/<system_id>/trends")
def trends(system_id):
    return jsonify(get_repository().trends(system_id))


@bp.get("/systems/<system_id>/atom-pairs")
def atom_pairs(system_id):
    return jsonify(get_repository().atom_pairs(system_id, atom_pair_params_from_query()))


@bp.post("/systems/<system_id>/atom-pairs/batch")
def atom_pairs_batch(system_id):
    payload = request.get_json(silent=True) or {}
    pairs = payload.get("pairs", payload if isinstance(payload, list) else [])
    return jsonify(get_repository().atom_pairs_batch(system_id, pairs))


@bp.get("/systems/<system_id>/interaction-distances")
def interaction_distances(system_id):
    return jsonify(get_repository().interaction_distances(system_id))


@bp.get("/systems/<system_id>/distance-distributions")
def distance_distributions(system_id):
    return jsonify(get_repository().distance_distributions(system_id, interaction_types_from_request()))


@bp.get("/systems/<system_id>/conserved-islands")
def conserved_islands(system_id):
    get_repository().validate_system(system_id)
    return jsonify({"system": system_id, "islands": []})


@bp.get("/systems/<system_id>/frame/<int:frame_number>/pdb")
def frame_pdb(system_id, frame_number):
    get_repository().validate_system(system_id)
    return jsonify({"error": f"No PDB viewer file is bundled for frame {frame_number}."}), 404

