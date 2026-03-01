from datetime import timedelta
from live_trains import calculate_train_position, parse_time


class TrainTracker:

    def __init__(self, route_service, current_time):
        self.service = route_service
        self.current_time = current_time

    def get_active_trains(self, from_station: str, to_station: str, time_str: str | None, date_str: str | None = None) -> list[dict]:
        trips = self.service.get_route_between(from_station, to_station, date_str)
        active_trains = []

        for trip in trips:
            train_data = self._process_trip(trip, time_str)
            if train_data:
                active_trains.append(train_data)

        return active_trains

    def _process_trip(self, trip: dict, time_str: str | None) -> dict | None:
        dep_order = int(trip["dep_order"])
        arr_order = int(trip["arr_order"])
        trip_id = trip["trip_id"]

        dep_stop = next((s for s in trip["route"] if s["order"] == dep_order), None)
        arr_stop = next((s for s in trip["route"] if s["order"] == arr_order), None)

        if not dep_stop or not arr_stop:
            return None

        t_dep = parse_time(dep_stop["departure"] or dep_stop["arrival"])
        t_arr = parse_time(arr_stop["arrival"] or arr_stop["departure"])

        if not t_dep or not t_arr:
            return None

        if t_arr < t_dep:
            t_arr += timedelta(days=1)

        current = self.current_time
        if current < t_dep and (t_dep - current).total_seconds() > 12 * 3600:
            current += timedelta(days=1)

        if not (t_dep <= current <= t_arr):
            return None

        return self._build_train_entry(trip, trip_id, time_str)

    @staticmethod
    def _build_train_entry(trip: dict, trip_id: int, time_str: str | None) -> dict | None:
        feature = calculate_train_position(trip_id, current_time_str=time_str)
        if not feature:
            return None

        props = feature["properties"]
        lat = feature["geometry"]["coordinates"][1]
        lon = feature["geometry"]["coordinates"][0]

        return {
            "trip_id": trip_id,
            "train_number": trip["train_number"],
            "lat": lat,
            "lon": lon,
            "previous_station": props["previous_station"],
            "next_station": props["next_station"],
            "speed_ratio": props["current_speed_ratio"],
        }