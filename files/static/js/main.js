let STATIONS = [];

document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => {
        document.getElementById('top-clock').textContent = new Date().toLocaleTimeString();
    }, 1000);

    loadStations();
    setupAC('from-input', 'from-drop');
    setupAC('to-input', 'to-drop');
});

async function loadStations() {
    const res = await fetch('/api/stations');
    STATIONS = await res.json();
}

function setupAC(id, dropId) {
    const inp = document.getElementById(id);
    const drop = document.getElementById(dropId);

    inp.addEventListener('input', () => {
        const val = inp.value.toLowerCase();
        drop.innerHTML = '';
        if (!val) { drop.classList.remove('show'); return; }

        const hits = STATIONS.filter(s => s.name.toLowerCase().includes(val)).slice(0, 6);
        hits.forEach(s => {
            const div = document.createElement('div');
            div.className = 'ac-item';
            div.textContent = s.name;
            div.onclick = () => {
                inp.value = s.name;
                drop.classList.remove('show');
                if (id === 'from-input') handleFromSelect(s.name);
            };
            drop.appendChild(div);
        });
        drop.classList.toggle('show', hits.length > 0);
    });
}

// ЛОГІКА СКЕЙЛІНГУ ТА ПРОЗОРОСТІ
async function handleFromSelect(name) {
    // 1. Отримуємо список доступних станцій з бекенду
    const res = await fetch(`/api/reachable?name=${encodeURIComponent(name)}`);
    const reachable = await res.json();

    // 2. Надсилаємо сигнал в iframe карти
    const mapFrame = document.getElementById('map-frame').contentWindow;
    mapFrame.postMessage({
        type: 'HIGHLIGHT_STATIONS',
        selected: name,
        reachable: reachable
    }, '*');
}

// Виклик з Popup карти
window.selectStation = function(name) {
    const from = document.getElementById('from-input');
    const to = document.getElementById('to-input');

    if (!from.value || (from.value && to.value)) {
        from.value = name;
        to.value = '';
        handleFromSelect(name);
    } else {
        to.value = name;
    }
};

async function findRoutes() {
    const from = document.getElementById('from-input').value;
    const向 = document.getElementById('to-input').value;
    const date = document.getElementById('date-input').value;

    document.getElementById('left-panel').classList.add('active');
    const res = await fetch(`/api/search?from=${from}&to=${to}&date=${date}`);
    const routes = await res.json();

    const container = document.getElementById('routes-container');
    container.innerHTML = routes.map(r => `
        <div class="route-card" onclick='showDetails(${JSON.stringify(r)})'>
            <h3>${r.train_number} ${r.train_name}</h3>
            <p>${r.route[0].departure} ➔ ${r.route[r.route.length-1].arrival}</p>
        </div>
    `).join('');
}

function showDetails(route) {
    const p = document.getElementById('right-panel');
    p.classList.add('active');
    document.getElementById('details-container').innerHTML = `
        <h3>Зупинки рейсу ${route.train_number}</h3>
        ${route.route.map(s => `
            <div style="margin: 10px 0; border-left: 2px solid var(--orange); padding-left: 10px;">
                <b>${s.station}</b><br>
                <small>${s.arrival || '--:--'} / ${s.departure || '--:--'}</small>
            </div>
        `).join('')}
    `;
}

function resetUI() {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('input').forEach(i => i.value = '');
    // Скидаємо карту до початкового стану
    document.getElementById('map-frame').contentWindow.postMessage({
        type: 'HIGHLIGHT_STATIONS', selected: '', reachable: STATIONS.map(s => s.name)
    }, '*');
}