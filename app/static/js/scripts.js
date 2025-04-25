document.addEventListener('DOMContentLoaded', function() {
    const feedbackButton = document.getElementById('feedback-button');
    const feedbackModal = document.getElementById('feedback-modal');
    const closeButton = document.querySelector('.close-button');
    const feedbackForm = document.getElementById('feedback-form');

    if (!feedbackButton || !feedbackModal || !closeButton || !feedbackForm) return;

    // Modal functions
    function openModal() {
        feedbackModal.style.display = 'block';
        feedbackModal.setAttribute('aria-hidden', 'false');
        document.getElementById('feedback-text').focus();
    }

    function closeModal() {
        feedbackModal.style.display = 'none';
        feedbackModal.setAttribute('aria-hidden', 'true');
        feedbackButton.focus();
    }

    // Event listeners
    feedbackButton.addEventListener('click', openModal);
    closeButton.addEventListener('click', closeModal);

    // Keyboard accessibility
    closeButton.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') closeModal();
    });

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && feedbackModal.style.display === 'block') {
            closeModal();
        }
    });

    // Form submission
    feedbackForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const feedbackText = document.getElementById('feedback-text').value.trim();
        if (!feedbackText) return;

        const submitButton = this.querySelector('button[type="submit"]');
        submitButton.disabled = true;

        try {
            const response = await fetch('/api/submit_feedback', { // Corrected API endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value // More specific selector
                },
                body: JSON.stringify({ feedback: feedbackText })
            });

            if (response.ok) {
                alert('Feedback submitted successfully!');
                feedbackForm.reset();
                closeModal();
            } else {
                const errorData = await response.json();
                const errorMessage = errorData.error || 'Submission failed';
                throw new Error(errorMessage);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error submitting feedback. Please try again.');
        } finally {
            submitButton.disabled = false;
        }
    });
});

function fetchLatestData() {
    fetch('/latest_sensor_data')
        .then(response => response.json())
        .then(data => {
            if (data) {
                document.querySelector('.latest-data table tbody tr td:nth-child(1)').textContent = (data.temperature || '--') + ' °C';
                document.querySelector('.latest-data table tbody tr td:nth-child(2)').textContent = (data.humidity || '--') + ' %';
                document.querySelector('.latest-data table tbody tr td:nth-child(3)').textContent = (data.light_intensity || '--') + ' lux';
                document.querySelector('.latest-data table tbody tr td:nth-child(4)').textContent = (data.pressure || '--') + ' hPa';
                document.querySelector('.latest-data table tbody tr td:nth-child(5)').textContent = (data.air_quality || '--') + ' ppm';
                document.querySelector('.latest-data table tbody tr td:nth-child(6)').textContent = (data.pH || '--') + ' level';
                document.querySelector('.latest-data table tbody tr td:nth-child(7)').textContent = (data.moisture || '--') + ' %';
                document.querySelector('.latest-data table tbody tr td:nth-child(8)').textContent = data.timestamp || '--';
            }
        })
        .catch(error => {
            console.error('Error fetching latest data:', error);
        });
}

fetchLatestData();

setInterval(fetchLatestData, 60000);

function fetchActiveAlerts() {
    fetch('/alerts')
        .then(response => response.json())
        .then(alerts => {
            const alertsList = document.querySelector('.active-alerts ul');
            if (alertsList) {
                alertsList.innerHTML = ''; // Clear existing alerts
                if (alerts.length > 0) {
                    alerts.forEach(alert => {
                        const listItem = document.createElement('li');
                        listItem.innerHTML = `
                            <strong>${alert.sensor_type.charAt(0).toUpperCase() + alert.sensor_type.slice(1)}</strong>:
                            Reading ${alert.reading_value} breached
                            ${alert.threshold_type === 'min' ? 'minimum' : 'maximum'} threshold of ${alert.threshold_value}
                            at ${new Date(alert.timestamp).toLocaleString()}
                            <span class="alert-status ${alert.status.toLowerCase().replace(' ', '-')}">${alert.status}</span>
                        `;
                        alertsList.appendChild(listItem);
                    });
                } else {
                    alertsList.innerHTML = '<p>No active alerts reported.</p>';
                }
            }
        })
        .catch(error => {
            console.error('Error fetching active alerts:', error);
        });
}

fetchActiveAlerts();

setInterval(fetchActiveAlerts, 60000);