// web/static/js/dashboard.js
// Dashboard functionality

(function () {
    'use strict';

    /* ==============================
       SIDEBAR
    ============================== */
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem(
                'sidebarCollapsed',
                sidebar.classList.contains('collapsed')
            );
        });
    }

    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        sidebar.classList.add('collapsed');
    }

    /* ==============================
       SEVERITY BAR RENDER
    ============================== */
    function renderSeverityBar(sev) {
        const total =
            sev.critical + sev.high + sev.medium + sev.low;

        if (!total) return;

        document.getElementById('severity-critical-seg').style.width =
            (sev.critical / total) * 100 + '%';
        document.getElementById('severity-high-seg').style.width =
            (sev.high / total) * 100 + '%';
        document.getElementById('severity-medium-seg').style.width =
            (sev.medium / total) * 100 + '%';
        document.getElementById('severity-low-seg').style.width =
            (sev.low / total) * 100 + '%';
    }

    /* ==============================
       DASHBOARD LIVE UPDATE (3.4A.2)
    ============================== */
    async function loadLatestScan() {
        try {
            const res = await fetch('/scan/latest');
            const data = await res.json();

            if (!res.ok || data.status === 'no_scan') return;

            // Last scan time
            const lastScan = document.getElementById('last-scan-time');
            if (lastScan && data.start_time) {
                lastScan.textContent = new Date(
                    data.start_time
                ).toLocaleString();
            }

            // Summary cards
            if (data.summary) {
                const s = data.summary;

                setText('hosts_scanned', s.hosts_scanned);
                setText('open_ports', s.open_ports);
                setText('total_cves', s.total_cves);
                setText('critical', s.severity?.critical);

                if (s.severity) {
                    renderSeverityBar(s.severity);
                }
            }

            // Nếu scan đang chạy → auto refresh
            if (data.status === 'running') {
                setTimeout(loadLatestScan, 3000);
            }
        } catch (err) {
            console.warn('Dashboard update failed:', err);
        }
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el && value !== undefined) {
            el.textContent = value;
        }
    }

    /* ==============================
       INIT
    ============================== */
    document.addEventListener('DOMContentLoaded', function () {
        loadLatestScan();
    });
})();
