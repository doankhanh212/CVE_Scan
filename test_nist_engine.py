#!/usr/bin/env python
# Test NIST recommendation engine

from modules.nist_recommendation import get_engine

engine = get_engine()

# Test with mitigation text from CWE
test_text = "If a function returns an error, it is important to either fix the problem and try again, alert the user that an error has happened and let the program continue, or alert the user and dose and cleanup the program."

print("\n" + "="*80)
print("NIST RECOMMENDATION ENGINE TEST")
print("="*80)
print(f"\nInput text: {test_text[:100]}...\n")

recommendations = engine.get_recommendations(test_text)

print(f"Found {len(recommendations)} recommendations:\n")
for rec in recommendations:
    print(f"  [{rec['control_id']}] {rec['control_name']}")
    print(f"      Group: {rec['group']}")
    print(f"      Type: {rec['type']}")
    print(f"      Action: {rec['action']}\n")

print("="*80)
