# Release Notes — v1.0.0

Initial public release focusing on stability and Windows usability.

## Highlights
- Input Mode selector: IP/CIDR vs Hostname flow
- Threaded ping discovery with retries for Windows networks
- Extended nmap probes for improved host detection
- Fast port scan via RustScan, service fingerprints via Nmap
- CPE → CVE mapping with NVD or local DB, defensive severity parsing
- CSV/JSON/PDF exports and GUI logging with color tags

## Known Considerations
- ICMP/ARP behavior varies by environment; Npcap recommended on Windows
- CVE severity may be string or structured dict; both are supported
- Large CIDRs are capped by policy (adaptive/cidr_full) for performance

## Next
- Optional KEV enrichment and CVSS 4.0 E-metric badge in GUI
- Settings toggles for discovery mode and workers
