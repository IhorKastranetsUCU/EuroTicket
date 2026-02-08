import requests
import json

overpass_url = "http://overpass-api.de/api/interpreter"

query = """
[out:json][timeout:1800];
node["railway"="station"](49.0,14.1,54.9,24.1);
out body;
"""

response = requests.get(overpass_url, params={'data': query})

# перевіримо статус
if response.status_code != 200:
    raise Exception(f"Overpass API Error: {response.status_code}")

data = response.json()  # тепер працює
print(f"Знайдено {len(data['elements'])} вокзалів")