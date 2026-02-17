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
    has_bycycle_holder = Column(Boolean, default=False)
    is_accessible = Column(Boolean, default=False)
    trips = relationship("Trip", back_populates="train")


class Trip(Base):
    __tablename__ = 'trips'

    id = Column(Integer, primary_key=True)
    train_id = Column(Integer, ForeignKey('trains.id'))
    days_mask = Column(Integer, default=127)

    train = relationship("Train", back_populates="trips")
    stops = relationship("RouteStop", back_populates="trip", order_by="RouteStop.stop_order")
    exceptions = relationship("CalendarException", back_populates="trip")


class RouteStop(Base):
    __tablename__ = 'route_stops'

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey('trips.id'), index=True)
    station_id = Column(Integer, ForeignKey('stations.id'))

    arrival_time = Column(Time)
    departure_time = Column(Time)
    stop_order = Column(Integer)

    trip = relationship("Trip", back_populates="stops")
    station = relationship("Station", back_populates="stops")


class CalendarException(Base):
    __tablename__ = 'calendar_exceptions'

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey('trips.id'))
    date = Column(Date, nullable=False)
    is_running = Column(Boolean, nullable=False)
    trip = relationship("Trip", back_populates="exceptions")

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

if __name__ == "__main__":
    engine = create_engine("sqlite:///EuroTicket.db")
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)
    StationFill(session).fill_from_json("railway_stations.json")
    session.close()