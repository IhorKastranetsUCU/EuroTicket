from sqlalchemy import Column, Integer, String, JSON, Float, ForeignKey, Time, Date, Boolean, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
import json

Base = declarative_base()


class Station(Base):
    __tablename__ = 'stations'

    id = Column(Integer,  primary_key=True)
    name = Column(String, nullable=False, index=True)
    platform = Column(Integer)
    latitude = Column(Float)
    longitude = Column(Float)
    stops = relationship("RouteStop", back_populates="station")


class Train(Base):
    __tablename__ = 'trains'

    id = Column(Integer, primary_key=True)
    number = Column(String, nullable=False)
    name = Column(String)

    has_wifi = Column(Boolean, default=False)
    has_air_con = Column(Boolean, default=False)
    has_restaurant = Column(Boolean, default=False)
    has_bicycle_holder = Column(Boolean, default=False)
    is_accessible = Column(Boolean, default=False)
    trips = relationship("Trip", back_populates="train")


class Trip(Base):
    __tablename__ = 'trips'

    id = Column(Integer, primary_key=True)
    train_id = Column(Integer, ForeignKey('trains.id'))
    days_mask = Column(Integer, default=127)

    train = relationship("Train", back_populates="trips")
    stops = relationship("RouteStop", back_populates="trip", order_by="RouteStop.stop_order")


class RouteStop(Base):
    __tablename__ = 'route_stops'

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey('trips.id'), index=True)
    station_id = Column(Integer, ForeignKey('stations.id'), index=True)

    arrival_time = Column(Time)
    departure_time = Column(Time)
    stop_order = Column(Integer)

    trip = relationship("Trip", back_populates="stops")
    station = relationship("Station", back_populates="stops")


class Graph(Base):
    __tablename__ = "graph"

    id = Column(Integer, primary_key=True)
    departure = Column(Integer, ForeignKey("stations.id"))
    arrival = Column(Integer, ForeignKey("stations.id"))
    path = Column(JSON)



class DBFill:
    def __init__(self, session):
        self.session = session

    def commit(self):
        self.session.commit()


class StationFill(DBFill):
    def fill_from_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for name, coords in data.items():
            station = Station(
                name=name,
                platform=coords.get("platforms", 1),
                latitude=coords["lat"],
                longitude=coords["lon"]
            )
            self.session.add(station)

        self.commit()

from datetime import datetime

def parse_time(time_str):
    if not time_str:
        return None
    return datetime.strptime(time_str, "%H:%M").time()


class TrainFill(DBFill):
    def fill_from_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for number, train_info in data.items():
            train = Train(
                number=number,
                name=train_info.get("name"),
                has_wifi=train_info.get("has_wifi", False),
                has_air_con=train_info.get("has_AC", False),
                has_restaurant=train_info.get("has_restaurant", False),
                has_bicycle_holder=train_info.get("has_bicycle", False),
                is_accessible=train_info.get("accessible", False),
            )
            self.session.add(train)

        self.commit()


class TripFill(DBFill):
    def fill_from_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for number, train_info in data.items():
            train = self.session.query(Train).filter_by(number=number).first()
            if not train:
                continue

            trip = Trip(
                train_id=train.id,
                days_mask=train_info.get("day_mask", 127),
            )
            self.session.add(trip)

        self.commit()


class RouteStopFill(DBFill):
    def fill_from_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for number, train_info in data.items():
            train = self.session.query(Train).filter_by(number=number).first()
            if not train:
                continue

            trip = self.session.query(Trip).filter_by(train_id=train.id).first()
            if not trip:
                continue

            stations_data = train_info.get("stations", [])
            total = len(stations_data)

            for station_info in stations_data:
                order = station_info.get("orderNumber")
                station_name = station_info.get("stationName")

                station = self.session.query(Station).filter_by(name=station_name).first()
                if not station:
                    continue

                arrival = None
                departure = None

                if order == 1:
                    departure = parse_time(station_info.get("departureTime"))
                elif order == total:
                    arrival = parse_time(station_info.get("arrivalTime"))
                else:
                    arrival = parse_time(station_info.get("arrivalTime"))
                    departure = parse_time(station_info.get("departureTime"))

                route_stop = RouteStop(
                    trip_id=trip.id,
                    station_id=station.id,
                    arrival_time=arrival,
                    departure_time=departure,
                    stop_order=order,
                )
                self.session.add(route_stop)

        self.commit()




if __name__ == "__main__":
    engine = create_engine("sqlite:///EuroTicket1.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)

    StationFill(session).fill_from_json("railway_stations.json")
    TrainFill(session).fill_from_json("structure.json")
    TripFill(session).fill_from_json("structure.json")
    RouteStopFill(session).fill_from_json("structure.json")

    session.close()