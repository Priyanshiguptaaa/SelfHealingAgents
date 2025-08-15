#!/usr/bin/env python3
"""Test script to demonstrate MorphAI editing catalog_sync.py"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from agents.patch_generator import patch_generator
from models import RCAPlan

async def test_morph_editing():
    """Test MorphAI editing the catalog_sync.py file"""
    
    print("🧪 TESTING MORPHAI CODE EDITING")
    print("=" * 60)
    
    # Read the original code
    with open('demo_user_code/services/catalog_sync.py', 'r') as f:
        original_code = f.read()
    
    print("📝 ORIGINAL CODE (catalog_sync.py):")
    print("-" * 40)
    print(original_code)
    print("-" * 40)
    
    # Create a test RCA plan
    test_plan = RCAPlan(
        playbook="OutOfDateCatalogPolicy",
        cause="Schema validation failure - missing return_policy field",
        patch_spec={
            "file": "services/catalog_sync.py",
            "type": "add_field",
            "change": "+ 'return_policy'",
            "operation": "add_to_list",
            "line_number": 6,
            "anchor": "POLICY_FIELDS"
        },
        risk_score=0.15,
        confidence=0.95
    )
    
    print(f"\n🔧 RCA PLAN:")
    print(f"- Playbook: {test_plan.playbook}")
    print(f"- Cause: {test_plan.cause}")
    print(f"- Patch Spec: {test_plan.patch_spec}")
    print(f"- Risk Score: {test_plan.risk_score}")
    print(f"- Confidence: {test_plan.confidence}")
    
    print("\n🚀 CALLING MORPHAI TO EDIT THE CODE...")
    print("=" * 60)
    
    # Generate the patch using MorphAI
    machine_diff = await patch_generator.generate_patch(
        test_plan, 
        original_code, 
        "test-trace-001"
    )
    
    if machine_diff:
        print("\n✅ MORPHAI SUCCESSFULLY EDITED THE CODE!")
        print("=" * 60)
        
        print(f"📁 File: {machine_diff.file}")
        print(f"🔢 Lines changed: {machine_diff.loc_changed}")
        
        print("\n📝 UPDATED CODE:")
        print("-" * 40)
        print(machine_diff.updated_content)
        print("-" * 40)
        
        print("\n🔍 DIFF (What Changed):")
        print("-" * 40)
        for line in machine_diff.diff_lines:
            if line.startswith('+') or line.startswith('-'):
                print(line.rstrip())
        print("-" * 40)
        
        # Verify the change was made
        if "return_policy" in machine_diff.updated_content:
            print("\n✅ SUCCESS: return_policy field was added to POLICY_FIELDS!")
        else:
            print("\n❌ FAILURE: return_policy field was NOT added")
            
    else:
        print("\n❌ MORPHAI FAILED TO EDIT THE CODE")
    
    # Clean up
    await patch_generator.client.aclose()

if __name__ == "__main__":
    asyncio.run(test_morph_editing()) 