from modules.scanners.auth_linux_scanner import AuthLinuxScanner


class Dummy(AuthLinuxScanner):
    def get_installed_packages(self):
        return [("pkg1", "1.0"), ("pkg2", "2.0")]


def test_get_installed_software_alias():
    d = Dummy("127.0.0.1", "user")
    assert hasattr(d, "get_installed_software")
    assert d.get_installed_software() == d.get_installed_packages()
