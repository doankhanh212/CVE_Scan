"""
NIST Recommendation Engine
Mapping CVE mitigations to NIST R5 controls via CWE keyword matching
"""

import json
import os
from pathlib import Path

class NISTRecommendationEngine:
    def __init__(self, keywords_file=None):
        """
        Initialize the engine with NIST control keywords
        
        Args:
            keywords_file: Path to keywords.json file
        """
        if keywords_file is None:
            # Default path relative to this module
            keywords_file = os.path.join(os.path.dirname(__file__), 'keywords.json')
        
        self.keywords_file = keywords_file
        self.rules = self._load_rules()
    
    def _load_rules(self):
        """Load NIST control rules from JSON file"""
        try:
            with open(self.keywords_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Warning: keywords.json not found at {self.keywords_file}")
            return {}
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON in {self.keywords_file}")
            return {}
    
    def get_recommendations(self, mitigation_text, cwe_ids=None):
        """
        Get NIST control recommendations based on mitigation text
        
        Args:
            mitigation_text (str): CVE mitigation or description text
            cwe_ids (list): Optional list of CWE IDs for additional context
            
        Returns:
            list: List of dicts with NIST control recommendations
        """
        if not mitigation_text:
            return []
        
        text = mitigation_text.lower()
        aggregated_results = {}
        
        # Match based on keywords in mitigation text
        for control_id, info in self.rules.items():
            keywords = info.get('keywords', [])
            if any(kw.lower() in text for kw in keywords):
                if control_id not in aggregated_results:
                    aggregated_results[control_id] = {
                        'control_id': control_id,
                        'group': info.get('group', ''),
                        'control_name': info.get('control_name', ''),
                        'action': info.get('action', ''),
                        'iso_27001': info.get('iso_27001', ''),
                        'type': info.get('type', ''),  # Preventive, Detective, Corrective
                        'matched_keywords': [kw for kw in keywords if kw.lower() in text]
                    }
        
        # Sort by type: Preventive → Detective → Corrective
        type_priority = {'Preventive': 0, 'Detective': 1, 'Corrective': 2}
        sorted_results = sorted(
            aggregated_results.values(),
            key=lambda x: type_priority.get(x.get('type', ''), 99)
        )
        
        return sorted_results
    
    def get_recommendations_for_cve(self, cve_data):
        """
        Get recommendations from full CVE data
        
        Args:
            cve_data (dict): CVE data with 'description' and optionally 'mitigation', 'cwe_ids'
            
        Returns:
            list: List of NIST control recommendations
        """
        # Combine all relevant text for keyword matching
        text_parts = []
        
        if 'description' in cve_data:
            text_parts.append(str(cve_data.get('description', '')))
        
        if 'mitigation' in cve_data:
            text_parts.append(str(cve_data.get('mitigation', '')))
        
        if 'cwe_ids' in cve_data and cve_data['cwe_ids']:
            # CWE IDs могут быть в рекомендациях
            text_parts.append(' '.join(str(cwe_id) for cwe_id in cve_data['cwe_ids']))
        
        combined_text = ' '.join(text_parts)
        return self.get_recommendations(combined_text)
    
    def get_nist_control(self, control_id):
        """Get a specific NIST control details"""
        if control_id in self.rules:
            info = self.rules[control_id]
            return {
                'control_id': control_id,
                'group': info.get('group', ''),
                'control_name': info.get('control_name', ''),
                'action': info.get('action', ''),
                'iso_27001': info.get('iso_27001', ''),
                'type': info.get('type', ''),
                'keywords': info.get('keywords', [])
            }
        return None
    
    def get_all_controls(self):
        """Get all available NIST controls"""
        result = []
        for control_id, info in self.rules.items():
            result.append({
                'control_id': control_id,
                'group': info.get('group', ''),
                'control_name': info.get('control_name', ''),
                'action': info.get('action', ''),
                'iso_27001': info.get('iso_27001', ''),
                'type': info.get('type', '')
            })
        return result


# Singleton instance
_engine_instance = None

def get_engine():
    """Get or create the NIST recommendation engine instance"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NISTRecommendationEngine()
    return _engine_instance
