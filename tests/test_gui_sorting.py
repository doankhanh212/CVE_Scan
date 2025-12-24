from modules.gui import results_to_rows


def test_sort_rows_helper():
    rows = [
        ("192.168.1.10","22/tcp","ssh","OpenSSH","7.4","HIGH",1),
        ("192.168.1.7","53/tcp","dnsmasq","dnsmasq","2.73","MEDIUM",2),
        ("192.168.1.15","80/tcp","http","Apache","2.4.49","NONE",0),
    ]

    # sort by host
    from modules.gui import results_sort_rows
    sorted_by_host = results_sort_rows(rows, "host")
    assert sorted_by_host[0][0] == "192.168.1.10"

    # sort by severity (alphabetical fallback)
    sorted_by_sev = results_sort_rows(rows, "severity")
    assert len(sorted_by_sev) == 3
