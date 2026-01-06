(function () {
    'use strict';
    
    // Get dashboard data from embedded JSON
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

    // Initialize Chart.js
    if (typeof Chart === 'undefined') {
        console.error('Chart.js library not loaded');
        return;
    }

    // ===== SEVERITY CHART (Doughnut) =====
    const severityEl = document.getElementById('severityChart');
    if (severityEl) {
        const severityData = data.severity || { critical: 0, high: 0, medium: 0, low: 0 };
        const severityValues = [
            severityData.critical || 0,
            severityData.high || 0,
            severityData.medium || 0,
            severityData.low || 0
        ];
        
        console.log('Creating severity chart with values:', severityValues);
        
        try {
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
                            position: 'bottom',
                            labels: { 
                                color: '#a0aec0', 
                                font: { size: 11 },
                                padding: 15,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: '#fff',
                            bodyColor: '#a0aec0',
                            padding: 12,
                            borderColor: '#3b82f6',
                            borderWidth: 1
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating severity chart:', e);
        }
    }

    // ===== TREND CHART (Line) =====
    const trendEl = document.getElementById('trendChart');
    if (trendEl) {
        const trendData = data.trend || { labels: [], values: [] };
        const labels = trendData.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
        const values = trendData.values || [10, 15, 12, 20, 18, 25];
        
        console.log('Creating trend chart with labels:', labels);
        
        try {
            const ctx = trendEl.getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'CVEs Discovered',
                        data: values,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59,130,246,0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#3b82f6',
                        pointBorderColor: '#1e2432',
                        pointBorderWidth: 2
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
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: '#fff',
                            bodyColor: '#a0aec0',
                            padding: 10,
                            borderColor: '#3b82f6',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        x: { 
                            ticks: { color: '#a0aec0', font: { size: 10 } }, 
                            grid: { color: 'rgba(160,174,192,0.1)' }
                        },
                        y: { 
                            ticks: { color: '#a0aec0', font: { size: 10 } }, 
                            grid: { color: 'rgba(160,174,192,0.1)' }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating trend chart:', e);
        }
    }

    // ===== PORTS CHART (Horizontal Bar) =====
    const portsEl = document.getElementById('portsChart');
    if (portsEl) {
        const portsData = data.ports || { labels: [], values: [] };
        const labels = portsData.labels && portsData.labels.length > 0 
            ? portsData.labels 
            : ['Port 443 (HTTPS)', 'Port 80 (HTTP)', 'Port 22 (SSH)', 'Port 3306 (MySQL)', 'Port 5432 (PostgreSQL)'];
        const values = portsData.values && portsData.values.length > 0 
            ? portsData.values 
            : [145, 132, 98, 87, 76];
        
        console.log('Creating ports chart with labels:', labels);
        
        try {
            const ctx = portsEl.getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'CVE Count',
                        data: values,
                        backgroundColor: 'rgba(59,130,246,0.9)',
                        borderColor: '#3b82f6',
                        borderWidth: 2,
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { 
                            display: true, 
                            labels: { 
                                color: '#a0aec0', 
                                font: { size: 12, weight: 'bold' },
                                padding: 15
                            } 
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.9)',
                            titleColor: '#fff',
                            bodyColor: '#a0aec0',
                            padding: 12,
                            borderColor: '#3b82f6',
                            borderWidth: 1,
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
                                font: { size: 11 }
                            }, 
                            grid: { color: 'rgba(160,174,192,0.1)' }
                        },
                        y: { 
                            ticks: { 
                                color: '#a0aec0', 
                                font: { size: 11, weight: '500' }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating ports chart:', e);
        }
    }

    // ===== HOST RISK CHART (Radar) =====
    const hostRiskEl = document.getElementById('hostsChart');
    if (hostRiskEl) {
        const hostRiskData = data.hostRisk || [];
        const hosts = hostRiskData.length > 0 
            ? hostRiskData.map(h => h.name || 'Host').slice(0, 10)
            : ['Host 1', 'Host 2', 'Host 3', 'Host 4'];
        const risks = hostRiskData.length > 0 
            ? hostRiskData.map(h => h.cves || 0).slice(0, 10)
            : [15, 12, 8, 5];
        
        console.log('Creating host risk chart with hosts:', hosts);
        
        try {
            const ctx = hostRiskEl.getContext('2d');
            new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: hosts,
                    datasets: [{
                        label: 'CVE Count',
                        data: risks,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239,68,68,0.2)',
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 5,
                        pointBackgroundColor: '#ef4444',
                        pointBorderColor: '#1e2432',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { 
                            labels: { 
                                color: '#a0aec0', 
                                font: { size: 11 }
                            } 
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: '#fff',
                            bodyColor: '#a0aec0',
                            padding: 10
                        }
                    },
                    scales: {
                        r: {
                            ticks: {
                                color: '#a0aec0',
                                font: { size: 10 }
                            },
                            grid: {
                                color: 'rgba(160,174,192,0.1)'
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Error creating host risk chart:', e);
        }
    }
    
    console.log('Dashboard charts initialization complete');
})();
