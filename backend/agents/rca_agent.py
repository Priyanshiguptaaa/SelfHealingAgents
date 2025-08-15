import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx
import asyncio
from models.events import Event, EventType, TraceStep, RCAPlan, FailureDetail
from services.event_bus import event_bus
from config import settings

class RCAAgent:
    """Root Cause Analysis Agent - uses Anthropic for intelligent failure 
    analysis and business logic evaluation"""

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

        # 🔧 Enhanced: Business logic evaluation test cases
        self.evaluation_test_cases = {
            "return_policy_validation": [
                {
                    "name": "Valid return policy present",
                    "input": {"sku": "TEST001", "order_id": "ORD001"},
                    "expected": {"return_policy": "30 days", "eligible": True},
                    "description": "Test case where return policy is properly "
                                   "populated"
                },
                {
                    "name": "Missing return policy",
                    "input": {"sku": "TEST002", "order_id": "ORD002"},
                    "expected": {"return_policy": None, "eligible": False},
                    "description": "Test case where return policy is missing "
                                   "(failure case)"
                }
            ],
            "schema_validation": [
                {
                    "name": "Complete product data",
                    "input": {"product_id": "PROD001"},
                    "expected": {"name": "Test Product", "price": 99.99,
                               "category": "Electronics"},
                    "description": "Test case with complete product schema"
                },
                {
                    "name": "Incomplete product data",
                    "input": {"product_id": "PROD002"},
                    "expected": {"name": "Test Product", "price": None,
                               "category": None},
                    "description": "Test case with missing required fields"
                }
            ]
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

            # 🔧 OPTIMIZED: Skip verbose business logic evaluation for speed
            # Go directly to RCA analysis
            
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

        # 🔧 OPTIMIZED: Simplified event payload with essential info only
        await event_bus.publish(Event(
            type=EventType.RCA_READY,
            key=trace_id,
            payload={
                "playbook": plan.playbook,
                "cause": plan.cause,
                "risk_score": risk_score,
                "confidence": plan.confidence,
                "patch_spec": patch_spec,
                "analysis_method": cause_analysis.get("method", "pattern_match")
            },
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="rca_complete",
        ))

        print(f"🧠 RCA completed: {plan.cause} (confidence: {plan.confidence})")
        return plan

    # 🔧 OPTIMIZED: Remove verbose business logic evaluation methods for speed
    # These methods were causing delays and are not essential for quick fixes

    async def _analyze_with_anthropic(self, trace_step: TraceStep) -> Optional[Dict[str, Any]]:
        print("🧠 DEBUG: Anthropic config ok?:", bool(settings.anthropic_api_key))
        if not settings.anthropic_api_key:
            return None
        try:
            # 🔧 OPTIMIZED: Simplified prompt for faster analysis
            prompt = f"""You are an expert software engineer analyzing a system failure. Provide a CONCISE analysis.

Context:
- Step: {trace_step.step}
- Failure: {trace_step.failure.type} - {trace_step.failure.message}
- Field: {trace_step.failure.field}

Respond in this JSON format (be BRIEF and to the point):

{{
    "root_cause": "Brief description of the issue",
    "playbook": "One of: OutOfDateCatalogPolicy, SchemaMismatch, TimeoutError",
    "confidence": 0.0-1.0,
    "fix_approach": "Specific action to resolve",
    "risk_level": "low/medium/high",
    "method": "anthropic_analysis"
}}

Focus only on identifying the root cause and appropriate playbook. Be concise."""
            
            payload = {
                "model": getattr(settings, "anthropic_model", "claude-3-5-sonnet-latest"),
                "max_tokens": 300,  # 🔧 REDUCED: Much smaller token limit for speed
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

    async def _evaluate_business_logic(self, trace_step: TraceStep) -> Dict[str, Any]:
        """Evaluate business logic against test cases to identify specific failures"""
        print(f"🧠 RCAAgent: Evaluating business logic for step {trace_step.step}")
        
        evaluation_results = {
            "step": trace_step.step,
            "timestamp": datetime.now().isoformat(),
            "test_results": [],
            "failure_patterns": [],
            "business_impact": {},
            "recommendations": []
        }

        try:
            # Run relevant test cases based on the step
            if ("return" in trace_step.step.lower() or
                "policy" in trace_step.step.lower()):
                test_results = await self._run_return_policy_tests(trace_step)
                evaluation_results["test_results"].extend(test_results)
                
            if ("schema" in trace_step.step.lower() or
                "validation" in trace_step.step.lower()):
                test_results = await self._run_schema_validation_tests(
                    trace_step
                )
                evaluation_results["test_results"].extend(test_results)

            # Analyze failure patterns
            evaluation_results["failure_patterns"] = self._analyze_failure_patterns(
                trace_step, evaluation_results["test_results"]
            )

            # Assess business impact
            evaluation_results["business_impact"] = self._assess_business_impact(
                trace_step, evaluation_results["failure_patterns"]
            )

            # Generate recommendations
            evaluation_results["recommendations"] = self._generate_evaluation_recommendations(
                evaluation_results
            )

            print(f"🧠 RCAAgent: Business logic evaluation completed with "
                  f"{len(evaluation_results['test_results'])} test results")
            return evaluation_results

        except Exception as e:
            print(f"🧠 RCAAgent: Error during business logic evaluation: {e}")
            evaluation_results["error"] = str(e)
            return evaluation_results

    async def _run_return_policy_tests(self, trace_step: TraceStep) -> List[Dict[str, Any]]:
        """Run return policy validation tests"""
        test_results = []
        
        for test_case in self.evaluation_test_cases["return_policy_validation"]:
            try:
                # Simulate the test case execution
                test_result = {
                    "test_name": test_case["name"],
                    "description": test_case["description"],
                    "input": test_case["input"],
                    "expected": test_case["expected"],
                    "actual": await self._simulate_return_policy_check(test_case["input"]),
                    "passed": False,
                    "failure_details": None
                }
                
                # Check if test passed
                if test_result["actual"]:
                    test_result["passed"] = (
                        test_result["actual"].get("return_policy") ==
                        test_case["expected"]["return_policy"] and
                        test_result["actual"].get("eligible") ==
                        test_case["expected"]["eligible"]
                    )
                
                if not test_result["passed"]:
                    test_result["failure_details"] = {
                        "missing_fields": self._identify_missing_fields(test_result["expected"], test_result["actual"]),
                        "type_mismatches": self._identify_type_mismatches(test_result["expected"], test_result["actual"]),
                        "business_rule_violations": self._identify_business_rule_violations(test_result["expected"], test_result["actual"])
                    }
                
                test_results.append(test_result)
                
            except Exception as e:
                test_results.append({
                    "test_name": test_case["name"],
                    "description": test_case["description"],
                    "error": str(e),
                    "passed": False
                })
        
        return test_results

    async def _run_schema_validation_tests(self, trace_step: TraceStep) -> List[Dict[str, Any]]:
        """Run schema validation tests"""
        test_results = []
        
        for test_case in self.evaluation_test_cases["schema_validation"]:
            try:
                test_result = {
                    "test_name": test_case["name"],
                    "description": test_case["description"],
                    "input": test_case["input"],
                    "expected": test_case["expected"],
                    "actual": await self._simulate_product_lookup(test_case["input"]),
                    "passed": False,
                    "failure_details": None
                }
                
                # Check schema completeness
                if test_result["actual"]:
                    test_result["passed"] = all(
                        test_result["actual"].get(key) is not None 
                        for key in test_case["expected"].keys()
                    )
                
                if not test_result["passed"]:
                    test_result["failure_details"] = {
                        "missing_fields": self._identify_missing_fields(test_result["expected"], test_result["actual"]),
                        "null_values": self._identify_null_values(test_result["expected"], test_result["actual"])
                    }
                
                test_results.append(test_result)
                
            except Exception as e:
                test_results.append({
                    "test_name": test_case["name"],
                    "description": test_case["description"],
                    "error": str(e),
                    "passed": False
                })
        
        return test_results

    async def _simulate_return_policy_check(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate return policy eligibility check"""
        # This would normally call the actual business logic
        # For evaluation purposes, we simulate different scenarios
        sku = input_data.get("sku", "")
        
        if "TEST001" in sku:
            return {"return_policy": "30 days", "eligible": True}
        elif "TEST002" in sku:
            return {"return_policy": None, "eligible": False}
        else:
            return {"return_policy": "14 days", "eligible": True}

    async def _simulate_product_lookup(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate product data lookup"""
        product_id = input_data.get("product_id", "")
        
        if "PROD001" in product_id:
            return {"name": "Test Product", "price": 99.99, "category": "Electronics"}
        elif "PROD002" in product_id:
            return {"name": "Test Product", "price": None, "category": None}
        else:
            return {"name": "Unknown Product", "price": 0.0, "category": "Unknown"}

    def _identify_missing_fields(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
        """Identify fields that are missing from the actual result"""
        return [key for key in expected.keys() if key not in actual or actual[key] is None]

    def _identify_type_mismatches(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify type mismatches between expected and actual values"""
        mismatches = []
        for key in expected.keys():
            if key in actual and actual[key] is not None:
                expected_type = type(expected[key])
                actual_type = type(actual[key])
                if expected_type != actual_type:
                    mismatches.append({
                        "field": key,
                        "expected_type": expected_type.__name__,
                        "actual_type": actual_type.__name__,
                        "expected_value": expected[key],
                        "actual_value": actual[key]
                    })
        return mismatches

    def _identify_business_rule_violations(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify business rule violations"""
        violations = []
        
        # Example business rule: return_policy must be present for eligibility
        if "return_policy" in expected and "eligible" in expected:
            if expected["eligible"] and (actual.get("return_policy") is None or actual.get("return_policy") == ""):
                violations.append({
                    "rule": "return_policy_required_for_eligibility",
                    "description": "Return policy must be present for eligible returns",
                    "field": "return_policy",
                    "expected": "non-empty string",
                    "actual": actual.get("return_policy")
                })
        
        return violations

    def _identify_null_values(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
        """Identify fields that have null values when they shouldn't"""
        return [key for key in expected.keys() if key in actual and actual[key] is None and expected[key] is not None]

    def _analyze_failure_patterns(self, trace_step: TraceStep, test_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze patterns in test failures"""
        patterns = []
        failed_tests = [t for t in test_results if not t.get("passed", True)]
        
        if not failed_tests:
            return patterns
        
        # Group failures by type
        failure_types = {}
        for test in failed_tests:
            failure_type = "unknown"
            if "missing_fields" in test.get("failure_details", {}):
                failure_type = "missing_fields"
            elif "type_mismatches" in test.get("failure_details", {}):
                failure_type = "type_mismatches"
            elif "business_rule_violations" in test.get("failure_details", {}):
                failure_type = "business_rule_violations"
            
            if failure_type not in failure_types:
                failure_types[failure_type] = []
            failure_types[failure_type].append(test)
        
        # Create pattern analysis
        for failure_type, tests in failure_types.items():
            patterns.append({
                "pattern_type": failure_type,
                "frequency": len(tests),
                "affected_tests": [t["test_name"] for t in tests],
                "common_fields": self._find_common_affected_fields(tests),
                "severity": self._assess_pattern_severity(failure_type, tests)
            })
        
        return patterns

    def _find_common_affected_fields(self, tests: List[Dict[str, Any]]) -> List[str]:
        """Find fields commonly affected across multiple test failures"""
        field_counts = {}
        for test in tests:
            if "failure_details" in test:
                for detail_type, details in test["failure_details"].items():
                    if detail_type == "missing_fields" and isinstance(details, list):
                        for field in details:
                            field_counts[field] = field_counts.get(field, 0) + 1
                    elif detail_type == "type_mismatches" and isinstance(details, list):
                        for mismatch in details:
                            field = mismatch.get("field", "")
                            if field:
                                field_counts[field] = field_counts.get(field, 0) + 1
        
        # Return fields that appear in multiple failures
        return [field for field, count in field_counts.items() if count > 1]

    def _assess_pattern_severity(self, pattern_type: str, tests: List[Dict[str, Any]]) -> str:
        """Assess the severity of a failure pattern"""
        if pattern_type == "business_rule_violations":
            return "high"
        elif pattern_type == "missing_fields":
            return "medium"
        elif pattern_type == "type_mismatches":
            return "low"
        else:
            return "unknown"

    def _assess_business_impact(self, trace_step: TraceStep, failure_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess the business impact of identified failures"""
        impact = {
            "customer_experience": "good",
            "revenue_impact": "none",
            "operational_impact": "low",
            "compliance_risk": "low",
            "affected_services": [],
            "estimated_downtime": "0 minutes"
        }
        
        if not failure_patterns:
            return impact
        
        # Assess impact based on failure patterns
        high_severity_patterns = [p for p in failure_patterns if p.get("severity") == "high"]
        medium_severity_patterns = [p for p in failure_patterns if p.get("severity") == "medium"]
        
        if high_severity_patterns:
            impact["customer_experience"] = "poor"
            impact["revenue_impact"] = "high"
            impact["operational_impact"] = "high"
            impact["compliance_risk"] = "high"
            impact["estimated_downtime"] = "30+ minutes"
        
        elif medium_severity_patterns:
            impact["customer_experience"] = "degraded"
            impact["revenue_impact"] = "medium"
            impact["operational_impact"] = "medium"
            impact["compliance_risk"] = "medium"
            impact["estimated_downtime"] = "5-15 minutes"
        
        # Identify affected services
        if "return" in trace_step.step.lower():
            impact["affected_services"].append("return_processing")
        if "policy" in trace_step.step.lower():
            impact["affected_services"].append("policy_management")
        if "schema" in trace_step.step.lower():
            impact["affected_services"].append("data_validation")
        
        return impact

    def _generate_evaluation_recommendations(self, evaluation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations based on evaluation results"""
        recommendations = []
        
        # Add recommendations based on failure patterns
        for pattern in evaluation_results.get("failure_patterns", []):
            if pattern["pattern_type"] == "missing_fields":
                recommendations.append({
                    "priority": "high" if pattern["severity"] == "high" else "medium",
                    "action": "Add missing field validation and default values",
                    "description": f"Fields {', '.join(pattern['common_fields'])} are commonly missing",
                    "estimated_effort": "2-4 hours",
                    "files_to_modify": ["services/catalog_sync.py", "models/product.py"]
                })
            
            elif pattern["pattern_type"] == "business_rule_violations":
                recommendations.append({
                    "priority": "high",
                    "action": "Implement business rule validation",
                    "description": "Critical business rules are being violated",
                    "estimated_effort": "4-8 hours",
                    "files_to_modify": ["services/validation.py", "models/business_rules.py"]
                })
        
        # Add recommendations based on business impact
        business_impact = evaluation_results.get("business_impact", {})
        if business_impact.get("customer_experience") == "poor":
            recommendations.append({
                "priority": "critical",
                "action": "Immediate hotfix deployment",
                "description": "Customer experience is severely impacted",
                "estimated_effort": "1-2 hours",
                "files_to_modify": ["services/fallback.py"]
            })
        
        return recommendations

    async def aclose(self):
        await self.anthropic_client.aclose()

# Global instance (constructed once)
rca_agent = RCAAgent() 