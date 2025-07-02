#!/usr/bin/env python3
"""
Test script to verify JSON format compatibility between iam-check.py and remediation.py
"""

import json
import sys
from pathlib import Path

def verify_json_structure(json_file):
    """Verify the JSON structure matches expected format"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Check required top-level fields
    required_fields = [
        'account_id', 'analysis_date', 'security_score',
        'total_findings', 'findings', 'recommendations'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ Missing required fields: {', '.join(missing_fields)}")
        return False
    
    print("✅ All required top-level fields present")
    
    # Check findings structure
    if isinstance(data['findings'], list) and len(data['findings']) > 0:
        finding = data['findings'][0]
        finding_fields = [
            'finding_id', 'title', 'description', 'severity',
            'resource', 'recommendation', 'risk'
        ]
        
        missing_finding_fields = []
        for field in finding_fields:
            if field not in finding:
                missing_finding_fields.append(field)
        
        if missing_finding_fields:
            print(f"❌ Finding missing fields: {', '.join(missing_finding_fields)}")
            return False
        
        print("✅ Finding structure is correct")
    
    # Check recommendations structure
    if isinstance(data['recommendations'], list) and len(data['recommendations']) > 0:
        rec = data['recommendations'][0]
        rec_fields = [
            'recommendation_id', 'title', 'description', 'severity',
            'category', 'impact', 'effort', 'related_findings',
            'remediation_steps'
        ]
        
        missing_rec_fields = []
        for field in rec_fields:
            if field not in rec:
                missing_rec_fields.append(field)
        
        if missing_rec_fields:
            print(f"❌ Recommendation missing fields: {', '.join(missing_rec_fields)}")
            return False
        
        print("✅ Recommendation structure is correct")
        
        # Check remediation steps
        if 'remediation_steps' in rec and len(rec['remediation_steps']) > 0:
            step = rec['remediation_steps'][0]
            step_fields = [
                'step_number', 'description', 'commands',
                'prerequisites', 'automation_safe'
            ]
            
            missing_step_fields = []
            for field in step_fields:
                if field not in step:
                    missing_step_fields.append(field)
            
            if missing_step_fields:
                print(f"⚠️  Remediation step missing optional fields: {', '.join(missing_step_fields)}")
            else:
                print("✅ Remediation step structure is complete")
    
    # Check execution plan
    if 'execution_plan' in data:
        print("✅ Execution plan present")
        priorities = ['critical', 'high', 'medium', 'low']
        for priority in priorities:
            if priority in data['execution_plan']:
                print(f"  - {priority}: {len(data['execution_plan'][priority])} items")
    
    return True

def test_remediation_compatibility(json_file):
    """Test if remediation.py can process the JSON file"""
    
    print("\n🔍 Testing remediation.py compatibility...")
    
    try:
        # Import the remediation module
        sys.path.insert(0, str(Path(__file__).parent))
        from remediation import IAMRemediator
        
        remediator = IAMRemediator(dry_run=True)
        data = remediator.load_findings(json_file)
        
        print(f"✅ Successfully loaded {len(data.get('findings', []))} findings")
        
        # Test finding processing
        findings = data.get('findings', [])
        recommendations = data.get('recommendations', [])
        
        if findings:
            finding = findings[0]
            related_rec = remediator.find_related_recommendation(finding, recommendations)
            if related_rec:
                print(f"✅ Found related recommendation: {related_rec['title']}")
            
            # Check if remediation method exists
            finding_id = finding['finding_id']
            can_remediate = False
            for pattern in remediator.remediation_methods.keys():
                if finding_id.startswith(pattern):
                    can_remediate = True
                    print(f"✅ Remediation method available for {finding_id}")
                    break
            
            if not can_remediate:
                print(f"ℹ️  No specific remediation method for {finding_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing remediation compatibility: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_json_sync.py <findings.json>")
        print("\nThis script verifies JSON format compatibility between iam-check.py and remediation.py")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    if not Path(json_file).exists():
        print(f"Error: File '{json_file}' not found")
        print("\nGenerate a findings file first:")
        print("  python iam-check.py --json --format pretty --output findings.json")
        sys.exit(1)
    
    print(f"📋 Verifying JSON structure in {json_file}")
    print("=" * 60)
    
    # Verify JSON structure
    if verify_json_structure(json_file):
        print("\n✅ JSON structure verification passed")
    else:
        print("\n❌ JSON structure verification failed")
        sys.exit(1)
    
    # Test remediation compatibility
    if test_remediation_compatibility(json_file):
        print("\n✅ Remediation compatibility test passed")
    else:
        print("\n❌ Remediation compatibility test failed")
        sys.exit(1)
    
    print("\n✅ All tests passed! The JSON format is properly synchronized.")

if __name__ == "__main__":
    main()