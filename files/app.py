import os
import json
import folium
from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Імпортуємо твій сервіс та моделі
# Переконайся, що файли db_interface.py та SQL_fill.py лежать поруч
from db_interface import RouteService
from SQL_fill import Station, Trip, RouteStop

app = Flask(__name__)

# ─── НАЛАШТУВАННЯ БАЗИ ДАНИХ ──────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
# Вказуємо шлях до EuroTicket.db (можна змінити на EuroTicket1.db якщо потрібно)
db_path = os.path.join(basedir, 'EuroTicket.db')
engine = create_engine(f"sqlite:///{db_path}", connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)


# ─── МАРШРУТИ FLASK ──────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/map')
def get_map():
    session = Session()
    try:
        stations = session.query(Station).all()

        # Створюємо карту з темною темою
        m = folium.Map(
            location=[52.2, 19.2],
            zoom_start=6,
            tiles="CartoDB dark_matter",
            zoom_control=False
        )

        # JS скрипт для маніпуляцій з маркерами без перезавантаження карти
        custom_js = """
        window.addEventListener('message', function(event) {
            if (event.data.type === 'HIGHLIGHT_STATIONS') {
                const selected = event.data.selected;
                const reachable = event.data.reachable;

                window.Object.keys(window).forEach(key => {
                    let obj = window[key];
                    if (obj && obj.options && obj.options.tooltip) {
                        let stationName = obj.options.tooltip.split(' (')[0];

                        if (stationName === selected) {
                            // Обрана станція: збільшуємо x1.2 та робимо білою
                            obj.setRadius(obj.options.originalRadius * 1.2);
                            obj.setStyle({opacity: 1, fillOpacity: 1, color: '#FFFFFF', weight: 3});
                        } else if (reachable.includes(stationName)) {
                            // Доступні станції: залишаємо помаранчевими
                            obj.setRadius(obj.options.originalRadius);
                            obj.setStyle({opacity: 1, fillOpacity: 0.8, color: '#E8722A', weight: 1});
                        } else {
                            // Решта: стають прозорими
                            obj.setRadius(obj.options.originalRadius);
                            obj.setStyle({opacity: 0.1, fillOpacity: 0.05, color: '#E8722A'});
                        }
                    }
                });
            }
        });
        """
        m.get_root().script.add_child(folium.Element(custom_js))

        for s in stations:
            if s.latitude and s.longitude:
                # Парсимо платформи (захист від помилок у БД)
                try:
                    p_count = int(s.platform) if s.platform else 1
                except (ValueError, TypeError):
                    p_count = 1

                radius = 3 + (p_count * 1.5)

                folium.CircleMarker(
                    location=[s.latitude, s.longitude],
                    radius=radius,
                    originalRadius=radius,  # Зберігаємо для JS скейлінгу
                    color="#E8722A",
                    fill=True,
                    fill_color="#E8722A",
                    fill_opacity=0.8,
                    weight=1,
                    tooltip=f"{s.name} (Платформ: {p_count})",
                    # Виклик функції selectStation у батьківському вікні
                    popup=folium.Popup(
                        f'<button onclick="parent.selectStation(\'{s.name}\')" style="cursor:pointer; padding:5px; background:#E8722A; color:white; border:none; border-radius:4px;">Вибрати</button>')
                ).add_to(m)

        return m._repr_html_()
    except Exception as e:
        return f"Database error: {str(e)}"
    finally:
        session.close()


@app.route('/api/stations')
def get_stations():
    session = Session()
    stations = session.query(Station).all()
    data = [{"name": s.name, "lat": s.latitude, "lon": s.longitude} for s in stations]
    session.close()
    return jsonify(data)


@app.route('/api/reachable')
def get_reachable():
    name = request.args.get('name')
    if not name: return jsonify([])

    session = Session()
    service = RouteService(session)
    reachable_list = service.get_reachable_stations(name)
    session.close()
    return jsonify(reachable_list)


@app.route('/api/search')
def search():
    from_st = request.args.get('from')
    to_st = request.args.get('to')
    date = request.args.get('date')

    if not from_st or not to_st:
        return jsonify([])

    session = Session()
    service = RouteService(session)
    routes = service.get_route_between(from_st, to_st)
    session.close()
    return jsonify(routes)


if __name__ == '__main__':
    # Перевіряємо наявність папок, якщо потрібно
    app.run(debug=True, port=5001)