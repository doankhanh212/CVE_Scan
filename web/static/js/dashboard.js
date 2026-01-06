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

        // Safe rendering - check if elements exist
        const criticalEl = document.getElementById('severity-critical-seg');
        const highEl = document.getElementById('severity-high-seg');
        const mediumEl = document.getElementById('severity-medium-seg');
        const lowEl = document.getElementById('severity-low-seg');

        if (criticalEl) criticalEl.style.width = (sev.critical / total) * 100 + '%';
        if (highEl) highEl.style.width = (sev.high / total) * 100 + '%';
        if (mediumEl) mediumEl.style.width = (sev.medium / total) * 100 + '%';
        if (lowEl) lowEl.style.width = (sev.low / total) * 100 + '%';
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
    /* ==============================
       TABLE SEARCH/FILTER WITH SEVERITY
    ============================== */
    function initTableSearch() {
        const searchInput = document.getElementById('cveSearch');
        const severityFilter = document.getElementById('severityFilter');
        const cveRows = document.querySelectorAll('.cve-row');

        function applyFilters() {
            const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
            const severityTerm = severityFilter ? severityFilter.value : '';

            cveRows.forEach(row => {
                const cveText = row.textContent.toLowerCase();
                const cveSeverity = row.getAttribute('data-severity') || '';
                
                const matchSearch = !searchTerm || cveText.includes(searchTerm);
                const matchSeverity = !severityTerm || cveSeverity === severityTerm;
                
                if (matchSearch && matchSeverity) {
                    row.classList.remove('hidden');
                } else {
                    row.classList.add('hidden');
                }
            });
        }

        if (searchInput) {
            searchInput.addEventListener('input', applyFilters);
        }
        if (severityFilter) {
            severityFilter.addEventListener('change', applyFilters);
        }
    }

    /* ==============================
       HOST RISK FILTER
    ============================== */
    function populateHostFilter() {
        const hostFilterSelect = document.getElementById('hostFilter');
        const hostRows = document.querySelectorAll('.host-risk-row');
        
        if (!hostFilterSelect) return;
        
        // Extract hosts with their CVE counts from rows
        const hostsWithCounts = Array.from(hostRows).map(row => {
            const host = row.getAttribute('data-host');
            // Get total CVEs from the severity badges
            const badges = row.querySelectorAll('.risk-count');
            const totalCves = Array.from(badges).reduce((sum, badge) => {
                return sum + parseInt(badge.textContent || '0');
            }, 0);
            return { host, totalCves };
        });
        
        // Sort by CVE count descending (most vulnerable first)
        hostsWithCounts.sort((a, b) => b.totalCves - a.totalCves);
        const allHosts = hostsWithCounts.map(item => item.host);
        
        // Clear existing options except "All Hosts"
        while (hostFilterSelect.options.length > 1) {
            hostFilterSelect.remove(1);
        }
        
        // Add all host options with truncated display names
        allHosts.forEach(host => {
            const opt = document.createElement('option');
            opt.value = host;
            // Truncate long hostnames for display
            const displayName = host.length > 35 ? host.substring(0, 32) + '...' : host;
            opt.textContent = displayName;
            opt.title = host; // Full name on hover
            hostFilterSelect.appendChild(opt);
        });
    }

    function initHostRiskFilter() {
        const hostSearchInput = document.getElementById('hostSearch');
        const hostFilterSelect = document.getElementById('hostFilter');
        const hostRows = document.querySelectorAll('.host-risk-row');

        function applyHostFilters() {
            const searchTerm = hostSearchInput ? hostSearchInput.value.toLowerCase() : '';
            const selectedHost = hostFilterSelect ? hostFilterSelect.value : '';

            hostRows.forEach(row => {
                const hostText = row.textContent.toLowerCase();
                const hostValue = row.getAttribute('data-host') || '';
                
                const matchSearch = !searchTerm || hostText.includes(searchTerm);
                const matchHost = !selectedHost || hostValue === selectedHost;
                
                if (matchSearch && matchHost) {
                    row.classList.remove('hidden');
                } else {
                    row.classList.add('hidden');
                }
            });
        }

        if (hostSearchInput) {
            hostSearchInput.addEventListener('input', applyHostFilters);
        }
        if (hostFilterSelect) {
            hostFilterSelect.addEventListener('change', applyHostFilters);
        }
    }

    /* ==============================
       INIT
    ============================== */
    document.addEventListener('DOMContentLoaded', function () {
        loadLatestScan();
        initTableSearch();
        populateHostFilter();
        initHostRiskFilter();
    });
})();
