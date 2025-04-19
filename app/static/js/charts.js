function renderCharts(data) {
    const dates = data.map(item => item.date);

    // Temperature Chart
    createChart('tempChart', 'Temperature (°C)',
               data.map(item => item.avg_temp), '#4CAF50');

    // Pressure Chart
    createChart('pressureChart', 'Pressure (hPa)',
               data.map(item => item.avg_pressure), '#3F51B5');

    // pH Chart (Note capital pH)
    createChart('phChart', 'pH Level',
               data.map(item => item.avg_ph), '#008080');

    // Humidity Chart
    createChart('humidityChart', 'Humidity (%)',
               data.map(item => item.avg_humidity), '#2196F3');

    // Light Intensity Chart
    createChart('lightChart', 'Light Intensity (Lux)',
               data.map(item => item.avg_light), '#FFC107');

    // Air Quality Chart
    createChart('airQualityChart', 'Air Quality (ppm)',
               data.map(item => item.avg_air_quality), '#9C27B0');

    // Moisture Chart
    createChart('moistureChart', 'Moisture (%)',
               data.map(item => item.avg_moisture), '#795548');
}

function createChart(elementId, label, data, color) {
    const dates = data.map(item => item.date); // Ensure dates are available within this scope
    new Chart(document.getElementById(elementId), {
        type: 'line',
        data: {
            labels: dates,
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
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: label.split('(')[0].trim() // Extract unitless label for y-axis
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
                    display: false // Hide the dataset label as it's redundant with the chart title
                }
            }
        }
    });
}