from json import loads

def missed_stations(stations_path, schedule_path):
    missed = []

    with open(stations_path, "r", encoding="utf-8") as f:
        stations_data = loads(f.read())
    stations = stations_data.keys()

    with open(schedule_path, "r", encoding="utf-8") as f:
        schedule_data = loads(f.read())

    for train in schedule_data.values():
        for stop in train.get("stations", []):
            station_name = stop.get("stationName")
            if station_name not in stations and station_name not in missed:
                missed.append(station_name)
    print(len(missed))
    return missed
if __name__ == "__main__":
    print(missed_stations("railway_stations.json", "structure2.json"))