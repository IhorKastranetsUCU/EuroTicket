from SQL_fill import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class RouteService:
    def __init__(self, session):
        self.session = session

    def get_reachable_stations(self, station_name: str):
        """Function to receive all the station that possible to reach from the given station
        :param station_name: Name of the station you look paths from

        >>> engine = create_engine("sqlite:///EuroTicket1.db")
        >>> Session = sessionmaker(bind=engine)
        >>> session = Session()
        >>> db = RouteService(session)
        >>> db.get_reachable_stations("Zlochiv")
        ['Lviv', 'Przemyśl Główny']
        """
        start_station = self.session.query(Station).filter_by(name=station_name).first()
        if not start_station:
            return []

        reachable = set()

        stops = self.session.query(RouteStop).filter_by(station_id=start_station.id).all()

        for stop in stops:
            next_stops = (self.session.query(RouteStop).filter(RouteStop.trip_id == stop.trip_id,RouteStop.stop_order > stop.stop_order).all())

            for ns in next_stops:
                reachable.add(ns.station.name)

        return list(reachable)


    def get_route_between(self, departure_name: str, arrival_name: str) -> list[dict]:
        """
        All the possible routes between two given stations
        :param departure_name: Name of the departure station
        :param arrival_name: Name of the arrival station

        >>> engine = create_engine("sqlite:///EuroTicket1.db")
        >>> Session = sessionmaker(bind=engine)
        >>> session = Session()
        >>> db = RouteService(session)
        >>> db.get_route_between("Zlochiv", "Przemyśl Główny")
        [{'train_number': '33006', 'train_name': None, 'has_wifi': True, 'has_air_con': True, 'route': [{'station': 'Zlochiv', 'arrival': None, 'departure': datetime.time(6, 27)}, {'station': 'Lviv', 'arrival': None, 'departure': datetime.time(9, 0)}, {'station': 'Przemyśl Główny', 'arrival': datetime.time(11, 20), 'departure': None}]}]

        """
        departure = self.session.query(Station).filter_by(name=departure_name).first()
        arrival = self.session.query(Station).filter_by(name=arrival_name).first()

        if not departure or not arrival:
            return []

        trips = self.session.query(Trip).all()
        results = []

        for trip in trips:
            stops = trip.stops

            dep_stop = next((s for s in stops if s.station_id == departure.id), None)
            arr_stop = next((s for s in stops if s.station_id == arrival.id), None)

            if dep_stop and arr_stop and dep_stop.stop_order < arr_stop.stop_order:

                route_segment = [
                    {
                        "station": s.station.name,
                        "arrival": s.arrival_time,
                        "departure": s.departure_time
                    }
                    for s in stops
                    if dep_stop.stop_order <= s.stop_order <= arr_stop.stop_order
                ]

                results.append({
                    "train_number": trip.train.number,
                    "train_name": trip.train.name,
                    "has_wifi": trip.train.has_wifi,
                    "has_air_con": trip.train.has_air_con,
                    "route": route_segment
                })

        return results

""" part of the code to set up the session with DB
engine = create_engine("sqlite:///EuroTicket1.db")
Session = sessionmaker(bind=engine)
session = Session()

db = RouteService(session)
"""


