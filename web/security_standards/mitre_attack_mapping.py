"""
MITRE ATT&CK Enterprise Mapping using Configuration Loader
Maps vulnerabilities to MITRE ATT&CK Framework
Source: https://attack.mitre.org/
"""

from typing import Dict, List
from web.config_loader import ConfigLoader


class MITREMapper:
    """Maps CVE/CWE findings to MITRE ATT&CK Enterprise tactics and techniques"""
    
    @staticmethod
    def get_by_cwe(cwe_id: int) -> List[str]:
        """Get MITRE technique IDs by CWE ID"""
        mapping = ConfigLoader.get_cwe_mapping(cwe_id)
        return mapping.get("mitre_techniques", [])
    
    @staticmethod
    def get_by_cve(cve_id: str, cwe_ids: List[int] = None, vulnerability_type: str = None) -> Dict:
        """Map CVE to MITRE ATT&CK techniques based on CWE IDs"""
        if not cwe_ids:
            cwe_ids = []
        
        # DEBUG: Log input
        import sys
        print(f"[MITRE] CVE: {cve_id}, CWE IDs: {cwe_ids}", file=sys.stderr)
        
        matched_techniques = {}
        matched_tactics = set()
        
        # Get all techniques to create a lookup
        all_techniques = ConfigLoader.get_all_mitre_techniques()
        technique_map = {t["id"]: t for t in all_techniques}
        
        for cwe_id in cwe_ids:
            technique_ids = MITREMapper.get_by_cwe(cwe_id)
            print(f"[MITRE]   CWE {cwe_id} → Found {len(technique_ids)} techniques: {technique_ids}", file=sys.stderr)
            
            for tech_id in technique_ids:
                if tech_id in technique_map and tech_id not in matched_techniques:
                    technique = technique_map[tech_id]
                    matched_techniques[tech_id] = {
                        "technique_id": tech_id,
                        "technique_name": technique.get("name"),
                        "tactic_id": technique.get("tactic_id"),
                        "tactic_name": ConfigLoader.get_mitre_tactic(technique.get("tactic_id")).get("name"),
                        "description": technique.get("description")
                    }
                    matched_tactics.add(technique.get("tactic_id"))
        
        print(f"[MITRE] Result: {len(matched_techniques)} techniques, {len(matched_tactics)} tactics", file=sys.stderr)
        
        return {
            "cve_id": cve_id,
            "techniques": list(matched_techniques.values()),
            "tactics": list(matched_tactics),
            "attack_chain": MITREMapper._build_attack_chain(list(matched_techniques.keys()))
        }
    
    @staticmethod
    def _build_attack_chain(technique_ids: List[str]) -> List[str]:
        """Build logical attack chain from techniques (ordered by tactic progression)"""
        tactic_order = ["TA0043", "TA0042", "TA0001", "TA0002", "TA0003", 
                       "TA0004", "TA0005", "TA0006", "TA0007", "TA0008", 
                       "TA0009", "TA0010", "TA0011", "TA0040"]
        
        chain = []
        technique_map = {t["id"]: t for t in ConfigLoader.get_all_mitre_techniques()}
        
        for tactic_id in tactic_order:
            for tech_id in technique_ids:
                if tech_id in technique_map:
                    if technique_map[tech_id].get("tactic_id") == tactic_id:
                        chain.append(tech_id)
        
        return chain
    
    @staticmethod
    def get_reconnaissance_threats() -> List[str]:
        """Get all reconnaissance techniques (critical for ASM)"""
        all_techniques = ConfigLoader.get_all_mitre_techniques()
        return [t["id"] for t in all_techniques if t.get("tactic_id") == "TA0043"]
    
    @staticmethod
    def get_initial_access_threats() -> List[str]:
        """Get all initial access techniques"""
        all_techniques = ConfigLoader.get_all_mitre_techniques()
        return [t["id"] for t in all_techniques if t.get("tactic_id") == "TA0001"]
    
    @staticmethod
    def get_all_tactics() -> List[Dict]:
        """Get all MITRE tactics"""
        return ConfigLoader.get_all_mitre_tactics()
    
    @staticmethod
    def get_all_techniques() -> List[Dict]:
        """Get all MITRE techniques"""
        return ConfigLoader.get_all_mitre_techniques()
    
    @staticmethod
    def get_tactic(tactic_id: str) -> Dict:
        """Get MITRE tactic by ID"""
        return ConfigLoader.get_mitre_tactic(tactic_id)
    
    @staticmethod
    def get_technique(technique_id: str) -> Dict:
        """Get MITRE technique by ID"""
        return ConfigLoader.get_mitre_technique(technique_id)
