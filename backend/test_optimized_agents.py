#!/usr/bin/env python3
"""
Test script for optimized agents - verify they work correctly and are faster
"""

import asyncio
from datetime import datetime
from agents.rca_agent import rca_agent
from agents.patch_generator import patch_generator
from models import TraceStep, FailureDetail

async def test_optimized_agents():
    """Test that optimized agents work correctly and are faster"""
    
    print("🧪 Testing Optimized Agents...")
    
    # Test RCA Agent
    print("\n🔍 Testing RCA Agent...")
    test_step = TraceStep(
        trace_id='test-optimized-123',
        step='CheckReturnEligibility',
        input={'sku': 'SKU-1001'},
        output={},
        schema_ok=False,
        failure=FailureDetail(
            type='SchemaMismatch',
            field='return_policy',
            message='return_policy field is missing'
        ),
        latency_ms=100,
        timestamp=datetime.now()
    )
    
    try:
        start_time = datetime.now()
        rca_result = await rca_agent.analyze_failure(test_step, trace_id='test-123')
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        print(f"✅ RCA completed in {processing_time:.2f} seconds")
        print(f"✅ Root Cause: {rca_result.cause}")
        print(f"✅ Playbook: {rca_result.playbook}")
        print(f"✅ Confidence: {rca_result.confidence}")
        
        if processing_time < 5.0:  # Should be much faster now
            print("🚀 RCA Agent is now FAST!")
        else:
            print("⚠️ RCA Agent still slow - needs more optimization")
            
    except Exception as e:
        print(f"❌ RCA Agent error: {e}")
    
    # Test Patch Generator
    print("\n🔧 Testing Patch Generator...")
    try:
        # Simulate a simple patch spec
        patch_spec = {
            "type": "add_field",
            "file": "config.py",
            "change": "Add 'return_policy' to POLICY_FIELDS"
        }
        
        original_code = 'POLICY_FIELDS = ["price", "inventory", "category"]'
        
        start_time = datetime.now()
        update_snippet = patch_generator._create_update_snippet(patch_spec, original_code)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        print(f"✅ Update snippet created in {processing_time:.3f} seconds")
        print(f"✅ Snippet: {update_snippet[:100]}...")
        
        if processing_time < 0.1:  # Should be very fast
            print("🚀 Patch Generator is now FAST!")
        else:
            print("⚠️ Patch Generator still slow - needs more optimization")
            
    except Exception as e:
        print(f"❌ Patch Generator error: {e}")
    
    print("\n🎯 Optimization Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_optimized_agents()) 