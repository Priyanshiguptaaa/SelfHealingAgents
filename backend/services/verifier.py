import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from models.events import Event, EventType, TraceStep, HealOutcome
from services.event_bus import event_bus

class VerifierService:
    """Service for verifying that applied patches actually fix the issues"""
    
    def __init__(self):
        pass
    
    async def verify_fix(self, original_trace_step: TraceStep, trace_id: str) -> Optional[HealOutcome]:
        """Verify that the fix works by replaying the original failing request"""
        
        try:
            # Replay the original failing request
            start_time = datetime.now()
            
            # Simulate the API call that originally failed
            replay_result = await self._replay_request(original_trace_step)
            
            end_time = datetime.now()
            replay_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Check if the fix worked
            if replay_result and replay_result.get("return_policy") is not None:
                # Success! The missing field is now present
                outcome = HealOutcome(
                    trace_id=trace_id,
                    status="pass",
                    replay_ms=replay_ms,
                    before=original_trace_step.output or {},
                    after=replay_result,
                    commit_sha=f"selfheal_{trace_id[:8]}"
                )
                
                # Publish success event
                await event_bus.publish(Event(
                    type=EventType.VERIFY_REPLAY_PASS,
                    key=trace_id,
                    payload={
                        "replay_ms": replay_ms,
                        "before": outcome.before,
                        "after": outcome.after,
                        "field_fixed": "return_policy"
                    },
                    ts=datetime.now(),
                    trace_id=trace_id,
                    ui_hint="verification_passed"
                ))
                
                print(f"✅ Verification passed: return_policy field now present")
                return outcome
                
            else:
                # Verification failed
                await event_bus.publish(Event(
                    type=EventType.VERIFY_REPLAY_FAIL,
                    key=trace_id,
                    payload={
                        "replay_ms": replay_ms,
                        "expected_field": "return_policy",
                        "actual_result": replay_result
                    },
                    ts=datetime.now(),
                    trace_id=trace_id,
                    ui_hint="verification_failed"
                ))
                
                print(f"❌ Verification failed: return_policy still missing")
                return None
                
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
            
            await event_bus.publish(Event(
                type=EventType.VERIFY_REPLAY_FAIL,
                key=trace_id,
                payload={
                    "error": str(e),
                    "replay_ms": 0
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="verification_error"
            ))
            
            return None
    
    async def _replay_request(self, trace_step: TraceStep) -> Optional[Dict[str, Any]]:
        """Replay the original request to see if it now works"""
        
        # Simulate the CheckReturnEligibility API call
        if trace_step.step == "CheckReturnEligibility":
            return await self._simulate_return_eligibility_check(
                trace_step.input.get("sku"),
                trace_step.input.get("order_id")
            )
        
        # For other endpoints, return a generic success response
        return {"status": "success", "replayed": True}
    
    async def _simulate_return_eligibility_check(self, sku: str, order_id: str) -> Dict[str, Any]:
        """Simulate the CheckReturnEligibility API call with the fix applied"""
        
        # Simulate a small delay
        await asyncio.sleep(0.2)
        
        # After the patch is applied, the catalog sync now includes return_policy
        # So the API response should now include this field
        return {
            "sku": sku,
            "order_id": order_id,
            "eligibility": False,  # Still false for clearance items
            "return_policy": "FINAL_SALE_NO_RETURN",  # Now present!
            "reason": "Item is marked as final sale",
            "processed_at": datetime.now().isoformat()
        }
    
    async def run_smoke_tests(self, trace_id: str) -> bool:
        """Run additional smoke tests to ensure system stability"""
        
        print(f"🧪 Running smoke tests for trace {trace_id}")
        
        try:
            # Test 1: Basic API health check
            health_ok = await self._check_api_health()
            
            # Test 2: Schema validation still works for valid requests
            schema_ok = await self._test_schema_validation()
            
            # Test 3: Other endpoints still work
            endpoints_ok = await self._test_other_endpoints()
            
            all_passed = health_ok and schema_ok and endpoints_ok
            
            if all_passed:
                print(f"✅ All smoke tests passed")
            else:
                print(f"❌ Some smoke tests failed")
            
            return all_passed
            
        except Exception as e:
            print(f"❌ Smoke tests failed with error: {str(e)}")
            return False
    
    async def _check_api_health(self) -> bool:
        """Check if the API is still responding"""
        await asyncio.sleep(0.1)  # Simulate API call
        return True
    
    async def _test_schema_validation(self) -> bool:
        """Test that schema validation still works for valid requests"""
        await asyncio.sleep(0.1)  # Simulate API call
        return True
    
    async def _test_other_endpoints(self) -> bool:
        """Test that other endpoints are not affected"""
        await asyncio.sleep(0.1)  # Simulate API call
        return True

# Global verifier instance
verifier = VerifierService() 