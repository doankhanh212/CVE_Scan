from modules.gui import GUIController


def test_process_host_result_updates_state():
    g = GUIController()

    # prepare a host result
    host = "10.0.0.5"
    result = {"gui": {"ports": [{"port": 22, "protocol": "tcp", "service": "ssh", "product": "OpenSSH", "version": "8.0", "cves": [{"id":"CVE-2025-0002","severity":"HIGH"}]}]}}

    # call process_host_result synchronously
    g.process_host_result(host, result, sync=True)

    assert host in g.last_results
    # verify KPI updated
    from modules.gui import results_to_rows
    rows, kpi, sev = results_to_rows(g.last_results)
    assert kpi["hosts"] == 1
    assert kpi["open_services"] == 1
    assert sev["HIGH"] == 1
