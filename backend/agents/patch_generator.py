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
        """Generate a patch based on the RCA plan"""

        print(f"\n🔧 PATCH GENERATOR: Starting patch generation for trace {trace_id}")
        print(f"🔧 PATCH GENERATOR: File to modify: {plan.patch_spec.get('file', 'unknown')}")
        print(f"🔧 PATCH GENERATOR: Change type: {plan.patch_spec.get('type', 'unknown')}")
        print(f"🔧 PATCH GENERATOR: Risk score: {plan.risk_score}")

        # Publish log to frontend
        await self._publish_patch_log(
            trace_id, 
            f"🔧 Starting patch generation for {plan.patch_spec.get('file', 'unknown')}"
        )
        await self._publish_patch_log(
            trace_id, 
            f"🔧 Change type: {plan.patch_spec.get('type', 'unknown')}"
        )
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
            print("🔧 PATCH GENERATOR: Creating update snippet...")
            await self._publish_patch_log(trace_id, "🔧 Creating update snippet...")
            update_snippet = self._create_update_snippet(
                plan.patch_spec, original_code
            )
            print(f"🔧 PATCH GENERATOR: Update snippet created: {update_snippet[:100]}...")
            await self._publish_patch_log(trace_id, f"🔧 Update snippet: {update_snippet}")

            # Call Morph API
            print("🔧 PATCH GENERATOR: Calling Morph API...")
            await self._publish_patch_log(trace_id, "🔧 Calling Morph API...")
            raw_response = await self._call_morph_apply(
                original_code, update_snippet, trace_id
            )

            if not raw_response:
                print("🔧 PATCH GENERATOR: Morph API call failed - no response")
                await self._publish_failure_event(
                    trace_id, "Morph API call failed"
                )
                return None

            print(f"🔧 PATCH GENERATOR: Morph API response received, length: {len(raw_response)}")
            print(f"🔧 PATCH GENERATOR: Raw response preview: {raw_response[:200]}...")

            # Extract the actual updated code from Morph response
            print("🔧 PATCH GENERATOR: Extracting updated code from response...")
            updated_code = self._extract_updated_code_from_response(raw_response, original_code)
            print(f"🔧 PATCH GENERATOR: Updated code extracted, length: {len(updated_code)}")
            
            # Check if code was actually modified
            if updated_code == original_code:
                print("⚠️ PATCH GENERATOR: WARNING - No changes detected in Morph response!")
                print(f"🔧 PATCH GENERATOR: Original code length: {len(original_code)}")
                print(f"🔧 PATCH GENERATOR: Updated code length: {len(updated_code)}")
            else:
                print("✅ PATCH GENERATOR: Code successfully modified by Morph API!")
                print("🔧 PATCH GENERATOR: Changes detected in response")
            
            # Create diff
            print("🔧 PATCH GENERATOR: Creating diff between original and updated code...")
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

            # 🔧 OPTIMIZED: Remove verbose AI recommendations for speed
            # Only extract essential information needed for the frontend
            
            # Publish success event with essential information only
            await event_bus.publish(Event(
                type=EventType.MORPH_APPLY_SUCCEEDED,
                key=trace_id,
                payload={
                    "file": plan.patch_spec.get("file", "unknown"),
                    "loc_changed": machine_diff.loc_changed,
                    "diff_preview": diff_lines[-10:] if len(diff_lines) > 10 else diff_lines,
                    "original_code": original_code,
                    "updated_code": updated_code
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="patch_generated"
            ))

            return machine_diff

        except Exception as e:
            print(f"🔧 PATCH GENERATOR: Error during patch generation: {e}")
            await self._publish_failure_event(trace_id, f"Patch generation error: {str(e)}")
            return None

    def _create_update_snippet(self, patch_spec: Dict[str, Any], original_code: str) -> str:
        """Create simple update instruction for Morph API - focused on quick fixes"""

        # 🔧 OPTIMIZED: Simple, direct instructions for faster processing
        change_type = patch_spec.get("type", "unknown")
        file_path = patch_spec.get("file", "unknown")
        change = patch_spec.get("change", "")
        
        # Create a simple, direct instruction
        simple_instruction = f"""
Fix this issue in {file_path}:
- Type: {change_type}
- Change needed: {change}

Make the minimal necessary changes to fix the issue.
"""
        
        return simple_instruction.strip()

    def _get_detailed_change_instruction(self, patch_spec: Dict[str, Any], change_type: str) -> str:
        """Get detailed change instruction based on change type"""
        
        if change_type == "add_field":
            field_to_add = patch_spec.get("change", "").replace("+ ", "").strip("'\"")
            return f"Add the field '{field_to_add}' to the POLICY_FIELDS list in the configuration"
        
        elif change_type == "add_default":
            field = patch_spec.get("field", "unknown_field")
            return f"Add a default value for the '{field}' field when it's missing from the data"
        
        else:
            # Generic update with full context
            change = patch_spec.get("change", "")
            return f"Apply this specific change: {change}"

    async def _call_morph_apply(self, original_code: str, update_snippet: str, trace_id: str) -> Optional[str]:
        """Call Morph Apply API to merge the update"""

        print("🔧 MORPH API: Starting API call...")
        print(f"🔧 MORPH API: Original code length: {len(original_code)}")
        print(f"🔧 MORPH API: Update snippet length: {len(update_snippet)}")
        
        # Publish log to frontend
        await self._publish_patch_log(
            trace_id, "🔧 MORPH API: Starting API call..."
        )
        await self._publish_patch_log(
            trace_id, 
            f"🔧 MORPH API: Original code length: {len(original_code)}"
        )
        await self._publish_patch_log(
            trace_id, 
            f"🔧 MORPH API: Update snippet length: {len(update_snippet)}"
        )

        print("🔧 MORPH API: Config check:")
        print(f"🔧 MORPH API: API key present: {bool(settings.morph_api_key)}")
        print(f"🔧 MORPH API: Key length: {len(settings.morph_api_key) if settings.morph_api_key else 0}")

        # Use simulation if no API key is set
        if not settings.morph_api_key or settings.morph_api_key == "":
            print("🔧 MORPH API: No API key configured - using simulation")
            return self._simulate_morph_apply(original_code, update_snippet)

        try:
            # 🔧 OPTIMIZED: Simplified prompt for faster processing
            prompt = f"""Fix this Python code:

{original_code}

Issue: {update_snippet}

Return ONLY the fixed Python code."""

            print("🔧 MORPH API: Simplified prompt built")
            print(f"🔧 MORPH API: Prompt preview: {prompt[:100]}...")

            payload = {
                "model": "morph-v3-large",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # Low temperature for consistent code generation
                "max_tokens": 1000   # 🔧 REDUCED: Smaller token limit for speed
            }

            print("🔧 MORPH API: Sending request to Morph API...")
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
            await self._publish_patch_log(
                trace_id, 
                f"🔧 MORPH API: Response received - Status: {response.status_code}"
            )
            await self._publish_patch_log(
                trace_id, 
                f"🔧 MORPH API: Response length: {len(response.text)}"
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"🔧 MORPH API: Successfully extracted content, length: {len(content)}")
                
                # Clean up the response - remove any markdown formatting
                cleaned_content = self._clean_morph_response(content)
                print(f"🔧 MORPH API: Cleaned content length: {len(cleaned_content)}")
                
                return cleaned_content
            else:
                print(f"🔧 MORPH API: Error response: {response.status_code} - {response.text}")
                await self._publish_patch_log(
                    trace_id, f"❌ MORPH API Error: {response.status_code}"
                )
                return None

        except Exception as e:
            print(f"🔧 MORPH API: Exception occurred: {e}")
            await self._publish_patch_log(
                trace_id, f"❌ MORPH API Exception: {str(e)}"
            )
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

    def _clean_morph_response(self, response: str) -> str:
        """Clean up Morph API response to extract just the code"""
        # Remove markdown code blocks
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # Remove markdown code blocks without language
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # Remove any leading/trailing whitespace and common prefixes
        cleaned = response.strip()
        if cleaned.startswith("Here's the modified code:"):
            cleaned = cleaned[26:].strip()
        if cleaned.startswith("Modified code:"):
            cleaned = cleaned[15:].strip()
        
        return cleaned

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