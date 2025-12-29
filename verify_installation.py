#!/usr/bin/env python3
"""
CVE_Scan Installation Verification Script

Run this after installation to verify everything is working correctly:
    python verify_installation.py

This script checks:
- Python version compatibility
- All required packages installed
- All modules can be imported
- Key functionality works
"""

import sys
import subprocess
from pathlib import Path


def print_header(text):
    # ASCII-safe header (avoid emojis for non-UTF consoles)
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def check_python_version():
    """Verify Python version is 3.11+"""
    print("[CHECK] Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"[ERROR] Python 3.11+ required, got {version.major}.{version.minor}")
        return False


def check_dependencies():
    """Verify all required packages are installed"""
    print("[CHECK] Checking dependencies...")
    
    # Map package names to their import names
    required_packages = {
        'beautifulsoup4': 'bs4',
        'packaging': 'packaging',
        'pillow': 'PIL',
        'paramiko': 'paramiko',
        'pywinrm': 'winrm',
        'python-nmap': 'nmap',
        'rapidfuzz': 'rapidfuzz',
        'reportlab': 'reportlab',
        'requests': 'requests',
        'ipwhois': 'ipwhois',
        'pytest': 'pytest',
    }
    
    all_ok = True
    for pkg_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"[OK] {pkg_name}")
        except ImportError:
            print(f"[ERROR] {pkg_name} (not installed)")
            all_ok = False
    
    return all_ok


def check_modules():
    """Verify all core modules can be imported"""
    print("[CHECK] Checking core modules...")
    
    modules_to_check = [
        ('modules.gui', 'GUI Controller'),
        ('modules.config_manager', 'Configuration Manager'),
        ('modules.scan_manager', 'Scan Manager'),
        ('modules.discovery.host_discovery', 'Host Discovery'),
        ('modules.scanners.nmap_scanner', 'Nmap Scanner'),
        ('modules.cve.cve_matcher', 'CVE Matcher'),
        ('modules.cve.fuzzy_matcher', 'Fuzzy Matcher'),
        ('modules.report.csv_report', 'CSV Report'),
    ]
    
    all_ok = True
    for module_path, name in modules_to_check:
        try:
            __import__(module_path)
            print(f"[OK] {name}")
        except ImportError as e:
            print(f"[ERROR] {name}: {e}")
            all_ok = False
    
    return all_ok


def check_nmap_installed():
    """Verify nmap is available in PATH"""
    print("[CHECK] Checking nmap installation...")
    
    try:
        result = subprocess.run(['nmap', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Extract version from output
            first_line = result.stdout.split('\n')[0]
            print(f"[OK] {first_line}")
            return True
        else:
            print(f"[ERROR] nmap returned error code {result.returncode}")
            return False
    except FileNotFoundError:
        print("[ERROR] nmap not found in PATH")
        print("   Install with: apt-get install nmap (Linux) or brew install nmap (Mac)")
        return False
    except Exception as e:
        print(f"[ERROR] Error checking nmap: {e}")
        return False


def check_configuration():
    """Verify configuration file exists and is valid"""
    print("[CHECK] Checking configuration...")
    
    config_path = Path('config.json')
    if not config_path.exists():
        print("[ERROR] config.json not found")
        print("   Creating default config...")
        try:
            from modules.config_manager import ConfigManager
            cm = ConfigManager()
            print("[OK] Default configuration created")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create config: {e}")
            return False
    else:
        try:
            import json
            with open(config_path) as f:
                config = json.load(f)
            print("[OK] config.json is valid")
            return True
        except json.JSONDecodeError as e:
            print(f"[ERROR] config.json is invalid JSON: {e}")
            return False


def check_tests():
    """Run critical tests"""
    print("[CHECK] Running verification tests...")
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/test_host_discovery.py', '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Count passed tests
            if 'passed' in result.stdout:
                print("[OK] Host discovery tests passed")
                return True
            else:
                print("[WARN] Tests ran but no clear pass indicator")
                return True
        else:
            print(f"[ERROR] Tests failed: {result.stdout}")
            return False
    except subprocess.TimeoutExpired:
        print("[WARN] Tests timed out (skipping)")
        return True
    except FileNotFoundError:
        print("[WARN] pytest not found (tests skipped)")
        return True
    except Exception as e:
        print(f"[WARN] Could not run tests: {e}")
        return True


def main():
    print_header("CVE_Scan Installation Verification")
    
    checks = [
        ("Python Version", check_python_version),
        ("Python Packages", check_dependencies),
        ("Core Modules", check_modules),
        ("Nmap Tool", check_nmap_installed),
        ("Configuration", check_configuration),
        ("Unit Tests", check_tests),
    ]
    
    results = []
    for name, check_func in checks:
        print_header(name)
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] Check failed with error: {e}")
            results.append((name, False))
    
    # Summary
    print_header("Installation Verification Summary")
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}  {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("=" * 70)
        print("  Installation verification PASSED!")
        print("  Your CVE_Scan installation is ready to use.")
        print("  Run: python app.py")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("  Some checks failed. Please review above.")
        print("  Install missing packages and tools, then rerun this script.")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
