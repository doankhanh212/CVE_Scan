// web/static/js/result.js

let pollInterval = null;

async function loadScanStatus() {
    try {
        const response = await fetch(`/scan/${scanId}/status`);
        const status = await response.json();

        if (!response.ok) {
            throw new Error(status.error || 'Không thể tải status');
        }

        const statusContainer = document.getElementById('scan-status');
        statusContainer.innerHTML = `
            <div class="status-badge status-${status.status}">
                ${status.status.toUpperCase()}
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${status.progress}%">
                    ${status.progress}%
                </div>
            </div>
            ${status.message ? `<p>${status.message}</p>` : ''}
            ${status.error ? `<p class="error">Lỗi: ${status.error}</p>` : ''}
        `;

        if (status.status === 'completed') {
            clearInterval(pollInterval);
            loadResults();
        } else if (status.status === 'failed') {
            clearInterval(pollInterval);
        }

    } catch (error) {
        document.getElementById('scan-status').innerHTML =
            `<p class="error">Lỗi: ${error.message}</p>`;
    }
}

async function loadResults() {
    try {
        // 🔥 FIX QUAN TRỌNG Ở ĐÂY
        const response = await fetch(`/api/scan/${scanId}`);
        const scanInfo = await response.json();

        if (!response.ok) {
            throw new Error(scanInfo.error || 'Không thể tải kết quả');
        }

        if (scanInfo.status !== 'completed') {
            document.getElementById('results-container').innerHTML =
                `<p>Scan chưa hoàn tất</p>`;
            return;
        }

        const results = scanInfo.results || {};
        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Host</th>
                        <th>Ports</th>
                        <th>Services</th>
                        <th>CVEs</th>
                    </tr>
                </thead>
                <tbody>
        `;

        for (const [host, hostResult] of Object.entries(results)) {
            const ports = hostResult.gui?.ports || [];
            const totalCves = ports.reduce(
                (sum, p) => sum + (p.cves?.length || 0),
                0
            );

            html += `
                <tr>
                    <td>${host}</td>
                    <td>${ports.length}</td>
                    <td>${ports.map(p => p.service || 'N/A').join(', ')}</td>
                    <td>${totalCves}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        document.getElementById('results-container').innerHTML = html;

    } catch (error) {
        document.getElementById('results-container').innerHTML =
            `<p class="error">Lỗi: ${error.message}</p>`;
    }
}

// EXPORT (giữ nguyên nếu backend có)
document.getElementById('export-csv')?.addEventListener('click', () => {
    window.location.href = `/export/csv?scan_id=${scanId}`;
});

document.getElementById('export-html')?.addEventListener('click', () => {
    window.location.href = `/export/html?scan_id=${scanId}`;
});

document.getElementById('export-pdf')?.addEventListener('click', () => {
    window.location.href = `/export/pdf?scan_id=${scanId}`;
});

document.addEventListener('DOMContentLoaded', () => {
    loadScanStatus();
    pollInterval = setInterval(loadScanStatus, 2000);
});
