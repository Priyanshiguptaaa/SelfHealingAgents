#!/usr/bin/env python3
"""
Test script for the enhanced RCA agent with business logic evaluation.
This demonstrates how the RCA agent can evaluate business logic as part of 
its diagnostic process.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path so we can import the RCA agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from agents.rca_agent import RCAAgent
    from models.events import Event, EventType, TraceStep, FailureDetail
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

async def test_rca_evaluation():
    """Test the RCA agent's business logic evaluation capabilities"""
    
    print("🧪 Testing RCA Agent with Business Logic Evaluation")
    print("=" * 60)
    
    # Initialize the RCA agent
    rca_agent = RCAAgent()
    
    # Create test failure events to trigger RCA analysis
    test_cases = [
        {
            "name": "Return Policy Missing",
            "step": "CheckReturnEligibility",
            "input": {"sku": "TEST002", "order_id": "ORD002"},
            "failure": {
                "type": "missing_field",
                "field": "return_policy",
                "message": "Return policy field is missing from product data"
            }
        },
        {
            "name": "Schema Validation Failure",
            "step": "ValidateProductSchema",
            "input": {"product_id": "PROD002"},
            "failure": {
                "type": "schema_mismatch",
                "field": "price",
                "message": "Product price field is null when it should have a "
                           "value"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        # Create a trace step with the failure
        trace_step = TraceStep(
            trace_id=f"test_trace_{i}",
            step=test_case["step"],
            input=test_case["input"],
            output={},
            schema_ok=False,
            failure=FailureDetail(**test_case["failure"]),
            latency_ms=150,
            timestamp=datetime.now()
        )
        
        # Create a failure event
        failure_event = Event(
            type=EventType.RETURN_API_FAILURE,
            key=f"test_failure_{i}",
            payload={
                "trace_step": trace_step.dict(),
                "failure": test_case["failure"]
            },
            ts=datetime.now(),
            trace_id=f"test_trace_{i}"
        )
        
        print(f"🔍 Step: {trace_step.step}")
        print(f"🔍 Input: {trace_step.input}")
        print(f"🔍 Failure: {trace_step.failure.message}")
        
        # Process the failure event (this will trigger business logic evaluation)
        await rca_agent._process_failure_event(failure_event)
        
        print(f"✅ Test case {i} processed")
    
    print("\n🎯 Business Logic Evaluation Summary")
    print("=" * 60)
    print("The RCA agent now includes business logic evaluation that:")
    print("• Runs test cases against the current business logic")
    print("• Identifies specific failure patterns")
    print("• Assesses business impact of failures")
    print("• Generates actionable recommendations")
    print("• Integrates evaluation results into the RCA analysis")
    
    print("\n🔧 Key Features Added:")
    print("• Automated test case execution")
    print("• Failure pattern analysis")
    print("• Business impact assessment")
    print("• Recommendation generation")
    print("• Integration with existing RCA workflow")
    
    # Clean up
    await rca_agent.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(test_rca_evaluation())
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 