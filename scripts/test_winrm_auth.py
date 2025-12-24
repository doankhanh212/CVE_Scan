import argparse
import getpass
import sys

try:
    import winrm
except Exception:
    winrm = None


REGISTRY_SCRIPT = r"""
$keys = @(
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$out = @()
foreach ($k in $keys) {
  Get-ItemProperty $k -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.DisplayName) {
      $out += "{0}|||{1}" -f $_.DisplayName, ($_.DisplayVersion -replace '\r|\n','')
    }
  }
}
$out -join "`n"
"""


def build_session(host: str, username: str, password: str, transport: str, port: int, use_ssl: bool, timeout: int):
    scheme = "https" if use_ssl else "http"
    endpoint = f"{scheme}://{host}:{port}/wsman"

    # WinRM requires read_timeout_sec > operation_timeout_sec
    operation_timeout = max(int(timeout), 30)
    read_timeout = operation_timeout + 10

    print(f"[INFO] Endpoint: {endpoint}")
    print(f"[INFO] Transport: {transport}")
    print(f"[INFO] Timeouts: operation={operation_timeout}s, read={read_timeout}s")

    session = winrm.Session(
        endpoint,
        auth=(username, password),
        transport=transport,
        server_cert_validation='ignore',
        read_timeout_sec=read_timeout,
        operation_timeout_sec=operation_timeout,
    )
    return session


def decode_bytes(val):
    if isinstance(val, (bytes, bytearray)):
        try:
            return val.decode(errors="ignore")
        except Exception:
            return str(val)
    return str(val)


def run_ps(session, script: str, label: str):
    print(f"[INFO] Running PowerShell: {label}")
    r = session.run_ps(script)
    status = getattr(r, "status_code", None)
    stdout = decode_bytes(getattr(r, "std_out", b""))
    stderr = decode_bytes(getattr(r, "std_err", b""))
    print(f"[INFO] Exit code: {status}")
    if stderr:
        print(f"[WARN] stderr: {stderr}")
    print(f"[INFO] stdout length: {len(stdout)} bytes")
    if stdout:
        print(f"[INFO] stdout preview:\n{stdout[:500]}")
    return status, stdout, stderr


def main():
    parser = argparse.ArgumentParser(description="Quick WinRM auth and software enumeration test")
    parser.add_argument("host", help="Target host (IP or hostname)")
    parser.add_argument("username", help="Username (try khanh, .\\khanh, or COMPUTERNAME\\khanh)")
    parser.add_argument("transport", nargs="?", default="ntlm", choices=["ntlm", "basic", "kerberos"], help="Auth transport")
    parser.add_argument("port", nargs="?", type=int, default=5985, help="WinRM port (5985 HTTP / 5986 HTTPS)")
    parser.add_argument("timeout", nargs="?", type=int, default=30, help="Operation timeout seconds (read timeout = +10)")
    parser.add_argument("use_ssl", nargs="?", type=int, default=0, help="1 to use HTTPS, 0 for HTTP")
    args = parser.parse_args()

    if winrm is None:
        print("[ERROR] pywinrm not installed. Install with: pip install pywinrm")
        sys.exit(2)

    password = getpass.getpass("Password: ")

    # Try combinations of username/transport until success
    base_user = args.username
    user_candidates = [base_user]
    if "\\" not in base_user and not base_user.lower().startswith(".\\"):
        user_candidates.append(f".\\{base_user}")
        user_candidates.append(f"{args.host}\\{base_user}")

    transport_candidates = [args.transport]
    if args.transport != "basic":
        transport_candidates.append("basic")

    session = None
    success = False
    last_error = None
    for u in user_candidates:
        for t in transport_candidates:
            print(f"[INFO] Attempting username='{u}' transport='{t}'")
            try:
                session = build_session(
                    host=args.host,
                    username=u,
                    password=password,
                    transport=t,
                    port=args.port,
                    use_ssl=bool(args.use_ssl),
                    timeout=args.timeout,
                )
            except Exception as e:
                last_error = e
                print(f"[ERROR] Failed to create WinRM session: {e}")
                session = None
                continue

            try:
                status, stdout, stderr = run_ps(session, "hostname", "hostname")
                if status == 0:
                    print(f"[SUCCESS] Connected with username='{u}' transport='{t}'")
                    success = True
                    break
                else:
                    print("[WARN] Hostname failed; trying next combination...")
            except Exception as e:
                last_error = e
                print(f"[ERROR] Exception running hostname: {e}")
                session = None
                continue
        if success:
            break

    if not success or not session:
        print("[ERROR] All combinations failed.")
        if last_error:
            print(f"[ERROR] Last error: {last_error}")
        print("Hint: verify user added to 'Remote Management Users' or 'Administrators', and try COMPUTERNAME\\user format.")
        sys.exit(5)

    # Try registry software enumeration
    status2, stdout2, stderr2 = run_ps(session, REGISTRY_SCRIPT, "registry uninstall keys")
    if status2 == 0 and stdout2:
        lines = stdout2.splitlines()
        parsed = []
        for idx, line in enumerate(lines):
            if "|||" in line:
                name, ver = line.split("|||", 1)
                name = name.strip()
                ver = ver.strip() or "unknown"
                if name:
                    parsed.append((name, ver))
        print(f"[SUCCESS] Parsed {len(parsed)} software entries from registry")
        print(f"[INFO] Sample: {parsed[:5]}")
    else:
        print("[WARN] Registry output empty or failed; you can try WMI fallback (slow)")

    print("[DONE] WinRM test completed")


if __name__ == "__main__":
    main()
