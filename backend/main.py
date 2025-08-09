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
from agents.coordinator_agent import coordinator_agent


# Request/Response Models
class TriggerFailureRequest(BaseModel):
    sku: str = "SKU-1001"  # Use clearance SKU
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
    print("🎯 Multi-Agent Architecture:")
    print("   - User System: E-commerce Agents (Catalog + Customer)")
    print("   - Healing System: Multi-Agent Healing Platform")
    
    # Connect to event bus
    await event_bus.connect()
    
    # Start the coordinator agent (manages all healing agents)
    await coordinator_agent.start()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Self-Healing E-commerce System")
    await coordinator_agent.stop()
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
    """Trigger a schema validation failure by simulating a customer return request"""
    
    # Import here to avoid circular imports
    import sys
    from pathlib import Path
    
    # Add demo_user_code to path
    demo_path = Path(__file__).parent.parent / "demo_user_code"
    sys.path.insert(0, str(demo_path))
    
    try:
        # Try to import customer_agent
        try:
            from agents.customer_agent import customer_agent
        except ImportError as import_error:
            print(f"⚠️ Import error: {import_error}")
            # Fallback: create a simple failure event directly
            trace_id = str(uuid.uuid4())
            
            # Create a return API failure event directly
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
                trace_id=trace_id,
                ui_hint="failure_triggered"
            )
            
            # Publish the failure event
            await event_bus.publish(failure_event)
            
            return {
                "message": "E-commerce failure detected - healing initiated",
                "error": "return_policy missing",
                "sku": request.sku,
                "order_id": request.order_id,
                "status": "healing_initiated",
                "note": "Watch the frontend for real-time healing progress!"
            }
        
        print(f"🎬 DEMO: Triggering customer return request for {request.sku}")
        print("🎯 This will cause the e-commerce system to emit a non-human signal")
        print("🎯 Our healing system will detect and autonomously fix the issue")
        
        # Customer agent simulates return request
        result = await customer_agent.simulate_return_request(
            sku=request.sku,
            order_id=request.order_id
        )
        
        if result["status"] == "error":
            return {
                "message": "E-commerce failure detected - healing initiated",
                "error": result["error"],
                "sku": result["sku"],
                "order_id": result["order_id"],
                "status": "healing_initiated",
                "note": "Watch the frontend for real-time healing progress!"
            }
        else:
            return {
                "message": "No failure detected - system working correctly",
                "result": result,
                "status": "success"
            }
            
    except Exception as e:
        print(f"❌ Error in trigger_failure: {e}")
        raise HTTPException(status_code=500, detail=f"Demo error: {str(e)}")


@app.get("/api/events/stream")
async def stream_events():
    """Server-Sent Events stream for real-time frontend updates"""
    
    async def event_stream():
        """Generate SSE events with complete healing workflow"""
        
        # Send initial connection event
        connection_event = {
            'type': 'connected', 
            'timestamp': datetime.now().isoformat(),
            'message': 'Connected to healing system event stream'
        }
        yield f"data: {json.dumps(connection_event)}\n\n"
        
        # Subscribe to all events for complete visibility
        try:
            async for event in event_bus.subscribe():
                # Format as SSE with rich UI hints
                event_data = {
                    "type": event.type.value,
                    "key": event.key,
                    "payload": event.payload,
                    "timestamp": event.ts.isoformat(),
                    "trace_id": event.trace_id,
                    "ui_hint": event.ui_hint,
                    # Add step metadata for frontend
                    "step_info": _get_step_info(event)
                }
                
                yield f"data: {json.dumps(event_data)}\n\n"
                
        except asyncio.CancelledError:
            disconnect_event = {
                'type': 'disconnected', 
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(disconnect_event)}\n\n"
    
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


def _get_step_info(event: Event) -> dict:
    """Get step information for frontend display"""
    step_map = {
        EventType.RETURN_API_FAILURE: {
            "step_name": "Failure Detected",
            "icon": "🚨",
            "description": "Schema validation failure detected"
        },
        EventType.RCA_READY: {
            "step_name": "Root Cause Analysis",
            "icon": "🧠",
            "description": "Analyzing failure with AI"
        },
        EventType.MORPH_APPLY_REQUESTED: {
            "step_name": "Generating Patch",
            "icon": "🤖",
            "description": "Creating code fix with Morph API"
        },
        EventType.MORPH_APPLY_SUCCEEDED: {
            "step_name": "Patch Applied",
            "icon": "⚡",
            "description": "Code fix applied successfully"
        },
        EventType.HEAL_COMPLETED: {
            "step_name": "Healing Complete",
            "icon": "✅",
            "description": "Issue resolved and verified"
        }
    }
    
    return step_map.get(event.type, {
        "step_name": event.type.value,
        "icon": "⚙️",
        "description": "Processing..."
    })


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
        "active_healings": coordinator_agent.active_healings,
        "total_active": len(coordinator_agent.active_healings)
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
        trace_start_event = next((e for e in events 
                                 if e.type == EventType.RETURN_API_FAILURE), None)
        if not trace_start_event:
            raise HTTPException(status_code=400, detail="No failure event found")
        
        # Simulate replay by re-triggering the customer request
        sku = trace_start_event.payload.get("sku")
        order_id = trace_start_event.payload.get("order_id")
        
        if sku and order_id:
            # Import customer agent
            import sys
            from pathlib import Path
            demo_path = Path(__file__).parent.parent / "demo_user_code"
            sys.path.insert(0, str(demo_path))
            
            try:
                from agents.customer_agent import customer_agent
                result = await customer_agent.simulate_return_request(sku, order_id)
            except ImportError:
                # Fallback: simulate the failure directly
                result = {
                    "status": "error",
                    "error": "return_policy missing",
                    "sku": sku,
                    "order_id": order_id
                }
            
            return {
                "trace_id": trace_id,
                "status": "success" if result["status"] == "success" else "failed",
                "result": result
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid trace data")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rollback/{trace_id}")
async def rollback_patch(trace_id: str):
    """Rollback a previously applied patch"""
    try:
        from services.patch_applier import patch_applier
        
        # Attempt rollback
        success = await patch_applier.rollback_patch(
            "services/catalog_sync.py", trace_id
        )
        
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
        rca_event = next((e for e in events 
                         if e.type == EventType.RCA_READY), None)
        
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