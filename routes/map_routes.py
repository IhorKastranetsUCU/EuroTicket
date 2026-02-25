from flask import Blueprint, request, render_template
from db_helpers import get_route_service
from services.map_builder import MapBuilder

map_bp = Blueprint('map', __name__)


@map_bp.route('/')
def index():
    return render_template('index.html')


@map_bp.route('/api/map')
def get_map():
    from_station = request.args.get('from_station')
    to_station = request.args.get('to_station')
    time_str = request.args.get('time')
    map_theme = request.args.get('map_theme', 'light')

    service = get_route_service()
    builder = MapBuilder(service, map_theme)

    folium_map = builder.build(
        from_station=from_station,
        to_station=to_station,
        time_str=time_str,
    )
    return folium_map.get_root().render()