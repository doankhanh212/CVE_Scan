/**
 * Settings Page JavaScript
 * Handles form interactions, validation, API calls, and UI updates
 */

document.addEventListener('DOMContentLoaded', function() {
    initSettings();
});

// Initialize settings page
async function initSettings() {
    loadSettings();
    setupTabNavigation();
    setupEventListeners();
    loadDbStatus();
}

// Load current settings
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();
        
        if (!data.settings) return;
        
        const settings = data.settings;
        
        // Populate form fields
        document.getElementById('nvdApiKey').value = settings.nvd_api_key || '';
        document.getElementById('useLocalDb').checked = settings.use_local_db;
        document.getElementById('localDbPath').value = settings.local_db_path || '';
        document.getElementById('logVerbosity').value = settings.log_verbosity || 'info';
        document.getElementById('maxConcurrentScans').value = settings.max_concurrent_scans || 2;
        document.getElementById('scanTimeout').value = settings.scan_timeout || 60;
        document.getElementById('nmapThreads').value = settings.nmap_threads || 10;
        document.getElementById('cveCapPerService').value = settings.cve_cap_per_service || 100;
        document.getElementById('fuzzyMatchThreshold').value = settings.fuzzy_match_threshold || 80;
        document.getElementById('thresholdValue').textContent = (settings.fuzzy_match_threshold || 80) + '%';
        document.getElementById('retentionDays').value = settings.retention_days || 90;
        
        // Set checkboxes
        document.querySelector('[name="fuzzy_match_cpe"]').checked = settings.fuzzy_match_cpe;
        document.querySelector('[name="enable_scheduling"]').checked = settings.enable_scheduling;
        document.querySelector('[name="enable_email_alerts"]').checked = settings.enable_email_alerts;
        document.getElementById('emailSmtpServer').value = settings.email_smtp_server || '';
        
        // Show/hide local DB path
        updateLocalDbPathVisibility();
    } catch (error) {
        console.error('Error loading settings:', error);
        showNotification('Failed to load settings', 'error');
    }
}

// Setup tab navigation
function setupTabNavigation() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked
            this.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        });
    });
}

// Setup event listeners
function setupEventListeners() {
    // Toggle API key visibility
    document.getElementById('toggleApiKey').addEventListener('click', function(e) {
        e.preventDefault();
        const input = document.getElementById('nvdApiKey');
        const icon = this.querySelector('i');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    });
    
    // Test API button
    document.getElementById('testApiBtn').addEventListener('click', testApiConnection);
    
    // Use local DB checkbox
    document.getElementById('useLocalDb').addEventListener('change', updateLocalDbPathVisibility);
    
    // Browse DB button
    document.getElementById('browseDbBtn').addEventListener('click', browseDbPath);
    
    // Rebuild DB button
    document.getElementById('rebuildDbBtn').addEventListener('click', rebuildDatabase);
    
    // Fuzzy match threshold range
    document.getElementById('fuzzyMatchThreshold').addEventListener('input', function() {
        document.getElementById('thresholdValue').textContent = this.value + '%';
    });
    
    // Enable email alerts checkbox
    document.querySelector('[name="enable_email_alerts"]').addEventListener('change', function() {
        document.getElementById('emailSmtpServer').disabled = !this.checked;
    });
    
    // Export/Import/Reset buttons
    document.getElementById('exportSettingsBtn').addEventListener('click', exportSettings);
    document.getElementById('importSettingsBtn').addEventListener('click', () => {
        document.getElementById('importFile').click();
    });
    document.getElementById('resetSettingsBtn').addEventListener('click', resetSettings);
    
    // Save/Cancel buttons
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    document.getElementById('cancelBtn').addEventListener('click', cancelSettings);
    
    // Create hidden file input for import
    if (!document.getElementById('importFile')) {
        const input = document.createElement('input');
        input.type = 'file';
        input.id = 'importFile';
        input.style.display = 'none';
        input.accept = '.json';
        input.addEventListener('change', importSettings);
        document.body.appendChild(input);
    }
}

// Update local DB path visibility
// Update local DB path visibility and visual modes
function updateLocalDbPathVisibility() {
    const useLocalDb = document.getElementById('useLocalDb').checked;
    const pathGroup = document.getElementById('localDbPathGroup');
    const modeLocalDb = document.getElementById('modeLocalDb');
    const modeApiKey = document.getElementById('modeApiKey');
    const apiKeyHelp = document.getElementById('apiKeyHelp');
    
    // Show/hide DB path input
    if (pathGroup) {
        pathGroup.style.display = useLocalDb ? 'block' : 'none';
    }
    
    // Update mode visual states
    if (modeLocalDb && modeApiKey) {
        if (useLocalDb) {
            modeLocalDb.classList.add('active');
            modeLocalDb.style.opacity = '1';
            modeApiKey.classList.remove('active');
            modeApiKey.style.opacity = '0.6';
            
            if (apiKeyHelp) {
                apiKeyHelp.innerHTML = '🔒 <strong>Not currently used</strong> - Local Database is enabled';
            }
        } else {
            modeLocalDb.classList.remove('active');
            modeLocalDb.style.opacity = '0.6';
            modeApiKey.classList.add('active');
            modeApiKey.style.opacity = '1';
            
            if (apiKeyHelp) {
                apiKeyHelp.innerHTML = 'Get your API key from <a href="https://nvd.nist.gov/developers/request-an-api-key" target="_blank" rel="noopener noreferrer">nvd.nist.gov</a>';
            }
        }
    }
}

// Test API connection
async function testApiConnection() {
    const apiKey = document.getElementById('nvdApiKey').value.trim();
    
    if (!apiKey || apiKey === '***') {
        showNotification('⚠️ Please enter an API key first', 'warning');
        return;
    }
    
    const btn = document.getElementById('testApiBtn');
    const status = document.getElementById('testStatus');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    status.textContent = 'Testing...';
    status.className = '';
    
    try {
        const response = await fetch('/api/settings/test-api', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nvd_api_key: apiKey })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === 'success') {
            status.textContent = '✓ Valid';
            status.classList.add('success');
            showNotification('✅ API key is valid! Save settings to use it in scans.', 'success');
        } else {
            status.textContent = '✗ Invalid';
            status.classList.add('error');
            showNotification('❌ ' + (data.message || 'API test failed'), 'error');
        }
    } catch (error) {
        status.textContent = '✗ Error';
        status.classList.add('error');
        showNotification('🔌 Network error: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Browse database path
async function browseDbPath() {
    // Since we cannot access file system directly from browser,
    // show a message or use file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.db';
    input.addEventListener('change', function() {
        if (this.files.length > 0) {
            document.getElementById('localDbPath').value = this.files[0].name;
        }
    });
    input.click();
}

// Rebuild database
async function rebuildDatabase() {
    if (!confirm('This will rebuild the entire CVE database. This may take a long time. Continue?')) {
        return;
    }
    
    const btn = document.getElementById('rebuildDbBtn');
    const status = document.getElementById('rebuildStatus');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rebuilding...';
    
    try {
        const response = await fetch('/api/settings/rebuild-db', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        status.textContent = 'Processing...';
        status.classList.remove('error', 'success');
        status.classList.add('warning');
        
        showNotification(data.message || 'Database rebuild started', 'info');
        
        // Poll for completion
        pollDbStatus();
    } catch (error) {
        status.textContent = 'Error';
        status.classList.remove('success', 'warning');
        status.classList.add('error');
        showNotification('Failed to rebuild database: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Load database status
async function loadDbStatus() {
    try {
        const response = await fetch('/api/settings/db-status');
        const data = await response.json();
        
        document.getElementById('dbStatus').textContent = data.status || 'Unknown';
        document.getElementById('dbLastUpdate').textContent = data.last_updated || 'Never';
        document.getElementById('dbCveCount').textContent = data.cve_count || '0';
        document.getElementById('dbSize').textContent = (data.db_size || 0) + ' MB';
    } catch (error) {
        console.error('Error loading DB status:', error);
    }
}

// Poll database status during rebuild
async function pollDbStatus() {
    const maxAttempts = 60; // 60 * 5 seconds = 5 minutes
    let attempt = 0;
    
    const poll = setInterval(async () => {
        attempt++;
        await loadDbStatus();
        
        if (attempt >= maxAttempts) {
            clearInterval(poll);
            showNotification('Database rebuild may be complete. Check status above.', 'info');
        }
    }, 5000); // Check every 5 seconds
}

// Save settings
async function saveSettings(e) {
    if (e) e.preventDefault();
    
    const btn = document.getElementById('saveSettingsBtn');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    try {
        const formData = new FormData(document.getElementById('settingsForm'));
        const data = {
            nvd_api_key: document.getElementById('nvdApiKey').value,
            use_local_db: document.getElementById('useLocalDb').checked,
            local_db_path: document.getElementById('localDbPath').value,
            log_verbosity: document.getElementById('logVerbosity').value,
            max_concurrent_scans: document.getElementById('maxConcurrentScans').value,
            scan_timeout: document.getElementById('scanTimeout').value,
            nmap_threads: document.getElementById('nmapThreads').value,
            cve_cap_per_service: document.getElementById('cveCapPerService').value,
            fuzzy_match_cpe: document.querySelector('[name="fuzzy_match_cpe"]').checked,
            fuzzy_match_threshold: document.getElementById('fuzzyMatchThreshold').value,
            enable_scheduling: document.querySelector('[name="enable_scheduling"]').checked,
            enable_email_alerts: document.querySelector('[name="enable_email_alerts"]').checked,
            email_smtp_server: document.getElementById('emailSmtpServer').value,
            retention_days: document.getElementById('retentionDays').value
        };
        
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Settings saved successfully!', 'success');
        } else {
            showNotification(result.error || 'Failed to save settings', 'error');
        }
    } catch (error) {
        showNotification('Error saving settings: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Cancel and reload settings
function cancelSettings() {
    if (confirm('Discard changes and reload settings?')) {
        loadSettings();
        showNotification('Settings reloaded', 'info');
    }
}

// Export settings
async function exportSettings() {
    try {
        const response = await fetch('/api/settings/export');
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cve_scan_settings_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        showNotification('Settings exported successfully', 'success');
    } catch (error) {
        showNotification('Failed to export settings: ' + error.message, 'error');
    }
}

// Import settings
async function importSettings(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(event) {
        try {
            const data = JSON.parse(event.target.result);
            
            // Ask for confirmation
            if (!confirm('Import settings from file? Current settings will be overwritten.')) {
                return;
            }
            
            // POST the data
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                showNotification('Settings imported successfully!', 'success');
                loadSettings();
            } else {
                showNotification('Failed to import settings', 'error');
            }
        } catch (error) {
            showNotification('Invalid settings file: ' + error.message, 'error');
        }
    };
    reader.readAsText(file);
}

// Reset to default settings
async function resetSettings() {
    if (!confirm('Reset ALL settings to defaults? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/settings/reset', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Settings reset to defaults', 'success');
            setTimeout(() => loadSettings(), 1000);
        } else {
            showNotification(data.error || 'Failed to reset settings', 'error');
        }
    } catch (error) {
        showNotification('Error resetting settings: ' + error.message, 'error');
    }
}

// Show notification toast
function showNotification(message, type = 'info') {
    // If no notification container exists, create one
    let container = document.getElementById('notificationContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notificationContainer';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }
    
    const notification = document.createElement('div');
    notification.style.cssText = `
        background: ${type === 'success' ? '#00ff88' : type === 'error' ? '#ff6b6b' : type === 'warning' ? '#ffd93d' : '#00d4ff'};
        color: ${type === 'warning' ? '#000' : '#fff'};
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-weight: 600;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
