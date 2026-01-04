"""
Unified Security Standards Mapper
Combines OWASP, MITRE ATT&CK, and Secure Coding Practices
"""

from typing import Dict, List, Any
from web.security_standards.owasp_mapping import OWASPMapper
from web.security_standards.mitre_attack_mapping import MITREMapper
from web.security_standards.secure_coding_mapper import SecureCodeMapper


class UnifiedSecurityMapper:
    """Unified framework mapping CVE findings to security standards"""
    
    @staticmethod
    def analyze_cve(
        cve_id: str,
        cwe_ids: List[int] = None,
        description: str = "",
        severity: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of CVE against all security standards
        """
        if not cwe_ids:
            cwe_ids = []
        
        # Map to OWASP
        owasp_result = OWASPMapper.get_by_cve_id(cve_id, cwe_ids)
        
        # Map to MITRE ATT&CK
        mitre_result = MITREMapper.get_by_cve(cve_id, cwe_ids)
        
        # Map to Secure Coding Practices
        scp_result = SecureCodeMapper.get_by_cve(cve_id, cwe_ids)
        
        # Calculate overall risk score
        risk_score = UnifiedSecurityMapper._calculate_risk_score(
            owasp_result,
            mitre_result,
            scp_result,
            severity
        )
        
        return {
            "cve_id": cve_id,
            "cwe_ids": cwe_ids,
            "severity": severity,
            "risk_score": risk_score,
            
            # OWASP Mapping
            "owasp": {
                "mappings": owasp_result.get("owasp_mappings", []),
                "primary": owasp_result.get("primary_owasp"),
                "coverage": owasp_result.get("coverage")
            },
            
            # MITRE Mapping
            "mitre_attack": {
                "techniques": mitre_result.get("techniques", []),
                "tactics": mitre_result.get("tactics", []),
                "attack_chain": mitre_result.get("attack_chain", [])
            },
            
            # Secure Coding Practices
            "secure_coding": {
                "practices": scp_result.get("practices", []),
                "categories": scp_result.get("categories", []),
                "critical_count": scp_result.get("critical_count", 0),
                "high_count": scp_result.get("high_count", 0)
            },
            
            # Attack context
            "attack_context": UnifiedSecurityMapper._build_attack_context(mitre_result),
            
            # Recommendations
            "recommendations": UnifiedSecurityMapper._generate_recommendations(
                owasp_result,
                mitre_result,
                scp_result
            )
        }
    
    @staticmethod
    def analyze_multiple_cves(
        findings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze multiple CVE findings and provide aggregate insights
        """
        analyses = []
        owasp_counts = {}
        mitre_tactics = {}
        critical_practices = []
        
        for finding in findings:
            analysis = UnifiedSecurityMapper.analyze_cve(
                cve_id=finding.get("id", finding.get("cve_id")),
                cwe_ids=finding.get("cwe_ids", []),
                description=finding.get("description", ""),
                severity=finding.get("severity", "MEDIUM")
            )
            analyses.append(analysis)
            
            # Aggregate OWASP
            for owasp in analysis["owasp"]["mappings"]:
                code = owasp["owasp_code"]
                owasp_counts[code] = owasp_counts.get(code, 0) + 1
            
            # Aggregate MITRE tactics
            for tactic in analysis["mitre_attack"]["tactics"]:
                mitre_tactics[tactic] = mitre_tactics.get(tactic, 0) + 1
            
            # Collect critical practices
            for practice in analysis["secure_coding"]["practices"]:
                if practice["severity"] == "CRITICAL":
                    critical_practices.append(practice)
        
        return {
            "total_findings": len(findings),
            "analyses": analyses,
            
            # Aggregate stats
            "aggregate_stats": {
                "owasp_top_risks": sorted(
                    [(k, v) for k, v in owasp_counts.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:3],
                "mitre_tactics": sorted(
                    [(k, v) for k, v in mitre_tactics.items()],
                    key=lambda x: x[1],
                    reverse=True
                ),
                "critical_practices_count": len(set(p["practice_id"] for p in critical_practices))
            },
            
            # Risk summary
            "risk_summary": {
                "average_risk_score": sum(a["risk_score"] for a in analyses) / len(analyses) if analyses else 0,
                "high_risk_count": sum(1 for a in analyses if a["risk_score"] >= 7.0),
                "critical_risk_count": sum(1 for a in analyses if a["risk_score"] >= 8.5)
            }
        }
    
    @staticmethod
    def _calculate_risk_score(
        owasp_result: Dict,
        mitre_result: Dict,
        scp_result: Dict,
        severity: str
    ) -> float:
        """
        Calculate comprehensive risk score (0-10)
        Factors:
        - OWASP risk weight (4)
        - MITRE ATT&CK presence (2)
        - Secure coding violations (2)
        - CVSS severity (2)
        """
        score = 0.0
        
        # OWASP component (40%)
        if owasp_result.get("primary_owasp"):
            # primary_owasp is a string code (e.g., "A01:2021")
            owasp_code = owasp_result["primary_owasp"]
            # Get the category data from ConfigLoader
            from web.config_loader import ConfigLoader
            category = ConfigLoader.get_owasp_by_code(owasp_code)
            owasp_weight = category.get("risk_weight", 5.0) if category else 5.0
            score += (owasp_weight / 10.0) * 4
        
        # MITRE ATT&CK component (20%)
        technique_count = len(mitre_result.get("techniques", []))
        if technique_count > 0:
            score += min(2.0, technique_count * 0.5)
        
        # Secure Coding component (20%)
        critical_count = scp_result.get("critical_count", 0)
        high_count = scp_result.get("high_count", 0)
        score += min(2.0, critical_count * 0.8 + high_count * 0.4)
        
        # CVSS Severity component (20%)
        severity_map = {
            "CRITICAL": 2.0,
            "HIGH": 1.6,
            "MEDIUM": 1.2,
            "LOW": 0.8,
            "INFO": 0.4
        }
        score += severity_map.get(severity, 1.0)
        
        return round(min(10.0, score), 2)
    
    @staticmethod
    def _build_attack_context(mitre_result: Dict) -> Dict[str, Any]:
        """Build attack context from MITRE techniques"""
        techniques = mitre_result.get("techniques", [])
        
        return {
            "phases": [t.get("tactic_name") for t in techniques],
            "techniques_chain": mitre_result.get("attack_chain", []),
            "primary_attack_phase": techniques[0].get("tactic_name") if techniques else None,
            "attack_complexity": "Low" if len(techniques) <= 2 else "Medium" if len(techniques) <= 4 else "High"
        }
    
    @staticmethod
    def _generate_recommendations(
        owasp_result: Dict,
        mitre_result: Dict,
        scp_result: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # OWASP recommendations
        if owasp_result.get("primary_owasp"):
            primary_code = owasp_result["primary_owasp"]
            # primary is a string code, get full data from ConfigLoader
            from web.config_loader import ConfigLoader
            category = ConfigLoader.get_owasp_by_code(primary_code)
            if category:
                recommendations.append(
                    f"Address {category.get('name', 'OWASP vulnerability')} - "
                    f"Implement controls for {primary_code}"
                )
        
        # MITRE recommendations
        if mitre_result.get("tactics"):
            tactics = [t for t in mitre_result["techniques"]]
            if tactics:
                recommendations.append(
                    f"Implement detections for {tactics[0].get('tactic_name')} phase"
                )
        
        # Secure coding recommendations
        critical = scp_result.get("practices", [])
        if critical:
            top_practice = critical[0]
            recommendations.append(
                f"Implement {top_practice.get('practice')} practice - {top_practice.get('remediation')}"
            )
        
        return recommendations
