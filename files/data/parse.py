import json

def stations(input_data):
    with open(input_data, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for element in data.get('elements', []):
        tags = element.get('tags', {})
        name = tags.get('name')

        if name:
            station_info = {
                "lat": element.get('lat'),
                "lon": element.get('lon')
            }
            if 'platforms' in tags:
                station_info['platforms'] = tags['platforms']
            result[name] = station_info
    return result


if __name__ == "__main__":
    data = stations("stations.json")
    with open("railway_stations.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)