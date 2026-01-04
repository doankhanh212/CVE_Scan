/**
 * Modal Handlers - Global functions for all modal interactions
 * Defines functions called from template onclick attributes
 */

// ===========================
// CVE DETAIL MODAL HANDLERS
// ===========================
function closeCVEDetail() {
    const modal = document.getElementById('cveDetailModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
}

function switchCVETab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.classList.remove('active');
        tab.style.display = 'none';
    });

    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    const tabContent = document.getElementById(`tab-${tabName}`);
    if (tabContent) {
        tabContent.classList.add('active');
        tabContent.style.display = 'block';
    }

    // Add active class to clicked button
    event.target.closest('.tab-button')?.classList.add('active');
}

function exportCVEDetail() {
    const cveId = document.getElementById('cveModalTitle')?.textContent || 'CVE-Unknown';
    alert(`Export CVE ${cveId} - Feature coming soon`);
}

// ===========================
// CVE MODAL (vulnerabilities.html)
// ===========================
function closeCVEModal() {
    const modal = document.getElementById('cve-detail-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// ===========================
// API TEST MODAL HANDLERS
// ===========================
function closeApiTestModal() {
    const modal = document.getElementById('api-test-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// ===========================
// SCAN HANDLERS
// ===========================
function viewScanDetail(scanId) {
    if (!scanId) {
        alert('Scan ID not provided');
        return;
    }
    window.location.href = `/result/${scanId}`;
}

function stopScan(scanId) {
    if (!confirm('Are you sure you want to stop this scan?')) {
        return;
    }
    
    fetch(`/api/scan/${scanId}/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('Scan stopped successfully');
            location.reload();
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(err => alert('Error: ' + err.message));
}

function viewScan(scanId) {
    if (!scanId) {
        alert('Scan ID not provided');
        return;
    }
    window.location.href = `/result/${scanId}`;
}

function exportScan(scanId) {
    if (!scanId) {
        alert('Scan ID not provided');
        return;
    }
    window.location.href = `/export/csv?scan_id=${scanId}`;
}

function deleteScan(scanId) {
    if (!confirm('Are you sure you want to delete this scan? This action cannot be undone.')) {
        return;
    }
    
    fetch(`/api/scan/${scanId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('Scan deleted successfully');
            location.reload();
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(err => alert('Error: ' + err.message));
}

// ===========================
// SECURITY STANDARDS HANDLERS
// ===========================
function loadOWASPFramework() {
    console.log('Loading OWASP Framework...');
    // Implementation depends on your backend API
    // For now, just log the action
    alert('OWASP Framework - Feature implementation needed');
}

function loadMITREFramework() {
    console.log('Loading MITRE Framework...');
    // Implementation depends on your backend API
    alert('MITRE Framework - Feature implementation needed');
}

function loadSCPFramework() {
    console.log('Loading Secure Coding Practices Framework...');
    // Implementation depends on your backend API
    alert('SCP Framework - Feature implementation needed');
}

// ===========================
// MODAL OUTSIDE CLICK HANDLERS
// ===========================
document.addEventListener('DOMContentLoaded', function() {
    // Close CVE Detail Modal on outside click
    const cveDetailModal = document.getElementById('cveDetailModal');
    if (cveDetailModal) {
        cveDetailModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeCVEDetail();
            }
        });
    }

    // Close API Test Modal on outside click
    const apiTestModal = document.getElementById('api-test-modal');
    if (apiTestModal) {
        apiTestModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeApiTestModal();
            }
        });
    }

    // Close CVE Modal on outside click
    const cveModal = document.getElementById('cve-detail-modal');
    if (cveModal) {
        cveModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeCVEModal();
            }
        });
    }
});
