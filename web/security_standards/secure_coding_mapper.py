"""
Secure Coding Practices Mapper using Configuration Loader
Maps CWE to security coding best practices
"""

from typing import Dict, List
from web.config_loader import ConfigLoader


class SecureCodeMapper:
    """Maps CWE findings to Secure Coding Practices"""
    
    @staticmethod
    def get_by_cwe(cwe_id: int) -> Dict[str, List]:
        """Get SCP practices by CWE ID"""
        practices = ConfigLoader.get_scp_by_cwe(cwe_id)
        
        return {
            "practices": practices,
            "categories": list(set(p.get("category") for p in practices)),
            "critical_count": len([p for p in practices if p.get("severity") == "CRITICAL"]),
            "high_count": len([p for p in practices if p.get("severity") == "HIGH"])
        }
    
    @staticmethod
    def get_by_cve(cve_id: str, cwe_ids: List[int] = None) -> Dict[str, List]:
        """Get SCP practices by CVE and CWE IDs"""
        if not cwe_ids:
            cwe_ids = []
        
        all_practices = {}
        
        for cwe_id in cwe_ids:
            result = SecureCodeMapper.get_by_cwe(cwe_id)
            for practice in result.get("practices", []):
                practice_id = practice.get("id")
                if practice_id not in all_practices:
                    all_practices[practice_id] = practice
        
        practices_list = list(all_practices.values())
        
        return {
            "practices": practices_list,
            "categories": list(set(p.get("category") for p in practices_list)),
            "critical_count": len([p for p in practices_list if p.get("severity") == "CRITICAL"]),
            "high_count": len([p for p in practices_list if p.get("severity") == "HIGH"])
        }
    
    @staticmethod
    def get_all_practices() -> List[Dict]:
        """Get all SCP practices"""
        scp_data = ConfigLoader.load_scp_practices()
        return scp_data.get("practices", [])
    
    @staticmethod
    def get_by_category(category: str) -> List[Dict]:
        """Get SCP practices by category"""
        all_practices = SecureCodeMapper.get_all_practices()
        return [p for p in all_practices if p.get("category") == category]
    
    @staticmethod
    def get_critical_practices() -> List[Dict]:
        """Get all critical SCP practices"""
        all_practices = SecureCodeMapper.get_all_practices()
        return [p for p in all_practices if p.get("severity") == "CRITICAL"]
    
    @staticmethod
    def get_by_cve(cve_id: str, cwe_ids: List[int] = None) -> Dict:
        """Map CVE to secure coding practices"""
        if not cwe_ids:
            cwe_ids = []
        
        matched_practices = {}
        
        for cwe_id in cwe_ids:
            practices = ConfigLoader.get_scp_by_cwe(cwe_id)
            for practice in practices:
                practice_id = practice.get("id")
                if practice_id not in matched_practices:
                    matched_practices[practice_id] = practice
        
        practices_list = list(matched_practices.values())
        
        return {
            "cve_id": cve_id,
            "practices": practices_list,
            "categories": list(set([p.get("category") for p in practices_list])),
            "critical_count": sum(1 for p in practices_list if p.get("severity") == "CRITICAL"),
            "high_count": sum(1 for p in practices_list if p.get("severity") == "HIGH")
        }
    
    @staticmethod
    def get_by_category(category: str) -> List[Dict]:
        """Get all practices in a category"""
        all_practices = SecureCodeMapper.get_all_practices()
        return [p for p in all_practices if p.get("category") == category]
    
    @staticmethod
    def get_all_categories() -> List[str]:
        """Get all unique practice categories"""
        all_practices = SecureCodeMapper.get_all_practices()
        return list(set([p.get("category") for p in all_practices]))
