import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator, List
from collections import defaultdict, deque
from models.events import Event, EventType
from config import settings


class InMemoryEventBus:
    """In-memory event bus for demo purposes when Redis is not available"""
    
    def __init__(self):
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.subscribers = []
        self.events_by_trace = defaultdict(list)
    
    async def publish(self, event: Event):
        """Publish event to in-memory storage"""
        self.events.append(event)
        
        if event.trace_id:
            self.events_by_trace[event.trace_id].append(event)
        
        # Notify all subscribers
        for subscriber in self.subscribers[:]:
            try:
                await subscriber.put(event)
            except Exception:
                # Remove broken subscribers
                self.subscribers.remove(subscriber)
    
    async def subscribe(
        self, event_types: List[EventType] = None
    ) -> AsyncGenerator[Event, None]:
        """Subscribe to events"""
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        
        try:
            while True:
                event = await queue.get()
                if event_types is None or event.type in event_types:
                    yield event
        finally:
            if queue in self.subscribers:
                self.subscribers.remove(queue)
    
    async def get_events_for_trace(self, trace_id: str) -> List[Event]:
        """Get all events for a specific trace"""
        return sorted(self.events_by_trace[trace_id], key=lambda x: x.ts)


class EventBus:
    def __init__(self):
        self.redis = None
        self.in_memory_bus = InMemoryEventBus()
        self.use_redis = settings.use_redis
        
    async def connect(self):
        if self.use_redis:
            try:
                import redis.asyncio as redis
                self.redis = redis.from_url(
                    settings.redis_url, decode_responses=True
                )
                # Test connection
                await self.redis.ping()
                print("✅ Connected to Redis")
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}")
                print("📝 Falling back to in-memory event bus")
                self.use_redis = False
        else:
            print("📝 Using in-memory event bus")
        
    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            
    async def publish(self, event: Event):
        """Publish event to Redis stream or in-memory"""
        if self.use_redis and self.redis:
            await self._publish_redis(event)
        else:
            await self.in_memory_bus.publish(event)
    
    async def _publish_redis(self, event: Event):
        """Publish event to Redis stream"""
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
        
    async def subscribe(
        self, event_types: List[EventType] = None
    ) -> AsyncGenerator[Event, None]:
        """Subscribe to events stream"""
        if self.use_redis and self.redis:
            async for event in self._subscribe_redis(event_types):
                yield event
        else:
            async for event in self.in_memory_bus.subscribe(event_types):
                yield event
    
    async def _subscribe_redis(
        self, event_types: List[EventType] = None
    ) -> AsyncGenerator[Event, None]:
        """Subscribe to Redis events stream"""
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
                                trace_id=(
                                    fields["trace_id"] 
                                    if fields["trace_id"] else None
                                ),
                                ui_hint=(
                                    fields["ui_hint"] 
                                    if fields["ui_hint"] else None
                                )
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
                
    async def get_events_for_trace(self, trace_id: str) -> List[Event]:
        """Get all events for a specific trace"""
        if self.use_redis and self.redis:
            return await self._get_events_for_trace_redis(trace_id)
        else:
            return await self.in_memory_bus.get_events_for_trace(trace_id)
    
    async def _get_events_for_trace_redis(self, trace_id: str) -> List[Event]:
        """Get all events for a specific trace from Redis"""
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
                        trace_id=(
                                    fields["trace_id"] 
                                    if fields["trace_id"] else None
                                ),
                        ui_hint=(
                                    fields["ui_hint"] 
                                    if fields["ui_hint"] else None
                                )
                    )
                    events.append(event)
                except Exception as e:
                    print(f"Error parsing event: {e}")
                    continue
                    
        return sorted(events, key=lambda x: x.ts)


# Global event bus instance
event_bus = EventBus() 