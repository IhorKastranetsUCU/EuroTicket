import json
import math
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, MetaData, Table, select

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'EuroTicket_2.db')

engine = create_engine(f"sqlite:///{db_path}")

metadata = MetaData()
stations_table = Table('stations', metadata, autoload_with=engine)
route_stops_table = Table('route_stops', metadata, autoload_with=engine)
graph_table = Table('graph', metadata, autoload_with=engine)

def get_db_connection():
    return engine.connect()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0

    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def calculate_traveled_distance(elapsed_seconds, total_seconds, total_segment_distance):
    if total_seconds <= 0:
        return total_segment_distance

    speed_ratio = elapsed_seconds / total_seconds
    speed_ratio = max(0.0, min(1.0, speed_ratio))

    return speed_ratio * total_segment_distance, speed_ratio

def parse_time(time_val):
    if not time_val:
        return None
    if isinstance(time_val, str):
        try:
            time_obj = datetime.strptime(time_val, '%H:%M:%S.%f').time()
        except ValueError:
            try:
                time_obj = datetime.strptime(time_val, '%H:%M:%S').time()
            except ValueError:
                return None
    else:
        time_obj = time_val
    return datetime.combine(datetime.today(), time_obj)

def get_active_segment(conn, trip_id, current_time):
    j = route_stops_table.join(stations_table, route_stops_table.c.station_id == stations_table.c.id)
    query = select(
        route_stops_table.c.id,
        route_stops_table.c.station_id,
        stations_table.c.name,
        route_stops_table.c.arrival_time,
        route_stops_table.c.departure_time,
        route_stops_table.c.stop_order,
        stations_table.c.latitude,
        stations_table.c.longitude
    ).select_from(j).where(route_stops_table.c.trip_id == trip_id).order_by(route_stops_table.c.stop_order)

    stops = conn.execute(query).fetchall()

    if not stops:
        return None, None, None

    for i in range(len(stops) - 1):
        dep_stop = stops[i]
        arr_stop = stops[i + 1]

        dep_time_str = dep_stop[4]
        arr_time_str = arr_stop[3] or arr_stop[4]

        if not dep_time_str or not arr_time_str:
            continue

        dep_time = parse_time(dep_time_str)
        arr_time = parse_time(arr_time_str)

        if arr_time < dep_time:
            arr_time += timedelta(days=1)

        c_time = current_time
        if c_time < dep_time and (dep_time - c_time).total_seconds() > 12 * 3600:
            c_time += timedelta(days=1)

        if dep_time <= c_time <= arr_time:
            dep_station_id = dep_stop[1]
            arr_station_id = arr_stop[1]

            graph_query = select(graph_table.c.path, graph_table.c.maxspeed).where(
                (graph_table.c.departure == dep_station_id) &
                (graph_table.c.arrival == arr_station_id))

            graph_row = conn.execute(graph_query).fetchone()

            track_path = []
            if graph_row and graph_row[0]:
                if isinstance(graph_row[0], str):
                    track_path = json.loads(graph_row[0])
                else:
                    track_path = graph_row[0]

            return {
                'station_id': dep_station_id,
                'name': dep_stop[2],
                'time': dep_time,
                'coords': (dep_stop[6], dep_stop[7]),
                'stop_order': dep_stop[5]
            }, {
                'station_id': arr_station_id,
                'name': arr_stop[2],
                'time': arr_time,
                'coords': (arr_stop[6], arr_stop[7]),
                'stop_order': arr_stop[5]
            }, track_path

    return None, None, None

def calculate_train_position(trip_id, current_time_str=None):
    if current_time_str:
        current_time = parse_time(current_time_str)
    else:
        current_time = datetime.now() - timedelta(hours=1)

    conn = get_db_connection()

    try:
        dep_info, arr_info, track_path = get_active_segment(conn, trip_id, current_time)

        if not dep_info or not arr_info:
            return None

        elapsed_seconds = (current_time - dep_info['time']).total_seconds()
        total_seconds = (arr_info['time'] - dep_info['time']).total_seconds()
        if not track_path or len(track_path) < 2:
            track_path = [dep_info['coords'], arr_info['coords']]

        total_distance = 0
        segment_distances = []
        for i in range(len(track_path) - 1):
            p1 = track_path[i]
            p2 = track_path[i + 1]
            dist = haversine(p1[0], p1[1], p2[0], p2[1])
            segment_distances.append(dist)
            total_distance += dist

        traveled_distance, speed_ratio = calculate_traveled_distance(elapsed_seconds, total_seconds, total_distance)

        current_distance = 0
        current_coord = track_path[-1]

        for i, dist in enumerate(segment_distances):
            if current_distance + dist >= traveled_distance:
                overshoot = traveled_distance - current_distance

                segment_ratio = overshoot / dist if dist > 0 else 0

                p1_lat, p1_lon = track_path[i]
                p2_lat, p2_lon = track_path[i + 1]

                interp_lat = p1_lat + (p2_lat - p1_lat) * segment_ratio
                interp_lon = p1_lon + (p2_lon - p1_lon) * segment_ratio

                current_coord = (interp_lat, interp_lon)
                break

            current_distance += dist

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [current_coord[1], current_coord[0]]
            },
            "properties": {
                "trip_id": trip_id,
                "current_speed_ratio": round(speed_ratio, 4),
                "next_station": arr_info['name'],
                "next_station_id": arr_info['station_id'],
                "previous_station": dep_info['name'],
                "dep_stop_order": int(dep_info['stop_order']),
                "arr_stop_order": int(arr_info['stop_order']),
                "delay_status": "on_time",
                "calculated_at": current_time.strftime('%H:%M:%S')
            }
        }

        return feature

    finally:
        conn.close()

def export_geojson(features, filename='live_trains.geojson'):
    feature_collection = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(feature_collection, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(features)} trains to {filename}")
    return json.dumps(feature_collection, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    sample_trip_id = 52
    time_to_check = '17:25:00'

    print(f"Calculating position for Trip {sample_trip_id} at {time_to_check}...")
    feature = calculate_train_position(sample_trip_id, time_to_check)

    if feature:
        export_geojson([feature])
    else:
        print("Train is not active at the given time or trip not found.")
