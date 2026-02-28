import json
from sqlalchemy import text

class RouteService:
    def __init__(self, session):
        self.session = session

    def get_all_stations(self) -> list:
        query = text("""
            SELECT id, name, latitude as lat, longitude as lon, platform as platforms
            FROM stations
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)
        rows = self.session.execute(query).mappings().all()
        return [dict(r) for r in rows]

    def get_reachable_stations(self, station_name: str) -> list:
        query = text("""
            SELECT DISTINCT s_end.name
            FROM stations s_start
            JOIN route_stops rs_start ON s_start.id = rs_start.station_id
            JOIN route_stops rs_end ON rs_start.trip_id = rs_end.trip_id
            JOIN stations s_end ON rs_end.station_id = s_end.id
            WHERE s_start.name = :station_name
              AND CAST(rs_end.stop_order AS INTEGER) > CAST(rs_start.stop_order AS INTEGER)
        """)

        rows = self.session.execute(query, {"station_name": station_name}).mappings().all()
        return [row['name'] for row in rows]

    def get_reachable_paths(self, station_name: str) -> list:
        id_query = text("SELECT id FROM stations WHERE name = :station_name")
        row = self.session.execute(id_query, {"station_name": station_name}).mappings().first()

        if not row:
            return []

        start_id = row['id']

        reachable_query = text("""
            SELECT DISTINCT rs_end.station_id
            FROM route_stops rs_start
            JOIN route_stops rs_end ON rs_start.trip_id = rs_end.trip_id
            WHERE rs_start.station_id = :start_id
              AND CAST(rs_end.stop_order AS INTEGER) > CAST(rs_start.stop_order AS INTEGER)
        """)
        reachable_rows = self.session.execute(reachable_query, {"start_id": start_id}).mappings().all()
        reachable_ids = [str(r['station_id']) for r in reachable_rows]

        if not reachable_ids:
            return []

        path_query = text(f"""
            SELECT path FROM graph
            WHERE departure = :start_id
            AND arrival IN ({','.join([':id_' + str(i) for i in range(len(reachable_ids))])})
            AND path IS NOT NULL AND path != ''
        """)

        # Build the parameters dictionary
        params = {"start_id": start_id}
        for i, r_id in enumerate(reachable_ids):
            params[f"id_{i}"] = r_id

        path_rows = self.session.execute(path_query, params).mappings().all()

        paths = []
        for r in path_rows:
            try:
                paths.append(json.loads(r['path']))
            except Exception:
                pass

        return paths

    def get_route_between(self, departure_name: str, arrival_name: str, date_str: str = None) -> list:
        dep_query = text("SELECT id FROM stations WHERE name = :name")
        arr_query = text("SELECT id FROM stations WHERE name = :name")

        dep_row = self.session.execute(dep_query, {"name": departure_name}).mappings().first()
        arr_row = self.session.execute(arr_query, {"name": arrival_name}).mappings().first()

        if not dep_row or not arr_row:
            return []

        dep_id = dep_row['id']
        arr_id = arr_row['id']

        # Визначаємо біт дня тижня: пн=0, вт=1, ..., нд=6
        day_bit = None
        if date_str:
            from datetime import date as _date
            try:
                d = _date.fromisoformat(date_str)
                day_bit = d.weekday()  # 0=пн, 6=нд
            except ValueError:
                pass

        trip_query = text("""
            SELECT t.id AS trip_id, t.days_mask, tr.number AS train_number, tr.name AS train_name,
                   tr.has_wifi, tr.has_air_con, tr.has_restaurant, tr.has_bicycle_holder, tr.is_accessible,
                   rs_dep.stop_order AS dep_order, rs_arr.stop_order AS arr_order
            FROM trips t
            JOIN trains tr ON t.train_id = tr.id
            JOIN route_stops rs_dep ON t.id = rs_dep.trip_id AND rs_dep.station_id = :dep_id
            JOIN route_stops rs_arr ON t.id = rs_arr.trip_id AND rs_arr.station_id = :arr_id
            WHERE CAST(rs_dep.stop_order AS INTEGER) < CAST(rs_arr.stop_order AS INTEGER)
        """)

        trips = self.session.execute(trip_query, {"dep_id": dep_id, "arr_id": arr_id}).mappings().all()

        # Фільтруємо по дню тижня якщо дата передана
        if day_bit is not None:
            trips = [t for t in trips if (t['days_mask'] >> day_bit) & 1]

        results = []

        segment_query = text("""
            SELECT s.name AS station, rs.arrival_time, rs.departure_time, CAST(rs.stop_order AS INTEGER) as stop_order
            FROM route_stops rs
            JOIN stations s ON rs.station_id = s.id
            WHERE rs.trip_id = :trip_id
            ORDER BY CAST(rs.stop_order AS INTEGER)
        """)

        for trip_row in trips:
            segment_stops = self.session.execute(segment_query, {
                "trip_id": trip_row['trip_id']
            }).mappings().all()

            route_full = [{"station": rs['station'], "arrival": rs['arrival_time'], "departure": rs['departure_time'], "order": rs['stop_order']} for rs in segment_stops]

            results.append({
                "trip_id": trip_row['trip_id'],
                "train_number": trip_row['train_number'],
                "train_name": trip_row['train_name'],
                "has_wifi": bool(trip_row['has_wifi']),
                "has_air_con": bool(trip_row['has_air_con']),
                "has_restaurant": bool(trip_row['has_restaurant']),
                "has_bicycle": bool(trip_row['has_bicycle_holder']),
                "accessible": bool(trip_row['is_accessible']),
                "route": route_full,
                "dep_order": int(trip_row['dep_order']),
                "arr_order": int(trip_row['arr_order'])
            })

        return results

    def get_specific_path(self, departure_name: str, arrival_name: str) -> list:
        """
        Fetches the exact physical track geometry (polyline) between two stations
        by stitching together paths for each station stop segment along a valid trip.
        Returns a list of coordinate pairs: [[[lat, lon], [lat, lon]], [[lat...]]]
        """
        routes = self.get_route_between(departure_name, arrival_name)
        if not routes:
            return []

        trip = routes[0]
        dep_order = trip["dep_order"]
        arr_order = trip["arr_order"]

        station_names = [
            stop["station"] for stop in trip["route"]
            if stop["order"] >= dep_order and stop["order"] <= arr_order
        ]

        if len(station_names) < 2:
            return []

        placeholders = ', '.join([f":name_{i}" for i in range(len(station_names))])
        params = {f"name_{i}": name for i, name in enumerate(station_names)}

        query = text(f"SELECT id, name FROM stations WHERE name IN ({placeholders})")
        rows = self.session.execute(query, params).mappings().all()
        name_to_id = {r['name']: r['id'] for r in rows}

        path_segments = []

        for i in range(len(station_names) - 1):
            dep_id = name_to_id.get(station_names[i])
            arr_id = name_to_id.get(station_names[i+1])

            if dep_id and arr_id:
                graph_query = text("SELECT path FROM graph WHERE departure = :dep AND arrival = :arr AND path IS NOT NULL AND path != ''")
                g_row = self.session.execute(graph_query, {"dep": dep_id, "arr": arr_id}).mappings().first()
                if g_row and g_row['path']:
                    try:
                        path_data = g_row['path']
                        coords = json.loads(path_data) if isinstance(path_data, str) else path_data
                        if coords:
                            path_segments.append(coords)
                    except Exception as e:
                        print(f"Error parsing path JSON: {e}")

        return path_segments