import re
import os
from typing import List, Dict, Any
from models.events import MachineDiff, GuardrailCheck
from config import settings

class GuardrailService:
    """Safety validation for code patches before application"""
    
    def __init__(self):
        self.rules = [
            self._check_file_allowlist,
            self._check_file_forbidden,
            self._check_patch_size,
            self._check_no_secrets,
            self._check_no_dangerous_operations
        ]
    
    async def validate_patch(self, diff: MachineDiff) -> List[GuardrailCheck]:
        """Run all guardrail checks on a patch"""
        checks = []
        
        for rule in self.rules:
            try:
                check = await rule(diff)
                checks.append(check)
            except Exception as e:
                checks.append(GuardrailCheck(
                    rule=rule.__name__,
                    passed=False,
                    message=f"Guardrail check failed: {str(e)}",
                    risk_score=1.0
                ))
        
        return checks
    
    def is_patch_safe(self, checks: List[GuardrailCheck]) -> bool:
        """Determine if patch passes all critical safety checks"""
        for check in checks:
            if not check.passed and check.risk_score > 0.5:
                return False
        return True
    
    def calculate_total_risk(self, checks: List[GuardrailCheck]) -> float:
        """Calculate total risk score from all checks"""
        if not checks:
            return 1.0
            
        total_risk = sum(check.risk_score for check in checks if not check.passed)
        return min(total_risk / len(checks), 1.0)
    
    async def _check_file_allowlist(self, diff: MachineDiff) -> GuardrailCheck:
        """Check if file is in allowed patterns"""
        file_path = diff.file
        
        for pattern in settings.allowed_file_patterns:
            if re.match(pattern.replace("*", ".*"), file_path):
                return GuardrailCheck(
                    rule="file_allowlist",
                    passed=True,
                    message=f"File {file_path} matches allowed pattern {pattern}",
                    risk_score=0.0
                )
        
        return GuardrailCheck(
            rule="file_allowlist",
            passed=False,
            message=f"File {file_path} not in allowed patterns",
            risk_score=0.8
        )
    
    async def _check_file_forbidden(self, diff: MachineDiff) -> GuardrailCheck:
        """Check if file is in forbidden patterns"""
        file_path = diff.file
        
        for pattern in settings.forbidden_file_patterns:
            if re.match(pattern.replace("*", ".*"), file_path):
                return GuardrailCheck(
                    rule="file_forbidden",
                    passed=False,
                    message=f"File {file_path} matches forbidden pattern {pattern}",
                    risk_score=1.0
                )
        
        return GuardrailCheck(
            rule="file_forbidden",
            passed=True,
            message=f"File {file_path} not in forbidden patterns",
            risk_score=0.0
        )
    
    async def _check_patch_size(self, diff: MachineDiff) -> GuardrailCheck:
        """Check if patch size is within limits"""
        loc_changed = diff.loc_changed
        max_lines = settings.max_patch_size_lines
        
        if loc_changed <= max_lines:
            return GuardrailCheck(
                rule="patch_size",
                passed=True,
                message=f"Patch size {loc_changed} lines within limit {max_lines}",
                risk_score=0.0
            )
        
        risk_score = min((loc_changed - max_lines) / max_lines, 1.0)
        return GuardrailCheck(
            rule="patch_size",
            passed=False,
            message=f"Patch size {loc_changed} lines exceeds limit {max_lines}",
            risk_score=risk_score
        )
    
    async def _check_no_secrets(self, diff: MachineDiff) -> GuardrailCheck:
        """Check for potential secrets in the patch"""
        content = diff.updated_content.lower()
        
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'["\'][a-f0-9]{32,}["\']',  # Hex strings that might be secrets
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, content):
                return GuardrailCheck(
                    rule="no_secrets",
                    passed=False,
                    message="Potential secret detected in patch",
                    risk_score=1.0
                )
        
        return GuardrailCheck(
            rule="no_secrets",
            passed=True,
            message="No secrets detected",
            risk_score=0.0
        )
    
    async def _check_no_dangerous_operations(self, diff: MachineDiff) -> GuardrailCheck:
        """Check for dangerous operations in the patch"""
        content = diff.updated_content.lower()
        
        dangerous_patterns = [
            r'os\.system\s*\(',
            r'subprocess\.',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'open\s*\(.+["\']w["\']',  # File writes
            r'rm\s+-rf',
            r'delete\s+from\s+\w+\s*;',  # SQL deletes without WHERE
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content):
                return GuardrailCheck(
                    rule="no_dangerous_ops",
                    passed=False,
                    message=f"Dangerous operation detected: {pattern}",
                    risk_score=0.9
                )
        
        return GuardrailCheck(
            rule="no_dangerous_ops",
            passed=True,
            message="No dangerous operations detected",
            risk_score=0.0
        )

# Global guardrails instance
guardrails = GuardrailService() 