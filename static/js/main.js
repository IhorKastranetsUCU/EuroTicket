let ALL_STATIONS = [];

document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/stations')
        .then(res => res.json())
        .then(stations => { ALL_STATIONS = stations; })
        .catch(err => console.error("Error loading stations:", err));

    const themeToggler = document.getElementById('theme-toggler');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');
    let isDark = localStorage.getItem('theme') === 'dark';
    let currentMapTheme = isDark ? 'dark' : 'light';

    function applyTheme() {
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        sunIcon.style.display = isDark ? 'none' : 'block';
        moonIcon.style.display = isDark ? 'block' : 'none';
        currentMapTheme = isDark ? 'dark' : 'light';
        localStorage.setItem('theme', currentMapTheme);
    }

    applyTheme();

    if (themeToggler) {
        themeToggler.addEventListener('click', () => {
            isDark = !isDark;
            applyTheme();
            updateMap();
        });
    }

    const rightSidebar = document.getElementById('right-sidebar');
    const closeRightSidebar = document.getElementById('close-right-sidebar');
    const trainDetailsContent = document.getElementById('train-details-content');

    if (closeRightSidebar) {
        closeRightSidebar.addEventListener('click', () => {
            rightSidebar.classList.remove('open');
            document.body.classList.remove('right-panel-active');
        });
    }

    const inputFrom = document.getElementById('from-input');
    const inputTo = document.getElementById('to-input');
    const clearFromBtn = document.getElementById('clear-from-btn');
    const clearToBtn = document.getElementById('clear-to-btn');

    function updateClearBtnVisibility(input, btn) {
        if (input && btn) {
            btn.style.display = input.value.trim().length > 0 ? 'block' : 'none';
        }
    }

    updateClearBtnVisibility(inputFrom, clearFromBtn);
    updateClearBtnVisibility(inputTo, clearToBtn);

    const swapBtn = document.querySelector('.swap-btn');
    if (swapBtn && inputFrom && inputTo) {
        swapBtn.addEventListener('click', () => {
            const temp = inputFrom.value;
            inputFrom.value = inputTo.value;
            inputTo.value = temp;
            updateClearBtnVisibility(inputFrom, clearFromBtn);
            updateClearBtnVisibility(inputTo, clearToBtn);
            updateMap();
        });
    }

    if (inputFrom && clearFromBtn) {
        inputFrom.addEventListener('input', () => updateClearBtnVisibility(inputFrom, clearFromBtn));
        clearFromBtn.addEventListener('click', () => {
            inputFrom.value = '';
            updateClearBtnVisibility(inputFrom, clearFromBtn);
            updateMap();
        });
    }

    if (inputTo && clearToBtn) {
        inputTo.addEventListener('input', () => updateClearBtnVisibility(inputTo, clearToBtn));
        clearToBtn.addEventListener('click', () => {
            inputTo.value = '';
            updateClearBtnVisibility(inputTo, clearToBtn);
            updateMap();
        });
    }

    const dateInput = document.getElementById('date-input');
    const timeInput = document.getElementById('time-input');
    const now = new Date();
    if (dateInput) dateInput.value = now.toISOString().split('T')[0];
    if (timeInput) timeInput.value = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
    const resetBtn = document.getElementById('reset-datetime-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            const now = new Date();
            dateInput.value = now.toISOString().split('T')[0];
            timeInput.value = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
            window.isLiveMode = true;
            document.getElementById('date-warning').style.display = 'none';
            updateMap();
        });
    }

    window.isLiveMode = true;

    if (dateInput) dateInput.addEventListener('change', () => {
        window.isLiveMode = false;
        const selected = new Date(dateInput.value);
        const cutoff = new Date('2026-03-08');
        const warning = document.getElementById('date-warning');
        if (selected > cutoff) {
            warning.style.display = 'block';
        } else {
            warning.style.display = 'none';
        }
        updateMap();
    });
    if (timeInput) timeInput.addEventListener('change', () => { window.isLiveMode = false; });

    function setupAutocomplete(inputElement, listElement, isFromInput) {
        if (!inputElement || !listElement) return;

        inputElement.addEventListener('input', (e) => {
            const val = e.target.value.toLowerCase();
            listElement.innerHTML = '';

            if (!val) {
                listElement.classList.remove('active');
                return;
            }

            const matches = ALL_STATIONS.filter(st => st.name.toLowerCase().includes(val)).slice(0, 7);

            if (matches.length > 0) {
                listElement.classList.add('active');
                matches.forEach(match => {
                    const item = document.createElement('div');
                    item.className = 'autocomplete-item';
                    item.textContent = match.name;
                    item.addEventListener('click', () => {
                        inputElement.value = match.name;
                        listElement.classList.remove('active');
                        updateClearBtnVisibility(inputElement, isFromInput ? clearFromBtn : clearToBtn);
                        updateMap();
                    });
                    listElement.appendChild(item);
                });
            } else {
                listElement.classList.remove('active');
            }
        });

        document.addEventListener('click', (e) => {
            if (e.target !== inputElement && e.target !== listElement && !listElement.contains(e.target)) {
                listElement.classList.remove('active');
            }
        });
    }

    setupAutocomplete(inputFrom, document.getElementById('from-autocomplete'), true);
    setupAutocomplete(inputTo, document.getElementById('to-autocomplete'), false);

    const clockElement = document.getElementById('digital-clock');
    if (clockElement) {
        setInterval(() => {
            const now = new Date();
            clockElement.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        }, 1000);
    }

    window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'station_clicked') {
            const stationName = event.data.name;

            if (!inputFrom.value || (inputFrom.value && inputTo.value)) {
                inputFrom.value = stationName;
                inputTo.value = '';
                updateClearBtnVisibility(inputFrom, clearFromBtn);
                updateClearBtnVisibility(inputTo, clearToBtn);
                updateMap();
            } else {
                inputTo.value = stationName;
                updateClearBtnVisibility(inputTo, clearToBtn);
                updateMap();
            }
        }
    });

    function updateMap() {
        const fromVal = inputFrom.value;
        const toVal = inputTo.value;

        let url = '/api/map?';
        if (fromVal) url += `from_station=${encodeURIComponent(fromVal)}&`;
        if (toVal) url += `to_station=${encodeURIComponent(toVal)}&`;
        url += `map_theme=${currentMapTheme}&`;

        const timeInputEl = document.getElementById('time-input');
        let timeVal = timeInputEl ? timeInputEl.value : null;
        if (timeVal) {
            if (timeVal.length === 5) timeVal += ':00';
            url += `time=${encodeURIComponent(timeVal)}&`;
        }

        const iframe = document.getElementById('map-frame');
        if (iframe) iframe.src = url;

        const resultsContainer = document.getElementById('train-results-container');
        const resultsList = document.getElementById('train-results-list');
        const leftSidebar = document.getElementById('left-sidebar');

        const selectedDate = new Date(document.getElementById('date-input').value);
        const cutoff = new Date('2026-03-08');
        const dateExceeded = selectedDate > cutoff;

        if (fromVal && toVal && resultsContainer && resultsList && !dateExceeded) {
            if (leftSidebar) leftSidebar.style.display = 'flex';
            resultsContainer.style.display = 'block';
            resultsList.innerHTML = '<div style="color:var(--text-secondary); padding: 10px;">Завантаження...</div>';

            let fetchUrl = `/api/route_trains?from_station=${encodeURIComponent(fromVal)}&to_station=${encodeURIComponent(toVal)}`;
            const dateVal = document.getElementById('date-input').value;
            if (dateVal) fetchUrl += `&date=${encodeURIComponent(dateVal)}`;
            if (timeVal) fetchUrl += `&time=${encodeURIComponent(timeVal)}`;

            fetch(fetchUrl)
                .then(res => res.json())
                .then(trains => {
                    resultsList.innerHTML = '';

                    if (!trains || trains.length === 0) {
                        resultsList.innerHTML = '<div style="color:var(--text-secondary); padding: 10px;">Прямих поїздів не знайдено.</div>';
                        return;
                    }

                    trains.forEach(trip => {
                        const route = trip.route;
                        const dep = route.find(s => s.order === trip.dep_order) || route[0];
                        const arr = route.find(s => s.order === trip.arr_order) || route[route.length - 1];

                        const card = document.createElement('div');
                        card.className = 'train-card';

                        const depTime = dep.departure ? dep.departure.slice(0, 5) : (dep.arrival ? dep.arrival.slice(0, 5) : '--:--');
                        const arrTime = arr.arrival ? arr.arrival.slice(0, 5) : (arr.departure ? arr.departure.slice(0, 5) : '--:--');

                        card.innerHTML = `
                            <div class="train-card-header">
                                <span class="train-number">${trip.train_number || 'Поїзд'}</span>
                                ${trip.train_name ? `<div class="train-name">${trip.train_name}</div>` : ''}
                            </div>
                            <div class="train-route-info">
                                <div class="route-point">
                                    <span class="route-time">${depTime}</span>
                                    <span class="route-station" title="${dep.station}">${dep.station}</span>
                                </div>
                                <div class="route-arrow">➔</div>
                                <div class="route-point" style="text-align: right;">
                                    <span class="route-time">${arrTime}</span>
                                    <span class="route-station" title="${arr.station}">${arr.station}</span>
                                </div>
                            </div>
                        `;

                        card.addEventListener('click', () => showTrainDetails(trip));
                        resultsList.appendChild(card);
                    });
                })
                .catch(err => {
                    console.error('Error fetching trains:', err);
                    resultsList.innerHTML = '<div style="color:#ff4b4b; padding: 10px;">Сталася помилка при завантаженні поїздів.</div>';
                });
        } else if (resultsContainer) {
            if (leftSidebar) leftSidebar.style.display = 'none';
            resultsContainer.style.display = 'none';
        }
    }

    function showTrainDetails(trip) {
        if (!trainDetailsContent || !rightSidebar) return;

        let html = `<div class="details-header">${trip.train_number || 'Поїзд'}</div>`;
        html += `<div class="details-subheader">${trip.train_name || 'Деталі маршруту'}</div>`;

        html += `<div class="amenities-list">
            <span class="amenity-badge ${trip.has_wifi ? 'active' : ''}">WiFi</span>
            <span class="amenity-badge ${trip.has_air_con ? 'active' : ''}">Кондиціонер</span>
            <span class="amenity-badge ${trip.has_restaurant ? 'active' : ''}">Ресторан</span>
            <span class="amenity-badge ${trip.has_bicycle ? 'active' : ''}">Велосипед</span>
            <span class="amenity-badge ${trip.accessible ? 'active' : ''}">Інклюзивність</span>
        </div>`;

        html += `<div class="stops-timeline">`;
        trip.route.forEach((stop, index) => {
            const isTerminal = index === 0 || index === trip.route.length - 1;
            const isActive = stop.order >= trip.dep_order && stop.order <= trip.arr_order;
            let timeClass = '';
            if (isTerminal) timeClass += 'terminal ';
            if (isActive) timeClass += 'active-segment ';
            const t = stop.arrival ? stop.arrival.slice(0, 5) : (stop.departure ? stop.departure.slice(0, 5) : '--:--');
            html += `
                <div class="stop-item ${timeClass.trim()}">
                    <span class="stop-time">${t}</span>
                    <span class="stop-name">${stop.station}</span>
                </div>
            `;
        });
        html += `</div>`;

        trainDetailsContent.innerHTML = html;
        rightSidebar.classList.add('open');
        document.body.classList.add('right-panel-active');
    }

    const projectInfoBtn = document.getElementById('project-info-btn');
    const projectModal = document.getElementById('project-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');

    if (projectInfoBtn && projectModal && closeModalBtn) {
        projectInfoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            projectModal.classList.add('active');
        });

        closeModalBtn.addEventListener('click', () => projectModal.classList.remove('active'));

        projectModal.addEventListener('click', (e) => {
            if (e.target === projectModal) projectModal.classList.remove('active');
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && projectModal.classList.contains('active')) projectModal.classList.remove('active');
        });
    }

    updateMap();
});
