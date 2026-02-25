import folium
from folium import Element


TILE_THEMES = {
    'dark': 'CartoDB dark_matter',
    'light': 'CartoDB positron',
}

STATION_DEFAULTS = {
    'color': '#000000',
    'fill_color': '#f27b21',
    'weight': 1.5,
    'fill_opacity': 1.0,
}


class MapBuilder:
    def __init__(self, route_service, map_theme: str = 'light'):
        self.service = route_service
        self.tiles = TILE_THEMES.get(map_theme, TILE_THEMES['light'])

    def build(self, from_station: str | None, to_station: str | None, time_str: str | None) -> folium.Map:
        m = folium.Map(location=[52.0, 19.0], zoom_start=6, tiles=self.tiles, zoom_control=False)

        all_stations = self.service.get_all_stations()
        reachable_names: list[str] = []

        if from_station and not to_station:
            reachable_names = self.service.get_reachable_stations(from_station)

        elif from_station and to_station:
            self._add_route_polyline(m, from_station, to_station)
            self._add_live_train_js(m, from_station, to_station, time_str)

        self._add_station_markers(m, all_stations, from_station, to_station, reachable_names)
        return m

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_route_polyline(self, m: folium.Map, from_station: str, to_station: str) -> None:
        coords = self.service.get_specific_path(from_station, to_station)
        if not coords:
            return
        if isinstance(coords[0], (float, int)):
            coords = [coords]

        folium.PolyLine(
            locations=coords,
            color='#00ff00',
            weight=4,
            opacity=0.9,
            smooth_factor=1,
        ).add_to(m)

    def _add_live_train_js(
        self, m: folium.Map, from_station: str, to_station: str, time_str: str | None
    ) -> None:
        fallback_time = time_str or ''
        js = f"""
        <style>
        .leaflet-marker-icon.train-marker {{
            transition: transform 2.5s linear, opacity 0.5s ease !important;
        }}
        </style>
        <script src="/static/js/train_map.js"></script>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            initTrainMap({{
                fromStation: '{from_station}',
                toStation: '{to_station}',
                fallbackTime: '{fallback_time}'
            }});
        }});
        </script>
        """
        m.get_root().html.add_child(Element(js))

    def _add_station_markers(
        self,
        m: folium.Map,
        all_stations: list[dict],
        from_station: str | None,
        to_station: str | None,
        reachable_names: list[str],
    ) -> None:
        for st in all_stations:
            style = self._resolve_station_style(st, from_station, to_station, reachable_names)
            self._place_marker(m, st, style)

    @staticmethod
    def _resolve_station_style(
        st: dict,
        from_station: str | None,
        to_station: str | None,
        reachable_names: list[str],
    ) -> dict:
        try:
            platforms = int(st.get('platforms') or 1)
        except (ValueError, TypeError):
            platforms = 1

        base_radius = 3 + platforms * 1.5
        name = st['name']

        if not from_station and not to_station:
            return dict(color='#000000', fill_color='#f27b21', weight=1.5,
                        radius=base_radius, fill_opacity=1.0)

        if name == from_station:
            return dict(color='#ffffff', fill_color='#ffffff', weight=3.0,
                        radius=base_radius * 1.4, fill_opacity=1.0)

        if name == to_station:
            return dict(color='#00ff00', fill_color='#00ff00', weight=3.0,
                        radius=base_radius * 1.4, fill_opacity=1.0)

        if not to_station and name in reachable_names:
            return dict(color='#000000', fill_color='#f27b21', weight=1.5,
                        radius=base_radius, fill_opacity=1.0)

        return dict(color='#000000', fill_color='#f27b21', weight=1.0,
                    radius=base_radius, fill_opacity=0.2)

    @staticmethod
    def _place_marker(m: folium.Map, st: dict, style: dict) -> None:
        lat, lon = st['lat'], st['lon']
        name = st['name']

        folium.CircleMarker(
            location=[lat, lon],
            radius=style['radius'],
            color=style['color'],
            weight=style['weight'],
            fill_color=style['fill_color'],
            fill_opacity=style['fill_opacity'],
            opacity=style['fill_opacity'],
            tooltip=name,
        ).add_to(m)

        click_js = f"""
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var marker = Object.values(window).find(
                    x => x && x._latlng && x._latlng.lat === {lat} && x._latlng.lng === {lon}
                );
                if (marker) {{
                    marker.on('click', function() {{
                        window.parent.postMessage({{type: 'station_clicked', name: '{name}'}}, '*');
                    }});
                }}
            }});
        </script>
        """
        m.get_root().html.add_child(Element(click_js))