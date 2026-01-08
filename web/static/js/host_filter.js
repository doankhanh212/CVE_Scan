/**
 * Host Risk Assessment Filter Handler
 * Manages filtering and searching of host risk data
 */
(function () {
    // Get references to filter elements
    const hostFilterSelect = document.getElementById('hostFilter');
    const hostSearchInput = document.getElementById('hostSearch');
    const hostRiskRows = document.querySelectorAll('.host-risk-row');
    const hostRiskContainer = document.querySelector('.host-risk-container-sm');

    if (!hostFilterSelect || !hostSearchInput) {
        console.warn('Host filter elements not found');
        return;
    }

    // Populate host dropdown from all available hosts
    function populateHostDropdown() {
        const hosts = new Set();
        hostRiskRows.forEach(row => {
            const hostValue = row.getAttribute('data-host');
            if (hostValue) {
                hosts.add(hostValue);
            }
        });

        // Clear existing options except "All Hosts"
        const options = hostFilterSelect.querySelectorAll('option');
        options.forEach((opt, idx) => {
            if (idx > 0) opt.remove();
        });

        // Add each host to dropdown
        const sortedHosts = Array.from(hosts).sort();
        sortedHosts.forEach(host => {
            const option = document.createElement('option');
            option.value = host;
            option.textContent = host;
            hostFilterSelect.appendChild(option);
        });
    }

    // Filter rows based on selected host and search term
    function applyFilters() {
        const selectedHost = hostFilterSelect.value;  // "" for "All Hosts" or specific host
        const searchTerm = hostSearchInput.value.toLowerCase().trim();

        let visibleCount = 0;

        hostRiskRows.forEach(row => {
            const rowHost = row.getAttribute('data-host');
            
            // Check host filter
            const hostMatch = selectedHost === '' || rowHost === selectedHost;
            
            // Check search filter
            const searchMatch = searchTerm === '' || rowHost.toLowerCase().includes(searchTerm);

            // Show/hide row based on both filters
            if (hostMatch && searchMatch) {
                row.classList.remove('hidden');
                visibleCount++;
            } else {
                row.classList.add('hidden');
            }
        });

        // Adjust container height based on visible rows
        if (hostRiskContainer) {
            if (selectedHost !== '' || searchTerm !== '') {
                // Filtered mode: allow container to collapse
                hostRiskContainer.style.maxHeight = 'none';
                hostRiskContainer.style.minHeight = 'auto';
            } else {
                // All hosts mode: fixed height
                hostRiskContainer.style.maxHeight = '420px';
                hostRiskContainer.style.minHeight = 'auto';
            }
        }

        console.log('Filtered to', visibleCount, 'visible rows');
    }

    // Event listeners
    hostFilterSelect.addEventListener('change', applyFilters);
    hostSearchInput.addEventListener('input', applyFilters);

    // Initialize: populate dropdown and apply initial filters
    populateHostDropdown();
    applyFilters();

    console.log('Host filter initialized with', hostRiskRows.length, 'rows');
})();
