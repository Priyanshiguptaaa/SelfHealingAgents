import os
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional
from models.events import Event, EventType, MachineDiff
from services.event_bus import event_bus

class PatchApplier:
    """Service for applying code patches with rollback capability"""
    
    def __init__(self):
        self.backup_dir = tempfile.mkdtemp(prefix="selfheal_backup_")
        self.applied_patches = {}
    
    async def apply_patch(self, diff: MachineDiff, trace_id: str) -> bool:
        """Apply a patch to the target file with backup for rollback"""
        
        try:
            file_path = diff.file
            
            # Create backup
            backup_path = await self._create_backup(file_path, trace_id)
            if not backup_path:
                return False
            
            # For demo purposes, we'll simulate file writing
            # In production, this would write to the actual file system
            print(f"📝 Applying patch to {file_path}")
            print(f"💾 Backup created at {backup_path}")
            
            # Simulate writing the updated content
            success = await self._write_file_content(file_path, diff.updated_content)
            
            if success:
                # Track the applied patch for potential rollback
                self.applied_patches[trace_id] = {
                    "file": file_path,
                    "backup_path": backup_path,
                    "applied_at": datetime.now()
                }
                
                # Publish reload event
                await event_bus.publish(Event(
                    type=EventType.RELOAD_DONE,
                    key=trace_id,
                    payload={
                        "file": file_path,
                        "service": "catalog_sync",
                        "pid": os.getpid(),
                        "status": "reloaded"
                    },
                    ts=datetime.now(),
                    trace_id=trace_id,
                    ui_hint="service_reloaded"
                ))
                
                print(f"✅ Patch applied successfully to {file_path}")
                return True
            else:
                # Cleanup backup on failure
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return False
                
        except Exception as e:
            print(f"❌ Error applying patch: {str(e)}")
            return False
    
    async def rollback_patch(self, file_path: str, trace_id: str) -> bool:
        """Rollback a previously applied patch"""
        
        if trace_id not in self.applied_patches:
            print(f"⚠️ No patch found to rollback for trace {trace_id}")
            return False
        
        try:
            patch_info = self.applied_patches[trace_id]
            backup_path = patch_info["backup_path"]
            
            if not os.path.exists(backup_path):
                print(f"❌ Backup file not found: {backup_path}")
                return False
            
            # Restore from backup
            success = await self._restore_from_backup(file_path, backup_path)
            
            if success:
                # Clean up
                os.remove(backup_path)
                del self.applied_patches[trace_id]
                
                print(f"🔄 Successfully rolled back patch for {file_path}")
                return True
            else:
                print(f"❌ Failed to rollback patch for {file_path}")
                return False
                
        except Exception as e:
            print(f"❌ Error during rollback: {str(e)}")
            return False
    
    async def _create_backup(self, file_path: str, trace_id: str) -> Optional[str]:
        """Create a backup of the original file"""
        
        try:
            # For demo purposes, create a simulated backup
            backup_filename = f"{trace_id}_{os.path.basename(file_path)}.backup"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # In a real system, this would copy the actual file
            # For demo, we'll create a placeholder backup
            original_content = await self._read_original_content(file_path)
            
            with open(backup_path, 'w') as backup_file:
                backup_file.write(original_content)
            
            return backup_path
            
        except Exception as e:
            print(f"❌ Error creating backup: {str(e)}")
            return None
    
    async def _read_original_content(self, file_path: str) -> str:
        """Read the original content of a file"""
        
        # For demo purposes, return the sample catalog_sync.py content
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
        
        return "# Original file content"
    
    async def _write_file_content(self, file_path: str, content: str) -> bool:
        """Write content to a file (simulated for demo)"""
        
        try:
            # In production, this would write to the actual file
            print(f"📝 Writing {len(content)} characters to {file_path}")
            
            # For demo, just log the change
            if "return_policy" in content and "POLICY_FIELDS" in content:
                print("✅ Successfully added 'return_policy' to POLICY_FIELDS")
            
            return True
            
        except Exception as e:
            print(f"❌ Error writing file: {str(e)}")
            return False
    
    async def _restore_from_backup(self, file_path: str, backup_path: str) -> bool:
        """Restore file from backup"""
        
        try:
            with open(backup_path, 'r') as backup_file:
                original_content = backup_file.read()
            
            return await self._write_file_content(file_path, original_content)
            
        except Exception as e:
            print(f"❌ Error restoring from backup: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up backup directory"""
        if os.path.exists(self.backup_dir):
            shutil.rmtree(self.backup_dir)

# Global patch applier instance
patch_applier = PatchApplier() 