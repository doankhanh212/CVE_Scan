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

function switchCVETab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.modal-tab-content');
    tabs.forEach(tab => {
        tab.style.display = 'none';
    });

    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.modal-tab');
    buttons.forEach(btn => {
        btn.classList.remove('active');
        btn.style.borderBottomColor = 'transparent';
        btn.style.color = 'var(--text-secondary)';
    });

    // Show selected tab
    const tabContent = document.getElementById(`tab-${tabName}`);
    if (tabContent) {
        tabContent.style.display = 'block';
    }

    // Add active class to clicked button
    event.target.closest('.modal-tab').classList.add('active');
    event.target.closest('.modal-tab').style.borderBottomColor = 'var(--primary)';
    event.target.closest('.modal-tab').style.color = 'var(--primary)';

    // Load CWE data when clicking CWE tab
    if (tabName === 'cwe' && window.currentCveId) {
        loadCWEData(window.currentCveId);
    }

    // Load NIST data when clicking NIST tab
    if (tabName === 'nist' && window.currentCveId) {
        loadNISTData(window.currentCveId);
    }
}

async function loadCWEData(cveId) {
    console.log('[CVE_MODAL] Loading CWE data for', cveId);
    
    const container = document.getElementById('cwe-consequences-container');
    if (!container) {
        console.error('[CVE_MODAL] CWE container not found!');
        return;
    }
    
    try {
        const url = `/api/cve/${cveId}/cwe-data`;
        console.log('[CVE_MODAL] Fetching from:', url);
        
        const response = await fetch(url);
        console.log('[CVE_MODAL] Response status:', response.status);
        
        const data = await response.json();
        console.log('[CVE_MODAL] Response data:', data);

        if (data.success && data.cwe_consequences) {
            const consequences = data.cwe_consequences;
            console.log('[CVE_MODAL] Consequences:', consequences);
            
            if (consequences.consequences && consequences.consequences.length > 0) {
                let html = '<div style="display: flex; flex-direction: column; gap: 10px;">';
                
                consequences.consequences.forEach((c, idx) => {
                    console.log(`[CVE_MODAL] Consequence ${idx}:`, c);
                    html += `<div style="padding: 12px; background: var(--bg-tertiary); border-radius: 4px; border-left: 3px solid var(--primary);">
                        <strong>${c.scope || 'Consequence'}</strong><br/>
                        <span style="color: var(--text-secondary); font-size: 13px;">${c.impact || '-'}</span>
                    </div>`;
                });
                html += '</div>';
                console.log('[CVE_MODAL] Setting CWE HTML');
                container.innerHTML = html;
            } else {
                console.log('[CVE_MODAL] No consequences array found');
                container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No data available</p>';
            }
        } else {
            console.log('[CVE_MODAL] Response not success or no cwe_consequences');
            container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No data available</p>';
        }
    } catch (error) {
        console.error('[CVE_MODAL] Error loading CWE data:', error);
        container.innerHTML = '<p style="text-align: center; color: var(--error);">Error: ' + error.message + '</p>';
    }
}

async function loadNISTData(cveId) {
    console.log('[CVE_MODAL] Loading NIST data for', cveId);
    
    const container = document.getElementById('nist-recommendations-container');
    if (!container) {
        console.error('[CVE_MODAL] NIST container not found!');
        return;
    }
    
    try {
        const descText = document.getElementById('modalDescription').textContent || '';
        const remediationText = window.currentCveData?.remediation || '';
        
        // Get CWE data from modal (set by openCveModal)
        const cweData = window.currentCveData?.cwe || '';
        
        // Extract CWE IDs if available
        let cweIds = [];
        if (cweData) {
            try {
                const parsed = JSON.parse(cweData);
                if (Array.isArray(parsed)) {
                    cweIds = parsed;
                } else if (typeof parsed === 'object') {
                    cweIds = [parsed.id || parsed];
                }
            } catch (e) {
                if (typeof cweData === 'string') {
                    cweIds = cweData.split(',').map(id => id.trim()).filter(Boolean);
                }
            }
        }
        
        console.log('[CVE_MODAL] CWE IDs:', cweIds);
        
        // First, try to get analysis data to extract CWE mitigations (like vulnerabilities page does)
        let mitigation_texts = [remediationText].filter(Boolean);
        
        try {
            console.log('[CVE_MODAL] Fetching CVE analysis for mitigations...');
            const analysisResponse = await fetch(`/api/cve/${cveId}/analysis`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (analysisResponse.ok) {
                const analysis = await analysisResponse.json();
                console.log('[CVE_MODAL] Analysis response:', analysis);
                
                // Extract mitigations from CWE explanations (like vulnerabilities page does)
                if (analysis.cwe_explanations && Array.isArray(analysis.cwe_explanations)) {
                    analysis.cwe_explanations.forEach(cweItem => {
                        if (cweItem.mitigations && Array.isArray(cweItem.mitigations)) {
                            cweItem.mitigations.forEach(mit => {
                                if (mit.description && !mitigation_texts.includes(mit.description)) {
                                    mitigation_texts.push(mit.description);
                                    console.log('[CVE_MODAL] Added mitigation from analysis:', mit.description.substring(0, 50) + '...');
                                }
                            });
                        }
                    });
                }
            }
        } catch (analysisError) {
            console.warn('[CVE_MODAL] Could not get analysis data:', analysisError);
            // Continue anyway with just remediation text
        }
        
        console.log('[CVE_MODAL] Total mitigation texts:', mitigation_texts.length);
        console.log('[CVE_MODAL] Mitigation texts:', mitigation_texts);
        
        const response = await fetch(`/api/cve/${cveId}/nist-recommendations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mitigation_texts: mitigation_texts,
                cve_description: descText,
                cwe_ids: cweIds
            })
        });
        
        console.log('[CVE_MODAL] NIST response status:', response.status);
        const data = await response.json();
        console.log('[CVE_MODAL] NIST response data:', JSON.stringify(data, null, 2));

        if (data.recommendations && data.recommendations.length > 0) {
            let html = '<table style="width: 100%; border-collapse: collapse;">';
            html += '<tr style="background: var(--bg-tertiary);"><th style="padding: 8px; text-align: left; border-bottom: 1px solid var(--border-color); width: 80px;">Control ID</th><th style="padding: 8px; text-align: left; border-bottom: 1px solid var(--border-color); width: 150px;">Control Name</th><th style="padding: 8px; text-align: left; border-bottom: 1px solid var(--border-color); width: 100px;">Type</th><th style="padding: 8px; text-align: left; border-bottom: 1px solid var(--border-color);">Recommended Action</th></tr>';
            
            data.recommendations.forEach((rec, idx) => {
                console.log(`[CVE_MODAL] NIST rec ${idx}:`, JSON.stringify(rec, null, 2));
                
                // Use exact field names from API response (matching vulnerabilities.html)
                const controlId = rec.control_id || '-';
                const controlName = rec.control_name || '-';
                const type = rec.type || '-';
                const action = rec.action || '-';  // Changed from recommended_action to action
                
                // Determine badge color based on type
                let badgeColor = '#2196F3';  // Detective blue
                if (type.toUpperCase() === 'PREVENTIVE') badgeColor = '#4CAF50';  // Preventive green
                if (type.toUpperCase() === 'CORRECTIVE') badgeColor = '#FF9800';  // Corrective orange
                
                html += `<tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 8px; font-weight: 500;">${controlId}</td>
                    <td style="padding: 8px;">${controlName}</td>
                    <td style="padding: 8px;"><span style="background: ${badgeColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: bold;">${type}</span></td>
                    <td style="padding: 8px; max-width: 400px; word-break: break-word;">${action}</td>
                </tr>`;
            });
            html += '</table>';
            console.log('[CVE_MODAL] Setting NIST HTML');
            container.innerHTML = html;
        } else {
            console.log('[CVE_MODAL] No recommendations in response');
            container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No recommendations available</p>';
        }
    } catch (error) {
        console.error('[CVE_MODAL] Error loading NIST data:', error);
        container.innerHTML = '<p style="text-align: center; color: var(--error);">Error: ' + error.message + '</p>';
    }
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
    const cwe = element.getAttribute('data-cve-cwe') || '';
    const cpe = element.getAttribute('data-cve-cpe') || '';

    // Update modal content
    document.getElementById('modalCveId').textContent = cveId;
    document.getElementById('modalHost').textContent = host;
    document.getElementById('modalPort').textContent = `${port} (${service})`;
    document.getElementById('modalSeverity').innerHTML = `<span class="severity-badge ${severity.toLowerCase()}">${severity}</span>`;
    document.getElementById('modalCvss').textContent = cvss;
    document.getElementById('modalDescription').textContent = description;

    // Store CVE ID and additional data for other functions
    window.currentCveId = cveId;
    window.currentCveData = { cwe, cpe, remediation };

    // Immediately load CWE and NIST data
    loadCWEData(cveId);
    loadNISTData(cveId);

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
