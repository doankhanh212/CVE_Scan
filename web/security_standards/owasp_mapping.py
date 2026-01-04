"""
OWASP Top 10 2021 Mapping using Configuration Loader
Maps vulnerabilities to OWASP Top 10 categories
Source: https://owasp.org/www-project-top-ten/
"""

from typing import Dict, List
from web.config_loader import ConfigLoader


class OWASPMapper:
    """Maps CVE/CWE findings to OWASP Top 10 2021 framework"""
    
    @staticmethod
    def get_by_cwe(cwe_id: int) -> Dict[str, List]:
        """Get OWASP categories by CWE ID"""
        mapping = ConfigLoader.get_cwe_mapping(cwe_id)
        owasp_codes = mapping.get("owasp_codes", [])
        
        owasp_mappings = []
        for code in owasp_codes:
            category = ConfigLoader.get_owasp_by_code(code)
            if category:
                owasp_mappings.append({
                    "owasp_code": code,
                    "owasp_name": category.get("name"),
                    "description": category.get("description"),
                    "risk_weight": OWASPMapper._calculate_risk_weight(code)
                })
        
        return {
            "owasp_mappings": owasp_mappings,
            "primary_owasp": owasp_codes[0] if owasp_codes else None,
            "coverage": len(owasp_codes) > 0
        }
    
    @staticmethod
    def get_by_cve_id(cve_id: str, cwe_ids: List[int] = None) -> Dict[str, List]:
        """Get OWASP mappings by CVE and CWE IDs"""
        if not cwe_ids:
            cwe_ids = []
        
        all_mappings = {}
        
        for cwe_id in cwe_ids:
            result = OWASPMapper.get_by_cwe(cwe_id)
            for mapping in result.get("owasp_mappings", []):
                code = mapping["owasp_code"]
                if code not in all_mappings:
                    all_mappings[code] = mapping
        
        return {
            "owasp_mappings": list(all_mappings.values()),
            "primary_owasp": list(all_mappings.keys())[0] if all_mappings else None,
            "coverage": len(all_mappings) > 0
        }
    
    @staticmethod
    def _calculate_risk_weight(owasp_code: str) -> float:
        """Calculate risk weight for OWASP category (1-10)"""
        risk_weights = {
            "A01:2021": 9.0,  # Broken Access Control
            "A02:2021": 9.1,  # Cryptographic Failures
            "A03:2021": 9.8,  # Injection
            "A04:2021": 8.0,  # Insecure Design
            "A05:2021": 7.5,  # Security Misconfiguration
            "A06:2021": 8.0,  # Vulnerable and Outdated Components
            "A07:2021": 9.3,  # Identification and Authentication Failures
            "A08:2021": 8.1,  # Software and Data Integrity Failures
            "A09:2021": 7.0,  # Logging and Monitoring Failures
            "A10:2021": 8.6,  # Server-Side Request Forgery
        }
        return risk_weights.get(owasp_code, 5.0)
    
    @staticmethod
    def get_all_categories() -> List[Dict]:
        """Get all OWASP Top 10 2021 categories"""
        owasp_data = ConfigLoader.load_owasp_mapping()
        return owasp_data.get("categories", [])
    
    @staticmethod
    def get_common_cwe_for_category(category_code: str) -> List[int]:
        """Get common CWE IDs for OWASP category"""
        category = ConfigLoader.get_owasp_by_code(category_code)
        return category.get("common_cwe", []) if category else []
