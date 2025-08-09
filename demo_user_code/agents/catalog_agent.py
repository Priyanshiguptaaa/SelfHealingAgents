"""Catalog synchronization agent for e-commerce system"""
import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from models.product import Product
from services.catalog_sync import CatalogSync

# Import healing system components to emit signals
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))
try:
    from models.events import Event, EventType
    from services.event_bus import event_bus
    HEALING_SYSTEM_AVAILABLE = True
except ImportError:
    print("⚠️ Healing system not available - running in standalone mode")
    HEALING_SYSTEM_AVAILABLE = False


class CatalogAgent:
    """Autonomous agent that manages catalog synchronization and updates"""
    
    def __init__(self):
        self.catalog_sync = CatalogSync("https://external-catalog-api.com")
        self.running = False
        self.sync_interval = 300  # 5 minutes
        self.product_cache = {}
        self._load_catalog_data()
    
    def _load_catalog_data(self):
        """Load catalog data from external source"""
        data_path = Path(__file__).parent.parent.parent / "data"
        products_file = data_path / "products_after.jsonl"
        
        if products_file.exists():
            with open(products_file, 'r') as f:
                for line in f:
                    if line.strip():
                        product_data = json.loads(line)
                        # Set return policy based on clearance status
                        if product_data.get("is_clearance", False):
                            product_data["return_policy"] = (
                                "FINAL_SALE_NO_RETURNS"
                            )
                        else:
                            product_data["return_policy"] = "30_DAY_RETURN"
                        
                        sku = product_data["sku"]
                        self.product_cache[sku] = product_data
    
    async def start(self):
        """Start the catalog agent"""
        self.running = True
        print("🛒 Catalog Agent started - monitoring for updates")
        
        # Start background sync process
        asyncio.create_task(self._sync_loop())
    
    async def stop(self):
        """Stop the catalog agent"""
        self.running = False
        print("🛒 Catalog Agent stopped")
    
    async def _sync_loop(self):
        """Background loop for periodic catalog synchronization"""
        while self.running:
            try:
                await self._perform_sync()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                print(f"🛒 Catalog sync error: {e}")
                await asyncio.sleep(30)  # Retry in 30 seconds
    
    async def _perform_sync(self):
        """Perform catalog synchronization"""
        print("🛒 Performing catalog sync...")
        
        # Sync each product in cache
        for sku in self.product_cache.keys():
            try:
                # This calls the buggy sync that misses return_policy
                synced_data = await self.catalog_sync.sync_product(sku)
                
                # Update cache with synced data
                if synced_data:
                    original_data = self.product_cache[sku].copy()
                    self.product_cache[sku].update(synced_data)
                    
                    # Check if sync lost important data
                    if ("return_policy" in original_data and 
                            "return_policy" not in synced_data):
                        print(f"⚠️ Sync issue: return_policy lost for {sku}")
                        
            except Exception as e:
                print(f"🛒 Sync failed for {sku}: {e}")
    
    async def get_product(self, sku: str) -> Optional[Product]:
        """Get product data - this is where the bug manifests"""
        if sku not in self.product_cache:
            return None
        
        # Get the potentially buggy synced data
        product_data = self.product_cache[sku]
        return Product.from_catalog_data(product_data)
    
    async def process_return_request(self, sku: str, order_id: str) -> Dict[str, Any]:
        """Process return eligibility request - autonomous action"""
        print(f"🛒 Processing return request for {sku}, order {order_id}")
        
        product = await self.get_product(sku)
        
        if not product:
            return {
                "status": "error",
                "error": "Product not found",
                "sku": sku,
                "order_id": order_id
            }
        
        # Schema validation - this is where the failure occurs
        if not product.return_policy:
            # Agent detects the issue and emits non-human signal
            print(f"🚨 Schema validation failed for {sku}: return_policy missing")
            
            # EMIT NON-HUMAN SIGNAL to healing system
            await self._emit_healing_signal(sku, order_id, 
                "Schema validation failed: return_policy missing")
            
            raise ValueError(
                f"Schema validation failed: return_policy missing for SKU {sku}"
            )
        
        # Process the request
        eligible = product.return_policy != "FINAL_SALE_NO_RETURNS"
        
        result = {
            "status": "success",
            "sku": sku,
            "order_id": order_id,
            "eligible": eligible,
            "return_policy": product.return_policy,
            "reason": "Final sale item" if not eligible else "Standard return",
            "is_clearance": product.is_clearance,
            "processed_at": datetime.now().isoformat()
        }
        
        success_msg = "✅ Eligible" if eligible else "❌ Not eligible"
        print(f"🛒 Return request processed: {success_msg}")
        return result
    
    async def _emit_healing_signal(self, sku: str, order_id: str, error: str):
        """Emit non-human signal to trigger healing system"""
        if not HEALING_SYSTEM_AVAILABLE:
            print("🚨 Would emit healing signal but system not available")
            return
        
        import uuid
        trace_id = str(uuid.uuid4())
        
        # Create the non-human signal that triggers healing
        failure_event = Event(
            type=EventType.RETURN_API_FAILURE,
            key=f"order_{order_id}",
            payload={
                "sku": sku,
                "order_id": order_id,
                "endpoint": "CheckReturnEligibility",
                "error_type": "SchemaMismatch",
                "field": "return_policy",
                "detail": "return_policy field missing from catalog sync",
                "catalog_sync_file": "services/catalog_sync.py",
                "customer_impact": "Unable to process return request",
                "source_system": "ecommerce_catalog_agent",
                "severity": "high"
            },
            ts=datetime.now(),
            trace_id=trace_id
        )
        
        print(f"🚨 Emitting non-human healing signal: {trace_id}")
        
        # This triggers our healing system
        await event_bus.publish(failure_event)
        
        return trace_id


# Global catalog agent instance
catalog_agent = CatalogAgent() 