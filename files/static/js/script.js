document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('searchBtn');
    const departureInput = document.getElementById('departure');
    const arrivalInput = document.getElementById('arrival');
    const resultPanel = document.getElementById('result');
    const resultText = document.getElementById('resultText');
    
    searchBtn.addEventListener('click', function() {
        const departure = departureInput.value.trim();
        const arrival = arrivalInput.value.trim();
        
        if (!departure || !arrival) {
            alert('Будь ласка, заповніть обидва поля!');
            return;
        }
        
        // Відправляємо дані на сервер
        fetch('/search_stations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                departure: departure,
                arrival: arrival
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                resultPanel.style.display = 'block';
                resultText.textContent = `Шукаємо маршрут з "${data.departure}" до "${data.arrival}"`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Виникла помилка при пошуку маршруту');
        });
    });
    
    departureInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            arrivalInput.focus();
        }
    });
    
    arrivalInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });
});
