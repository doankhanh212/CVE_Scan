"""
Likelihood Calculator Integration Guide
Shows how to integrate likelihood calculation into CVE scanning pipeline

Usage patterns:
1. Single CVE enrichment
2. Batch scan results enrichment
3. Integration with existing scan_manager
"""

import json
import logging
from pathlib import Path
from modules.cve.likelihood_calculator import LikelihoodCalculator

logger = logging.getLogger(__name__)


def integrate_likelihood_into_scan_results(
    scan_results: dict,
    epss_db_path: str = None
) -> dict:
    """
    Main integration point: enrich scan results with likelihood scores
    
    Typical usage in scan_manager.py:
    
        # After scan completion and CVE detection
        enriched_results = integrate_likelihood_into_scan_results(
            scan_results,
            epss_db_path='modules/cve/epss.db'
        )
        
        # Save enriched results
        with open('scan_results_enriched.json', 'w') as f:
            json.dump(enriched_results, f, indent=2)
    """
    calculator = LikelihoodCalculator(epss_db_path)
    return calculator.enrich_scan_results(scan_results)


# Example 1: Simple CLI enrichment
def enrich_json_file(input_path: str, output_path: str, epss_db_path: str = None):
    """
    Load scan results JSON, enrich with likelihood, save results
    
    Usage:
        python -c "from ... import enrich_json_file; \
        enrich_json_file('results.json', 'results_enriched.json')"
    """
    logger.info(f"Loading scan results from {input_path}")
    with open(input_path, 'r') as f:
        scan_results = json.load(f)

    logger.info("Calculating likelihood scores...")
    enriched = integrate_likelihood_into_scan_results(scan_results, epss_db_path)

    logger.info(f"Saving enriched results to {output_path}")
    with open(output_path, 'w') as f:
        json.dump(enriched, f, indent=2)

    logger.info("Likelihood enrichment complete")


# Example 2: Integration with scan_manager workflow
class ScanManagerWithLikelihood:
    """
    Example of integrating likelihood calculator into scan workflow
    
    This shows how to use likelihood_calculator in scan_manager.py:
    
        from modules.cve.likelihood_calculator import LikelihoodCalculator
        
        class ScanManager:
            def __init__(self):
                self.likelihood_calc = LikelihoodCalculator()
            
            def complete_scan(self, targets, ...):
                # Existing scan logic
                scan_results = {}
                # ... discover hosts, scan ports, detect CVEs ...
                
                # NEW: Enrich with likelihood
                scan_results = self.likelihood_calc.enrich_scan_results(
                    scan_results
                )
                
                return scan_results
    """
    
    def __init__(self, epss_db_path: str = None):
        self.calculator = LikelihoodCalculator(epss_db_path)
        logger.info("ScanManager initialized with likelihood calculator")
    
    def process_scan_results(self, raw_scan_results: dict) -> dict:
        """
        Process raw scan results and add likelihood enrichment
        
        Args:
            raw_scan_results: Results from nmap/port scanning
            
        Returns:
            Enhanced results with likelihood data
        """
        logger.info("Enriching scan results with likelihood calculations")
        enriched = self.calculator.enrich_scan_results(raw_scan_results)
        
        # Example: filter to high-likelihood vulnerabilities
        high_likelihood_cves = self._extract_high_likelihood(enriched)
        logger.info(
            f"Found {len(high_likelihood_cves)} high-likelihood vulnerabilities"
        )
        
        return enriched
    
    @staticmethod
    def _extract_high_likelihood(scan_results: dict) -> list:
        """Extract CVEs with HIGH likelihood for alerting"""
        high_cves = []
        
        for host_label, host_data in scan_results.items():
            if not isinstance(host_data, dict):
                continue
            
            for port_info in host_data.get('ports', []):
                for cve in port_info.get('cves', []):
                    likelihood = cve.get('likelihood')
                    if likelihood and likelihood.get('level') == 'HIGH':
                        high_cves.append({
                            'host': host_label,
                            'cve_id': cve.get('id'),
                            'likelihood_score': likelihood.get('score'),
                            'cvss': cve.get('cvss_v3', {}).get('baseScore')
                        })
        
        return high_cves


# Example 3: API endpoint for on-demand likelihood calculation
def calculate_likelihood_for_cve(cve_id: str, cvss_score: float, epss_db_path: str = None) -> dict:
    """
    REST API endpoint: calculate likelihood for single CVE
    
    Usage in Flask/web routes:
    
        @app.route('/api/cve/<cve_id>/likelihood', methods=['GET'])
        def get_cve_likelihood(cve_id):
            cvss = request.args.get('cvss', type=float)
            result = calculate_likelihood_for_cve(cve_id, cvss)
            return jsonify(result)
    """
    calculator = LikelihoodCalculator(epss_db_path)
    
    epss, percentile = calculator.get_epss_from_db(cve_id)
    likelihood = calculator.calculate_likelihood(cvss_score, epss)
    
    return {
        'cve_id': cve_id,
        'cvss': cvss_score,
        'epss': epss,
        'percentile': percentile,
        'likelihood_score': likelihood['score'],
        'likelihood_level': likelihood['level'],
        'source': 'FIRST.org'
    }


# Example 4: Batch processing with reporting
def generate_likelihood_report(scan_results: dict, epss_db_path: str = None) -> dict:
    """
    Generate summary report of likelihood distribution
    
    Returns statistics like:
    - Total CVEs by likelihood level
    - Average likelihood scores
    - Top high-likelihood CVEs
    """
    calculator = LikelihoodCalculator(epss_db_path)
    enriched = calculator.enrich_scan_results(scan_results)
    
    stats = {
        'HIGH': {'count': 0, 'avg_score': 0, 'total_score': 0},
        'MEDIUM': {'count': 0, 'avg_score': 0, 'total_score': 0},
        'LOW': {'count': 0, 'avg_score': 0, 'total_score': 0}
    }
    
    all_cves = []
    
    for host_label, host_data in enriched.items():
        if not isinstance(host_data, dict):
            continue
        
        for port_info in host_data.get('ports', []):
            for cve in port_info.get('cves', []):
                likelihood = cve.get('likelihood')
                if likelihood:
                    level = likelihood['level']
                    score = likelihood['score']
                    
                    stats[level]['count'] += 1
                    stats[level]['total_score'] += score
                    
                    all_cves.append({
                        'host': host_label,
                        'cve_id': cve.get('id'),
                        'likelihood_score': score,
                        'likelihood_level': level
                    })
    
    # Calculate averages
    for level in stats:
        if stats[level]['count'] > 0:
            stats[level]['avg_score'] = round(
                stats[level]['total_score'] / stats[level]['count'], 2
            )
    
    # Sort by likelihood score
    all_cves.sort(key=lambda x: x['likelihood_score'], reverse=True)
    
    return {
        'summary': stats,
        'total_cves': sum(s['count'] for s in stats.values()),
        'top_10_cves': all_cves[:10],
        'all_cves': all_cves
    }


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example scan results
    sample_results = {
        'test-host': {
            'ports': [
                {
                    'port': 22,
                    'service': 'ssh',
                    'cves': [
                        {
                            'id': 'CVE-2024-1234',
                            'cvss_v3': {'baseScore': 8.5},
                            'description': 'Test CVE'
                        }
                    ]
                }
            ]
        }
    }
    
    # Enrich with likelihood
    enriched = integrate_likelihood_into_scan_results(sample_results)
    print("\nEnriched Results:")
    print(json.dumps(enriched, indent=2))
    
    # Generate report
    report = generate_likelihood_report(enriched)
    print("\nLikelihood Report:")
    print(f"Total CVEs: {report['total_cves']}")
    print(f"Summary: {report['summary']}")
