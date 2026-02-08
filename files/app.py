from flask import Flask, render_template, request, jsonify
import folium

app = Flask(__name__)

@app.route('/')
def index():
    # Створюємо карту з центром на Польщі
    # Координати центру Польщі приблизно 52.0, 19.0
    poland_map = folium.Map(
        location=[52.0, 19.0],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Зберігаємо карту як HTML
    map_html = poland_map._repr_html_()
    
    return render_template('index.html', map_html=map_html)

@app.route('/search_stations', methods=['POST'])
def search_stations():
    data = request.get_json()
    departure = data.get('departure', '')
    arrival = data.get('arrival', '')
    
    # Тут буде логіка пошуку станцій
    # Поки що повертаємо отримані дані
    return jsonify({
        'status': 'success',
        'departure': departure,
        'arrival': arrival
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
