"""
EPSS Database Builder
Converts EPSS CSV files to SQLite database for runtime use

Usage:
    python modules/cve/build_epss_db.py <csv_file> [--db <output_db>]
    
Example:
    python modules/cve/build_epss_db.py modules/cve/epss_scores-2026-01-06.csv
    python modules/cve/build_epss_db.py data.csv --db modules/cve/epss.db
"""

import sqlite3
import csv
import logging
import argparse
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class EPSSDatabase:
    """Enterprise EPSS database builder and manager"""

    # Database schema
    SCHEMA_VERSION = "1.0"
    TABLE_NAME = "epss"

    def __init__(self, db_path: str = None):
        """Initialize EPSS database builder
        
        Args:
            db_path: Path to SQLite database file (default: modules/cve/epss.db)
        """
        if db_path is None:
            # Default to modules/cve/epss.db
            module_dir = Path(__file__).parent
            db_path = str(module_dir / 'epss.db')
        self.db_path = db_path
        self.connection = None

    def create_database(self) -> None:
        """Create SQLite database and schema"""
        logger.info(f"Creating EPSS database: {self.db_path}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create EPSS table with schema
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                        cve TEXT PRIMARY KEY,
                        epss REAL NOT NULL,
                        percentile REAL,
                        epss_date TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_epss_cve 
                    ON {self.TABLE_NAME}(cve)
                ''')
                
                # Create metadata table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                
                conn.commit()
                logger.info(f"Database schema created successfully")
        
        except sqlite3.Error as e:
            logger.error(f"Failed to create database: {e}")
            raise

    def import_csv(self, csv_path: str, skip_validation: bool = False) -> Tuple[int, int, int]:
        """Import EPSS data from CSV file
        
        Args:
            csv_path: Path to EPSS CSV file
            skip_validation: Skip data validation (faster for trusted sources)
            
        Returns:
            Tuple of (inserted, updated, skipped) counts
            
        CSV format expected (3 or 4 columns):
            cve,epss,percentile
            CVE-2024-0001,0.75,92.5
            
            Or with optional date column:
            cve,epss,percentile,date
            CVE-2024-0001,0.75,92.5,2024-01-06
            
        Note: Supports CISA EPSS CSV format with metadata header
        """
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"Starting import from: {csv_path}")
        
        inserted = 0
        updated = 0
        skipped = 0
        epss_date = datetime.now().strftime('%Y-%m-%d')  # Default to today
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    # Skip CISA metadata line if present
                    first_line = csvfile.readline()
                    if first_line.startswith('#'):
                        # Parse metadata to extract date if available
                        if 'score_date:' in first_line:
                            try:
                                date_str = first_line.split('score_date:')[1].split('T')[0]
                                epss_date = date_str
                                logger.info(f"Extracted EPSS date from metadata: {epss_date}")
                            except:
                                pass
                    else:
                        # Reset file pointer if first line wasn't metadata
                        csvfile.seek(0)
                    
                    reader = csv.DictReader(csvfile)
                    
                    # Validate headers
                    if not reader.fieldnames:
                        raise ValueError("CSV file is empty")
                    
                    required_fields = {'cve', 'epss', 'percentile'}
                    actual_fields = set(reader.fieldnames)
                    
                    if not required_fields.issubset(actual_fields):
                        missing = required_fields - actual_fields
                        raise ValueError(f"Missing required columns: {missing}")
                    
                    logger.info(f"CSV headers validated: {list(reader.fieldnames)}")
                    
                    # Import rows
                    for row_num, row in enumerate(reader, start=2):  # Start at 2 (skip header)
                        try:
                            cve_id = row['cve'].strip()
                            epss_score = float(row['epss'])
                            percentile = float(row['percentile']) if row['percentile'] else None
                            
                            # Use date from CSV if available, otherwise use extracted/default date
                            if 'date' in row and row['date']:
                                csv_date = row['date'].strip()
                            else:
                                csv_date = epss_date
                            
                            # Validate data
                            if not skip_validation:
                                if not cve_id.startswith('CVE-'):
                                    logger.warning(f"Row {row_num}: Invalid CVE format: {cve_id}")
                                    skipped += 1
                                    continue
                                
                                if not (0.0 <= epss_score <= 1.0):
                                    logger.warning(f"Row {row_num}: EPSS out of range: {epss_score}")
                                    skipped += 1
                                    continue
                                
                                if percentile and not (0.0 <= percentile <= 100.0):
                                    logger.warning(f"Row {row_num}: Percentile out of range: {percentile}")
                                    skipped += 1
                                    continue
                            
                            # Insert or update record
                            cursor.execute(f'''
                                INSERT OR REPLACE INTO {self.TABLE_NAME}
                                (cve, epss, percentile, epss_date, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (cve_id, epss_score, percentile, csv_date, datetime.utcnow().isoformat()))
                            
                            # Check if this was an update or insert
                            cursor.execute(f'SELECT changes()')
                            if cursor.fetchone()[0] == 1:
                                inserted += 1
                            else:
                                updated += 1
                        
                        except ValueError as e:
                            logger.warning(f"Row {row_num}: Invalid data - {e}")
                            skipped += 1
                            continue
                        except Exception as e:
                            logger.error(f"Row {row_num}: Unexpected error - {e}")
                            skipped += 1
                            continue
                
                # Update metadata
                cursor.execute('''
                    INSERT OR REPLACE INTO metadata (key, value)
                    VALUES (?, ?)
                ''', ('last_import', datetime.utcnow().isoformat()))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO metadata (key, value)
                    VALUES (?, ?)
                ''', ('schema_version', self.SCHEMA_VERSION))
                
                conn.commit()
                
                logger.info(
                    f"Import complete: {inserted} inserted, "
                    f"{updated} updated, {skipped} skipped"
                )
        
        except sqlite3.Error as e:
            logger.error(f"Database error during import: {e}")
            raise
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
        
        return inserted, updated, skipped

    def verify_database(self) -> dict:
        """Verify database integrity and return statistics
        
        Returns:
            Dictionary with verification results
        """
        logger.info("Verifying database...")
        
        try:
            with sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True) as conn:
                cursor = conn.cursor()
                
                # Count records
                cursor.execute(f'SELECT COUNT(*) FROM {self.TABLE_NAME}')
                total_records = cursor.fetchone()[0]
                
                # Check for nulls
                cursor.execute(f'SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE epss IS NULL')
                null_epss = cursor.fetchone()[0]
                
                cursor.execute(f'SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE percentile IS NULL')
                null_percentile = cursor.fetchone()[0]
                
                # Get EPSS statistics
                cursor.execute(f'SELECT MIN(epss), MAX(epss), AVG(epss) FROM {self.TABLE_NAME}')
                min_epss, max_epss, avg_epss = cursor.fetchone()
                
                # Get sample records
                cursor.execute(f'SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE epss >= 0.5')
                high_epss = cursor.fetchone()[0]
                
                cursor.execute(f'SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE epss < 0.1')
                low_epss = cursor.fetchone()[0]
                
                stats = {
                    'total_records': total_records,
                    'null_epss': null_epss,
                    'null_percentile': null_percentile,
                    'epss_min': min_epss,
                    'epss_max': max_epss,
                    'epss_avg': round(avg_epss, 4) if avg_epss else None,
                    'high_epss_count': high_epss,
                    'low_epss_count': low_epss
                }
                
                logger.info("Database verification complete:")
                logger.info(f"  Total records: {stats['total_records']}")
                logger.info(f"  EPSS range: {stats['epss_min']} - {stats['epss_max']}")
                logger.info(f"  EPSS average: {stats['epss_avg']}")
                logger.info(f"  High EPSS (>= 0.5): {stats['high_epss_count']}")
                logger.info(f"  Low EPSS (< 0.1): {stats['low_epss_count']}")
                logger.info(f"  Null EPSS: {stats['null_epss']}")
                logger.info(f"  Null percentile: {stats['null_percentile']}")
                
                return stats
        
        except sqlite3.Error as e:
            logger.error(f"Verification failed: {e}")
            raise

    def get_epss(self, cve_id: str) -> Optional[Tuple[float, Optional[float]]]:
        """Query EPSS data for a specific CVE (read-only)
        
        Args:
            cve_id: CVE identifier
            
        Returns:
            Tuple of (epss, percentile) or None if not found
        """
        try:
            with sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f'SELECT epss, percentile FROM {self.TABLE_NAME} WHERE cve = ?',
                    (cve_id,)
                )
                row = cursor.fetchone()
                return row if row else None
        
        except sqlite3.Error as e:
            logger.error(f"Query failed for {cve_id}: {e}")
            return None


def build_epss_database(
    csv_path: str,
    db_path: str = None,
    skip_validation: bool = False,
    verify: bool = True
) -> Tuple[int, int, int]:
    """Build EPSS database from CSV file
    
    Args:
        csv_path: Path to EPSS CSV file
        db_path: Output database path (default: modules/cve/epss.db)
        skip_validation: Skip data validation
        verify: Verify database after import
        
    Returns:
        Tuple of (inserted, updated, skipped) counts
    """
    if db_path is None:
        # Default to modules/cve/epss.db
        db_path = str(Path(__file__).parent / 'epss.db')
    
    db = EPSSDatabase(db_path)
    
    # Create database
    db.create_database()
    
    # Import CSV
    inserted, updated, skipped = db.import_csv(csv_path, skip_validation)
    
    # Verify
    if verify:
        db.verify_database()
    
    return inserted, updated, skipped


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Convert EPSS CSV to SQLite database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python build_epss_db.py epss_scores-2026-01-06.csv
  python build_epss_db.py data.csv --db modules/cve/epss.db
  python build_epss_db.py data.csv --skip-validation
        '''
    )
    
    parser.add_argument('csv_file', help='EPSS CSV file path')
    parser.add_argument('--db', default=None, help='Output database path (default: modules/cve/epss.db)')
    parser.add_argument('--skip-validation', action='store_true', help='Skip data validation')
    parser.add_argument('--no-verify', action='store_true', help='Skip database verification')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        logger.info("Starting EPSS database build...")
        inserted, updated, skipped = build_epss_database(
            args.csv_file,
            args.db,
            skip_validation=args.skip_validation,
            verify=not args.no_verify
        )
        
        logger.info("=" * 60)
        logger.info("BUILD SUCCESSFUL")
        logger.info(f"Database: {args.db}")
        logger.info(f"Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
        logger.info("=" * 60)
        
        return 0
    
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Build failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
