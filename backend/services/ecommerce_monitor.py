"""E-commerce system monitoring service"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add demo_user_code to path so we can import from it
demo_path = Path(__file__).parent.parent.parent / "demo_user_code"
sys.path.insert(0, str(demo_path))

from services.product_service import ProductService
from models.events import Event, EventType
from services.event_bus import event_bus


class EcommerceMonitor:
    """Monitors the e-commerce system for failures and emits healing events"""
    
    def __init__(self):
        self.product_service = ProductService()
        self.monitoring = False
    
    async def simulate_customer_request(self, sku: str, order_id: str) -> Dict[str, Any]:
        """Simulate a customer trying to return an item"""
        try:
            # This will trigger the schema validation failure
            result = await self.product_service.check_return_eligibility(sku, order_id)
            return {
                "status": "success",
                "result": result
            }
        except ValueError as e:
            # Schema validation failure detected!
            await self._emit_failure_event(sku, order_id, str(e))
            return {
                "status": "failure", 
                "error": str(e),
                "sku": sku,
                "order_id": order_id
            }
    
    async def _emit_failure_event(self, sku: str, order_id: str, error: str):
        """Emit a failure event that triggers the healing system"""
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
                "customer_impact": "Unable to process return request"
            },
            ts=datetime.now(),
            trace_id=trace_id
        )
        
        print(f"🚨 E-commerce failure detected: {error}")
        print(f"📡 Emitting healing event for trace {trace_id}")
        
        # This triggers our healing system
        await event_bus.publish(failure_event)
        
        return trace_id


# Global monitor instance
ecommerce_monitor = EcommerceMonitor() 