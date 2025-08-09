import { useState, useEffect, useRef } from 'react';
import { Event } from '../types/events';

export const useEventStream = (url: string) => {
  const [events, setEvents] = useState<Event[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connectEventSource = () => {
      try {
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setIsConnected(true);
          setError(null);
          console.log('🔗 Connected to event stream');
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // Skip connection events
            if (data.type === 'connected' || data.type === 'disconnected') {
              return;
            }

            setEvents(prev => [...prev, data]);
          } catch (err) {
            console.error('Error parsing event data:', err);
          }
        };

        eventSource.onerror = (err) => {
          console.error('EventSource error:', err);
          setIsConnected(false);
          setError('Connection lost. Attempting to reconnect...');
          
          // Attempt to reconnect after a delay
          setTimeout(() => {
            if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
              connectEventSource();
            }
          }, 3000);
        };

      } catch (err) {
        setError('Failed to connect to event stream');
        console.error('Failed to create EventSource:', err);
      }
    };

    connectEventSource();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setIsConnected(false);
    };
  }, [url]);

  const clearEvents = () => {
    setEvents([]);
  };

  return {
    events,
    isConnected,
    error,
    clearEvents
  };
}; 