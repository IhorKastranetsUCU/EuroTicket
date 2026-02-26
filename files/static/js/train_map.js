function initTrainMap(config) {
  const { fromStation, toStation, fallbackTime } = config;

  const map = findLeafletMap();
  if (!map) return;

  const trainIcon = L.divIcon({
    html: '<div style="color:red;font-size:20px;text-shadow:1px 1px 2px white;"><i class="fa fa-train"></i></div>',
    className: 'leaflet-marker-icon train-marker',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });

  /** @type {Object.<number, L.Marker>} */
  const trainMarkers = {};

  function fetchAndUpdateTrains() {
    const endpoint = buildEndpoint(fromStation, toStation, fallbackTime);

    fetch(endpoint)
      .then((res) => res.json())
      .then((trains) => updateMarkers(trains))
      .catch(() => {
      });
  }

  function updateMarkers(trains) {
    const activeTripIds = new Set(trains.map((t) => t.trip_id));

    for (const tid in trainMarkers) {
      if (!activeTripIds.has(parseInt(tid))) {
        map.removeLayer(trainMarkers[tid]);
        delete trainMarkers[tid];
      }
    }

    trains.forEach((train) => {
      const latLng = [train.lat, train.lon];
      const popup = buildPopup(train);

      if (trainMarkers[train.trip_id]) {
        trainMarkers[train.trip_id].setLatLng(latLng);
        trainMarkers[train.trip_id].getPopup().setContent(popup);
      } else {
        trainMarkers[train.trip_id] = L.marker(latLng, { icon: trainIcon })
          .bindPopup(popup)
          .addTo(map);
      }
    });
  }

  function buildEndpoint(from, to, fallback) {
    let url = `/api/train_positions?from_station=${encodeURIComponent(from)}&to_station=${encodeURIComponent(to)}`;

    if (window.parent && window.parent.isLiveMode === false) {
      const parentInput = window.parent.document.getElementById('time-input');
      let timeParam = parentInput ? parentInput.value : fallback;
      if (timeParam && timeParam.length === 5) timeParam += ':00';
      if (timeParam) url += `&time=${encodeURIComponent(timeParam)}`;
    }

    return url;
  }

  function buildPopup(train) {
    return `<b>Поїзд ${train.train_number}</b><br>${train.previous_station} ➔ ${train.next_station}`;
  }

  function disableTransitions() {
    document.querySelectorAll('.train-marker').forEach((el) => {
      el.style.setProperty('transition', 'none', 'important');
    });
  }

  function enableTransitions() {
    setTimeout(() => {
      document.querySelectorAll('.train-marker').forEach((el) => {
        el.style.setProperty('transition', 'transform 2.5s linear, opacity 0.5s ease', 'important');
      });
    }, 100);
  }

  map.on('zoomstart', disableTransitions);
  map.on('zoomend', enableTransitions);

  setTimeout(fetchAndUpdateTrains, 500);
  setInterval(fetchAndUpdateTrains, 2500);
}
function findLeafletMap() {
  for (const key in window) {
    if (window[key] && window[key]._panes) {
      return window[key];
    }
  }
  return null;
}
