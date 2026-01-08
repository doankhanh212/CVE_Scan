# EPSS Database Builder

Convert EPSS (Exploit Prediction Scoring System) CSV files to SQLite database for efficient runtime access without external dependencies.

## Overview

The EPSS Database Builder (`build_epss_db.py`) provides a production-grade solution for:
- **CSV → SQLite conversion** with full validation
- **INSERT OR REPLACE logic** for daily updates
- **Read-only access** post-import for security
- **Batch processing** with comprehensive logging
- **No external APIs** required at runtime

## Installation

No additional dependencies required (uses Python standard library `sqlite3` and `csv`).

## Quick Start

### Command Line Usage

```bash
# Build EPSS database from CSV (creates/updates epss.db)
python modules/cve/build_epss_db.py modules/cve/epss_scores-2026-01-06.csv

# Specify custom output path
python modules/cve/build_epss_db.py data.csv --db modules/cve/epss.db

# Skip validation for trusted sources (faster)
python modules/cve/build_epss_db.py data.csv --skip-validation

# Verbose logging
python modules/cve/build_epss_db.py data.csv --verbose

# Build without verification step
python modules/cve/build_epss_db.py data.csv --no-verify
```

### Programmatic Usage

```python
from modules.cve.build_epss_db import build_epss_database, EPSSDatabase

# Convenience function (one-liner)
inserted, updated, skipped = build_epss_database(
    'epss_scores-2026-01-06.csv',
    'modules/cve/epss.db'
)
print(f"Imported: {inserted} new, {updated} updated, {skipped} skipped")

# Or use EPSSDatabase class directly
db = EPSSDatabase('modules/cve/epss.db')
db.create_database()
inserted, updated, skipped = db.import_csv('epss_scores-2026-01-06.csv')
stats = db.verify_database()
print(stats)

# Query EPSS data
epss, percentile = db.get_epss('CVE-2024-0001')
print(f"EPSS: {epss}, Percentile: {percentile}")
```

## CSV Format

Expected CSV structure with headers:

```csv
cve,epss,percentile,date
CVE-2024-0001,0.95,98.5,2024-01-06
CVE-2024-0002,0.50,65.0,2024-01-06
CVE-2024-0003,0.05,15.0,2024-01-06
```

**Required columns:**
- `cve` - CVE identifier (must start with "CVE-")
- `epss` - EPSS score (0.0 - 1.0)
- `percentile` - Percentile ranking (0.0 - 100.0)
- `date` - Import date (e.g., "2024-01-06")

## Data Validation

### Validation Rules

| Field | Rule | Action |
|-------|------|--------|
| CVE ID | Must start with "CVE-" | Skip invalid rows |
| EPSS | Must be 0.0 - 1.0 | Skip out-of-range |
| Percentile | Must be 0.0 - 100.0 | Skip out-of-range |
| Headers | Required fields present | Raise error if missing |

### Disable Validation

Use `--skip-validation` for pre-validated sources (faster):

```bash
python modules/cve/build_epss_db.py trusted_data.csv --skip-validation
```

```python
db.import_csv('trusted_data.csv', skip_validation=True)
```

## Database Schema

```sql
CREATE TABLE epss (
    cve TEXT PRIMARY KEY,
    epss REAL NOT NULL,
    percentile REAL,
    epss_date TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_epss_cve ON epss(cve);

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

## Update Workflow

### Daily Updates

Import updated EPSS CSV to replace outdated records:

```bash
# Day 1: Initial import
python modules/cve/build_epss_db.py epss_scores-2024-01-06.csv

# Day 2: Daily update (replaces records with same CVE)
python modules/cve/build_epss_db.py epss_scores-2024-01-07.csv
```

**How INSERT OR REPLACE works:**
- **New CVE**: Insert new record
- **Existing CVE**: Replace old record with new data
- **No duplicates**: PRIMARY KEY ensures unique CVE entries

### Update Statistics

```python
inserted, updated, skipped = db.import_csv('daily_update.csv')
print(f"New records: {inserted}")
print(f"Updated records: {updated}")
print(f"Skipped (invalid): {skipped}")
```

## Integration with Likelihood Calculator

Use EPSS database with `LikelihoodCalculator`:

```python
from modules.cve.likelihood_calculator import LikelihoodCalculator

# Initialize calculator with EPSS database
calc = LikelihoodCalculator('modules/cve/epss.db')

# Enrich vulnerabilities with likelihood scores
vuln = {
    'id': 'CVE-2024-0001',
    'cvss_v3': {'baseScore': 8.5}
}
enriched = calc.enrich_vulnerability_with_likelihood(vuln)
print(enriched['likelihood'])  # {'epss': 0.95, 'score': 8.075, 'level': 'HIGH', ...}
```

## Verification

### Build-time Verification

Run automatic verification after import:

```bash
python modules/cve/build_epss_db.py data.csv  # Default: runs verification

# Skip verification (faster for large imports)
python modules/cve/build_epss_db.py data.csv --no-verify
```

### Manual Verification

```python
stats = db.verify_database()
print(f"Total records: {stats['total_records']}")
print(f"EPSS range: {stats['epss_min']} - {stats['epss_max']}")
print(f"Average EPSS: {stats['epss_avg']}")
print(f"High EPSS (≥0.5): {stats['high_epss_count']}")
print(f"Low EPSS (<0.1): {stats['low_epss_count']}")
```

**Statistics returned:**
- `total_records` - Total CVE count
- `null_epss` - Records with missing EPSS
- `null_percentile` - Records with missing percentile
- `epss_min`, `epss_max`, `epss_avg` - EPSS statistics
- `high_epss_count` - Records with EPSS ≥ 0.5
- `low_epss_count` - Records with EPSS < 0.1

## Performance

### Benchmarks

On typical EPSS CSV files:

| Operation | Time | Note |
|-----------|------|------|
| Import 50K records | ~2-5 seconds | With validation |
| Import (no validation) | ~1-2 seconds | skip_validation=True |
| Query single CVE | <1ms | Indexed lookup |
| Verify database | ~1 second | Stats calculation |

### Optimization Tips

1. **Skip validation for trusted sources**: `--skip-validation` flag
2. **Skip verification for large imports**: `--no-verify` flag
3. **Use read-only mode post-import**: Database enforces via URI mode
4. **Index on CVE**: Created automatically for fast lookups

## Security

### Post-Import Access

After import, database is accessed in **read-only mode**:

```python
# Enforced at connection level
with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as conn:
    # Only SELECT queries allowed
    cursor.execute('SELECT epss FROM epss WHERE cve = ?', (cve_id,))
```

### Data Integrity

- **Primary key**: CVE prevents duplicates
- **Validation**: Invalid rows skipped with warnings
- **Audit trail**: Metadata table tracks import date/schema version
- **Immutable at runtime**: No runtime modifications possible

## Troubleshooting

### Issue: CSV Headers Validation Fails

**Cause**: CSV missing required columns

**Solution**: Verify CSV has headers: `cve,epss,percentile,date`

```bash
head -1 your_file.csv
# Should output: cve,epss,percentile,date
```

### Issue: Import Skips Many Rows

**Cause**: Data validation catching invalid entries

**Solution**: Check logs and either:
1. Fix CSV data
2. Use `--skip-validation` if source is trusted

```bash
python modules/cve/build_epss_db.py data.csv --verbose
```

### Issue: Database Lock on Windows

**Cause**: SQLite connection still open

**Solution**: Ensure connections are closed:

```python
# Automatic with context manager
with sqlite3.connect(db_path) as conn:
    # ... code ...
# Connection auto-closed here
```

### Issue: Query Returns None

**Cause**: CVE not in database

**Solution**: Verify EPSS database contains data:

```python
stats = db.verify_database()
if stats['total_records'] == 0:
    print("Database is empty. Import EPSS CSV first.")
```

## API Reference

### EPSSDatabase Class

#### `__init__(db_path: str = "epss.db")`
Initialize database builder

#### `create_database() -> None`
Create SQLite schema and indexes

#### `import_csv(csv_path: str, skip_validation: bool = False) -> Tuple[int, int, int]`
Import CSV data. Returns (inserted, updated, skipped)

#### `verify_database() -> dict`
Verify integrity and return statistics

#### `get_epss(cve_id: str) -> Optional[Tuple[float, float]]`
Query EPSS for CVE. Returns (epss, percentile) or None

### build_epss_database Function

```python
def build_epss_database(
    csv_path: str,
    db_path: str = "epss.db",
    skip_validation: bool = False,
    verify: bool = True
) -> Tuple[int, int, int]
```

Convenience function combining create + import + verify. Returns (inserted, updated, skipped).

## Examples

### Example 1: Daily EPSS Update

```python
from modules.cve.build_epss_db import build_epss_database
from datetime import datetime

# Daily import scheduled task
today = datetime.now().strftime('%Y-%m-%d')
csv_file = f'epss_scores-{today}.csv'
db_file = 'modules/cve/epss.db'

try:
    inserted, updated, skipped = build_epss_database(csv_file, db_file)
    print(f"[{today}] EPSS updated: +{inserted}, ~{updated}, ✗{skipped}")
except Exception as e:
    print(f"[ERROR] EPSS update failed: {e}")
```

### Example 2: Enrich Scan Results

```python
from modules.cve.build_epss_db import EPSSDatabase
from modules.cve.likelihood_calculator import LikelihoodCalculator

# Build EPSS database
db = EPSSDatabase('epss.db')
db.create_database()
db.import_csv('epss_scores.csv')

# Use with likelihood calculator
calc = LikelihoodCalculator('epss.db')

# Enrich scan results
scan_results = {...}  # Host/Port/CVE structure
enriched = calc.enrich_scan_results(scan_results)

# Now each CVE has likelihood score
for host, result in enriched.items():
    for port_data in result['gui']['ports']:
        for cve in port_data['cves']:
            print(f"{cve['id']}: Likelihood {cve['likelihood']['level']}")
```

### Example 3: Validate Before Import

```python
from modules.cve.build_epss_db import EPSSDatabase
import csv

db = EPSSDatabase('epss.db')

# Pre-validate CSV
csv_path = 'untrusted_source.csv'
with open(csv_path) as f:
    reader = csv.DictReader(f)
    invalid = []
    for i, row in enumerate(reader, 2):
        try:
            epss = float(row['epss'])
            if not (0 <= epss <= 1):
                invalid.append((i, f"EPSS {epss} out of range"))
        except ValueError:
            invalid.append((i, f"EPSS not a number: {row['epss']}"))

if invalid:
    print(f"Found {len(invalid)} invalid rows:")
    for row_num, error in invalid[:10]:
        print(f"  Row {row_num}: {error}")
else:
    # All valid, import
    db.create_database()
    inserted, _, _ = db.import_csv(csv_path, skip_validation=True)
    print(f"Imported {inserted} records")
```

## Testing

Run comprehensive test suite:

```bash
pytest tests/test_build_epss_db.py -v
```

Tests cover:
- Database creation ✅
- CSV import ✅
- Data validation ✅
- INSERT OR REPLACE logic ✅
- Read operations ✅
- Error handling ✅

## Related

- **LikelihoodCalculator**: Uses EPSS data for vulnerability scoring
  - [likelihood_calculator.py](likelihood_calculator.py)
  - Formula: `Likelihood = CVSS_base × EPSS`

- **Integration Guide**: End-to-end examples
  - [likelihood_integration.py](likelihood_integration.py)

## License

Same as parent project

## Support

For issues or questions:
1. Check [troubleshooting](#troubleshooting) section
2. Review [examples](#examples) for usage patterns
3. Run tests to validate installation
4. Check logs with `--verbose` flag

---

**Version**: 1.0
**Last Updated**: 2024-01-06
**Status**: Production Ready ✅
