"""
Configuration Loader for Security Standards
Loads JSON config files and caches them for performance
"""

import json
import os
from typing import Dict, List, Any
from pathlib import Path

class ConfigLoader:
    """Loads and caches security standards configuration from JSON files"""
    
    _cache = {}
    CONFIG_DIR = Path(__file__).parent.parent / "config"
    
    @classmethod
    def load_owasp_mapping(cls) -> Dict[str, Any]:
        """Load OWASP Top 10 2021 mapping"""
        if "owasp" not in cls._cache:
            file_path = cls.CONFIG_DIR / "owasp_top10_2021.json"
            cls._cache["owasp"] = cls._load_json(file_path)
        return cls._cache["owasp"]
    
    @classmethod
    def load_mitre_attack(cls) -> Dict[str, Any]:
        """Load MITRE ATT&CK Enterprise mapping"""
        if "mitre" not in cls._cache:
            file_path = cls.CONFIG_DIR / "mitre_attack_enterprise.json"
            cls._cache["mitre"] = cls._load_json(file_path)
        return cls._cache["mitre"]
    
    @classmethod
    def load_cwe_mapping(cls) -> Dict[str, Any]:
        """Load CWE to OWASP/MITRE mappings"""
        if "cwe" not in cls._cache:
            file_path = cls.CONFIG_DIR / "cwe_mapping.json"
            cls._cache["cwe"] = cls._load_json(file_path)
        return cls._cache["cwe"]
    
    @classmethod
    def load_scp_practices(cls) -> Dict[str, Any]:
        """Load Secure Coding Practices"""
        if "scp" not in cls._cache:
            file_path = cls.CONFIG_DIR / "scp_practices.json"
            cls._cache["scp"] = cls._load_json(file_path)
        return cls._cache["scp"]
    
    @classmethod
    def _load_json(cls, file_path: Path) -> Dict[str, Any]:
        """Load JSON file and return as dict"""
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"Config file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"[ConfigLoader] Loaded {file_path.name}")
            return data
        except Exception as e:
            print(f"[ConfigLoader] Error loading {file_path}: {e}")
            return {}
    
    @classmethod
    def clear_cache(cls):
        """Clear cached configurations (useful for testing)"""
        cls._cache.clear()
    
    # ===== Helper Methods for Mappers =====
    
    @classmethod
    def get_owasp_by_code(cls, code: str) -> Dict[str, Any]:
        """Get OWASP category by code (e.g., 'A01:2021')"""
        owasp_data = cls.load_owasp_mapping()
        for category in owasp_data.get("categories", []):
            if category["code"] == code:
                return category
        return {}
    
    @classmethod
    def get_mitre_tactic(cls, tactic_id: str) -> Dict[str, Any]:
        """Get MITRE tactic by ID (e.g., 'TA0043')"""
        mitre_data = cls.load_mitre_attack()
        for tactic in mitre_data.get("tactics", []):
            if tactic["id"] == tactic_id:
                return tactic
        return {}
    
    @classmethod
    def get_mitre_technique(cls, technique_id: str) -> Dict[str, Any]:
        """Get MITRE technique by ID (e.g., 'T1190')"""
        mitre_data = cls.load_mitre_attack()
        for technique in mitre_data.get("techniques", []):
            if technique["id"] == technique_id:
                return technique
        return {}
    
    @classmethod
    def get_cwe_mapping(cls, cwe_id: int) -> Dict[str, Any]:
        """Get CWE mapping including OWASP and MITRE"""
        cwe_data = cls.load_cwe_mapping()
        for mapping in cwe_data.get("mappings", []):
            if mapping["cwe_id"] == cwe_id:
                return mapping
        return {
            "cwe_id": cwe_id,
            "owasp_codes": [],
            "mitre_techniques": [],
            "severity": "MEDIUM"
        }
    
    @classmethod
    def get_scp_by_cwe(cls, cwe_id: int) -> List[Dict[str, Any]]:
        """Get SCP practices related to CWE"""
        scp_data = cls.load_scp_practices()
        practices = []
        
        for practice in scp_data.get("practices", []):
            if cwe_id in practice.get("related_cwe", []):
                practices.append(practice)
        
        return practices
    
    @classmethod
    def get_all_owasp_codes(cls) -> List[str]:
        """Get all OWASP category codes"""
        owasp_data = cls.load_owasp_mapping()
        return [cat["code"] for cat in owasp_data.get("categories", [])]
    
    @classmethod
    def get_all_mitre_tactics(cls) -> List[Dict[str, Any]]:
        """Get all MITRE tactics"""
        mitre_data = cls.load_mitre_attack()
        return mitre_data.get("tactics", [])
    
    @classmethod
    def get_all_mitre_techniques(cls) -> List[Dict[str, Any]]:
        """Get all MITRE techniques"""
        mitre_data = cls.load_mitre_attack()
        return mitre_data.get("techniques", [])
