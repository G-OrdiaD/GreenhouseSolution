function renderCharts(data) {
    if (!data || data.length === 0) return;

    const dates = data.map(item => item.date);

    // Temperature Chart
    createChart('tempChart', 'Temperature (°C)', dates,
               data.map(item => item.avg_temp), '#4CAF50');

    // Pressure Chart
    createChart('pressureChart', 'Pressure (hPa)', dates,
               data.map(item => item.avg_pressure), '#3F51B5');

    // pH Chart
    createChart('phChart', 'pH Level', dates,
               data.map(item => item.avg_ph), '#008080');

    // Humidity Chart
    createChart('humidityChart', 'Humidity (%)', dates,
               data.map(item => item.avg_humidity), '#2196F3');

    // Light Intensity Chart
    createChart('lightChart', 'Light Intensity (Lux)', dates,
               data.map(item => item.avg_light), '#FFC107');

    // Air Quality Chart
    createChart('airQualityChart', 'Air Quality (ppm)', dates,
               data.map(item => item.avg_air_quality), '#9C27B0');

    // Moisture Chart
    createChart('moistureChart', 'Moisture (%)', dates,
               data.map(item => item.avg_moisture), '#795548');
}

function createChart(elementId, label, labels, data, color) {
    const ctx = document.getElementById(elementId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: label.split('(')[0].trim()
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: label
                },
                legend: {
                    display: false
                }
            }
        }
    });
}