import asyncio
import json
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from models.events import Event, EventType
from services.event_bus import event_bus
from services.orchestrator import orchestrator


# Request/Response Models
class TriggerFailureRequest(BaseModel):
    sku: str = "SKU-123"
    order_id: str = "8734"
    endpoint: str = "CheckReturnEligibility"


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("🚀 Starting Self-Healing E-commerce System")
    
    # Connect to Redis
    await event_bus.connect()
    
    # Start the healing orchestrator in the background
    orchestrator_task = asyncio.create_task(orchestrator.start())
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Self-Healing E-commerce System")
    await orchestrator.stop()
    orchestrator_task.cancel()
    await event_bus.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Self-Healing E-commerce Agents",
    description="Autonomous reactive agents for real-time issue detection and healing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with system health"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )

@app.post("/api/trigger-failure")
async def trigger_failure(request: TriggerFailureRequest):
    """Trigger a schema validation failure to demonstrate healing"""
    
    trace_id = str(uuid.uuid4())
    
    # Create a return API failure event
    failure_event = Event(
        type=EventType.RETURN_API_FAILURE,
        key=f"order_{request.order_id}",
        payload={
            "sku": request.sku,
            "order_id": request.order_id,
            "endpoint": request.endpoint,
            "detail": "return_policy missing",
            "error_type": "SchemaMismatch"
        },
        ts=datetime.now(),
        trace_id=trace_id
    )
    
    # Publish the event to trigger healing
    await event_bus.publish(failure_event)
    
    return {
        "message": "Failure event triggered",
        "trace_id": trace_id,
        "status": "healing_initiated"
    }

@app.get("/api/events/stream")
async def stream_events():
    """Server-Sent Events stream for real-time updates"""
    
    async def event_stream():
        """Generate SSE events"""
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"
        
        # Subscribe to all events
        try:
            async for event in event_bus.subscribe():
                # Format as SSE
                event_data = {
                    "type": event.type.value,
                    "key": event.key,
                    "payload": event.payload,
                    "timestamp": event.ts.isoformat(),
                    "trace_id": event.trace_id,
                    "ui_hint": event.ui_hint
                }
                
                yield f"data: {json.dumps(event_data)}\n\n"
                
        except asyncio.CancelledError:
            yield f"data: {json.dumps({'type': 'disconnected', 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get all events for a specific trace"""
    
    events = await event_bus.get_events_for_trace(trace_id)
    
    return {
        "trace_id": trace_id,
        "events": [
            {
                "type": event.type.value,
                "key": event.key,
                "payload": event.payload,
                "timestamp": event.ts.isoformat(),
                "ui_hint": event.ui_hint
            }
            for event in events
        ],
        "total_events": len(events)
    }

@app.get("/api/active-healings")
async def get_active_healings():
    """Get currently active healing processes"""
    
    return {
        "active_healings": orchestrator.active_healings,
        "total_active": len(orchestrator.active_healings)
    }

@app.post("/api/ecommerce/return-eligibility")
async def check_return_eligibility(sku: str, order_id: str):
    """Simulate the CheckReturnEligibility endpoint that can fail"""
    
    # Simulate the catalog lookup that might be missing return_policy
    # This would normally query your product database
    
    # For demo: randomly fail sometimes to show healing in action
    import random
    if random.random() < 0.3:  # 30% chance of failure
        # Simulate missing return_policy field
        return {
            "sku": sku,
            "order_id": order_id,
            "eligibility": False,
            # "return_policy": None  # Missing field!
        }
    
    # Normal success response
    return {
        "sku": sku,
        "order_id": order_id,
        "eligibility": True,
        "return_policy": "30_DAY_RETURN",
        "processed_at": datetime.now().isoformat()
    }

@app.get("/api/demo/sample-code")
async def get_sample_code():
    """Get the sample catalog_sync.py code for demo purposes"""
    
    sample_code = '''#!/usr/bin/env python3
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
    
    return {
        "filename": "services/catalog_sync.py",
        "content": sample_code,
        "issue": "POLICY_FIELDS is missing 'return_policy' field"
    }

@app.post("/api/replay/{trace_id}")
async def replay_request(trace_id: str):
    """Replay the original failing request for a trace"""
    try:
        # Get the trace events
        events = await event_bus.get_events_for_trace(trace_id)
        if not events:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        # Find the original trace step
        trace_start_event = next((e for e in events if e.type == EventType.TRACE_START), None)
        if not trace_start_event:
            raise HTTPException(status_code=400, detail="No trace start found")
        
        # Simulate replay
        from services.verifier import verifier
        from services.orchestrator import orchestrator
        
        # Create a mock trace step for verification
        trace_step = orchestrator._create_trace_step_from_event(trace_start_event, trace_id)
        
        # Run verification
        outcome = await verifier.verify_fix(trace_step, trace_id)
        
        return {
            "trace_id": trace_id,
            "status": "success" if outcome else "failed",
            "outcome": outcome.dict() if outcome else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rollback/{trace_id}")
async def rollback_patch(trace_id: str):
    """Rollback a previously applied patch"""
    try:
        from services.patch_applier import patch_applier
        
        # Attempt rollback
        success = await patch_applier.rollback_patch("services/catalog_sync.py", trace_id)
        
        if success:
            # Publish rollback event
            await event_bus.publish(Event(
                type=EventType.HEAL_COMPLETED,
                key=trace_id,
                payload={
                    "status": "rolled_back",
                    "message": "Patch successfully rolled back",
                    "duration_seconds": 1.2
                },
                ts=datetime.now(),
                trace_id=trace_id,
                ui_hint="rollback_complete"
            ))
            
            return {
                "trace_id": trace_id,
                "status": "success",
                "message": "Patch rolled back successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Rollback failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/approve/{trace_id}")
async def approve_patch(trace_id: str):
    """Manually approve a patch when auto-heal is disabled"""
    try:
        # Get the trace events to find the pending patch
        events = await event_bus.get_events_for_trace(trace_id)
        rca_event = next((e for e in events if e.type == EventType.RCA_READY), None)
        
        if not rca_event:
            raise HTTPException(status_code=404, detail="No pending patch found")
        
        # Publish approval event to continue the healing process
        await event_bus.publish(Event(
            type=EventType.MORPH_APPLY_REQUESTED,
            key=trace_id,
            payload={
                "file": "services/catalog_sync.py",
                "loc_estimate": 1,
                "approved_manually": True
            },
            ts=datetime.now(),
            trace_id=trace_id,
            ui_hint="manual_approval"
        ))
        
        return {
            "trace_id": trace_id,
            "status": "approved",
            "message": "Patch approved, continuing healing process"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 