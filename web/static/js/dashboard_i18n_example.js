/**
 * dashboard.js - Enhanced with i18n support
 * 
 * This example shows how to integrate i18n into existing JavaScript
 * while maintaining all original functionality
 */

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
       DASHBOARD LIVE UPDATE
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

            // Check if scan is still running
            if (data.status === 'running') {
                setTimeout(loadLatestScan, 3000);
            }
        } catch (error) {
            console.error('Error loading latest scan:', error);
            // Show error message with i18n
            if (typeof i18n !== 'undefined') {
                const errorMsg = i18n.t('messages.error_loading_data');
                console.warn(errorMsg);
            }
        }
    }

    /**
     * Helper to set text content safely
     */
    function setText(elementId, value) {
        const el = document.getElementById(elementId);
        if (el && value !== undefined && value !== null) {
            el.textContent = value;
        }
    }

    /* ==============================
       MESSAGE DISPLAY WITH I18N
    ============================== */
    function showMessage(messageKey, type = 'info') {
        if (typeof i18n === 'undefined') {
            console.warn('i18n not available');
            return;
        }

        const message = i18n.t(messageKey);
        const container = document.getElementById('message-container');
        
        if (!container) {
            console.log(`[${type}] ${message}`);
            return;
        }

        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.innerHTML = `
            <span>${message}</span>
            <button class="close-message" aria-label="Close message">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(messageEl);

        messageEl.querySelector('.close-message').addEventListener('click', () => {
            messageEl.remove();
        });

        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 5000);
    }

    /* ==============================
       INITIALIZATION
    ============================== */
    
    // Load latest scan on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadLatestScan);
    } else {
        loadLatestScan();
    }

    // Listen for language changes and reload relevant data
    if (document.addEventListener) {
        document.addEventListener('i18n:languageChanged', (e) => {
            console.log('Dashboard language changed to:', e.detail.newLanguage);
            
            // Optionally reload scan data to ensure consistency
            // loadLatestScan();
        });
    }

    // Expose functions for external use if needed
    window.dashboard = {
        loadLatestScan,
        showMessage,
        renderSeverityBar
    };
})();
