from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta

from db_helpers import get_route_service
from live_trains import calculate_train_position, parse_time
from services.train_tracker import TrainTracker

train_bp = Blueprint('trains', __name__)


@train_bp.route('/api/route_trains')
def get_route_trains():
    from_station = request.args.get('from_station')
    to_station = request.args.get('to_station')
    date_str = request.args.get('date')

    if not from_station or not to_station:
        return jsonify([])

    service = get_route_service()
    return jsonify(service.get_route_between(from_station, to_station, date_str))


@train_bp.route('/api/train_positions')
def get_train_positions():
    from_station = request.args.get('from_station')
    to_station = request.args.get('to_station')
    time_str = request.args.get('time')
    date_str = request.args.get('date')

    if not from_station or not to_station:
        return jsonify([])

    service = get_route_service()
    current_time = parse_time(time_str) if time_str else (datetime.now() - timedelta(hours=1))

    tracker = TrainTracker(service, current_time)
    active_trains = tracker.get_active_trains(from_station, to_station, time_str, date_str)

    return jsonify(active_trains)