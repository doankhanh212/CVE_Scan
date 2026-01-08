"""
Unit tests for EPSS Database Builder
Tests CSV import, validation, and database operations
"""

import unittest
import tempfile
import sqlite3
import csv
from pathlib import Path
from modules.cve.build_epss_db import EPSSDatabase, build_epss_database


class TestEPSSDatabase(unittest.TestCase):
    """Test suite for EPSS database builder"""

    @classmethod
    def setUpClass(cls):
        """Create temporary test CSV file"""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.csv_path = Path(cls.temp_dir.name) / 'test_epss.csv'
        cls.db_path = Path(cls.temp_dir.name) / 'test_epss.db'
        
        # Create test CSV with sample data
        with open(cls.csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['cve', 'epss', 'percentile', 'date'])
            writer.writeheader()
            writer.writerows([
                {'cve': 'CVE-2024-0001', 'epss': '0.95', 'percentile': '98.5', 'date': '2024-01-06'},
                {'cve': 'CVE-2024-0002', 'epss': '0.50', 'percentile': '65.0', 'date': '2024-01-06'},
                {'cve': 'CVE-2024-0003', 'epss': '0.05', 'percentile': '15.0', 'date': '2024-01-06'},
                {'cve': 'CVE-2024-0004', 'epss': '0.75', 'percentile': '90.0', 'date': '2024-01-06'},
            ])

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files"""
        # Ignore cleanup errors on Windows due to sqlite locking
        try:
            cls.temp_dir.cleanup()
        except PermissionError:
            pass

    def setUp(self):
        """Initialize database for each test"""
        self.db = EPSSDatabase(str(self.db_path))
        # Clean up any existing database from previous test
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except PermissionError:
                pass  # Will be overwritten anyway

    def tearDown(self):
        """Clean up database after each test"""
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except PermissionError:
                pass  # Database still in use, will clean up with temp dir

    def test_create_database(self):
        """Should create database with proper schema"""
        self.db.create_database()
        
        # Verify database exists
        self.assertTrue(self.db_path.exists())
        
        # Verify table exists
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='epss'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_import_csv(self):
        """Should import CSV data into database"""
        self.db.create_database()
        inserted, updated, skipped = self.db.import_csv(str(self.csv_path))
        
        self.assertEqual(inserted, 4)
        self.assertEqual(updated, 0)
        self.assertEqual(skipped, 0)
        
        # Verify records were inserted
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM epss')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 4)

    def test_import_csv_update(self):
        """Should update existing records with INSERT OR REPLACE"""
        self.db.create_database()
        
        # First import
        inserted1, _, _ = self.db.import_csv(str(self.csv_path))
        self.assertGreater(inserted1, 0)
        
        # Verify first import
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT epss FROM epss WHERE cve = ?', ('CVE-2024-0001',))
            original = cursor.fetchone()[0]
            self.assertEqual(original, 0.95)
        
        # Create updated CSV
        updated_csv = Path(self.temp_dir.name) / 'updated_epss.csv'
        with open(updated_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['cve', 'epss', 'percentile', 'date'])
            writer.writeheader()
            writer.writerow({'cve': 'CVE-2024-0001', 'epss': '0.85', 'percentile': '95.0', 'date': '2024-01-07'})
        
        # Import updated CSV - INSERT OR REPLACE increments inserted count
        inserted2, _, _ = self.db.import_csv(str(updated_csv))
        self.assertEqual(inserted2, 1)  # INSERT OR REPLACE counts as insert
        
        # Verify update
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT epss FROM epss WHERE cve = ?', ('CVE-2024-0001',))
            updated_value = cursor.fetchone()[0]
            self.assertEqual(updated_value, 0.85)

    def test_import_csv_validation(self):
        """Should validate data and skip invalid rows"""
        self.db.create_database()
        
        # Create CSV with invalid data
        invalid_csv = Path(self.temp_dir.name) / 'invalid_epss.csv'
        with open(invalid_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['cve', 'epss', 'percentile', 'date'])
            writer.writeheader()
            writer.writerows([
                {'cve': 'CVE-2024-0001', 'epss': '0.75', 'percentile': '90.0', 'date': '2024-01-06'},  # Valid
                {'cve': 'INVALID-CVE', 'epss': '0.50', 'percentile': '65.0', 'date': '2024-01-06'},     # Invalid CVE format
                {'cve': 'CVE-2024-0002', 'epss': '1.50', 'percentile': '100.0', 'date': '2024-01-06'},  # EPSS out of range
                {'cve': 'CVE-2024-0003', 'epss': '0.05', 'percentile': '150.0', 'date': '2024-01-06'},  # Percentile out of range
            ])
        
        inserted, updated, skipped = self.db.import_csv(str(invalid_csv))
        
        self.assertEqual(inserted, 1)  # Only first record is valid
        self.assertEqual(skipped, 3)

    def test_get_epss(self):
        """Should query EPSS data for CVE"""
        self.db.create_database()
        self.db.import_csv(str(self.csv_path))
        
        # Query existing CVE
        result = self.db.get_epss('CVE-2024-0001')
        self.assertIsNotNone(result)
        epss, percentile = result
        self.assertEqual(epss, 0.95)
        self.assertEqual(percentile, 98.5)
        
        # Query non-existent CVE
        result = self.db.get_epss('CVE-9999-9999')
        self.assertIsNone(result)

    def test_verify_database(self):
        """Should verify database and return statistics"""
        self.db.create_database()
        self.db.import_csv(str(self.csv_path))
        
        stats = self.db.verify_database()
        
        self.assertEqual(stats['total_records'], 4)
        self.assertEqual(stats['null_epss'], 0)
        self.assertEqual(stats['null_percentile'], 0)
        self.assertEqual(stats['epss_min'], 0.05)
        self.assertEqual(stats['epss_max'], 0.95)
        self.assertGreater(stats['epss_avg'], 0.5)
        self.assertEqual(stats['high_epss_count'], 3)  # Records with EPSS >= 0.5: 0.95, 0.75, 0.50
        self.assertEqual(stats['low_epss_count'], 1)   # Records with EPSS < 0.1: 0.05

    def test_missing_columns(self):
        """Should raise error if required columns missing"""
        self.db.create_database()
        
        # Create CSV with missing columns
        bad_csv = Path(self.temp_dir.name) / 'bad_epss.csv'
        with open(bad_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['cve', 'epss'])  # Missing 'percentile' and 'date'
            writer.writeheader()
            writer.writerow({'cve': 'CVE-2024-0001', 'epss': '0.75'})
        
        with self.assertRaises(ValueError):
            self.db.import_csv(str(bad_csv))

    def test_file_not_found(self):
        """Should raise error if CSV file not found"""
        self.db.create_database()
        
        with self.assertRaises(FileNotFoundError):
            self.db.import_csv('nonexistent.csv')

    def test_convenience_function(self):
        """Convenience function should work correctly"""
        inserted, updated, skipped = build_epss_database(
            str(self.csv_path),
            str(Path(self.temp_dir.name) / 'convenience_test.db'),
            verify=False
        )
        
        self.assertEqual(inserted, 4)
        self.assertEqual(updated, 0)
        self.assertEqual(skipped, 0)


if __name__ == '__main__':
    unittest.main()
