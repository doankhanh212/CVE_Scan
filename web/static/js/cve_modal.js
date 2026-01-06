/**
 * CVE Modal Handler
 * Manages CVE detail modal display and interactions
 */

let currentCveId = null;

/**
 * Open CVE detail modal
 * @param {HTMLElement} element - The alert item element clicked
 */
function openCveModal(element) {
    if (!element) return;
    
    try {
        // Extract CVE data from data attributes
        const cveId = element.getAttribute('data-cve-id') || 'Unknown';
        const severity = element.getAttribute('data-severity') || 'Unknown';
        const description = element.getAttribute('data-description') || 'No description available';
        const cvssScore = element.getAttribute('data-cvss') || 'N/A';
        const cpe = element.getAttribute('data-cpe') || 'N/A';
        const cweId = element.getAttribute('data-cwe') || 'N/A';
        
        currentCveId = cveId;
        
        // Update modal header
        const modalTitle = document.getElementById('cveModalTitle');
        if (modalTitle) {
            modalTitle.textContent = cveId;
        }
        
        // Build modal body HTML
        const modalBody = document.getElementById('cveModalBody');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="cve-detail-section">
                    <h3>Severity</h3>
                    <span class="severity-badge ${severity.toLowerCase()}">
                        ${severity}
                    </span>
                </div>
                
                <div class="cve-detail-section">
                    <h3>CVSS Score</h3>
                    <span class="cvss-score">${cvssScore}</span>
                </div>
                
                <div class="cve-detail-section">
                    <h3>Description</h3>
                    <p>${description}</p>
                </div>
                
                <div class="cve-detail-section">
                    <h3>CPE Match</h3>
                    <span class="cpe-tag">${cpe}</span>
                </div>
                
                <div class="cve-detail-section">
                    <h3>CWE ID</h3>
                    <p>${cweId}</p>
                </div>
            `;
        }
        
        // Show modal
        const modal = document.getElementById('cveModal');
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        }
    } catch (e) {
        console.error('Error opening CVE modal:', e);
    }
}

/**
 * Close CVE modal
 */
function closeCveModal() {
    const modal = document.getElementById('cveModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto'; // Re-enable scrolling
    }
    currentCveId = null;
}

/**
 * Open CVE on NVD website
 */
function viewOnNVD() {
    if (!currentCveId) {
        console.warn('No CVE selected');
        return;
    }
    const nvdUrl = `https://nvd.nist.gov/vuln/detail/${currentCveId}`;
    window.open(nvdUrl, '_blank');
}

/**
 * Copy CVE ID to clipboard
 */
function copyToClipboard() {
    if (!currentCveId) {
        console.warn('No CVE to copy');
        return;
    }
    
    navigator.clipboard.writeText(currentCveId).then(() => {
        // Visual feedback
        const btn = event.target.closest('button');
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            btn.style.backgroundColor = '#10b981';
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.backgroundColor = '';
            }, 2000);
        }
    }).catch(e => {
        console.error('Failed to copy CVE ID:', e);
    });
}

/**
 * Close modal when Escape key is pressed
 */
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeCveModal();
    }
});

/**
 * Handle modal backdrop click (only close if clicking on backdrop, not content)
 */
const modal = document.getElementById('cveModal');
if (modal) {
    modal.addEventListener('click', (e) => {
        // Only close if clicking directly on modal backdrop
        if (e.target === modal) {
            closeCveModal();
        }
    });
}

console.log('CVE Modal Handler loaded');
