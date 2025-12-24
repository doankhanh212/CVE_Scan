from modules.cve.cve_matcher import CVEMatcher

class DummyFetcher:
    def get_cve_by_cpe(self, cpe: str, max_results: int = 50):
        # Simulate NVD item with CVSS v4 metrics
        return [{
            "cve": {
                "id": "CVE-2099-0001",
                "descriptions": [{"lang": "en", "value": "Example CVE with CVSS v4"}],
                "metrics": {
                    "cvssMetricV40": [{
                        "cvssData": {
                            "baseScore": 8.8,
                            "vectorString": "CVSS:4.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L"
                        }
                    }]
                },
                "references": [{"url": "https://example.com/advisory"}]
            }
        }]


def test_cvss4_parsing_present():
    m = CVEMatcher()
    # inject dummy fetcher
    m.fetcher = DummyFetcher()
    out = m.match_by_cpe("cpe:2.3:a:vendor:product:1.0:*:*:*:*:*:*:*")
    assert out and out[0]["cvss4"]["score"] == 8.8
    assert out[0]["cvss4"]["vector"].startswith("CVSS:4.0")
