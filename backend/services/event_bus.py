import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
import redis.asyncio as redis
from models.events import Event, EventType
from config import settings

class EventBus:
    def __init__(self):
        self.redis = None
        self.subscribers = {}
        
    async def connect(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        
    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            
    async def publish(self, event: Event):
        """Publish event to Redis stream"""
        if not self.redis:
            await self.connect()
            
        event_data = {
            "type": event.type.value,
            "key": event.key,
            "payload": json.dumps(event.payload),
            "ts": event.ts.isoformat(),
            "trace_id": event.trace_id or "",
            "ui_hint": event.ui_hint or ""
        }
        
        # Add to main stream
        await self.redis.xadd("events", event_data)
        
        # Add to type-specific stream for targeted consumption
        await self.redis.xadd(f"events:{event.type.value}", event_data)
        
    async def subscribe(self, event_types: list[EventType] = None) -> AsyncGenerator[Event, None]:
        """Subscribe to events stream"""
        if not self.redis:
            await self.connect()
            
        if event_types:
            streams = {f"events:{et.value}": "$" for et in event_types}
        else:
            streams = {"events": "$"}
            
        while True:
            try:
                result = await self.redis.xread(streams, count=10, block=1000)
                
                for stream_name, messages in result:
                    for message_id, fields in messages:
                        try:
                            event = Event(
                                type=EventType(fields["type"]),
                                key=fields["key"],
                                payload=json.loads(fields["payload"]),
                                ts=datetime.fromisoformat(fields["ts"]),
                                trace_id=fields["trace_id"] if fields["trace_id"] else None,
                                ui_hint=fields["ui_hint"] if fields["ui_hint"] else None
                            )
                            yield event
                        except Exception as e:
                            print(f"Error parsing event: {e}")
                            continue
                            
                    # Update stream positions
                    for stream in streams:
                        streams[stream] = message_id
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error in event subscription: {e}")
                await asyncio.sleep(1)
                
    async def get_events_for_trace(self, trace_id: str) -> list[Event]:
        """Get all events for a specific trace"""
        if not self.redis:
            await self.connect()
            
        events = []
        
        # Read from main stream and filter by trace_id
        result = await self.redis.xrange("events")
        
        for message_id, fields in result:
            if fields.get("trace_id") == trace_id:
                try:
                    event = Event(
                        type=EventType(fields["type"]),
                        key=fields["key"],
                        payload=json.loads(fields["payload"]),
                        ts=datetime.fromisoformat(fields["ts"]),
                        trace_id=fields["trace_id"] if fields["trace_id"] else None,
                        ui_hint=fields["ui_hint"] if fields["ui_hint"] else None
                    )
                    events.append(event)
                except Exception as e:
                    print(f"Error parsing event: {e}")
                    continue
                    
        return sorted(events, key=lambda x: x.ts)

# Global event bus instance
event_bus = EventBus() 