from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
import os

app = Flask(__name__)

engine = create_engine("sqlite:///EuroTicket.db")
Session = sessionmaker(bind=engine)


def get_session():
    return Session()


# Load station data from JSON
with open("railway_stations.json", "r", encoding="utf-8") as f:
    STATIONS_JSON = json.load(f)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stations")
def get_stations():
    """Return all stations with their coordinates and platform info"""
    session = get_session()
    try:
        from SQL_fill import Station
        stations = session.query(Station).all()
        result = []
        for s in stations:
            if s.name in STATIONS_JSON:
                coords = STATIONS_JSON[s.name]
                result.append({
                    "id": s.id,
                    "name": s.name,
                    "lat": s.latitude or coords["lat"],
                    "lon": s.longitude or coords["lon"],
                    "platforms": s.platform or 1
                })
            elif s.latitude and s.longitude:
                result.append({
                    "id": s.id,
                    "name": s.name,
                    "lat": s.latitude,
                    "lon": s.longitude,
                    "platforms": s.platform or 1
                })
        return jsonify(result)
    finally:
        session.close()


@app.route("/api/reachable")
def get_reachable():
    """Get all reachable stations from a given station"""
    station_name = request.args.get("from", "")
    if not station_name:
        return jsonify([])

    session = get_session()
    try:
        from SQL_fill import Station, RouteStop
        start_station = session.query(Station).filter_by(name=station_name).first()
        if not start_station:
            return jsonify([])

        reachable = set()
        stops = session.query(RouteStop).filter_by(station_id=start_station.id).all()

        for stop in stops:
            next_stops = (session.query(RouteStop).filter(
                RouteStop.trip_id == stop.trip_id,
                RouteStop.stop_order > stop.stop_order
            ).all())
            for ns in next_stops:
                reachable.add(ns.station.name)

        return jsonify(list(reachable))
    finally:
        session.close()


@app.route("/api/routes")
def get_routes():
    """Get all routes between two stations"""
    departure_name = request.args.get("from", "")
    arrival_name = request.args.get("to", "")

    if not departure_name or not arrival_name:
        return jsonify([])

    session = get_session()
    try:
        from SQL_fill import Station, Trip, RouteStop

        departure = session.query(Station).filter_by(name=departure_name).first()
        arrival = session.query(Station).filter_by(name=arrival_name).first()

        if not departure or not arrival:
            return jsonify([])

        trips = session.query(Trip).all()
        results = []

        for trip in trips:
            stops = trip.stops
            dep_stop = next((s for s in stops if s.station_id == departure.id), None)
            arr_stop = next((s for s in stops if s.station_id == arrival.id), None)

            if dep_stop and arr_stop and dep_stop.stop_order < arr_stop.stop_order:
                route_segment = [
                    {
                        "station": s.station.name,
                        "arrival": s.arrival_time.strftime("%H:%M") if s.arrival_time else None,
                        "departure": s.departure_time.strftime("%H:%M") if s.departure_time else None
                    }
                    for s in stops
                    if dep_stop.stop_order <= s.stop_order <= arr_stop.stop_order
                ]

                results.append({
                    "train_number": trip.train.number,
                    "train_name": trip.train.name,
                    "has_wifi": trip.train.has_wifi,
                    "has_air_con": trip.train.has_air_con,
                    "has_restaurant": trip.train.has_restaurant,
                    "has_bicycle_holder": trip.train.has_bicycle_holder,
                    "is_accessible": trip.train.is_accessible,
                    "route": route_segment
                })

        return jsonify(results)
    finally:
        session.close()


if __name__ == "__main__":
    app.run(debug=True)