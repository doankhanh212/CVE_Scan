from modules.pipelines.basic_pipeline import BasicPipeline


def make_scan_data(entries):
    data = {}
    for port, svc, prod, ver in entries:
        data[port] = {"service": svc, "product": prod, "version": ver, "protocol": "tcp"}
    return data


def test_windows_os_mapping_on_well_known_port():
    bp = BasicPipeline(config={"use_local_db": True, "local_db_path": "modules/cve/nvd_cve.db"})
    # msrpc on port 135 should map to windows OS CPE
    scan_data = make_scan_data([(135, "msrpc", "Microsoft Windows RPC", "")])
    norm = bp._normalize_scan_data("127.0.0.1", scan_data)
    v = list(norm["vulnerabilities"].values())[0]
    assert v["cpe"].startswith("cpe:2.3:o:microsoft:windows")


def test_no_windows_mapping_on_random_port():
    bp = BasicPipeline(config={"use_local_db": True, "local_db_path": "modules/cve/nvd_cve.db"})
    # msrpc-like product on a random port should not auto map to OS
    scan_data = make_scan_data([(50000, "msrpc", "Microsoft Windows RPC", "")])
    norm = bp._normalize_scan_data("127.0.0.1", scan_data)
    v = list(norm["vulnerabilities"].values())[0]
    assert not v["cpe"].startswith("cpe:2.3:o:microsoft:windows")


def test_product_explicit_windows_string_maps():
    bp = BasicPipeline(config={"use_local_db": True, "local_db_path": "modules/cve/nvd_cve.db"})
    scan_data = make_scan_data([(50000, "unknown", "Microsoft Windows Server 2019", "10.0")])
    norm = bp._normalize_scan_data("127.0.0.1", scan_data)
    v = list(norm["vulnerabilities"].values())[0]
    assert v["cpe"].startswith("cpe:2.3:o:microsoft:windows")
