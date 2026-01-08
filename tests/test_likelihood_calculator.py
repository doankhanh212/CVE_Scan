"""
Unit tests for Likelihood Calculator
Tests CVSS extraction, EPSS lookup, and likelihood calculation
"""

import unittest
import tempfile
import sqlite3
import json
from pathlib import Path
from modules.cve.likelihood_calculator import LikelihoodCalculator, calculate_cve_likelihood


class TestLikelihoodCalculator(unittest.TestCase):
    """Test suite for likelihood calculation module"""

    @classmethod
    def setUpClass(cls):
        """Create temporary EPSS database for testing"""
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db_path = cls.temp_db.name
        cls.temp_db.close()

        # Create test EPSS database with sample data
        with sqlite3.connect(cls.temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE epss (
                    cve TEXT PRIMARY KEY,
                    epss REAL,
                    percentile REAL,
                    epss_date TEXT
                )
            ''')
            cursor.execute(
                'INSERT INTO epss VALUES (?, ?, ?, ?)',
                ('CVE-2024-0001', 0.75, 92.5, '2024-01-01')
            )
            cursor.execute(
                'INSERT INTO epss VALUES (?, ?, ?, ?)',
                ('CVE-2024-0002', 0.25, 45.0, '2024-01-01')
            )
            cursor.execute(
                'INSERT INTO epss VALUES (?, ?, ?, ?)',
                ('CVE-2024-0003', 0.05, 15.0, '2024-01-01')
            )
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary database"""
        import time
        time.sleep(0.1)  # Wait for DB connection to close
        try:
            Path(cls.temp_db_path).unlink(missing_ok=True)
        except PermissionError:
            pass  # File may still be locked on Windows

    def setUp(self):
        """Initialize calculator for each test"""
        self.calculator = LikelihoodCalculator(self.temp_db_path)

    # CVSS Extraction Tests
    def test_extract_cvss_v4_priority(self):
        """CVSS v4 should be preferred"""
        cve_data = {
            'cvss_v4': {'baseScore': 8.5},
            'cvss_v3': {'baseScore': 7.5},
            'cvss_v2': {'baseScore': 6.5}
        }
        score = self.calculator.extract_cvss_base(cve_data)
        self.assertEqual(score, 8.5)

    def test_extract_cvss_v3_fallback(self):
        """CVSS v3 should be used if v4 unavailable"""
        cve_data = {
            'cvss_v3_1': {'baseScore': 7.8},
            'cvss_v2': {'baseScore': 6.5}
        }
        score = self.calculator.extract_cvss_base(cve_data)
        self.assertEqual(score, 7.8)

    def test_extract_cvss_v2_fallback(self):
        """CVSS v2 should be used as last resort"""
        cve_data = {'cvss_v2': {'baseScore': 6.0}}
        score = self.calculator.extract_cvss_base(cve_data)
        self.assertEqual(score, 6.0)

    def test_extract_cvss_scalar_value(self):
        """Should handle scalar CVSS values, not just dict"""
        cve_data = {'cvss_v3': 7.5}
        score = self.calculator.extract_cvss_base(cve_data)
        self.assertEqual(score, 7.5)

    def test_extract_cvss_invalid_range(self):
        """Should reject CVSS scores outside 0-10 range"""
        cve_data = {'cvss_v3': 15.0}  # Invalid: > 10
        score = self.calculator.extract_cvss_base(cve_data)
        self.assertIsNone(score)

    def test_extract_cvss_missing(self):
        """Should return None if no CVSS available"""
        cve_data = {'id': 'CVE-2024-0001'}
        score = self.calculator.extract_cvss_base(cve_data)
        self.assertIsNone(score)

    # EPSS Lookup Tests
    def test_get_epss_from_db_found(self):
        """Should retrieve EPSS from database"""
        epss, percentile = self.calculator.get_epss_from_db('CVE-2024-0001')
        self.assertEqual(epss, 0.75)
        self.assertEqual(percentile, 92.5)

    def test_get_epss_from_db_not_found(self):
        """Should return default EPSS if not in database"""
        epss, percentile = self.calculator.get_epss_from_db('CVE-2024-9999')
        self.assertEqual(epss, self.calculator.DEFAULT_EPSS)
        self.assertIsNone(percentile)

    def test_get_epss_invalid_cve_format(self):
        """Should handle invalid CVE format gracefully"""
        epss, percentile = self.calculator.get_epss_from_db('INVALID-CVE')
        self.assertEqual(epss, self.calculator.DEFAULT_EPSS)
        self.assertIsNone(percentile)

    def test_get_epss_empty_string(self):
        """Should handle empty CVE ID"""
        epss, percentile = self.calculator.get_epss_from_db('')
        self.assertEqual(epss, self.calculator.DEFAULT_EPSS)

    # Likelihood Calculation Tests
    def test_calculate_likelihood_high(self):
        """Score >= 7.0 should be HIGH"""
        result = self.calculator.calculate_likelihood(9.0, 0.8)
        self.assertAlmostEqual(result['score'], 7.2, places=5)
        self.assertEqual(result['level'], 'HIGH')

    def test_calculate_likelihood_medium(self):
        """Score >= 4.0 and < 7.0 should be MEDIUM"""
        result = self.calculator.calculate_likelihood(8.0, 0.5)
        self.assertAlmostEqual(result['score'], 4.0, places=5)
        self.assertEqual(result['level'], 'MEDIUM')

    def test_calculate_likelihood_low(self):
        """Score < 4.0 should be LOW"""
        result = self.calculator.calculate_likelihood(5.0, 0.7)
        self.assertAlmostEqual(result['score'], 3.5, places=5)
        self.assertEqual(result['level'], 'LOW')

    def test_calculate_likelihood_formula(self):
        """Likelihood should be CVSS × EPSS"""
        result = self.calculator.calculate_likelihood(7.5, 0.6)
        self.assertAlmostEqual(result['score'], 4.5, places=5)

    def test_calculate_likelihood_boundary_high(self):
        """Score = 7.0 exactly should be HIGH"""
        result = self.calculator.calculate_likelihood(7.0, 1.0)
        self.assertEqual(result['level'], 'HIGH')

    def test_calculate_likelihood_boundary_medium(self):
        """Score = 4.0 exactly should be MEDIUM"""
        result = self.calculator.calculate_likelihood(4.0, 1.0)
        self.assertEqual(result['level'], 'MEDIUM')

    def test_calculate_likelihood_boundary_low(self):
        """Score = 3.99 should be LOW"""
        result = self.calculator.calculate_likelihood(3.99, 1.0)
        self.assertEqual(result['level'], 'LOW')

    # Enrichment Tests
    def test_enrich_vulnerability_complete(self):
        """Should enrich CVE with likelihood data"""
        cve_data = {
            'id': 'CVE-2024-0001',
            'cvss_v3': {'baseScore': 9.0},
            'description': 'Test vulnerability'
        }
        enriched = self.calculator.enrich_vulnerability_with_likelihood(
            cve_data, 'CVE-2024-0001'
        )

        self.assertIn('likelihood', enriched)
        likelihood = enriched['likelihood']
        self.assertEqual(likelihood['epss'], 0.75)
        self.assertEqual(likelihood['percentile'], 92.5)
        self.assertAlmostEqual(likelihood['score'], 6.75, places=5)  # 9.0 × 0.75
        self.assertEqual(likelihood['level'], 'MEDIUM')  # 6.75 is MEDIUM (>= 4.0, < 7.0)
        self.assertEqual(likelihood['source'], 'FIRST.org')

    def test_enrich_vulnerability_missing_cvss(self):
        """Should handle CVE without CVSS gracefully"""
        cve_data = {
            'id': 'CVE-2024-0001',
            'description': 'Test vulnerability without CVSS'
        }
        enriched = self.calculator.enrich_vulnerability_with_likelihood(
            cve_data, 'CVE-2024-0001'
        )
        self.assertIsNone(enriched['likelihood'])

    def test_enrich_vulnerability_preserves_data(self):
        """Should not modify existing CVE data"""
        cve_data = {
            'id': 'CVE-2024-0001',
            'cvss_v3': {'baseScore': 8.0},
            'description': 'Original description',
            'custom_field': 'custom_value'
        }
        original_cvss = cve_data['cvss_v3']
        original_description = cve_data['description']

        enriched = self.calculator.enrich_vulnerability_with_likelihood(
            cve_data, 'CVE-2024-0001'
        )

        # Original data should be unchanged
        self.assertEqual(enriched['cvss_v3'], original_cvss)
        self.assertEqual(enriched['description'], original_description)
        self.assertEqual(enriched['custom_field'], 'custom_value')

    def test_convenience_function(self):
        """Module-level convenience function should work"""
        cve_data = {
            'id': 'CVE-2024-0002',
            'cvss_v3': {'baseScore': 5.0}
        }
        enriched = calculate_cve_likelihood(
            cve_data, 'CVE-2024-0002', self.temp_db_path
        )

        self.assertIn('likelihood', enriched)
        self.assertEqual(enriched['likelihood']['score'], 1.25)  # 5.0 × 0.25
        self.assertEqual(enriched['likelihood']['level'], 'LOW')


class TestLikelihoodIntegration(unittest.TestCase):
    """Integration tests for realistic scan scenarios"""

    @classmethod
    def setUpClass(cls):
        """Create test database"""
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db_path = cls.temp_db.name
        cls.temp_db.close()

        with sqlite3.connect(cls.temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE epss (
                    cve TEXT PRIMARY KEY,
                    epss REAL,
                    percentile REAL,
                    epss_date TEXT
                )
            ''')
            # Add realistic EPSS data
            test_data = [
                ('CVE-2024-1001', 0.95, 98.5, '2024-01-06'),
                ('CVE-2024-1002', 0.45, 65.0, '2024-01-06'),
                ('CVE-2024-1003', 0.10, 20.0, '2024-01-06'),
            ]
            cursor.executemany(
                'INSERT INTO epss VALUES (?, ?, ?, ?)',
                test_data
            )
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        import time
        time.sleep(0.1)
        try:
            Path(cls.temp_db_path).unlink(missing_ok=True)
        except PermissionError:
            pass

    def test_enrich_scan_results(self):
        """Should enrich realistic scan results"""
        calculator = LikelihoodCalculator(self.temp_db_path)

        scan_results = {
            'host1.example.com': {
                'ports': [
                    {
                        'port': 22,
                        'service': 'ssh',
                        'cves': [
                            {
                                'id': 'CVE-2024-1001',
                                'cvss_v3': {'baseScore': 8.5},
                                'description': 'Critical SSH vuln'
                            }
                        ]
                    }
                ]
            },
            'host2.example.com': {
                'ports': [
                    {
                        'port': 443,
                        'service': 'https',
                        'cves': [
                            {
                                'id': 'CVE-2024-1002',
                                'cvss_v3': {'baseScore': 6.0},
                                'description': 'Medium vuln'
                            },
                            {
                                'id': 'CVE-2024-1003',
                                'cvss_v3': {'baseScore': 4.5},
                                'description': 'Low impact'
                            }
                        ]
                    }
                ]
            }
        }

        enriched = calculator.enrich_scan_results(scan_results)

        # Verify all CVEs have likelihood
        cve1 = enriched['host1.example.com']['ports'][0]['cves'][0]
        self.assertIn('likelihood', cve1)
        self.assertEqual(cve1['likelihood']['level'], 'HIGH')
        self.assertAlmostEqual(cve1['likelihood']['score'], 8.075, places=2)  # 8.5 × 0.95

        cve2 = enriched['host2.example.com']['ports'][0]['cves'][0]
        self.assertEqual(cve2['likelihood']['level'], 'LOW')  # 6.0 × 0.45 = 2.7 (< 4.0)

        cve3 = enriched['host2.example.com']['ports'][0]['cves'][1]
        self.assertEqual(cve3['likelihood']['level'], 'LOW')


if __name__ == '__main__':
    unittest.main()
