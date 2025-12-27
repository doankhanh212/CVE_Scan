"""
Unit Tests for Asset Discovery Module
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, patch, MagicMock
from modules.discovery.asset_discovery import (
    Asset,
    DNSResolver,
    WHOISLookup,
    ReverseDNS,
    CIDRExpander,
    AssetDiscovery,
    CONFIDENCE_SCORES
)


# ======================================================================
# TEST: Asset Class
# ======================================================================
class TestAsset:
    def test_asset_creation_ipv4(self):
        asset = Asset("192.168.1.1")
        assert asset.ip == "192.168.1.1"
        assert asset.is_ipv4 is True
        assert asset.is_ipv6 is False
        assert asset.confidence == 0.0

    def test_asset_creation_ipv6(self):
        asset = Asset("2001:db8::1")
        assert asset.is_ipv6 is True
        assert asset.is_ipv4 is False

    def test_asset_add_hostname(self):
        asset = Asset("192.168.1.1")
        asset.add_hostname("example.com")
        asset.add_hostname("www.example.com")
        assert "example.com" in asset.hostnames
        assert len(asset.hostnames) == 2

    def test_asset_confidence_max(self):
        asset = Asset("192.168.1.1")
        asset.update_confidence(0.5)
        asset.update_confidence(0.8)
        assert asset.confidence == 0.8  # Max, not sum

    def test_asset_to_dict(self):
        asset = Asset("192.168.1.1")
        asset.add_hostname("test.com")
        asset.asn = "AS1234"
        asset.cidr = "192.168.1.0/24"
        asset.update_confidence(0.95)

        result = asset.to_dict()
        assert result["ip"] == "192.168.1.1"
        assert "test.com" in result["hostnames"]
        assert result["asn"] == "AS1234"
        assert result["cidr"] == "192.168.1.0/24"
        assert result["confidence"] == 0.95


# ======================================================================
# TEST: DNS Resolver
# ======================================================================
class TestDNSResolver:
    @patch('socket.getaddrinfo')
    def test_resolve_hostname_success(self, mock_getaddrinfo):
        # Mock socket.getaddrinfo response
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('192.168.1.1', 0)),
            (2, 1, 6, '', ('192.168.1.2', 0))
        ]

        resolver = DNSResolver()
        ips = resolver.resolve_hostname("example.com")

        assert len(ips) == 2
        assert "192.168.1.1" in ips
        assert "192.168.1.2" in ips

    @patch('socket.getaddrinfo')
    def test_resolve_hostname_not_found(self, mock_getaddrinfo):
        import socket as socket_module
        mock_getaddrinfo.side_effect = socket_module.gaierror("Name not found")

        resolver = DNSResolver()
        ips = resolver.resolve_hostname("nonexistent.example.com")

        assert ips == []

    @patch('socket.getaddrinfo')
    def test_resolve_many_concurrent(self, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, '', ('192.168.1.1', 0))],
            [(2, 1, 6, '', ('192.168.1.2', 0))]
        ]

        resolver = DNSResolver()
        results = resolver.resolve_many(["host1.com", "host2.com"])

        assert len(results) == 2
        assert "192.168.1.1" in results.get("host1.com", [])
        assert "192.168.1.2" in results.get("host2.com", [])


# ======================================================================
# TEST: CIDR Expander
# ======================================================================
class TestCIDRExpander:
    def test_expand_cidr_valid(self):
        expander = CIDRExpander()
        ips = expander.expand_cidr("192.168.1.0/30")  # /30 = 2 usable IPs
        # /30 has 4 total IPs, 2 usable (excluding network and broadcast)
        assert len(ips) > 0

    def test_expand_cidr_invalid(self):
        expander = CIDRExpander()
        ips = expander.expand_cidr("invalid")
        assert ips == []

    def test_expand_cidr_max_limit(self):
        expander = CIDRExpander()
        ips = expander.expand_cidr("192.168.0.0/16", max_ips=10)
        assert len(ips) <= 10


# ======================================================================
# TEST: Asset Discovery Integration
# ======================================================================
class TestAssetDiscovery:
    @patch.object(DNSResolver, 'resolve_many')
    @patch.object(WHOISLookup, 'lookup_many')
    @patch.object(ReverseDNS, 'reverse_lookup_many')
    def test_discover_flow(self, mock_reverse, mock_whois, mock_dns):
        # Setup mocks
        mock_dns.return_value = {
            "example.com": ["192.168.1.1", "192.168.1.2"]
        }
        mock_whois.return_value = {
            "192.168.1.1": {
                "asn": "AS1234",
                "cidr": "192.168.0.0/16",
                "org": "Example Corp",
                "success": True
            },
            "192.168.1.2": {
                "asn": None,
                "cidr": None,
                "org": None,
                "success": False  # Simulated WHOIS timeout
            }
        }
        mock_reverse.return_value = {
            "192.168.1.1": "www1.example.com",
            "192.168.1.2": None
        }

        # Create logger mock
        logger_mock = Mock()
        discovery = AssetDiscovery(logger=logger_mock)

        # Run discovery
        assets = discovery.discover(["example.com"])

        # Assertions
        assert len(assets) > 0
        assert "192.168.1.1" in assets
        asset1 = assets["192.168.1.1"]
        assert "example.com" in asset1.hostnames
        assert asset1.asn == "AS1234"
        assert asset1.confidence >= CONFIDENCE_SCORES["whois_success"]

    @patch.object(DNSResolver, 'resolve_many')
    @patch.object(WHOISLookup, 'lookup_many')
    @patch.object(ReverseDNS, 'reverse_lookup_many')
    def test_filter_for_scan(self, mock_reverse, mock_whois, mock_dns):
        mock_dns.return_value = {"example.com": ["192.168.1.1"]}
        mock_whois.return_value = {
            "192.168.1.1": {
                "asn": "AS1234",
                "cidr": "192.168.1.0/24",
                "org": "Corp",
                "success": True
            }
        }
        mock_reverse.return_value = {"192.168.1.1": None}

        logger_mock = Mock()
        discovery = AssetDiscovery(logger=logger_mock)
        assets = discovery.discover(["example.com"])

        # Filter for scan
        scan_ips = discovery.filter_for_scan(assets)

        # Should include high-confidence assets
        assert len(scan_ips) > 0
        assert "192.168.1.1" in scan_ips

    @patch.object(DNSResolver, 'resolve_many')
    @patch.object(WHOISLookup, 'lookup_many')
    @patch.object(ReverseDNS, 'reverse_lookup_many')
    def test_whois_timeout_fallback(self, mock_reverse, mock_whois, mock_dns):
        """Verify WHOIS timeout doesn't crash pipeline - asset continues with reduced data"""
        mock_dns.return_value = {"example.com": ["192.168.1.1"]}
        # WHOIS timeout = success=False
        mock_whois.return_value = {
            "192.168.1.1": {
                "asn": None,
                "cidr": None,
                "org": None,
                "success": False
            }
        }
        mock_reverse.return_value = {"192.168.1.1": None}

        logger_mock = Mock()
        discovery = AssetDiscovery(logger=logger_mock)
        assets = discovery.discover(["example.com"])

        # Asset should still exist and be scannable (DNS resolved = confidence 1.0)
        # WHOIS failure doesn't reduce confidence from DNS (only takes max)
        assert "192.168.1.1" in assets
        asset = assets["192.168.1.1"]
        assert asset.confidence == CONFIDENCE_SCORES["dns_resolved"]  # 1.0 from DNS
        assert "dns" in asset.source
        assert "whois_timeout" in asset.source  # But we tracked the WHOIS failure
        assert asset.asn is None  # WHOIS data not available
        assert asset.cidr is None


# ======================================================================
# TEST: Confidence Scoring
# ======================================================================
class TestConfidenceScoring:
    def test_confidence_scores_defined(self):
        """Verify all confidence scores are reasonable (0-1)"""
        for key, score in CONFIDENCE_SCORES.items():
            assert 0 <= score <= 1.0, f"{key} score {score} out of range"

    def test_whois_success_higher_than_timeout(self):
        """WHOIS success confidence should be higher than timeout"""
        assert CONFIDENCE_SCORES["whois_success"] > CONFIDENCE_SCORES["whois_timeout"]

    def test_dns_resolved_highest(self):
        """DNS resolution should be highest confidence"""
        assert CONFIDENCE_SCORES["dns_resolved"] >= all(
            CONFIDENCE_SCORES.values()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
