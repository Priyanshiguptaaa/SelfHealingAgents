import httpx
import difflib
from datetime import datetime
from typing import Dict, Any, Optional, List
from models.events import Event, EventType, RCAPlan, MachineDiff
from services.event_bus import event_bus
from config import settings

class PatchGenerator:
    """Patch Generator Agent - converts RCA plans into executable code patches using Morph API"""
    
    def __init__(self):
        self.morph_base_url = "https://api.morph.com/v1"
        self.client = httpx.AsyncClient()
        
    async def generate_patch(self, plan: RCAPlan, original_code: str, trace_id: str) -> Optional[MachineDiff]:
        """Generate machine diff using Morph Apply API"""
        
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
            update_snippet = self._create_update_snippet(plan.patch_spec, original_code)
            
            # Call Morph Apply API
            updated_code = await self._call_morph_apply(original_code, update_snippet)
            
            if not updated_code:
                await self._publish_failure_event(trace_id, "Morph API call failed")
                return None
                
            # Create diff
            diff_lines = list(difflib.unified_diff(
                original_code.splitlines(keepends=True),
                updated_code.splitlines(keepends=True),
                fromfile=plan.patch_spec.get("file", "original"),
                tofile=plan.patch_spec.get("file", "updated"),
                lineterm=""
            ))
            
            machine_diff = MachineDiff(
                file=plan.patch_spec.get("file", "unknown"),
                original_content=original_code,
                updated_content=updated_code,
                diff_lines=diff_lines,
                loc_changed=self._count_changed_lines(diff_lines)
            )
            
            # Publish success event
            await event_bus.publish(Event(
                type=EventType.MORPH_APPLY_SUCCEEDED,
                key=trace_id,
                payload={
                    "file": machine_diff.file,
                    "loc_changed": machine_diff.loc_changed,
                    "diff_preview": diff_lines[:10] if diff_lines else []
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="patch_generated"
            ))
            
            return machine_diff
            
        except Exception as e:
            await self._publish_failure_event(trace_id, str(e))
            return None
    
    def _create_update_snippet(self, patch_spec: Dict[str, Any], original_code: str) -> str:
        """Create update snippet based on patch specification"""
        
        change_type = patch_spec.get("type", "unknown")
        
        if change_type == "add_field":
            # For adding a field to a list
            field_to_add = patch_spec.get("change", "").replace("+ ", "").strip("'\"")
            anchor = patch_spec.get("anchor", "")
            
            return f"""
<update>
Add '{field_to_add}' to the {anchor} list in the appropriate location.
If {anchor} is a list like ["field1", "field2"], add "{field_to_add}" to it.
</update>
"""
        
        elif change_type == "add_default":
            field = patch_spec.get("field", "unknown_field")
            return f"""
<update>
Add a default value for the '{field}' field when it's missing.
Add a fallback like: {field} = response.get('{field}', 'DEFAULT_VALUE')
</update>
"""
        
        else:
            # Generic update based on change description
            change = patch_spec.get("change", "")
            return f"""
<update>
{change}
</update>
"""
    
    async def _call_morph_apply(self, original_code: str, update_snippet: str) -> Optional[str]:
        """Call Morph Apply API to merge the update"""
        
        # For demo purposes, simulate Morph API behavior
        # In production, you'd call the actual Morph API
        if settings.morph_api_key == "your_morph_api_key_here":
            return self._simulate_morph_apply(original_code, update_snippet)
            
        try:
            headers = {
                "Authorization": f"Bearer {settings.morph_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "original_code": original_code,
                "update": update_snippet,
                "model": "morph-apply-v1"
            }
            
            response = await self.client.post(
                f"{self.morph_base_url}/apply",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("updated_code")
            else:
                print(f"Morph API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling Morph API: {e}")
            return None
    
    def _simulate_morph_apply(self, original_code: str, update_snippet: str) -> str:
        """Simulate Morph Apply API for demo purposes"""
        
        # Simple pattern matching for the return policy case
        if "Add 'return_policy'" in update_snippet and "POLICY_FIELDS" in original_code:
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
            
            return '\n'.join(updated_lines)
        
        # For other cases, return original with a comment
        return original_code + f"\n# TODO: Apply update - {update_snippet[:50]}..."
    
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

# Global patch generator instance
patch_generator = PatchGenerator() 