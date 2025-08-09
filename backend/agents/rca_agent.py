import json
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from models.events import Event, EventType, TraceStep, RCAPlan, FailureDetail
from services.event_bus import event_bus
from config import settings

class RCAAgent:
    """Root Cause Analysis Agent - uses Anthropic for intelligent failure analysis"""
    
    def __init__(self):
        self.anthropic_client = httpx.AsyncClient()
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
                "fix_template": "Add retry logic or increase timeout"
            }
        }
        
    async def analyze_failure(self, trace_step: TraceStep, trace_id: str) -> Optional[RCAPlan]:
        """Analyze a failed trace step using Anthropic AI for intelligent RCA"""
        
        print(f"🧠 RCA Agent analyzing failure for trace {trace_id}")
        
        if not trace_step.failure:
            return None
            
        failure = trace_step.failure
        
        # Use Anthropic for intelligent analysis
        cause_analysis = await self._analyze_with_anthropic(trace_step)
        
        if not cause_analysis:
            # Fallback to pattern matching
            cause_analysis = self._fallback_analysis(failure)
        
        # Generate patch specification
        patch_spec = self._generate_patch_spec(trace_step, cause_analysis)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(patch_spec, trace_step)
        
        plan = RCAPlan(
            playbook=cause_analysis.get("playbook", "SchemaMismatch"),
            cause=cause_analysis.get("root_cause", "Unknown failure"),
            patch_spec=patch_spec,
            risk_score=risk_score,
            confidence=cause_analysis.get("confidence", 0.75)
        )
        
        # Publish RCA ready event with detailed analysis
        await event_bus.publish(Event(
            type=EventType.RCA_READY,
            key=trace_id,
            payload={
                "playbook": plan.playbook,
                "cause": plan.cause,
                "risk_score": risk_score,
                "confidence": plan.confidence,
                "patch_spec": patch_spec,
                "analysis_method": "anthropic" if cause_analysis.get("method") == "ai" else "pattern_match"
            },
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="rca_complete"
        ))
        
        print(f"🧠 RCA completed: {plan.cause} (confidence: {plan.confidence})")
        return plan
    
    async def _analyze_with_anthropic(self, trace_step: TraceStep) -> Optional[Dict[str, Any]]:
        """Use Anthropic Claude for intelligent failure analysis"""
        
        if not settings.anthropic_api_key:
            print("🧠 No Anthropic API key - using fallback analysis")
            return None
        
        try:
            # Create detailed context for Claude
            context = {
                "failure_type": trace_step.failure.type,
                "failure_field": trace_step.failure.field,
                "failure_message": trace_step.failure.message,
                "endpoint": trace_step.step,
                "input_data": trace_step.input,
                "system_context": "E-commerce return policy system with catalog sync issues"
            }
            
            prompt = f"""
You are an expert software engineer analyzing a production failure in an e-commerce system.

FAILURE CONTEXT:
- System: E-commerce return policy validation
- Failure Type: {trace_step.failure.type}
- Missing Field: {trace_step.failure.field}
- Error Message: {trace_step.failure.message}
- Endpoint: {trace_step.step}
- Input: {json.dumps(trace_step.input)}

SYSTEM ARCHITECTURE:
- Catalog sync service pulls product data from external API
- Return policy validation requires 'return_policy' field
- Clearance items have different return policies

Analyze this failure and provide:
1. Root cause (what went wrong and why)
2. Confidence level (0.0-1.0)
3. Recommended fix approach
4. Risk assessment

Respond in JSON format:
{{
    "root_cause": "Detailed explanation of what went wrong",
    "playbook": "OutOfDateCatalogPolicy|SchemaMismatch|TimeoutError",
    "confidence": 0.85,
    "fix_approach": "Specific technical fix needed",
    "risk_level": "low|medium|high",
    "method": "ai"
}}
"""

            headers = {
                "Authorization": f"Bearer {settings.anthropic_api_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
            }
            
            response = await self.anthropic_client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["content"][0]["text"]
                
                # Parse JSON response
                analysis = json.loads(content)
                print(f"🧠 Anthropic analysis: {analysis['root_cause']}")
                return analysis
            else:
                print(f"🧠 Anthropic API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"🧠 Anthropic analysis failed: {e}")
            return None
    
    def _fallback_analysis(self, failure: FailureDetail) -> Dict[str, Any]:
        """Fallback pattern-based analysis when AI is unavailable"""
        print("🧠 Using fallback pattern analysis")
        
        # Pattern matching logic
        if "return_policy" in failure.message and "missing" in failure.message:
            return {
                "root_cause": "Catalog sync omitted 'return_policy' for clearance SKUs",
                "playbook": "OutOfDateCatalogPolicy", 
                "confidence": 0.80,
                "fix_approach": "Add 'return_policy' to POLICY_FIELDS list",
                "risk_level": "low",
                "method": "pattern_match"
            }
        
        return {
            "root_cause": f"Schema validation failed: {failure.message}",
            "playbook": "SchemaMismatch",
            "confidence": 0.60,
            "fix_approach": "Update field mapping or add validation",
            "risk_level": "medium", 
            "method": "pattern_match"
        }
    
    def _generate_patch_spec(self, trace_step: TraceStep, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate patch specification based on analysis"""
        
        if analysis.get("playbook") == "OutOfDateCatalogPolicy":
            return {
                "file": "services/catalog_sync.py",
                "anchor": "POLICY_FIELDS",
                "change": "+ 'return_policy'",
                "line_number": 3,
                "operation": "add_to_list"
            }
        
        return {
            "file": "services/catalog_sync.py", 
            "anchor": "POLICY_FIELDS",
            "change": "+ 'return_policy'",
            "line_number": 3,
            "operation": "modify"
        }
    
    def _calculate_risk_score(self, patch_spec: Dict[str, Any], trace_step: TraceStep) -> float:
        """Calculate risk score for the proposed patch"""
        
        base_risk = 0.1  # Low base risk
        
        # File risk
        if "config" in patch_spec.get("file", ""):
            base_risk += 0.3
        
        # Operation risk  
        if patch_spec.get("operation") == "add_to_list":
            base_risk += 0.05  # Very low risk
        elif patch_spec.get("operation") == "modify":
            base_risk += 0.15
        
        return min(base_risk, 0.5)  # Cap at medium risk

# Global RCA agent instance
rca_agent = RCAAgent() 