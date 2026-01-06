(function () {
    const raw = document.getElementById('dashboard-data');
    if (!raw) {
        console.error('Dashboard data element not found');
        return;
    }
    let data = {};
    try {
        data = JSON.parse(raw.textContent || raw.innerText || '{}');
        console.log('Dashboard data loaded:', data);
    } catch (e) {
        console.error('Invalid dashboard JSON data', e);
        return;
    }

    // Ensure severity data has proper fallback
    let severityData = data.severity;
    if (Array.isArray(severityData)) {
        severityData = {
            critical: severityData[0] || 0,
            high: severityData[1] || 0,
            medium: severityData[2] || 0,
            low: severityData[3] || 0
        };
    }
    if (!severityData || typeof severityData !== 'object') {
        severityData = { critical: 0, high: 0, medium: 0, low: 0 };
    }
    const severityValues = [
        severityData.critical || 0,
        severityData.high || 0,
        severityData.medium || 0,
        severityData.low || 0
    ];

    // Severity Distribution Doughnut
    const severityEl = document.getElementById('severityChart');
    if (severityEl && window.Chart) {
        console.log('Creating severity chart with values:', severityValues);
        const ctx = severityEl.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: severityValues,
                    backgroundColor: ['#ef4444', '#f97316', '#eab308', '#3b82f6'],
                    borderColor: '#1e2432',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#a0aec0', font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = severityValues.reduce((a, b) => a + b, 0);
                                const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percent}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Trend Line with full data
    const trendEl = document.getElementById('trendChart');
    if (trendEl && window.Chart) {
        const ctx = trendEl.getContext('2d');
        const labels = (data.trend && data.trend.labels) || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const values = (data.trend && data.trend.values) || [0, 0, 0, 0, 1899, 2245, 890];
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CVEs Discovered',
                    data: values,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.05)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#a0aec0', font: { size: 11 } } },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#a0aec0',
                        padding: 10,
                        borderColor: '#3b82f6',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: { ticks: { color: '#a0aec0', font: { size: 10 } }, grid: { color: 'rgba(160,174,192,0.1)' } },
                    y: { ticks: { color: '#a0aec0', font: { size: 10 } }, grid: { color: 'rgba(160,174,192,0.1)' } }
                }
            }
        });
    }

    // Ports Bar (horizontal) with top 10 data - better visualization
    const portsEl = document.getElementById('portsChart');
    if (portsEl && window.Chart) {
        const ctx = portsEl.getContext('2d');
        const labels = (data.ports && data.ports.labels) || ['Port 1723 (pptp)', 'Port 3306 (mysql)', 'Port 3389 (rdp)', 'Port 8043 (https)', 'Port 5050 (http)'];
        const values = (data.ports && data.ports.values) || [145, 132, 98, 87, 76];
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CVE Count',
                    data: values,
                    backgroundColor: 'rgba(59,130,246,0.9)',
                    borderColor: '#3b82f6',
                    borderWidth: 1.5,
                    borderSkipped: false,
                    borderRadius: 4,
                    barThickness: 'flex',  // Flexible bar thickness
                    maxBarThickness: 28    // Max 28px per bar for compact display
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 5,
                        right: 10,
                        top: 5,
                        bottom: 5
                    }
                },
                plugins: {
                    legend: { 
                        display: true, 
                        labels: { 
                            color: '#a0aec0', 
                            font: { size: 10, weight: 'bold' },
                            padding: 8
                        } 
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.9)',
                        titleColor: '#fff',
                        bodyColor: '#a0aec0',
                        padding: 10,
                        titleFont: { size: 11, weight: 'bold' },
                        bodyFont: { size: 10 },
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return 'CVEs: ' + context.parsed.x;
                            }
                        }
                    }
                },
                scales: {
                    x: { 
                        ticks: { 
                            color: '#a0aec0', 
                            font: { size: 10 },
                            callback: function(value) { return value; }
                        }, 
                        grid: { color: 'rgba(160,174,192,0.1)' },
                        title: { display: true, text: 'CVE Count', color: '#a0aec0', font: { size: 10 } }
                    },
                    y: { 
                        ticks: { 
                            color: '#a0aec0', 
                            font: { size: 10, weight: '500' },
                            padding: 6,
                            autoSkip: false  // Show all labels
                        },
                        grid: { display: false }  // Hide horizontal grid for cleaner look
                    }
                }
            }
        });
    }
})();
