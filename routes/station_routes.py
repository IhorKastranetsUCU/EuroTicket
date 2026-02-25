from flask import Blueprint, jsonify, request
from db_helpers import get_route_service

station_bp = Blueprint('stations', __name__)


@station_bp.route('/api/stations')
def get_stations():
    service = get_route_service()
    return jsonify(service.get_all_stations())


@station_bp.route('/api/reachable')
def get_reachable():
    name = request.args.get('name')
    if not name:
        return jsonify([])
    service = get_route_service()
    return jsonify(service.get_reachable_stations(name))


@station_bp.route('/api/reachable_paths')
def get_reachable_paths():
    name = request.args.get('name')
    if not name:
        return jsonify([])
    service = get_route_service()
    return jsonify(service.get_reachable_paths(name))