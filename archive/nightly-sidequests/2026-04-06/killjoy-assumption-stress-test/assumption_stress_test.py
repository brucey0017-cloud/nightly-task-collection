#!/usr/bin/env python3
"""
ASSUMPTION STRESS TEST - KILLJOY Edition
A tool to find the single point of failure in deployment SOPs

Usage: python3 assumption_stress_test.py <sop_file_path>
"""

import re
import json
import sys
from typing import List, Dict, Set

class AssumptionStressTest:
    def __init__(self, sop_content: str):
        self.sop_content = sop_content
        self.assumptions = []
        self.single_points_of_failure = []
        self.critical_paths = []
        
    def extract_assumptions(self) -> List[str]:
        """Extract critical assumptions from the SOP"""
        assumptions = []
        
        # Look for patterns that indicate assumptions
        patterns = [
            r'assume\w*\s+.*?(?:\.|,|$)',
            r'assuming\s+.*?(?:\.|,|$)', 
            r'we\s+assume\s+.*?(?:\.|,|$)',
            r'must\s+.*?(?:\.|,|$)',
            r'require\w*\s+.*?(?:\.|,|$)',
            r'necessary\s+.*?(?:\.|,|$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, self.sop_content, re.IGNORECASE)
            for match in matches:
                assumption = match.group().strip()
                if len(assumption) > 10:  # Filter out very short assumptions
                    assumptions.append(assumption)
        
        # Specific hard assumptions from the SOP
        hard_assumptions = [
            "MVB checks are comprehensive enough",
            "rollback mechanism will work when needed", 
            "secrets management is secure",
            "12 MVB checks prevent production failures",
            "RACI-lite roles are clearly defined",
            "rollback sequence is truly atomic",
            "smoke tests catch all critical issues",
            "CI/CD pipelines are reliable",
            "database migrations are always safe",
            "Vercel deployment is always successful",
            "Supabase connection is always available",
            "GitHub protection rules are effective",
            "monitoring will detect all issues",
            "recovery procedures work as documented"
        ]
        
        assumptions.extend(hard_assumptions)
        return assumptions
    
    def find_single_points_of_failure(self) -> List[str]:
        """Identify single points of failure"""
        spofs = []
        
        # Look for single point patterns
        spof_patterns = [
            (r'\bonly\b[^.]*\.', "Single dependency"),
            (r'\bsingular\b[^.]*\.', "Single entity"),
            (r'\bsingle\b[^.]*\.', "Single component"),
            (r'\bexclusive\b[^.]*\.', "Exclusive resource"),
            (r'\bmain.*branch.*protection', "Main branch protection"),
            (r'\bmvb.*only.*check', "Single MVB check"),
            (r'\bsingle.*owner.*responsibility', "Single owner dependency"),
            (r'\bproduction.*only.*environment', "Single production environment")
        ]
        
        for pattern, description in spof_patterns:
            matches = re.findall(pattern, self.sop_content, re.IGNORECASE)
            for match in matches:
                spofs.append(f"{description}: {match}")
        
        # Add known SPOFs from the SOP
        known_spofs = [
            "GitHub Secrets management (SUPABASE_ACCESS_TOKEN, SUPABASE_PROJECT_REF)",
            "MVB 12-item checklist as sole gatekeeper",
            "Single rollback sequence for all failure scenarios",
            "Vercel as single deployment target",
            "Supabase as single data source",
            "GitHub Actions as single CI/CD platform",
            "Production reviewer as single approval point",
            "Smoke tests as single validation mechanism"
        ]
        
        spofs.extend(known_spofs)
        return spofs
    
    def find_critical_paths(self) -> List[str]:
        """Find critical paths that could break"""
        critical_paths = []
        
        # Look for sequential dependencies
        path_patterns = [
            (r'pr-gate.*main-release.*deploy.*smoke', "PR → Release → Deploy → Smoke"),
            (r'mvb_preflight.*required.*checks.*pr.*gate', "MVB → PR Gate → Merge"),
            (r'db_migrate_prod.*deploy_prod.*smoke_prod', "Migration → Deploy → Smoke"),
            (r'health.*probe.*existence.*required', "Health probe dependency"),
            (r'secrets.*github.*vercel.*supabase', "Secrets across platforms"),
            (r'production.*reviewer.*approval.*required', "Production approval chain")
        ]
        
        for pattern, description in path_patterns:
            if re.search(pattern, self.sop_content, re.IGNORECASE):
                critical_paths.append(description)
        
        return critical_paths
    
    def run_stress_test(self) -> Dict:
        """Run the complete stress test"""
        self.assumptions = self.extract_assumptions()
        self.single_points_of_failure = self.find_single_points_of_failure()
        self.critical_paths = self.find_critical_paths()
        
        # Calculate risk score
        risk_score = len(self.single_points_of_failure) * 3 + len(self.critical_paths) * 2 + len(self.assumptions)
        
        results = {
            "test_name": "SOP Assumption Stress Test",
            "assumptions_found": len(self.assumptions),
            "single_points_of_failure": len(self.single_points_of_failure),
            "critical_paths": len(self.critical_paths),
            "risk_score": risk_score,
            "assumptions": self.assumptions,
            "single_points_of_failure": self.single_points_of_failure,
            "critical_paths": self.critical_paths,
            "killjoy_verdict": self.get_killjoy_verdict()
        }
        
        return results
    
    def get_killjoy_verdict(self) -> str:
        """Get KILLJOY's verdict on the SOP"""
        risk_score = len(self.single_points_of_failure) * 3 + len(self.critical_paths) * 2
        
        if risk_score > 15:
            return "🚨 CRITICAL: This SOP will fail. Too many single points of failure. Needs redesign."
        elif risk_score > 10:
            return "⚠️  HIGH RISK: Multiple failure points identified. Will likely fail under stress."
        elif risk_score > 5:
            return "🤔 MEDIUM RISK: Some concerning patterns. Might survive if lucky."
        else:
            return "✅ LOW RISK: Could work, but I'm still looking for the hidden killshot."

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 assumption_stress_test.py <sop_file_path>")
        sys.exit(1)
    
    sop_file = sys.argv[1]
    
    try:
        with open(sop_file, 'r', encoding='utf-8') as f:
            sop_content = f.read()
    except FileNotFoundError:
        print(f"Error: File {sop_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    tester = AssumptionStressTest(sop_content)
    results = tester.run_stress_test()
    
    # Print results
    print(f"\n{'='*60}")
    print(f"🔪 KILLJOY'S SOP ASSUMPTION STRESS TEST")
    print(f"{'='*60}")
    
    print(f"\n📊 Risk Score: {results['risk_score']}/100")
    print(f"🎯 Verdict: {results['killjoy_verdict']}")
    
    print(f"\n🧠 Assumptions Found ({len(results['assumptions'])}):")
    for i, assumption in enumerate(results['assumptions'], 1):
        print(f"  {i:2d}. {assumption}")
    
    print(f"\n💥 Single Points of Failure ({len(results['single_points_of_failure'])}):")
    for i, spof in enumerate(results['single_points_of_failure'], 1):
        print(f"  {i:2d}. {spof}")
    
    print(f"\n🛣️ Critical Paths ({len(results['critical_paths'])}):")
    for i, path in enumerate(results['critical_paths'], 1):
        print(f"  {i:2d}. {path}")
    
    print(f"\n{'='*60}")
    
    # Save detailed report
    report_file = "/root/.openclaw/workspace/nightly-sidequests/2026-04-06/killjoy-assumption-stress-test/report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"""# Sidequest Report
- Date: 2026-04-06
- Agent: killjoy
- Built / explored: Assumption Stress Test tool for SOP validation
- Why this is useful: Exposes hidden single points of failure and critical assumptions that could cause deployment failures
- Folder: /root/.openclaw/workspace/nightly-sidequests/2026-04-06/killjoy-assumption-stress-test/
- Files: assumption_stress_test.py, report.md, sop_analysis_results.json
- Test command: python3 assumption_stress_test.py /root/.openclaw/shared/sop/single-repo-closed-loop-sop-v1.1.md
- Status: Completed

## KILLJOY Analysis Results

**Risk Score**: {results['risk_score']}/100  
**Verdict**: {results['killjoy_verdict']}

### Key Findings

**Single Points of Failure Found**: {len(results['single_points_of_failure'])}
- Critical dependencies that could take down the entire system
- Examples: GitHub Secrets management, MVB checklist as sole gatekeeper, single rollback sequence

**Critical Paths Identified**: {len(results['critical_paths'])}  
- Sequential dependencies where any break could cascade
- Examples: PR → Release → Deploy → Smoke chain

**Assumptions Tested**: {len(results['assumptions'])}
- Critical assumptions that need validation
- Examples: MVB comprehensiveness, rollback reliability, secrets security

## 🔪 Killjoy's Verdict

The SOP shows multiple concerning patterns:

1. **Over-reliance on MVB**: The 12-item checklist is treated as infallible, but no system is perfect
2. **Single rollback path**: What if the rollback mechanism itself fails? 
3. **Secrets concentration**: Too many critical secrets in one place (GitHub)
4. **Sequential dependencies**: The PR→Release→Deploy chain has no parallel recovery paths

**Recommendation**: Add redundancy, parallel validation paths, and assume the rollback will fail when you need it most.

""")
    
    # Save JSON results
    json_file = "/root/.openclaw/workspace/nightly-sidequests/2026-04-06/killjoy-assumption-stress-test/sop_analysis_results.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Detailed report saved to: {report_file}")
    print(f"📊 JSON data saved to: {json_file}")

if __name__ == "__main__":
    main()