from SQL_fill import Trip
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///EuroTicket.db")
Session = sessionmaker(bind=engine)
session = Session()


def get_adjacent_pairs(session) -> list[tuple[int, int]]:
    trips = session.query(Trip).all()

    pairs = set()

    for trip in trips:
        stops = sorted(trip.stops, key=lambda s: s.stop_order)
        for i in range(len(stops) - 1):
            a = stops[i].station_id
            b = stops[i + 1].station_id
            pairs.add((a, b))

    return list(pairs)


def get_adjacent_pairs_named(session) -> list[tuple[str, str]]:
    trips = session.query(Trip).all()

    pairs = set()

    for trip in trips:
        stops = sorted(trip.stops, key=lambda s: s.stop_order)
        for i in range(len(stops) - 1):
            a = stops[i].station.name
            b = stops[i + 1].station.name
            pairs.add((a, b))

    return list(pairs)


if __name__ == "__main__":
    print(len(get_adjacent_pairs_named(session)))

    session.close()