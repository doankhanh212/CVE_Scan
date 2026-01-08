"""
Likelihood Calculation Module for CVE Management Platform
Implements EPSS-based likelihood scoring: L = CVSS_base × EPSS

Architecture:
- Read-only EPSS database access
- Deterministic and repeatable calculations
- Production-grade error handling
- No external API calls or CSV parsing at runtime
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class LikelihoodCalculator:
    """Enterprise CVE likelihood calculation engine"""

    # Likelihood level thresholds
    LIKELIHOOD_THRESHOLDS = {
        'HIGH': 7.0,
        'MEDIUM': 4.0,
        'LOW': 0.0
    }

    # Conservative EPSS fallback when data unavailable
    DEFAULT_EPSS = 0.01

    def __init__(self, epss_db_path: Optional[str] = None):
        """
        Initialize likelihood calculator with EPSS database path
        
        Args:
            epss_db_path: Path to epss.db. If None, uses default location.
        """
        if epss_db_path is None:
            # Default to standard module location
            module_dir = Path(__file__).parent
            epss_db_path = str(module_dir / 'epss.db')
        
        self.epss_db_path = epss_db_path
        self._validate_db_exists()

    def _validate_db_exists(self) -> None:
        """Validate EPSS database exists and is accessible"""
        if not Path(self.epss_db_path).exists():
            logger.warning(
                f"EPSS database not found at {self.epss_db_path}. "
                f"Using conservative fallback EPSS for all CVEs."
            )
        else:
            logger.info(f"EPSS database initialized: {self.epss_db_path}")

    @staticmethod
    def extract_cvss_base(cve_data: Dict[str, Any]) -> Optional[float]:
        """
        🔹 BƯỚC 1: Chọn CVSS_base "tốt nhất"
        Ưu tiên: CVSS 4.0 → CVSS 3.1 → CVSS 3.0 → CVSS 2.0
        
        Args:
            cve_data: CVE vulnerability object from scan results
            
        Returns:
            CVSS base score (float) or None if unavailable
        """
        # Priority 1: CVSS v4.0 (latest standard)
        if 'cvss_v4' in cve_data:
            v4 = cve_data['cvss_v4']
            if isinstance(v4, dict) and 'baseScore' in v4:
                score = v4['baseScore']
            else:
                score = v4
            
            if isinstance(score, (int, float)) and 0 <= score <= 10:
                logger.debug(f"CVSS 4.0 selected: {score}")
                return float(score)

        # Priority 2: CVSS v3.1
        if 'cvss_v3_1' in cve_data:
            v3_1 = cve_data['cvss_v3_1']
            if isinstance(v3_1, dict) and 'baseScore' in v3_1:
                score = v3_1['baseScore']
            else:
                score = v3_1
            
            if isinstance(score, (int, float)) and 0 <= score <= 10:
                logger.debug(f"CVSS 3.1 selected: {score}")
                return float(score)

        # Priority 3: CVSS v3.0 or generic v3
        for key in ['cvss_v3', 'cvss_v3_0']:
            if key in cve_data:
                v3 = cve_data[key]
                if isinstance(v3, dict) and 'baseScore' in v3:
                    score = v3['baseScore']
                else:
                    score = v3
                
                if isinstance(score, (int, float)) and 0 <= score <= 10:
                    logger.debug(f"CVSS 3.0 selected: {score}")
                    return float(score)

        # Priority 4: CVSS v2.0 (legacy)
        if 'cvss_v2' in cve_data:
            v2 = cve_data['cvss_v2']
            if isinstance(v2, dict) and 'baseScore' in v2:
                score = v2['baseScore']
            else:
                score = v2
            
            if isinstance(score, (int, float)) and 0 <= score <= 10:
                logger.debug(f"Using CVSS v2 score: {score}")
                return float(score)

        logger.warning(f"No valid CVSS score found in CVE data")
        return None

    def get_epss_from_db(self, cve_id: str) -> Tuple[float, Optional[float]]:
        """
        🔹 BƯỚC 2: Lấy EPSS theo CVE ID
        epss, percentile = get_epss(cve_id)
        
        Args:
            cve_id: CVE ID (e.g., 'CVE-2024-1234')
            
        Returns:
            Tuple of (epss, percentile)
            - epss: EPSS score (0.0-1.0)
            - percentile: EPSS percentile (0.0-1.0) or None
            - Returns (0.01, None) if CVE not found (conservative fallback)
        """
        # Validate CVE ID format
        if not cve_id or not cve_id.startswith('CVE-'):
            logger.warning(f"Invalid CVE ID format: {cve_id}")
            return (self.DEFAULT_EPSS, None)

        # Check if database exists before querying
        if not Path(self.epss_db_path).exists():
            logger.debug(f"EPSS database not available, using fallback for {cve_id}")
            return (self.DEFAULT_EPSS, None)

        try:
            # Read-only connection to EPSS database
            with sqlite3.connect(f'file:{self.epss_db_path}?mode=ro', uri=True) as conn:
                cursor = conn.cursor()
                
                # Query EPSS data
                cursor.execute(
                    'SELECT epss, percentile FROM epss WHERE cve = ?',
                    (cve_id,)
                )
                row = cursor.fetchone()

                if row:
                    epss, percentile = row
                    # Validate EPSS range [0.0, 1.0]
                    if isinstance(epss, (int, float)) and 0.0 <= epss <= 1.0:
                        logger.debug(f"{cve_id}: EPSS={epss}, percentile={percentile}")
                        return (float(epss), float(percentile) if percentile else None)
                    else:
                        logger.warning(f"{cve_id}: Invalid EPSS value {epss}")
                        return (self.DEFAULT_EPSS, None)
                else:
                    logger.debug(f"{cve_id}: Not found in EPSS database, using fallback")
                    return (self.DEFAULT_EPSS, None)

        except sqlite3.OperationalError as e:
            logger.error(f"EPSS database read failed for {cve_id}: {e}")
            return (self.DEFAULT_EPSS, None)
        except Exception as e:
            logger.error(f"Unexpected error reading EPSS for {cve_id}: {e}")
            return (self.DEFAULT_EPSS, None)

    @staticmethod
    def calculate_likelihood(cvss_base: float, epss: float) -> Dict[str, Any]:
        """
        Calculate likelihood score and determine risk level
        
        Args:
            cvss_base: CVSS base score (0-10)
            epss: EPSS score (0.0-1.0)
            
        Returns:
            Dictionary with likelihood score and level
            
        Formula: L = CVSS_base × EPSS
        
        Level mapping:
            - score >= 7.0  → HIGH
            - score >= 4.0  → MEDIUM
            - score < 4.0   → LOW
        """
        # Validate inputs
        if not (0 <= cvss_base <= 10):
            logger.warning(f"CVSS out of range: {cvss_base}")
            cvss_base = max(0, min(10, cvss_base))

        if not (0.0 <= epss <= 1.0):
            logger.warning(f"EPSS out of range: {epss}")
            epss = max(0.0, min(1.0, epss))

        # Calculate likelihood score
        score = round(cvss_base * epss, 5)

        # Determine likelihood level
        if score >= LikelihoodCalculator.LIKELIHOOD_THRESHOLDS['HIGH']:
            level = 'HIGH'
        elif score >= LikelihoodCalculator.LIKELIHOOD_THRESHOLDS['MEDIUM']:
            level = 'MEDIUM'
        else:
            level = 'LOW'

        return {
            'score': score,
            'level': level
        }

    def enrich_vulnerability_with_likelihood(
        self,
        cve_data: Dict[str, Any],
        cve_id: str
    ) -> Dict[str, Any]:
        """
        Enrich CVE vulnerability with likelihood calculation
        
        Args:
            cve_data: Original vulnerability object from scan results
            cve_id: CVE identifier
            
        Returns:
            Enhanced CVE data with 'likelihood' object added
            
        Side effects:
            - Adds 'likelihood' key to cve_data
            - Does NOT modify existing CVSS or other data
            - Deterministic and repeatable calculation
        """
        # Extract CVSS base score
        cvss_base = self.extract_cvss_base(cve_data)
        if cvss_base is None:
            logger.warning(f"{cve_id}: Cannot calculate likelihood without CVSS score")
            cve_data['likelihood'] = None
            return cve_data

        # Lookup EPSS from database
        epss, percentile = self.get_epss_from_db(cve_id)

        # Calculate likelihood
        likelihood_calc = self.calculate_likelihood(cvss_base, epss)

        # Build likelihood object
        cve_data['likelihood'] = {
            'epss': epss,
            'percentile': percentile,
            'score': likelihood_calc['score'],
            'level': likelihood_calc['level'],
            'source': 'FIRST.org',
            'date': datetime.now().isoformat() + 'Z'
        }

        logger.debug(
            f"{cve_id}: Likelihood={likelihood_calc['score']} "
            f"({likelihood_calc['level']}, CVSS={cvss_base}, EPSS={epss})"
        )

        return cve_data

    def enrich_scan_results(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich entire scan results with likelihood calculations
        
        Args:
            scan_results: Scan result dictionary with host/port/CVE structure:
                {
                    "host_label": {
                        "ports": [
                            {
                                "cves": [
                                    {"id": "CVE-2024-...", "cvss_v3": {...}, ...}
                                ]
                            }
                        ]
                    }
                }
            
        Returns:
            Enhanced scan results with likelihood data added to each CVE
            
        Processing:
            - Iterates through all hosts → ports → CVEs
            - Adds likelihood calculation to each vulnerability
            - Preserves original structure and data
            - Logs summary of processed CVEs
        """
        if not isinstance(scan_results, dict):
            logger.error("Invalid scan results format")
            return scan_results

        processed_count = 0
        error_count = 0

        for host_label, host_data in scan_results.items():
            if not isinstance(host_data, dict):
                continue

            ports = host_data.get('ports', [])
            if not isinstance(ports, list):
                continue

            for port_info in ports:
                if not isinstance(port_info, dict):
                    continue

                cves = port_info.get('cves', [])
                if not isinstance(cves, list):
                    continue

                for cve in cves:
                    if not isinstance(cve, dict):
                        continue

                    try:
                        cve_id = cve.get('id') or cve.get('cve_id')
                        if cve_id:
                            self.enrich_vulnerability_with_likelihood(cve, cve_id)
                            processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to enrich {cve.get('id')}: {e}")
                        error_count += 1

        logger.info(
            f"Likelihood enrichment complete: {processed_count} CVEs processed, "
            f"{error_count} errors"
        )

        return scan_results


# Module-level convenience function for single CVE processing
def calculate_cve_likelihood(
    cve_data: Dict[str, Any],
    cve_id: str,
    epss_db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate likelihood for a single CVE (convenience function)
    
    Args:
        cve_data: CVE vulnerability object
        cve_id: CVE ID
        epss_db_path: Optional path to EPSS database
        
    Returns:
        Enhanced CVE data with likelihood calculation
    """
    calculator = LikelihoodCalculator(epss_db_path)
    return calculator.enrich_vulnerability_with_likelihood(cve_data, cve_id)
