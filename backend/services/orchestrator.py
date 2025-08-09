import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from models.events import Event, EventType, TraceStep, HealOutcome
from services.event_bus import event_bus
from agents.rca_agent import rca_agent
from agents.patch_generator import patch_generator
from services.guardrails import guardrails
from services.patch_applier import patch_applier
from services.verifier import verifier

class HealingOrchestrator:
    """Main orchestrator for the autonomous healing process"""
    
    def __init__(self):
        self.active_healings = {}
        self.running = False
    
    async def start(self):
        """Start the orchestrator and begin processing events"""
        self.running = True
        print("🤖 Healing Orchestrator started")
        
        # Subscribe to failure events that trigger healing
        failure_events = [
            EventType.RETURN_API_FAILURE,
            EventType.SCHEMA_MISMATCH
        ]
        
        async for event in event_bus.subscribe(failure_events):
            if not self.running:
                break
                
            # Start healing process for this failure
            asyncio.create_task(self._handle_failure_event(event))
    
    async def stop(self):
        """Stop the orchestrator"""
        self.running = False
        print("🛑 Healing Orchestrator stopped")
    
    async def _handle_failure_event(self, event: Event):
        """Handle a failure event and orchestrate the healing process"""
        trace_id = event.trace_id or str(uuid.uuid4())
        
        if trace_id in self.active_healings:
            print(f"⚠️ Healing already in progress for trace {trace_id}")
            return
        
        print(f"🚨 Starting healing for trace {trace_id}")
        self.active_healings[trace_id] = {
            "start_time": datetime.now(),
            "status": "analyzing"
        }
        
        try:
            # Publish trace start event
            await event_bus.publish(Event(
                type=EventType.TRACE_START,
                key=trace_id,
                payload={
                    "failing_step": event.payload.get("endpoint", "unknown"),
                    "error_type": event.payload.get("detail", "unknown")
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="healing_started"
            ))
            
            # Step 1: Create trace step from event
            trace_step = self._create_trace_step_from_event(event, trace_id)
            
            # Step 2: RCA Analysis
            plan = await rca_agent.analyze_failure(trace_step)
            if not plan:
                await self._complete_healing(trace_id, "failed", "No RCA plan generated")
                return
            
            # Step 3: Load original code
            original_code = await self._load_original_code(plan.patch_spec.get("file"))
            if not original_code:
                await self._complete_healing(trace_id, "failed", "Could not load original code")
                return
            
            # Step 4: Generate patch
            machine_diff = await patch_generator.generate_patch(plan, original_code, trace_id)
            if not machine_diff:
                await self._complete_healing(trace_id, "failed", "Patch generation failed")
                return
            
            # Step 5: Guardrails validation
            guardrail_checks = await guardrails.validate_patch(machine_diff)
            if not guardrails.is_patch_safe(guardrail_checks):
                await self._complete_healing(trace_id, "failed", "Patch failed guardrails")
                return
            
            # Step 6: Apply patch
            success = await patch_applier.apply_patch(machine_diff, trace_id)
            if not success:
                await self._complete_healing(trace_id, "failed", "Patch application failed")
                return
            
            # Step 7: Verify the fix
            outcome = await verifier.verify_fix(trace_step, trace_id)
            if not outcome or outcome.status != "pass":
                # Rollback and fail
                await patch_applier.rollback_patch(machine_diff.file, trace_id)
                await self._complete_healing(trace_id, "failed", "Verification failed")
                return
            
            # Step 8: Success!
            await self._complete_healing(trace_id, "pass", "Healing completed successfully", outcome)
            
        except Exception as e:
            print(f"❌ Healing failed for trace {trace_id}: {str(e)}")
            await self._complete_healing(trace_id, "failed", f"Unexpected error: {str(e)}")
        
        finally:
            # Clean up
            if trace_id in self.active_healings:
                del self.active_healings[trace_id]
    
    def _create_trace_step_from_event(self, event: Event, trace_id: str) -> TraceStep:
        """Convert event to TraceStep for RCA analysis"""
        
        # Extract details from the event payload
        payload = event.payload
        
        # Simulate the failing API call details
        if event.type == EventType.RETURN_API_FAILURE:
            return TraceStep(
                trace_id=trace_id,
                step="CheckReturnEligibility",
                input={
                    "sku": payload.get("sku", "SKU-123"),
                    "order_id": payload.get("order_id", "8734")
                },
                output={
                    "eligibility": False,
                    "return_policy": None  # This is the missing field
                },
                schema_ok=False,
                failure={
                    "type": "SchemaMismatch",
                    "field": "return_policy",
                    "expected": "string",
                    "actual": None,
                    "message": "return_policy field is required but missing"
                },
                latency_ms=214,
                timestamp=event.ts
            )
        
        # Generic trace step for other event types
        return TraceStep(
            trace_id=trace_id,
            step=payload.get("endpoint", "unknown"),
            input=payload.get("input", {}),
            output=payload.get("output", {}),
            schema_ok=False,
            failure={
                "type": payload.get("error_type", "Unknown"),
                "field": payload.get("field"),
                "message": payload.get("detail", "Unknown error")
            },
            latency_ms=payload.get("latency_ms", 0),
            timestamp=event.ts
        )
    
    async def _load_original_code(self, file_path: str) -> Optional[str]:
        """Load the original code file for patching"""
        
        # For demo purposes, return sample code
        if "catalog_sync.py" in file_path:
            return '''#!/usr/bin/env python3
"""Catalog synchronization service"""

import requests
from typing import Dict, List, Any

# Fields to sync from catalog
POLICY_FIELDS = ["price", "inventory", "category"]

class CatalogSync:
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    async def sync_product(self, sku: str) -> Dict[str, Any]:
        """Sync a single product from catalog"""
        response = await self._fetch_product_data(sku)
        
        # Extract only the configured fields
        product_data = {}
        for field in POLICY_FIELDS:
            if field in response:
                product_data[field] = response[field]
        
        return product_data
    
    async def _fetch_product_data(self, sku: str) -> Dict[str, Any]:
        """Fetch product data from external catalog API"""
        # Simulate API call
        return {
            "sku": sku,
            "price": 29.99,
            "inventory": 100,
            "category": "electronics",
            "return_policy": "FINAL_SALE_NO_RETURN"  # This field exists but not synced
        }
'''
        
        return None
    
    async def _complete_healing(self, trace_id: str, status: str, message: str, outcome: Optional[HealOutcome] = None):
        """Complete the healing process and publish final event"""
        
        start_time = self.active_healings.get(trace_id, {}).get("start_time", datetime.now())
        duration = (datetime.now() - start_time).total_seconds()
        
        # Publish completion event
        await event_bus.publish(Event(
            type=EventType.HEAL_COMPLETED,
            key=trace_id,
            payload={
                "status": status,
                "message": message,
                "duration_seconds": duration,
                "outcome": outcome.dict() if outcome else None
            },
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="healing_complete"
        ))
        
        status_emoji = "✅" if status == "pass" else "❌"
        print(f"{status_emoji} Healing completed for trace {trace_id}: {message} (took {duration:.1f}s)")

# Global orchestrator instance
orchestrator = HealingOrchestrator() 