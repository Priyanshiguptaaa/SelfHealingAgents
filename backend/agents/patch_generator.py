import httpx
import difflib
from datetime import datetime
from typing import Dict, Any, Optional, List
from models import RCAPlan, MachineDiff
from services.event_bus import event_bus, EventType, Event
from config import settings


class PatchGenerator:
    """Patch Generator Agent - converts RCA plans into executable code patches
    using Morph API"""

    def __init__(self):
        self.client = httpx.AsyncClient()

    async def generate_patch(self, plan: RCAPlan, original_code: str,
                            trace_id: str) -> Optional[MachineDiff]:
        """Generate machine diff using Morph Apply API"""

        print(f"\n🔧 PATCH GENERATOR: Starting patch generation for trace {trace_id}")
        print(f"🔧 PATCH GENERATOR: File to modify: {plan.patch_spec.get('file', 'unknown')}")
        print(f"🔧 PATCH GENERATOR: Change type: {plan.patch_spec.get('type', 'unknown')}")
        print(f"🔧 PATCH GENERATOR: Risk score: {plan.risk_score}")

        # Publish log to frontend
        await self._publish_patch_log(trace_id, f"🔧 Starting patch generation for {plan.patch_spec.get('file', 'unknown')}")
        await self._publish_patch_log(trace_id, f"🔧 Change type: {plan.patch_spec.get('type', 'unknown')}")
        await self._publish_patch_log(trace_id, f"🔧 Risk score: {plan.risk_score}")

        # Publish generation start event
        await event_bus.publish(Event(
            type=EventType.MORPH_APPLY_REQUESTED,
            key=trace_id,
            payload={
                "file": plan.patch_spec.get("file", "unknown"),
                "loc_estimate": self._estimate_loc_change(plan.patch_spec),
                "risk_score": plan.risk_score
            },
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="generating_patch"
        ))

        try:
            # Generate update snippet based on patch spec
            print(f"🔧 PATCH GENERATOR: Creating update snippet...")
            await self._publish_patch_log(trace_id, "🔧 Creating update snippet...")
            update_snippet = self._create_update_snippet(
                plan.patch_spec, original_code
            )
            print(f"🔧 PATCH GENERATOR: Update snippet created: {update_snippet[:100]}...")
            await self._publish_patch_log(trace_id, f"🔧 Update snippet: {update_snippet}")

            # Call Morph API
            print(f"🔧 PATCH GENERATOR: Calling Morph API...")
            await self._publish_patch_log(trace_id, "🔧 Calling Morph API...")
            raw_response = await self._call_morph_apply(
                original_code, update_snippet, trace_id
            )

            if not raw_response:
                print(f"🔧 PATCH GENERATOR: Morph API call failed - no response")
                await self._publish_failure_event(
                    trace_id, "Morph API call failed"
                )
                return None

            print(f"🔧 PATCH GENERATOR: Morph API response received, length: {len(raw_response)}")
            print(f"🔧 PATCH GENERATOR: Raw response preview: {raw_response[:200]}...")

            # Extract the actual updated code from Morph response
            print(f"🔧 PATCH GENERATOR: Extracting updated code from response...")
            updated_code = self._extract_updated_code_from_response(raw_response, original_code)
            print(f"🔧 PATCH GENERATOR: Updated code extracted, length: {len(updated_code)}")
            
            # Check if code was actually modified
            if updated_code == original_code:
                print(f"⚠️ PATCH GENERATOR: WARNING - No changes detected in Morph response!")
                print(f"🔧 PATCH GENERATOR: Original code length: {len(original_code)}")
                print(f"🔧 PATCH GENERATOR: Updated code length: {len(updated_code)}")
            else:
                print(f"✅ PATCH GENERATOR: Code successfully modified by Morph API!")
                print(f"🔧 PATCH GENERATOR: Changes detected in response")
            
            # Create diff
            print(f"🔧 PATCH GENERATOR: Creating diff between original and updated code...")
            diff_lines = list(difflib.unified_diff(
                original_code.splitlines(keepends=True),
                updated_code.splitlines(keepends=True),
                fromfile=plan.patch_spec.get("file", "original"),
                tofile=plan.patch_spec.get("file", "updated"),
                lineterm=""
            ))
            print(f"🔧 PATCH GENERATOR: Diff created with {len(diff_lines)} lines")
            print(f"🔧 PATCH GENERATOR: Number of actual changes: {self._count_changed_lines(diff_lines)}")

            # 🔧 PRINT BEFORE AND AFTER CODE CHANGES
            print("\n" + "="*60)
            print("🔧 MORPH CODE CHANGES - BEFORE AND AFTER")
            print("="*60)
            print("📝 ORIGINAL CODE:")
            print(original_code)
            print("\n📝 UPDATED CODE:")
            print(updated_code)
            print("\n📝 DIFF LINES:")
            for line in diff_lines:
                if line.startswith('+') or line.startswith('-'):
                    print(line.rstrip())
            print("="*60)

            machine_diff = MachineDiff(
                file=plan.patch_spec.get("file", "unknown"),
                original_content=original_code,
                updated_content=updated_code,
                diff_lines=diff_lines,
                loc_changed=self._count_changed_lines(diff_lines)
            )

            # Extract reasoning from Morph API response if available
            reasoning = {}
            if "<reasoning>" in updated_code and "</reasoning>" in updated_code:
                try:
                    import re
                    reasoning_match = re.search(
                        r'<reasoning>(.*?)</reasoning>', 
                        updated_code, re.DOTALL
                    )
                    if reasoning_match:
                        reasoning["morph_reasoning"] = (
                            reasoning_match.group(1).strip()
                        )
                        # 🔧 PRINT MORPH REASONING
                        print("\n🧠 MORPH REASONING:")
                        print(reasoning["morph_reasoning"])
                        print("-" * 40)
                except Exception as e:
                    print(f"🔧 Could not extract reasoning: {e}")
            else:
                print("\n🔧 No reasoning found in Morph response")
                if len(updated_code) > 200:
                    print("Raw response preview:", updated_code[:200] + "...")
                else:
                    print("Raw response preview:", updated_code)

            # 🔧 Enhanced: Extract technical analysis and change summary
            technical_analysis = None
            change_summary = None
            
            if ("<technical_analysis>" in updated_code and 
                "</technical_analysis>" in updated_code):
                try:
                    import re
                    tech_match = re.search(
                        r'<technical_analysis>(.*?)</technical_analysis>', 
                        updated_code, re.DOTALL
                    )
                    if tech_match:
                        technical_analysis = tech_match.group(1).strip()
                        print("\n🔧 MORPH TECHNICAL ANALYSIS:")
                        print(technical_analysis)
                        print("-" * 40)
                except Exception as e:
                    print(f"🔧 Could not extract technical analysis: {e}")

            if ("<change_summary>" in updated_code and 
                "</change_summary>" in updated_code):
                try:
                    import re
                    summary_match = re.search(
                        r'<change_summary>(.*?)</change_summary>', 
                        updated_code, re.DOTALL
                    )
                    if summary_match:
                        change_summary = summary_match.group(1).strip()
                        print("\n🔧 MORPH CHANGE SUMMARY:")
                        print(change_summary)
                        print("-" * 40)
                except Exception as e:
                    print(f"🔧 Could not extract change summary: {e}")
            
            # Publish success event
            await event_bus.publish(Event(
                type=EventType.MORPH_APPLY_SUCCEEDED,
                key=trace_id,
                payload={
                    "file": machine_diff.file,
                    "loc_changed": machine_diff.loc_changed,
                    "diff_preview": diff_lines[:10] if diff_lines else [],
                    "reasoning": reasoning,
                    # 🔧 Enhanced: Pass detailed Morph API information
                    "technical_analysis": technical_analysis,
                    "change_summary": change_summary,
                    "original_code": original_code,
                    "updated_code": updated_code,
                    "diff_lines": diff_lines
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="patch_generated"
            ))

            print(f"✅ PATCH GENERATOR: Patch generation completed successfully!")
            print(f"🔧 PATCH GENERATOR: File: {machine_diff.file}")
            print(f"🔧 PATCH GENERATOR: Lines changed: {machine_diff.loc_changed}")
            print(f"🔧 PATCH GENERATOR: Diff preview: {diff_lines[:5] if diff_lines else 'No diff lines'}")

            # Publish completion log
            await self._publish_patch_log(trace_id, f"✅ Patch generation completed successfully!")
            await self._publish_patch_log(trace_id, f"🔧 File: {machine_diff.file}")
            await self._publish_patch_log(trace_id, f"🔧 Lines changed: {machine_diff.loc_changed}")

            return machine_diff

        except Exception as e:
            print(f"❌ PATCH GENERATOR: Patch generation failed with error: {e}")
            print(f"🔧 PATCH GENERATOR: Error type: {type(e).__name__}")
            
            # Publish failure log
            await self._publish_patch_log(trace_id, f"❌ Patch generation failed: {e}")
            
            await self._publish_failure_event(trace_id, str(e))
            return None

    def _create_update_snippet(self, patch_spec: Dict[str, Any], original_code: str) -> str:
        """Create natural language update instruction for Morph API"""

        change_type = patch_spec.get("type", "unknown")

        if change_type == "add_field":
            field_to_add = patch_spec.get("change", "").replace("+ ", "").strip("'\"")
            return f"Add the field '{field_to_add}' to the POLICY_FIELDS list"

        elif change_type == "add_default":
            field = patch_spec.get("field", "unknown_field")
            return f"Add a default value for the '{field}' field when it's missing"

        else:
            # Generic update
            change = patch_spec.get("change", "")
            return f"Apply this change: {change}"

    async def _call_morph_apply(self, original_code: str, update_snippet: str, trace_id: str) -> Optional[str]:
        """Call Morph Apply API to merge the update"""

        print(f"🔧 MORPH API: Starting API call...")
        print(f"🔧 MORPH API: Original code length: {len(original_code)}")
        print(f"🔧 MORPH API: Update snippet length: {len(update_snippet)}")
        
        # Publish log to frontend
        await self._publish_patch_log(trace_id, f"🔧 MORPH API: Starting API call...")
        await self._publish_patch_log(trace_id, f"🔧 MORPH API: Original code length: {len(original_code)}")
        await self._publish_patch_log(trace_id, f"🔧 MORPH API: Update snippet length: {len(update_snippet)}")

        print(f"🔧 MORPH API: Config check:")
        print(f"🔧 MORPH API: API key present: {bool(settings.morph_api_key)}")
        print(f"🔧 MORPH API: Key length: {len(settings.morph_api_key) if settings.morph_api_key else 0}")

        # Use simulation if no API key is set
        if not settings.morph_api_key or settings.morph_api_key == "":
            print("🔧 MORPH API: No API key configured - using simulation")
            return self._simulate_morph_apply(original_code, update_snippet)

        try:
            # Use OpenAI-compatible format as per Morph docs
            headers = {
                "Authorization": f"Bearer {settings.morph_api_key}",
                "Content-Type": "application/json"
            }

            # Simple, direct instruction for Morph API
            prompt = f"""You are a Python code modification expert. 

Here is the current Python code:
{original_code}

I need you to: {update_snippet}

Please modify the code to implement this change. Return only the modified Python code, no explanations or additional formatting.

The modified code should be ready to run and should include the requested change."""

            print(f"🔧 MORPH API: Simple prompt built, length: {len(prompt)}")
            print(f"🔧 MORPH API: Prompt: {prompt}")

            payload = {
                "model": "morph-v3-large",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            print(f"🔧 MORPH API: Sending request to Morph API...")
            response = await self.client.post(
                "https://api.morphllm.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30.0
            )

            print(f"🔧 MORPH API: Response received - Status: {response.status_code}")
            print(f"🔧 MORPH API: Response headers: {dict(response.headers)}")
            print(f"🔧 MORPH API: Response text length: {len(response.text)}")
            print(f"🔧 MORPH API: Response preview: {response.text[:300]}...")

            # Publish response log
            await self._publish_patch_log(trace_id, f"🔧 MORPH API: Response received - Status: {response.status_code}")
            await self._publish_patch_log(trace_id, f"🔧 MORPH API: Response length: {len(response.text)}")

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"🔧 MORPH API: Successfully extracted content, length: {len(content)}")
                return content
            else:
                print(f"🔧 MORPH API: Error response: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"🔧 MORPH API: Exception occurred: {e}")
            return None

    def _simulate_morph_apply(self, original_code: str, update_snippet: str) -> str:
        """Simulate Morph Apply API for demo purposes"""

        # Simple pattern matching for the return policy case
        if "Add the field 'return_policy'" in update_snippet and "POLICY_FIELDS" in original_code:
            # Find and update POLICY_FIELDS list
            lines = original_code.split('\n')
            updated_lines = []

            for line in lines:
                if 'POLICY_FIELDS = [' in line and ']' in line:
                    # Single line list - add field
                    line = line.replace(']', ', "return_policy"]')
                elif 'POLICY_FIELDS = [' in line:
                    # Multi-line list start
                    updated_lines.append(line)
                    continue
                elif line.strip().endswith(']') and any('POLICY_FIELDS' in prev_line for prev_line in updated_lines[-3:]):
                    # Multi-line list end - add field before closing
                    line = line.replace(']', ', "return_policy"]')

                updated_lines.append(line)

            updated_code = '\n'.join(updated_lines)
            print("🔧 SIMULATION: Applied return_policy field to POLICY_FIELDS")
            return updated_code

        # For other cases, return original with a comment
        print("🔧 SIMULATION: No specific pattern matched, returning original code")
        return original_code

    def _extract_updated_code_from_response(self, raw_response: str, original_code: str) -> str:
        """Extract the updated code from Morph API response."""
        print(f"🔧 EXTRACTOR: Starting response extraction...")
        print(f"🔧 EXTRACTOR: Raw response length: {len(raw_response)}")
        
        # Morph now returns just the modified code, so use the response directly
        updated_code = raw_response.strip()
        
        print(f"🔧 EXTRACTOR: Using response directly as updated code")
        print(f"🔧 EXTRACTOR: Updated code length: {len(updated_code)}")
        print(f"🔧 EXTRACTOR: Updated code preview: {updated_code[:200]}...")
        
        # Check if code was actually modified
        if updated_code == original_code:
            print("⚠️ EXTRACTOR: WARNING - No changes detected! Code is identical to original")
            print(f"🔧 EXTRACTOR: Original code: {original_code[:100]}...")
            print(f"🔧 EXTRACTOR: Updated code: {updated_code[:100]}...")
            return original_code  # Return original if no changes
        else:
            print("✅ EXTRACTOR: Changes detected! Code was modified by Morph API")
            return updated_code

    def _estimate_loc_change(self, patch_spec: Dict[str, Any]) -> int:
        """Estimate lines of code that will change"""
        change_type = patch_spec.get("type", "unknown")

        if change_type == "add_field":
            return 1
        elif change_type == "add_default":
            return 2
        else:
            return 5  # Conservative estimate

    def _count_changed_lines(self, diff_lines: List[str]) -> int:
        """Count actual changed lines from diff"""
        changed = 0
        for line in diff_lines:
            if line.startswith('+') or line.startswith('-'):
                if not line.startswith('+++') and not line.startswith('---'):
                    changed += 1
        return changed

    async def _publish_failure_event(self, trace_id: str, error: str):
        """Publish patch generation failure event"""
        await event_bus.publish(Event(
            type=EventType.MORPH_APPLY_FAILED,
            key=trace_id,
            payload={"error": error},
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="patch_failed"
        ))

    async def _publish_patch_log(self, trace_id: str, log_message: str):
        """Publish patch generation log to event bus"""
        await event_bus.publish(Event(
            type=EventType.PATCH_LOG,
            key=trace_id,
            payload={"log_message": log_message},
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="patch_log"
        ))

# Global patch generator instance
patch_generator = PatchGenerator() 