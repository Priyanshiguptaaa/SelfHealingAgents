"""Coordinator agent that orchestrates the multi-agent healing system"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from models.events import Event, EventType
from services.event_bus import event_bus
from agents.rca_agent import rca_agent
from agents.patch_generator import patch_generator
from services.guardrails import guardrails
from services.patch_applier import patch_applier
from services.verifier import verifier


class CoordinatorAgent:
    """Master agent that coordinates all healing agents"""
    
    def __init__(self):
        self.active_healings = {}
        self.running = False
        self.healing_agents = {
            "rca": rca_agent,
            "patch_generator": patch_generator,
            "guardrails": guardrails,
            "patch_applier": patch_applier,
            "verifier": verifier
        }
    
    async def start(self):
        """Start the coordinator agent and all healing agents"""
        self.running = True
        print("🎯 Coordinator Agent started - managing healing workflow")
        
        # Subscribe to failure events
        asyncio.create_task(self._monitor_failures())
    
    async def stop(self):
        """Stop the coordinator agent"""
        self.running = False
        print("🎯 Coordinator Agent stopped")
    
    async def _monitor_failures(self):
        """Monitor for failure events and coordinate healing response"""
        failure_types = [EventType.RETURN_API_FAILURE, EventType.SCHEMA_MISMATCH]
        
        async for event in event_bus.subscribe(failure_types):
            if not self.running:
                break
                
            if event.trace_id and event.trace_id not in self.active_healings:
                # New failure detected - coordinate healing response
                await self._coordinate_healing(event)
    
    async def _coordinate_healing(self, failure_event: Event):
        """Coordinate the healing workflow across all agents"""
        trace_id = failure_event.trace_id
        print(f"🎯 Coordinating healing for trace {trace_id}")
        
        # Track healing progress
        self.active_healings[trace_id] = {
            "start_time": datetime.now(),
            "status": "analyzing",
            "agents_involved": [],
            "current_step": "rca"
        }
        
        try:
            # Step 1: RCA Agent analyzes the failure
            print(f"🎯 Step 1: Activating RCA Agent for {trace_id}")
            self.active_healings[trace_id]["agents_involved"].append("rca")
            
            # Create trace step from failure event
            trace_step = self._create_trace_step(failure_event)
            
            # RCA Agent analyzes the failure
            plan = await rca_agent.analyze_failure(trace_step, trace_id)
            
            if not plan:
                await self._complete_healing(trace_id, "failed", "RCA analysis failed")
                return
            
            # Step 2: Patch Generator creates the fix
            print(f"🎯 Step 2: Activating Patch Generator for {trace_id}")
            self.active_healings[trace_id]["current_step"] = "generating"
            self.active_healings[trace_id]["agents_involved"].append("patch_generator")
            
            # Load original code
            original_code = await self._load_original_code(plan.patch_spec.get("file"))
            
            # Generate patch
            machine_diff = await patch_generator.generate_patch(plan, original_code, trace_id)
            
            if not machine_diff:
                await self._complete_healing(trace_id, "failed", "Patch generation failed")
                return
            
            # Step 3: Guardrails validate the patch
            print(f"🎯 Step 3: Activating Guardrails for {trace_id}")
            self.active_healings[trace_id]["current_step"] = "validating"
            self.active_healings[trace_id]["agents_involved"].append("guardrails")
            
            is_safe = await guardrails.validate_patch(machine_diff, trace_id)
            
            if not is_safe:
                await self._complete_healing(trace_id, "failed", "Patch failed safety checks")
                return
            
            # Step 4: Patch Applier applies the fix
            print(f"🎯 Step 4: Activating Patch Applier for {trace_id}")
            self.active_healings[trace_id]["current_step"] = "applying"
            self.active_healings[trace_id]["agents_involved"].append("patch_applier")
            
            applied = await patch_applier.apply_patch(machine_diff, trace_id)
            
            if not applied:
                await self._complete_healing(trace_id, "failed", "Patch application failed")
                return
            
            # Step 5: Verifier validates the fix
            print(f"🎯 Step 5: Activating Verifier for {trace_id}")
            self.active_healings[trace_id]["current_step"] = "verifying"
            self.active_healings[trace_id]["agents_involved"].append("verifier")
            
            outcome = await verifier.verify_fix(trace_step, trace_id)
            
            if outcome:
                await self._complete_healing(trace_id, "success", "Healing completed successfully")
            else:
                # Rollback and fail
                await patch_applier.rollback_patch(machine_diff.file, trace_id)
                await self._complete_healing(trace_id, "failed", "Verification failed - rolled back")
                
        except Exception as e:
            print(f"🎯 Coordination error for {trace_id}: {e}")
            await self._complete_healing(trace_id, "failed", f"Coordination error: {str(e)}")
    
    def _create_trace_step(self, failure_event: Event):
        """Create trace step from failure event"""
        # Import here to avoid circular imports
        from models.events import TraceStep, FailureDetail
        
        return TraceStep(
            trace_id=failure_event.trace_id,
            step=failure_event.payload.get("endpoint", "unknown"),
            input={"sku": failure_event.payload.get("sku"), "order_id": failure_event.payload.get("order_id")},
            output=None,
            schema_ok=False,
            failure=FailureDetail(
                type=failure_event.payload.get("error_type", "Unknown"),
                field=failure_event.payload.get("field"),
                message=failure_event.payload.get("detail", "")
            ),
            latency_ms=0,
            timestamp=failure_event.ts
        )
    
    async def _load_original_code(self, file_path: str) -> str:
        """Load original code for patching"""
        # Use patch applier's method
        return await patch_applier._read_original_content(file_path)
    
    async def _complete_healing(self, trace_id: str, status: str, message: str):
        """Complete the healing process and clean up"""
        if trace_id in self.active_healings:
            healing_info = self.active_healings[trace_id]
            duration = (datetime.now() - healing_info["start_time"]).total_seconds()
            
            print(f"🎯 Healing {status} for {trace_id}: {message} (took {duration:.1f}s)")
            print(f"🎯 Agents involved: {', '.join(healing_info['agents_involved'])}")
            
            # Publish completion event
            await event_bus.publish(Event(
                type=EventType.HEAL_COMPLETED,
                key=trace_id,
                payload={
                    "status": status,
                    "message": message,
                    "duration_seconds": duration,
                    "agents_involved": healing_info["agents_involved"]
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="healing_complete"
            ))
            
            # Clean up
            del self.active_healings[trace_id]


# Global coordinator agent instance
coordinator_agent = CoordinatorAgent() 