import json
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
import asyncio
from models.events import Event, EventType, TraceStep, RCAPlan, FailureDetail
from services.event_bus import event_bus
from config import settings

class RCAAgent:
    """Root Cause Analysis Agent - uses Anthropic for intelligent failure analysis"""

    def __init__(self):
        # ✅ Start monitoring events in background task
        self.running = False
        print("🧠 RCAAgent: Initialized - will monitor RETURN_API_FAILURE events")

        # ✅ Correct Anthropic client (headers must be Anthropic-style)
        self.anthropic_client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers={
                "x-api-key": settings.anthropic_api_key or "",
                "anthropic-version": getattr(settings, "anthropic_version", 
                                           "2023-06-01"),
                "content-type": "application/json",
            },
            timeout=getattr(settings, "anthropic_timeout_secs", 30),
        )

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
            },
        }

    async def start(self):
        """Start monitoring for failure events"""
        self.running = True
        print("🧠 RCAAgent: Started monitoring for RETURN_API_FAILURE events")
        asyncio.create_task(self._monitor_failures())

    async def stop(self):
        """Stop monitoring events"""
        self.running = False
        print("🧠 RCAAgent: Stopped monitoring events")

    async def _monitor_failures(self):
        """Monitor for RETURN_API_FAILURE events and process them"""
        async for event in event_bus.subscribe([EventType.RETURN_API_FAILURE]):
            if not self.running:
                break
                
            print(f"🧠 RCAAgent: received {event.type} for trace {event.trace_id}")
            await self._process_failure_event(event)

    async def _process_failure_event(self, event: Event) -> None:
        """Process a failure event and trigger RCA analysis"""
        try:
            payload = event.payload or {}

            # Expect either a full TraceStep dict, or {failure, step, input, ...}
            trace_step = self._coerce_trace_step(payload)
            if not trace_step or not trace_step.failure:
                print("🧠 RCAAgent: no failure found in payload — skipping")
                return

            await self.analyze_failure(trace_step, trace_id=event.trace_id)
        except Exception as e:
            print(f"🧠 RCAAgent: _process_failure_event error: {e}")

    def _coerce_trace_step(self, payload: Dict[str, Any]) -> Optional[TraceStep]:
        """Makes a TraceStep from various payload shapes safely."""
        try:
            if "trace_step" in payload:
                ts = payload["trace_step"]
                # ensure FailureDetail is constructed
                if ts.get("failure") and not isinstance(ts["failure"], FailureDetail):
                    ts["failure"] = FailureDetail(**ts["failure"])
                return TraceStep(**ts)

            # fallback: build from flat payload
            failure_dict = payload.get("failure") or {}
            if failure_dict and not isinstance(failure_dict, FailureDetail):
                failure = FailureDetail(**failure_dict)
            else:
                # tolerate legacy keys like message/type/field at top-level
                failure = FailureDetail(
                    type=payload.get("failure_type") or payload.get("type") or 
                          "Unknown",
                    field=payload.get("field"),
                    message=payload.get("message") or payload.get("error") or "",
                )

            return TraceStep(
                trace_id=payload.get("trace_id") or "unknown_trace",
                step=payload.get("step") or payload.get("endpoint") or "unknown_step",
                input=payload.get("input") or {},
                output=payload.get("output") or {},
                schema_ok=False,  # Since this is a failure event
                failure=failure,
                latency_ms=payload.get("latency_ms", 0),
                timestamp=datetime.now(),
            )
        except Exception as e:
            print(f"🧠 RCAAgent: _coerce_trace_step failed: {e}")
            return None

    async def analyze_failure(self, trace_step: TraceStep, trace_id: str) -> Optional[RCAPlan]:
        print(f"🧠 RCA analyzing failure for trace {trace_id}")

        if not trace_step.failure:
            return None

        cause_analysis = await self._analyze_with_anthropic(trace_step) or self._fallback_analysis(trace_step.failure)
        patch_spec = self._generate_patch_spec(trace_step, cause_analysis)
        risk_score = self._calculate_risk_score(patch_spec, trace_step)

        plan = RCAPlan(
            playbook=cause_analysis.get("playbook", "SchemaMismatch"),
            cause=cause_analysis.get("root_cause", "Unknown failure"),
            patch_spec=patch_spec,
            risk_score=risk_score,
            confidence=cause_analysis.get("confidence", 0.75),
        )

        await event_bus.publish(Event(
            type=EventType.RCA_READY,
            key=trace_id,
            payload={
                "playbook": plan.playbook,
                "cause": plan.cause,
                "risk_score": risk_score,
                "confidence": plan.confidence,
                "patch_spec": patch_spec,
                "analysis_method": cause_analysis.get("method", "pattern_match"),
                "step": {"name": trace_step.step, "input_keys": list((trace_step.input or {}).keys())},
                "failure": {
                    "type": trace_step.failure.type,
                    "field": getattr(trace_step.failure, "field", None),
                    "message": getattr(trace_step.failure, "message", None),
                },
                # 🔧 Enhanced: Pass detailed reasoning data
                "detailed_reasoning": cause_analysis.get("reasoning", {}),
                "recommendations": cause_analysis.get("recommendations", {}),
                "technical_details": cause_analysis.get("technical_details", {}),
                "code_analysis": cause_analysis.get("code_analysis", {}),
                "risk_level": cause_analysis.get("risk_level", "medium"),
                "fix_approach": cause_analysis.get("fix_approach", "Unknown"),
            },
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="rca_complete",
        ))

        print(f"🧠 RCA completed: {plan.cause} (confidence: {plan.confidence})")
        return plan

    async def _analyze_with_anthropic(self, trace_step: TraceStep) -> Optional[Dict[str, Any]]:
        print("🧠 DEBUG: Anthropic config ok?:", bool(settings.anthropic_api_key))
        if not settings.anthropic_api_key:
            return None
        try:
            prompt = f"""You are an expert software engineer analyzing a system failure. You are being asked to provide EXTREMELY DETAILED and VERBOSE analysis.

Context:
- Step: {trace_step.step}
- Input: {trace_step.input}
- Failure: {trace_step.failure.type} - {trace_step.failure.message}
- Field: {trace_step.failure.field}

Please provide a COMPREHENSIVE and DETAILED analysis with extensive reasoning. Be verbose and explain everything thoroughly. Respond in this exact JSON format:

{{
    "root_cause": "VERY DETAILED description of the underlying issue with technical specifics, code examples, and system architecture implications",
    "playbook": "One of: OutOfDateCatalogPolicy, SchemaMismatch, TimeoutError",
    "confidence": 0.0-1.0,
    "fix_approach": "VERY SPECIFIC and DETAILED action to resolve, including exact code changes, file locations, and step-by-step instructions",
    "risk_level": "low/medium/high",
    "method": "anthropic_analysis",
    "technical_details": {{
        "affected_components": ["List of all system components affected by this issue"],
        "data_flow_impact": "Detailed explanation of how data flows are disrupted",
        "performance_implications": "What performance issues this could cause",
        "security_considerations": "Any security implications of this failure",
        "scalability_concerns": "How this affects system scalability"
    }},
    "reasoning": {{
        "analysis_steps": [
            "Step 1: DETAILED observation of what I observed in the failure with specific error codes, stack traces, and system state",
            "Step 2: COMPREHENSIVE explanation of what patterns I recognized and why they are relevant",
            "Step 3: DETAILED justification of why this specific playbook fits best with alternatives considered",
            "Step 4: EXTENSIVE analysis of what alternatives I considered and why they were rejected",
            "Step 5: Technical deep-dive into the root cause with code examples and system architecture analysis"
        ],
        "evidence": "VERY SPECIFIC evidence from the failure that supports my analysis, including exact error messages, field names, data types, and system state",
        "patterns_recognized": "DETAILED explanation of what failure patterns I've seen before that match this case, including specific examples and lessons learned",
        "confidence_explanation": "COMPREHENSIVE explanation of why I'm confident/uncertain about this diagnosis, including factors that increase/decrease confidence",
        "alternative_playbooks": [
            "Alternative 1: DETAILED explanation of why this playbook doesn't fit as well, with specific technical reasons",
            "Alternative 2: DETAILED explanation of why this playbook doesn't fit as well, with specific technical reasons",
            "Alternative 3: DETAILED explanation of why this playbook doesn't fit as well, with specific technical reasons"
        ],
        "risk_assessment": "VERY DETAILED explanation of why I rated the risk as low/medium/high, including specific technical factors, system impact, and rollback complexity"
    }},
    "recommendations": {{
        "immediate_action": "VERY SPECIFIC and DETAILED action plan for what should be done right now, including exact commands, code changes, and verification steps",
        "prevention": "COMPREHENSIVE strategy for how to prevent this from happening again, including monitoring, testing, and architectural improvements",
        "monitoring": "DETAILED list of what to watch for after the fix, including specific metrics, log patterns, and alert conditions",
        "long_term_improvements": "Strategic recommendations for system improvements that would prevent similar issues"
    }},
    "code_analysis": {{
        "file_patterns": ["Specific file patterns that need to be modified"],
        "function_signatures": "Detailed analysis of affected function signatures and their contracts",
        "data_structures": "Analysis of data structures involved and their relationships",
        "api_contracts": "Detailed analysis of API contracts and their violations"
    }}
}}

IMPORTANT: Be EXTREMELY VERBOSE and DETAILED. Explain everything thoroughly. Include technical specifics, code examples, system architecture details, and comprehensive reasoning. This analysis will be used by other AI systems and developers, so be as detailed as possible."""
            
            payload = {
                "model": getattr(settings, "anthropic_model", "claude-3-5-sonnet-latest"),
                "max_tokens": 2000,  # Increased token limit for more detailed responses
                "messages": [{"role": "user", "content": prompt}],
            }
            resp = await self.anthropic_client.post("/v1/messages", json=payload)
            print("🧠 DEBUG: Anthropic status:", resp.status_code)
            if resp.status_code == 200:
                data = resp.json()
                text = data["content"][0]["text"]
                
                # Extract JSON from the response (AI might add extra text)
                try:
                    # Try to find JSON in the response
                    import re
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(0)
                        return json.loads(json_text)
                    else:
                        # Fallback: try to parse the entire text
                        return json.loads(text)
                except json.JSONDecodeError as json_err:
                    print(f"🧠 JSON parsing failed: {json_err}")
                    print(f"🧠 Raw response text: {text[:200]}...")
                    return None
            if resp.status_code in (401, 403):
                print("🧠 Anthropic auth error")
                return None
            print("🧠 Anthropic error:", resp.status_code, resp.text[:180])
            return None
        except Exception as e:
            print("🧠 Anthropic analysis failed:", e)
            return None

    def _fallback_analysis(self, failure: FailureDetail) -> Dict[str, Any]:
        msg = (getattr(failure, "message", "") or "").lower()
        if "return_policy" in msg and "missing" in msg:
            return {
                "root_cause": "Catalog sync omitted 'return_policy' for clearance SKUs",
                "playbook": "OutOfDateCatalogPolicy",
                "confidence": 0.80,
                "fix_approach": "Add 'return_policy' to POLICY_FIELDS list",
                "risk_level": "low",
                "method": "pattern_match",
                "reasoning": {
                    "analysis_steps": [
                        "Step 1: Detected 'return_policy' and 'missing' keywords in error message",
                        "Step 2: Recognized pattern from previous catalog sync failures",
                        "Step 3: Identified OutOfDateCatalogPolicy as best playbook match",
                        "Step 4: Ruled out SchemaMismatch (not a validation issue) and TimeoutError (not a timing issue)"
                    ],
                    "evidence": "Error message contains 'return_policy' and 'missing' - classic catalog sync field omission",
                    "patterns_recognized": "This matches the pattern where catalog sync jobs miss required policy fields",
                    "confidence_explanation": "High confidence due to clear keyword match and known failure pattern",
                    "alternative_playbooks": [
                        "SchemaMismatch: Doesn't fit - this is missing data, not invalid data format",
                        "TimeoutError: Doesn't fit - this is a data completeness issue, not a timing issue"
                    ],
                    "risk_assessment": "Low risk - adding a field to a list is a safe, additive change"
                },
                "recommendations": {
                    "immediate_action": "Add 'return_policy' to the POLICY_FIELDS list in catalog sync configuration",
                    "prevention": "Implement field validation in catalog sync to ensure all required policy fields are present",
                    "monitoring": "Watch for similar field omission errors in other policy-related syncs"
                }
            }
        return {
            "root_cause": f"Schema validation failed: {getattr(failure, 'message', '')}",
            "playbook": "SchemaMismatch",
            "confidence": 0.60,
            "fix_approach": "Update field mapping or add validation",
            "risk_level": "medium",
            "method": "pattern_match",
            "reasoning": {
                "analysis_steps": [
                    "Step 1: Detected schema validation failure in error message",
                    "Step 2: Recognized generic validation error pattern",
                    "Step 3: Applied SchemaMismatch playbook as default for validation issues",
                    "Step 4: Considered but ruled out other playbooks due to lack of specific evidence"
                ],
                "evidence": "Generic schema validation error message without specific field details",
                "patterns_recognized": "Common pattern for various schema validation failures",
                "confidence_explanation": "Medium confidence - generic error requires more investigation",
                "alternative_playbooks": [
                    "OutOfDateCatalogPolicy: Doesn't fit - no evidence of catalog sync issues",
                    "TimeoutError: Doesn't fit - not a timing-related error"
                ],
                "risk_assessment": "Medium risk - schema changes can affect multiple parts of the system"
            },
            "recommendations": {
                "immediate_action": "Investigate the specific schema validation failure to determine root cause",
                "prevention": "Add more detailed error logging to capture specific validation failures",
                "monitoring": "Track schema validation error patterns to identify systemic issues"
            }
        }

    def _generate_patch_spec(self, trace_step: TraceStep, analysis: Dict[str, Any]) -> Dict[str, Any]:
        if analysis.get("playbook") == "OutOfDateCatalogPolicy":
            return {"file": "services/catalog_sync.py", "anchor": "POLICY_FIELDS",
                    "change": "+ 'return_policy'", "line_number": 3, "operation": "add_to_list"}
        return {"file": "services/catalog_sync.py", "anchor": "POLICY_FIELDS",
                "change": "+ 'return_policy'", "line_number": 3, "operation": "modify"}

    def _calculate_risk_score(self, patch_spec: Dict[str, Any], trace_step: TraceStep) -> float:
        base = 0.1
        if "config" in patch_spec.get("file", ""):
            base += 0.3
        op = patch_spec.get("operation")
        if op == "add_to_list":
            base += 0.05
        elif op == "modify":
            base += 0.15
        return min(base, 0.5)

    async def aclose(self):
        await self.anthropic_client.aclose()

# Global instance (constructed once)
rca_agent = RCAAgent() 