import json
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from models.events import Event, EventType, TraceStep, RCAPlan, FailureDetail
from services.event_bus import event_bus
from config import settings

class RCAAgent:
    """Root Cause Analysis Agent - analyzes failures and generates healing plans"""
    
    def __init__(self):
        self.playbooks = {
            "OutOfDateCatalogPolicy": {
                "pattern": "return_policy missing",
                "typical_cause": "Catalog sync omitted return_policy field",
                "fix_template": "Add 'return_policy' to sync field mapping"
            },
            "SchemaMismatch": {
                "pattern": "schema validation failed",
                "typical_cause": "API response missing required field",
                "fix_template": "Update field mapping or add default value"
            },
            "TimeoutError": {
                "pattern": "request timeout",
                "typical_cause": "External service slow response",
                "fix_template": "Increase timeout or add retry logic"
            }
        }
        
    async def analyze_failure(self, trace_step: TraceStep, context: Dict[str, Any] = None) -> Optional[RCAPlan]:
        """Analyze a failed trace step and generate a healing plan"""
        
        if not trace_step.failure:
            return None
            
        failure = trace_step.failure
        
        # Pattern matching against known playbooks
        playbook = self._match_playbook(failure)
        
        if not playbook:
            return None
            
        # Generate specific cause analysis
        cause = await self._analyze_root_cause(trace_step, context, playbook)
        
        # Generate patch specification
        patch_spec = await self._generate_patch_spec(trace_step, cause, playbook)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(patch_spec, trace_step)
        
        plan = RCAPlan(
            playbook=playbook,
            cause=cause,
            patch_spec=patch_spec,
            risk_score=risk_score,
            confidence=0.85  # High confidence for known patterns
        )
        
        # Publish RCA ready event
        await event_bus.publish(Event(
            type=EventType.RCA_READY,
            key=trace_step.trace_id,
            payload={
                "playbook": playbook,
                "cause": cause,
                "risk_score": risk_score,
                "confidence": plan.confidence
            },
            ts=datetime.now(),
            trace_id=trace_step.trace_id,
            ui_hint="rca_complete"
        ))
        
        return plan
    
    def _match_playbook(self, failure: FailureDetail) -> Optional[str]:
        """Match failure to known playbook patterns"""
        
        if failure.type == "SchemaMismatch" and failure.field == "return_policy":
            return "OutOfDateCatalogPolicy"
        elif failure.type == "SchemaMismatch":
            return "SchemaMismatch"
        elif "timeout" in failure.message.lower():
            return "TimeoutError"
            
        return None
    
    async def _analyze_root_cause(self, trace_step: TraceStep, context: Dict[str, Any], playbook: str) -> str:
        """Generate detailed root cause analysis"""
        
        if playbook == "OutOfDateCatalogPolicy":
            # Check if this is specifically about return_policy
            if trace_step.failure and trace_step.failure.field == "return_policy":
                return f"Catalog sync omitted 'return_policy' for SKU {trace_step.input.get('sku', 'unknown')}. Field exists in catalog delta but missing from local DB."
                
        elif playbook == "SchemaMismatch":
            field = trace_step.failure.field if trace_step.failure else "unknown"
            return f"API response validation failed: required field '{field}' is missing or invalid."
            
        elif playbook == "TimeoutError":
            endpoint = trace_step.step
            return f"External service call to {endpoint} exceeded timeout threshold."
            
        return f"Unknown failure in {trace_step.step}"
    
    async def _generate_patch_spec(self, trace_step: TraceStep, cause: str, playbook: str) -> Dict[str, Any]:
        """Generate specific patch specification for the identified issue"""
        
        if playbook == "OutOfDateCatalogPolicy":
            return {
                "file": "services/catalog_sync.py",
                "anchor": "POLICY_FIELDS",
                "change": "+ 'return_policy'",
                "type": "add_field",
                "target_line_pattern": "POLICY_FIELDS = \\[.*\\]"
            }
            
        elif playbook == "SchemaMismatch":
            field = trace_step.failure.field if trace_step.failure else "unknown_field"
            return {
                "file": f"handlers/{trace_step.step.lower()}.py",
                "anchor": f"def {trace_step.step}",
                "change": f"# Add default for {field}",
                "type": "add_default",
                "field": field
            }
            
        return {
            "file": "unknown",
            "change": "manual_fix_required",
            "type": "manual"
        }
    
    def _calculate_risk_score(self, patch_spec: Dict[str, Any], trace_step: TraceStep) -> float:
        """Calculate risk score for the proposed patch (0.0 = safe, 1.0 = high risk)"""
        
        base_risk = 0.1
        
        # File-based risk
        file_path = patch_spec.get("file", "")
        if "catalog_sync" in file_path:
            base_risk += 0.05  # Low risk for sync files
        elif "handlers" in file_path:
            base_risk += 0.1   # Medium risk for handlers
        else:
            base_risk += 0.3   # Higher risk for unknown files
            
        # Change type risk
        change_type = patch_spec.get("type", "unknown")
        if change_type == "add_field":
            base_risk += 0.05  # Low risk for adding fields
        elif change_type == "add_default":
            base_risk += 0.1   # Medium risk for defaults
        else:
            base_risk += 0.2   # Higher risk for unknown changes
            
        return min(base_risk, 0.5)  # Cap at medium risk

# Global RCA agent instance
rca_agent = RCAAgent() 