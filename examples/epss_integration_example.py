"""
Integration Example: EPSS Database + Likelihood Calculator + Scan Manager

This example shows the complete workflow for:
1. Building EPSS database from CSV
2. Enriching scan results with likelihood scores
3. Reporting with likelihood data
"""

import logging
from pathlib import Path
from modules.cve.build_epss_db import build_epss_database
from modules.cve.likelihood_calculator import LikelihoodCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedScanPipeline:
    """Production pipeline combining EPSS database, likelihood calculation, and reporting"""
    
    def __init__(self, epss_csv_path, db_path='modules/cve/epss.db'):
        """
        Initialize enhanced scan pipeline
        
        Args:
            epss_csv_path: Path to EPSS CSV file
            db_path: Path to EPSS SQLite database
        """
        self.epss_csv_path = epss_csv_path
        self.db_path = db_path
        self.calculator = None
        
    def setup(self):
        """Build EPSS database and initialize calculator"""
        logger.info("Setting up enhanced scan pipeline...")
        
        # Step 1: Build EPSS database from CSV
        logger.info(f"Building EPSS database from {self.epss_csv_path}")
        try:
            inserted, updated, skipped = build_epss_database(
                self.epss_csv_path,
                self.db_path,
                verify=True
            )
            logger.info(
                f"EPSS database ready: {inserted} new, "
                f"{updated} updated, {skipped} skipped"
            )
        except Exception as e:
            logger.error(f"Failed to build EPSS database: {e}")
            raise
        
        # Step 2: Initialize likelihood calculator
        logger.info(f"Initializing likelihood calculator with {self.db_path}")
        self.calculator = LikelihoodCalculator(self.db_path)
        logger.info("Pipeline ready")
        
    def enrich_scan(self, scan_results):
        """
        Enrich scan results with likelihood scores
        
        Args:
            scan_results: Dict mapping host → result (standard CVE Scan structure)
            
        Returns:
            Enriched scan results with likelihood data
            
        Example structure:
            {
                '192.168.1.1': {
                    'gui': {
                        'ports': [
                            {
                                'port': 22,
                                'service': 'ssh',
                                'cves': [
                                    {
                                        'id': 'CVE-2024-0001',
                                        'severity': 'HIGH',
                                        'cvss_v3': {'baseScore': 8.5},
                                        'likelihood': {  # ADDED BY ENRICHMENT
                                            'epss': 0.95,
                                            'percentile': 98.5,
                                            'score': 8.075,  # CVSS × EPSS
                                            'level': 'HIGH'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        """
        if not self.calculator:
            raise RuntimeError("Pipeline not initialized. Call setup() first.")
        
        logger.info("Enriching scan results with likelihood scores...")
        enriched = self.calculator.enrich_scan_results(scan_results)
        logger.info("Enrichment complete")
        return enriched
        
    def get_high_likelihood_vulns(self, scan_results):
        """Get all HIGH likelihood vulnerabilities from scan"""
        high_risk = []
        
        for host, result in scan_results.items():
            if 'gui' not in result or 'ports' not in result['gui']:
                continue
                
            for port_data in result['gui']['ports']:
                for cve in port_data.get('cves', []):
                    if 'likelihood' in cve:
                        if cve['likelihood']['level'] == 'HIGH':
                            high_risk.append({
                                'host': host,
                                'port': port_data.get('port'),
                                'service': port_data.get('service'),
                                'cve': cve['id'],
                                'cvss': cve.get('cvss_v3', {}).get('baseScore'),
                                'epss': cve['likelihood']['epss'],
                                'likelihood_score': cve['likelihood']['score'],
                                'description': cve.get('description', '')[:100]
                            })
        
        return sorted(high_risk, key=lambda x: x['likelihood_score'], reverse=True)
        
    def generate_report(self, scan_results, output_path='report.txt'):
        """Generate text report with likelihood scores"""
        high_risk = self.get_high_likelihood_vulns(scan_results)
        
        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("SCAN REPORT WITH LIKELIHOOD SCORES\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Total HIGH Likelihood Vulnerabilities: {len(high_risk)}\n\n")
            
            for i, vuln in enumerate(high_risk, 1):
                f.write(f"{i}. {vuln['cve']} on {vuln['host']}:{vuln['port']}\n")
                f.write(f"   Service: {vuln['service']}\n")
                f.write(f"   CVSS Score: {vuln['cvss']}\n")
                f.write(f"   EPSS: {vuln['epss']}\n")
                f.write(f"   Likelihood Score: {vuln['likelihood_score']:.2f}\n")
                f.write(f"   Description: {vuln['description']}\n\n")
        
        logger.info(f"Report saved to {output_path}")
        
        return len(high_risk)


# Example usage
def example_workflow():
    """
    Complete example workflow
    """
    logger.info("=" * 80)
    logger.info("Enhanced Scan Pipeline Example")
    logger.info("=" * 80)
    
    # Sample EPSS CSV path (adjust to your actual file)
    epss_csv = 'modules/cve/epss_scores-2026-01-06.csv'
    db_path = 'modules/cve/epss.db'
    
    # Verify CSV exists
    if not Path(epss_csv).exists():
        logger.error(f"EPSS CSV not found: {epss_csv}")
        logger.info("Download EPSS data from: https://www.cisa.gov/epss/data")
        return
    
    # Initialize pipeline
    pipeline = EnhancedScanPipeline(epss_csv, db_path)
    pipeline.setup()
    
    # Sample scan results (replace with actual scan)
    sample_scan = {
        '192.168.1.100': {
            'gui': {
                'ports': [
                    {
                        'port': 22,
                        'service': 'openssh',
                        'cves': [
                            {
                                'id': 'CVE-2024-0001',
                                'severity': {'label': 'HIGH'},
                                'cvss_v3': {'baseScore': 8.5},
                                'description': 'Example vulnerability in OpenSSH'
                            }
                        ]
                    }
                ]
            }
        }
    }
    
    # Enrich with likelihood scores
    enriched = pipeline.enrich_scan(sample_scan)
    
    # Show high-risk vulnerabilities
    high_risk = pipeline.get_high_likelihood_vulns(enriched)
    logger.info(f"Found {len(high_risk)} HIGH likelihood vulnerabilities")
    
    # Generate report
    pipeline.generate_report(enriched, 'likelihood_report.txt')
    
    logger.info("=" * 80)
    logger.info("Pipeline execution complete")
    logger.info("=" * 80)


# Integration with ScanManager (pseudo-code)
def integrate_with_scan_manager():
    """
    Example of integrating with ScanManager for automated scans
    
    # In modules/scan_manager.py:
    
    from modules.cve.build_epss_db import build_epss_database
    from modules.cve.likelihood_calculator import LikelihoodCalculator
    
    class ScanManager:
        def __init__(self, config):
            self.config = config
            self.likelihood_calc = None
            
        def initialize_likelihood_calculator(self):
            '''Initialize EPSS database and likelihood calculator'''
            epss_db = self.config.get('epss_db', 'modules/cve/epss.db')
            epss_csv = self.config.get('epss_csv')
            
            if epss_csv and Path(epss_csv).exists():
                # Build EPSS database if CSV provided
                build_epss_database(epss_csv, epss_db)
            
            if Path(epss_db).exists():
                self.likelihood_calc = LikelihoodCalculator(epss_db)
        
        def scan(self, targets, authenticated=False, auth_data=None, host_result_cb=None):
            '''Scan targets and enrich with likelihood scores'''
            # ... existing scan logic ...
            
            # Enrich results with likelihood if available
            if self.likelihood_calc:
                scan_results = self.likelihood_calc.enrich_scan_results(scan_results)
            
            return scan_results
    """
    pass


if __name__ == '__main__':
    # Run example workflow
    example_workflow()
