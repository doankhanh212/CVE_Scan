// CVE Detail Modal Functions

// Initialize modal
const modal = document.getElementById('cveDetailModal');
const modalContent = modal.querySelector('.modal-content');

// Setup modal close handlers on page load
document.addEventListener('DOMContentLoaded', function() {
    setupAlertItemHandlers();
    setupModalHandlers();
});

function setupAlertItemHandlers() {
    const alertItems = document.querySelectorAll('.alert-item-compact');
    alertItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.stopPropagation();
            openCveModal(this);
        });
    });
}

function setupModalHandlers() {
    // Close with Escape key (optional)
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeCveModal();
        }
    });
}

function openCveModal(element) {
    // Extract data from data attributes
    const cveId = element.getAttribute('data-cve-id');
    const description = element.getAttribute('data-cve-description') || 'No description available';
    const cvss = element.getAttribute('data-cve-cvss') || 'N/A';
    const host = element.getAttribute('data-cve-host') || '-';
    const port = element.getAttribute('data-cve-port') || '-';
    const service = element.getAttribute('data-cve-service') || 'Unknown';
    const severity = element.getAttribute('data-cve-severity') || 'Unknown';
    const remediation = element.getAttribute('data-cve-remediation') || 'Contact vendor for security updates';

    // Update modal content
    document.getElementById('modalCveId').textContent = cveId;
    document.getElementById('modalHost').textContent = host;
    document.getElementById('modalPort').textContent = `${port} (${service})`;
    document.getElementById('modalSeverity').innerHTML = `<span class="severity-badge ${severity.toLowerCase()}">${severity}</span>`;
    document.getElementById('modalCvss').textContent = cvss;
    document.getElementById('modalDescription').textContent = description;
    document.getElementById('modalRemediation').textContent = remediation;

    // Store CVE ID for copy function
    window.currentCveId = cveId;

    // Show modal
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeCveModal() {
    modal.classList.remove('show');
    document.body.style.overflow = 'auto';
}

function copyToClipboard() {
    if (!window.currentCveId) return;

    const text = window.currentCveId;
    
    // Create temporary input element
    const temp = document.createElement('textarea');
    temp.value = text;
    document.body.appendChild(temp);
    temp.select();
    
    try {
        document.execCommand('copy');
        
        // Show feedback
        const btn = event.target.closest('.modal-btn-secondary');
        if (btn && btn.querySelector('i').classList.contains('fa-copy')) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            btn.style.background = 'var(--success)';
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = '';
            }, 2000);
        }
    } catch (err) {
        console.error('Failed to copy:', err);
        alert('Failed to copy CVE ID');
    }
    
    document.body.removeChild(temp);
}

function viewOnNVD() {
    if (!window.currentCveId) return;
    
    const nvdUrl = `https://nvd.nist.gov/vuln/detail/${window.currentCveId}`;
    window.open(nvdUrl, '_blank', 'noopener,noreferrer');
}
