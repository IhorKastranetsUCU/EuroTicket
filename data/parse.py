import json

def parse_osm_stations(input_data):
    if isinstance(input_data, str):
        data = json.loads(input_data)
    else:
        data = input_data
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


if main