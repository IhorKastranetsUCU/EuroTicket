from flask import Flask, render_template, render_template_string
import folium

TILES = {
    "dark": "CartoDB dark_matter",
    "light": "CartoDB positron",
    "osm": "OpenStreetMap",
    "sat": "Esri.WorldImagery",
    "satg": "Esri.WorldGrayCanvas",
    "topo": "OpenTopoMap"
}

app = Flask(__name__)

def create_map(tiles):
    return folium.Map(
        location=[52.0, 19.0],
        zoom_start=7,
        tiles=tiles
    )

@app.route("/")
def index():
    tiles_name = "CartoDB dark_matter"
    m = create_map(tiles_name)
    return render_template("index.html", map_html=m._repr_html_(), tiles=TILES)

@app.route("/set_tiles/<tiles>")
def set_tiles(tiles):
    print(tiles)
    tiles_name = TILES.get(tiles, "CartoDB dark_matter")
    m = create_map(tiles_name)
    return render_template("index.html", map_html=m._repr_html_(), tiles=TILES)

@app.route("/map")
def map():
    return render_template("index.html")
if __name__ == "__main__":
    app.run(debug=True) # для того, щоб користувач бачив помилки