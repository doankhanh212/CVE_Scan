# modules/scanner.py
# Scanner sử dụng python-nmap (nmap wrapper) để thực hiện quét port và phát hiện service/version
# Yêu cầu: Nmap phải được cài trên hệ thống và python-nmap (gói `nmap`) phải được cài trong môi trường Python.

import nmap  # Thư viện điều khiển Nmap từ Python (python-nmap cung cấp PortScanner)
import socket  # Dùng để kiểm tra địa chỉ IP hợp lệ


class Scanner:
    """
    Lớp Scanner: gói chức năng để quét một host, thu thập thông tin port/service/version.

    Thiết kế:
    - Dùng python-nmap (nmap.PortScanner) để gọi Nmap.
    - Trả về dict dạng { port: {'service': tên_service, 'version': phiên_bản, 'state': trạng_thái} }
    - Các vòng lặp được viết bằng while theo yêu cầu tránh for lồng nhau.
    """

    def __init__(self, ports='1-1024', nmap_path=None):
        """
        Khởi tạo Scanner.

        Tham số:
            ports (str): chuỗi định nghĩa port để quét (ví dụ '1-1024' hoặc '22,80,443')
            nmap_path (str|None): nếu Nmap không nằm trong PATH, truyền đường dẫn tới binary nmap
        """
        # Lưu lại dải port cần quét để dùng trong các lần gọi scan
        self.ports = ports

        # Khởi tạo PortScanner - python-nmap sẽ gọi binary nmap phía dưới
        try:
            self.nm = nmap.PortScanner()
        except nmap.PortScannerError:
            # Nếu không cài Nmap hoặc python-nmap không tìm thấy binary, PortScanner() sẽ ném lỗi
            print("[ERROR] Nmap is not installed or not in PATH.")
            raise

        # Nếu người dùng chỉ định đường dẫn nmap cụ thể, gán vào thuộc tính của PortScanner
        # Lưu ý: một số phiên bản python-nmap hỗ trợ set path qua self.nm.nmap_path
        if nmap_path:
            # Thiết lập đường dẫn tới nmap binary (nếu cần)
            self.nm.nmap_path = nmap_path

    def is_valid_host(self, host):
        """
        Kiểm tra host có phải địa chỉ IPv4 hợp lệ hoặc hostname hợp lệ theo RFC-ish.

        Trả về True nếu hợp lệ, False nếu không.
        """
        # 1) Thử parse như IPv4: socket.inet_aton sẽ ném exception nếu không phải dạng IPv4
        try:
            # inet_aton chấp nhận một số chuỗi nhưng không kiểm tra giới hạn 0-255 kỹ,
            # vì vậy ta thêm kiểm tra phần tử sau khi split
            socket.inet_aton(host)
            if host.count('.') == 3 and all(0 <= int(part) <= 255 for part in host.split('.')):
                return True
        except Exception:
            # Nếu không phải IPv4, tiếp tục kiểm tra như hostname
            pass

        # 2) Kiểm tra hostname: đảm bảo tổng độ dài <= 253 ký tự
        if len(host) > 253:
            return False

        # Regex đơn giản cho từng label của hostname (1-63 ký tự, không bắt đầu/ket thúc bằng '-')
        import re
        hostname_regex = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
        parts = host.split('.')
        # Mỗi phần phải match hostname_regex
        return all(re.match(hostname_regex, part) for part in parts)

    def scan_host(self, host):
        """
        Thực hiện quét service/version trên host.

        Tham số:
            host (str): địa chỉ IP hoặc hostname
        Trả về:
            dict: mapping port -> { 'service': str, 'version': str, 'state': str }

        Quy trình:
        - Validate host
        - Dùng nmap -sV để phát hiện service/version
        - Nếu không có kết quả TCP, thử lại bằng -sT (TCP connect)
        - Trích xuất thông tin và trả về
        """
        # Kiểm tra hợp lệ host trước khi quét
        if not self.is_valid_host(host):
            print(f"[ERROR] Invalid host: {host}")
            return {}

        # Kết quả cuối cùng (port -> info)
        result = {}

        # Bước 1: Thực thi lệnh nmap -sV để dò service/version
        try:
            scan_data = self.nm.scan(
                hosts=host,
                ports=self.ports,
                arguments='-sV'  # -sV: service/version detection
            )
            # In debug raw data để hỗ trợ phát triển (có thể thay bằng logging.debug)
            print(f"[DEBUG] raw scan_data for {host}: {scan_data}")
        except Exception as e:
            # Bắt lỗi khi gọi nmap (binary lỗi, quyền, v.v.)
            print(f"[ERROR] Nmap scan error for {host}: {e}")
            return result

        # Bước 2: Trích phần 'scan' (nơi python-nmap lưu dữ liệu của host)
        scan_hosts = scan_data.get('scan', {})
        # Nếu không có key 'scan' hoặc rỗng -> không có kết quả
        if not scan_hosts:
            return result

        # Bước 3: Lấy host đầu tiên trong kết quả (chúng ta chỉ scan 1 host tại một lần gọi)
        first_ip = next(iter(scan_hosts))
        host_data = scan_hosts[first_ip]

        # Bước 4: Lấy thông tin TCP nếu có
        tcp_info = host_data.get('tcp', {})

        # Bước 5: Nếu không có TCP info (ví dụ do scan mode cần quyền), thử lại với -sT
        if not tcp_info:
            print(f"[DEBUG] No tcp_info, retrying basic scan for {host}")
            try:
                # Thử lại bằng -sT (TCP connect scan) như phương án dự phòng
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
                # Nếu retry cũng lỗi, trả về rỗng
                print(f"[ERROR] Retry scan error for {host}: {e}")
                return result

        # Bước 6: Duyệt các port trong tcp_info
        # Chuyển dict thành list các tuple để duyệt bằng while
        port_items = list(tcp_info.items())  # [(port, info_dict), ...]
        idx = 0
        while idx < len(port_items):
            port, info = port_items[idx]

            # Lấy tên service; trường 'name' do python-nmap cung cấp (nmap service name)
            service_name = info.get('name')

            # Lấy version (nếu có); một số trường version có thể rỗng
            version = info.get('version', '')

            # Lấy trạng thái port (ví dụ: 'open', 'closed', 'filtered')
            state = info.get('state', '')

            # Lưu vào result theo cấu trúc mong muốn
            result[port] = {
                'service': service_name,
                'version': version,
                'state': state
            }
            idx += 1

        # Bước 7: Log debug danh sách port đã thu được
        print(f"[DEBUG] scan_host({host}) returned ports: {list(result.keys())}")

        # Trả về kết quả (có thể rỗng nếu không tìm thấy port mở)
        return result
