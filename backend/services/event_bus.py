import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, List
from collections import defaultdict
from models.events import Event, EventType
from config import settings

class InMemoryEventBus:
    def __init__(self):
        self.events: List[Event] = []
        self.subscribers: Dict[str, asyncio.Queue] = {}
        self.trace_events: Dict[str, List[Event]] = defaultdict(list)
        
    async def connect(self):
        """Initialize the in-memory event bus"""
        print("📡 In-memory event bus initialized")
        
    async def disconnect(self):
        """Clean up the event bus"""
        self.events.clear()
        self.subscribers.clear()
        self.trace_events.clear()
        
    async def publish(self, event: Event):
        """Publish event to in-memory storage"""
        # Store event
        self.events.append(event)
        
        # Store by trace_id for easy lookup
        if event.trace_id:
            self.trace_events[event.trace_id].append(event)
        
        # Notify all subscribers
        for queue in self.subscribers.values():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Skip if queue is full
                pass
        
        print(f"📢 Published event: {event.type.value} for {event.key}")
        
    async def subscribe(self, event_types: list[EventType] = None) -> AsyncGenerator[Event, None]:
        """Subscribe to events stream"""
        # Create a unique subscriber ID
        subscriber_id = f"sub_{len(self.subscribers)}"
        queue = asyncio.Queue(maxsize=100)
        self.subscribers[subscriber_id] = queue
        
        try:
            while True:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    # Filter by event types if specified
                    if event_types is None or event.type in event_types:
                        yield event
                        
                except asyncio.TimeoutError:
                    # Send a keepalive event every few seconds
                    continue
                except asyncio.CancelledError:
                    break
                    
        finally:
            # Clean up subscriber
            if subscriber_id in self.subscribers:
                del self.subscribers[subscriber_id]
                
    async def get_events_for_trace(self, trace_id: str) -> list[Event]:
        """Get all events for a specific trace"""
        return sorted(self.trace_events.get(trace_id, []), key=lambda x: x.ts)

# Use in-memory event bus by default
event_bus = InMemoryEventBus() 