import nmap  # Thư viện điều khiển Nmap từ Python (python-nmap)
import socket

class Scanner:
    def __init__(self, ports='1-1024', nmap_path=None):
        """
        Khởi tạo đối tượng Scanner để thực hiện quét port.

        Tham số:
            ports (str): Chuỗi định nghĩa khoảng port, ví dụ '1-1024'.
            nmap_path (str): Đường dẫn tới file nmap nếu không nằm trong PATH.
        """
        # Lưu lại chuỗi ports cho lần quét
        self.ports = ports
        # Kiểm tra Nmap đã cài chưa
        try:
            self.nm = nmap.PortScanner()
        except nmap.PortScannerError:
            print("[ERROR] Nmap is not installed or not in PATH.")
            raise
        # Nếu người dùng cung cấp đường dẫn nmap, gán vào thuộc tính
        if nmap_path:
            self.nm.nmap_path = nmap_path

    def is_valid_host(self, host):
        # Kiểm tra IP hoặc hostname hợp lệ
        try:
            socket.inet_aton(host)
            if host.count('.') == 3 and all(0 <= int(part) <= 255 for part in host.split('.')):
                return True
        except Exception:
            pass
        # Kiểm tra hostname hợp lệ (RFC 1035)
        if len(host) > 253:
            return False
        import re
        hostname_regex = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
        parts = host.split('.')
        return all(re.match(hostname_regex, part) for part in parts)

    def scan_host(self, host):
        """
        Thực hiện quét service/version trên host.

        Tham số:
            host (str): Địa chỉ IP hoặc hostname cần quét.
        Trả về:
            dict: { port: {'service': tên_service, 'version': phiên_bản} }
        """
        # Kiểm tra hợp lệ host đầu vào
        if not self.is_valid_host(host):
            print(f"[ERROR] Invalid host: {host}")
            return {}

        # Khởi tạo kết quả rỗng
        result = {}

        # Bước 1: Thử scan với -sV (service/version detection)
        try:
            scan_data = self.nm.scan(
                hosts=host,
                ports=self.ports,
                arguments='-sV'
            )
            # In debug raw data để kiểm tra
            print(f"[DEBUG] raw scan_data for {host}: {scan_data}")
        except Exception as e:
            # Nếu có lỗi Nmap, in thông báo và trả về kết quả trống
            print(f"[ERROR] Nmap scan error for {host}: {e}")
            return result

        # Bước 2: Trích phần 'scan' chứa dữ liệu quét
        scan_hosts = scan_data.get('scan', {})
        # Nếu không có kết quả, trả về rỗng
        if not scan_hosts:
            return result

        # Bước 3: Lấy host đầu tiên (chỉ scan một host)
        first_ip = next(iter(scan_hosts))
        host_data = scan_hosts[first_ip]
        # Bước 4: Lấy thông tin TCP
        tcp_info = host_data.get('tcp', {})

        # Bước 5: Nếu không lấy được TCP info, thử lại với -sT (TCP connect scan)
        if not tcp_info:
            print(f"[DEBUG] No tcp_info, retrying basic scan for {host}")
            try:
                scan_data = self.nm.scan(
                    hosts=host,
                    ports=self.ports,
                    arguments='-sT'
                )
                scan_hosts = scan_data.get('scan', {})
                if not scan_hosts:
                    return result
                first_ip = next(iter(scan_hosts))
                host_data = scan_hosts[first_ip]
                tcp_info = host_data.get('tcp', {})
                print(f"[DEBUG] retry raw scan_data for {host}: {scan_data}")
            except Exception as e:
                print(f"[ERROR] Retry scan error for {host}: {e}")
                return result

        # Bước 6: Duyệt ports đã quét
        # Chuyển dict thành list để dùng while
        port_items = list(tcp_info.items())  # [(port, info_dict), ...]
        idx = 0
        while idx < len(port_items):
            port, info = port_items[idx]
            # Lấy tên service (ví dụ 'ssh')
            service_name = info.get('name')
            # Lấy version (nếu có)
            version = info.get('version', '')
            # Lấy trạng thái port (open/closed)
            state = info.get('state', '')
            # Đưa vào kết quả
            result[port] = {
                'service': service_name,
                'version': version,
                'state': state
            }
            idx += 1

        # Bước 7: In log debug các port đã tìm
        print(f"[DEBUG] scan_host({host}) returned ports: {list(result.keys())}")
        # Trả về kết quả cuối cùng
        return result

if __name__ == "__main__":
    scanner = Scanner()
    print(scanner.scan_host("127.0.0.1"))
