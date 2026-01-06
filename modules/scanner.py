# modules/scanner.py
"""
Scanner wrapper (fixed imports + safer handling).
- Fallback imports for local vs package layout
"""

import socket
import ipaddress
import csv

# Try to import python-nmap if available
try:
    import nmap
except Exception:
    nmap = None

# try relative/module imports for cpe_builder / nvd fetcher compatibility
try:
    from modules.cpe_builder import build_cpe
except Exception:
    try:
        from cpe_builder import build_cpe
    except Exception:
        build_cpe = None

try:
    from modules.nvd_fetcher import get_cve_by_cpe
except Exception:
    try:
        from nvd_fetcher import get_cve_by_cpe
    except Exception:
        get_cve_by_cpe = None


class Scanner:

    def __init__(self, ports="1-1024", nmap_path=None):
        self.ports = ports

        if nmap is None:
            # not fatal — scanner methods will return empty results, GUI can fallback
            self.nm = None
        else:
            try:
                self.nm = nmap.PortScanner()
            except nmap.PortScannerError:
                print("[ERROR] Nmap is not installed or not accessible!")
                self.nm = None

        if nmap_path and self.nm:
            try:
                self.nm.nmap_path = nmap_path
            except Exception:
                pass

    def is_valid_host(self, host):
        try:
            socket.inet_aton(host)
            if host.count('.') == 3 and all(0 <= int(p) <= 255 for p in host.split(".")):
                return True
        except Exception:
            pass
        return False

    def extract_os(self, host_data):
        osmatches = host_data.get("osmatch", []) or []
        if not osmatches:
            return "Unknown"

        name = osmatches[0].get("name", "").lower()

        if "windows" in name:
            return "Windows"
        if "linux" in name:
            return "Linux"

        return "Unknown"

    def scan_host(self, host):
        """
        Returns dict of ports -> info
        If nmap not installed returns {} quietly.
        """
        if not self.is_valid_host(host):
            return {}

        if not self.nm:
            # nmap unavailable
            return {}

        try:
            scan_data = self.nm.scan(
                hosts=host,
                ports=self.ports,
                arguments='-T4 -sS -sV'
            )
        except Exception:
            return {}

        scan_hosts = scan_data.get("scan", {}) or {}
        if not scan_hosts:
            return {}

        first_ip = next(iter(scan_hosts))
        host_data = scan_hosts[first_ip] or {}

        # Extract OS
        os_detected = self.extract_os(host_data)

        # Extract port info
        ports_result = {}
        tcp_info = host_data.get("tcp", {}) or {}
        for port, info in tcp_info.items():
            try:
                pnum = int(port)
            except Exception:
                pnum = port
            ports_result[pnum] = {
                "service": info.get("name", ""),
                "version": info.get("version", ""),
                "product": info.get("product", ""),
                "state": info.get("state", ""),
                "os": os_detected,
                "scripts": {}
            }

        # Extract hostscript outputs
        script_output = {}
        if "hostscript" in host_data:
            for item in host_data.get("hostscript", []):
                script_output[item.get("id")] = item.get("output", "")

        # Extract per-port scripts (if present)
        if "ports" in host_data:
            for p in host_data.get("ports", []):
                if isinstance(p, dict) and "script" in p:
                    for sid, out in p.get("script", {}).items():
                        script_output[sid] = out

        for port in list(ports_result.keys()):
            ports_result[port]["scripts"] = script_output

        return ports_result
    

    
    def basic_scan_with_cve(self, host):
        """
        BASIC SCAN:
        nmap → port/service/version → CPE → CVE
        """
    
        # 1️⃣ BẮT BUỘC: gọi nmap
        ports = self.scan_host(host)
        if not ports:
            return {}
    
        results = {}
    
        for port, info in ports.items():
            service = info.get("service")
            version = info.get("version")
    
            results[port] = {
                "service": service,
                "version": version,
                "cves": []
            }
    
            # 2️⃣ Không có service/version thì bỏ qua CVE
            if not service or not version:
                continue
            
            # 3️⃣ Build CPE
            if build_cpe is None:
                continue
            
            cpe = build_cpe(service, version)
            if not cpe or cpe == "N/A":
                continue
            
            # 4️⃣ Query CVE
            if get_cve_by_cpe:
                try:
                    cves = get_cve_by_cpe(cpe)
                    if cves:
                        results[port]["cves"] = cves
                except Exception:
                    pass
                
        return results

    


    def scan_range(self, network_cidr):
        result = {}
        try:
            net = ipaddress.ip_network(network_cidr, strict=False)
        except Exception:
            return result

        ip_list = list(net.hosts())
        for ip in ip_list:
            ip_str = str(ip)
            host_result = self.scan_host(ip_str)
            if host_result:
                result[ip_str] = host_result

        return result


# ==============================
# FULL PIPELINE (CPE → CVE → CSV)
# ==============================
def full_scan_pipeline(ip, software_list, output_csv="scan_report.csv"):
    """
    Luồng đầy đủ:
        1. Software → CPE
        2. CPE → CVE
        3. Xuất CSV
    """
    results = []
    all_records = []

    print(f"[+] Bắt đầu quét thiết bị {ip}")

    for sw in software_list or []:
        name = sw.get("name")
        version = sw.get("version")

        # (1) software → CPE
        if build_cpe is None:
            cpe = "N/A"
        else:
            cpe = build_cpe(name, version)
        if cpe == "N/A":
            print(f"[WARN] Không tạo được CPE cho {name} {version}")
            continue

        print(f"[INFO] CPE cho {name} {version}: {cpe}")

        # (2) lấy CVE theo CPE
        if get_cve_by_cpe is None:
            cve_list = []
        else:
            cve_list = get_cve_by_cpe(cpe)

        if not cve_list:
            print(f"[INFO] Không tìm thấy CVE cho {cpe}")
            continue

        # (3) lưu record
        for cve in cve_list:
            # cve structure might be v2 or older; normalize
            try:
                cve_id = cve.get("cve", {}).get("id") if isinstance(cve, dict) else None
                # fallback if already friendly dict
                if not cve_id:
                    cve_id = cve.get("cve_id") or cve.get("id") or "N/A"
            except Exception:
                cve_id = "N/A"

            # Extract CVSS if present
            cvss_v3 = None
            cvss_v2 = None
            try:
                metrics = cve.get("cve", {}).get("metrics", {}) if isinstance(cve, dict) else {}
                if "cvssMetricV31" in metrics:
                    cvss_v3 = metrics["cvssMetricV31"][0]["cvssData"]["baseScore"]
                elif "cvssMetricV30" in metrics:
                    cvss_v3 = metrics["cvssMetricV30"][0]["cvssData"]["baseScore"]
                if "cvssMetricV2" in metrics:
                    cvss_v2 = metrics["cvssMetricV2"][0]["cvssData"]["baseScore"]
            except Exception:
                pass

            item = {
                "ip": ip,
                "software": name,
                "version": version,
                "cpe": cpe,
                "cve_id": cve_id,
                "cvss_v3": cvss_v3,
                "cvss_v2": cvss_v2,
            }
            all_records.append(item)

    # (4) xuất CSV
    if all_records:
        try:
            with open(output_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
                writer.writeheader()
                for r in all_records:
                    writer.writerow(r)
            print(f"[+] Báo cáo đã lưu tại: {output_csv}")
        except Exception as e:
            print("[ERROR] Cannot write CSV:", e)
    else:
        print("[!] Không có dữ liệu để xuất báo cáo.")

    return all_records

