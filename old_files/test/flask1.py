from flask import Flask, render_template
import folium
import json

with open("poland.json", encoding="utf-8") as f:
    osm_data = json.load(f)

railway_lines = []
for el in osm_data.get("elements", []):
    if el.get("type") == "way" and "geometry" in el:
        # Формуємо список координат [[lat1, lon1], [lat2, lon2]]
        line = [[pt["lat"], pt["lon"]] for pt in el["geometry"]]
        railway_lines.append(line)

TILES = {
    "dark": "CartoDB dark_matter",
    "light": "CartoDB positron",
    "osm": "OpenStreetMap",
    "sat": "Esri.WorldImagery",
    "topo": "OpenTopoMap"
}

app = Flask(__name__)


def create_map(tiles_name):
    start_location = [49.8, 22.5]
    if railway_lines:
        start_location = railway_lines[0][0]

    m = folium.Map(location=start_location, zoom_start=9, tiles=tiles_name)

    for line in railway_lines:
        folium.PolyLine(locations=line, color="red", weight=3, opacity=0.8).add_to(m)

    return m


@app.route("/")
def index():
    m = create_map(TILES["dark"])
    return render_template("index.html", map_html=m._repr_html_(), tiles=TILES)


@app.route("/set_tiles/<tiles>")
def set_tiles(tiles):
    tiles_name = TILES.get(tiles, TILES["dark"])
    m = create_map(tiles_name)
    return render_template("index.html", map_html=m._repr_html_(), tiles=TILES)


if __name__ == "__main__":
    app.run(debug=True)