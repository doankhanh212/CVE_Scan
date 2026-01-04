// web/static/js/vulnerabilities.js

let ALL_VULNS = [];

async function loadVulns() {
    const res = await fetch("/api/vulnerabilities");
    const data = await res.json();

    

    ALL_VULNS = data.vulnerabilities || [];
    renderTable(ALL_VULNS);
    populateHostFilter(ALL_VULNS);
}

/* ===============================
   RENDER TABLE
================================ */
function renderTable(vulns) {
    const tbody = document.getElementById("vuln-table-body");
    tbody.innerHTML = "";

    if (vulns.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6">No vulnerabilities</td></tr>`;
        return;
    }

    vulns.forEach(v => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${v.cve_id}</td>
            <td class="sev ${v.severity?.toLowerCase()}">${v.severity}</td>
            <td>${v.cvss ?? "-"}</td>
            <td>${v.host}</td>
            <td>${v.service ?? "-"}</td>
            <td>${v.summary ?? ""}</td>
        `;
        tbody.appendChild(tr);
    });
}

/* ===============================
   FILTER BY SEVERITY
================================ */
function filterBySeverity() {
    const sev = document.getElementById("severityFilter").value;
    let filtered = ALL_VULNS;

    if (sev !== "ALL") {
        filtered = filtered.filter(v => v.severity === sev);
    }

    renderTable(filtered);
}

/* ===============================
   FILTER BY HOST
================================ */
function populateHostFilter(vulns) {
    const select = document.getElementById("hostFilter");
    if (!select) return;

    const hosts = [...new Set(vulns.map(v => v.host))];

    hosts.forEach(h => {
        const opt = document.createElement("option");
        opt.value = h;
        opt.textContent = h;
        select.appendChild(opt);
    });
}

function filterByHost() {
    const host = document.getElementById("hostFilter").value;
    let filtered = ALL_VULNS;

    if (host !== "ALL") {
        filtered = filtered.filter(v => v.host === host);
    }

    renderTable(filtered);
}

/* ===============================
   INIT
================================ */
document.addEventListener("DOMContentLoaded", loadVulns);
