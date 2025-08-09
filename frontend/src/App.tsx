import React, { useState, useEffect } from 'react';
import { Activity, AlertCircle, CheckCircle, Clock, Code, Play, Zap } from 'lucide-react';
import { useEventStream } from './hooks/useEventStream';
import { HealingTrace, TraceStep, Event } from './types/events';
import TraceVisualization from './components/TraceVisualization';
import CodeDiffViewer from './components/CodeDiffViewer';
import TriggerButton from './components/TriggerButton';

function App() {
  const { events, isConnected, error } = useEventStream('/api/events/stream');
  const [activeTrace, setActiveTrace] = useState<HealingTrace | null>(null);
  const [healingStats, setHealingStats] = useState({
    total: 0,
    successful: 0,
    failed: 0,
    active: 0
  });

  // Process events into healing traces
  useEffect(() => {
    if (events.length === 0) return;

    const latestEvent = events[events.length - 1];
    
    if (latestEvent.trace_id) {
      updateTraceFromEvent(latestEvent);
    }
  }, [events]);

  const updateTraceFromEvent = (event: Event) => {
    if (!event.trace_id) return;

    setActiveTrace(prev => {
      // Create new trace if none exists
      if (!prev || prev.trace_id !== event.trace_id) {
        const newTrace: HealingTrace = {
          trace_id: event.trace_id,
          status: 'analyzing',
          start_time: event.timestamp,
          steps: [],
          cause: undefined,
          fix_applied: false
        };
        return updateTraceWithEvent(newTrace, event);
      }

      return updateTraceWithEvent(prev, event);
    });
  };

  const updateTraceWithEvent = (trace: HealingTrace, event: Event): HealingTrace => {
    const updatedTrace = { ...trace };

    switch (event.type) {
      case 'trace.start':
        updatedTrace.status = 'analyzing';
        updatedTrace.steps = [
          { step: 'Failure Detected', status: 'success', timestamp: event.timestamp, details: event.payload.failing_step }
        ];
        break;

      case 'rca.ready':
        updatedTrace.status = 'generating';
        updatedTrace.cause = event.payload.cause;
        updatedTrace.steps.push({
          step: 'Root Cause Analysis',
          status: 'success',
          timestamp: event.timestamp,
          details: `Playbook: ${event.payload.playbook}`
        });
        break;

      case 'morph.apply.requested':
        updatedTrace.steps.push({
          step: 'Generating Patch',
          status: 'running',
          timestamp: event.timestamp,
          details: `File: ${event.payload.file}`
        });
        break;

      case 'morph.apply.succeeded':
        updatedTrace.status = 'applying';
        // Update the generating step to success
        const genIndex = updatedTrace.steps.findIndex(s => s.step === 'Generating Patch');
        if (genIndex !== -1) {
          updatedTrace.steps[genIndex].status = 'success';
        }
        updatedTrace.steps.push({
          step: 'Applying Patch',
          status: 'running',
          timestamp: event.timestamp,
          details: `${event.payload.loc_changed} lines changed`
        });
        break;

      case 'reload.done':
        // Update applying step to success
        const applyIndex = updatedTrace.steps.findIndex(s => s.step === 'Applying Patch');
        if (applyIndex !== -1) {
          updatedTrace.steps[applyIndex].status = 'success';
        }
        updatedTrace.steps.push({
          step: 'Service Reloaded',
          status: 'success',
          timestamp: event.timestamp,
          details: `PID: ${event.payload.pid}`
        });
        break;

      case 'verify.replay.pass':
        updatedTrace.status = 'complete';
        updatedTrace.fix_applied = true;
        updatedTrace.steps.push({
          step: 'Verification',
          status: 'success',
          timestamp: event.timestamp,
          details: `Replay took ${event.payload.replay_ms}ms`
        });
        break;

      case 'heal.completed':
        updatedTrace.status = event.payload.status === 'pass' ? 'complete' : 'failed';
        updatedTrace.duration = event.payload.duration_seconds;
        if (event.payload.status !== 'pass') {
          updatedTrace.error_message = event.payload.message;
        }
        break;
    }

    return updatedTrace;
  };

  const triggerHealing = async () => {
    try {
      const response = await fetch('/api/trigger-failure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku: 'SKU-123',
          order_id: '8734',
          endpoint: 'CheckReturnEligibility'
        })
      });
      
      const result = await response.json();
      console.log('Healing triggered:', result);
    } catch (error) {
      console.error('Failed to trigger healing:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Zap className="h-8 w-8 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Self-Healing Agents</h1>
                <p className="text-sm text-gray-500">Autonomous E-commerce Issue Resolution</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <div className="flex items-center space-x-2">
                <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-success-500 animate-pulse' : 'bg-error-500'}`} />
                <span className="text-sm text-gray-600">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {/* Trigger Button */}
              <TriggerButton onTrigger={triggerHealing} />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 bg-error-50 border border-error-200 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-error-600" />
              <span className="text-error-700">{error}</span>
            </div>
          </div>
        )}

        {activeTrace ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column: Trace Visualization */}
            <div className="space-y-6">
              <TraceVisualization trace={activeTrace} />
              
              {/* Stats Card */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Healing Statistics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary-600">{healingStats.total}</div>
                    <div className="text-sm text-gray-500">Total Healings</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-success-600">{healingStats.successful}</div>
                    <div className="text-sm text-gray-500">Successful</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Details */}
            <div className="space-y-6">
              {/* Cause Analysis */}
              {activeTrace.cause && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Root Cause Analysis</h3>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-yellow-800">{activeTrace.cause}</p>
                  </div>
                </div>
              )}

              {/* Code Diff */}
              {activeTrace.fix_applied && (
                <CodeDiffViewer 
                  filename="services/catalog_sync.py"
                  before={`POLICY_FIELDS = ["price", "inventory", "category"]`}
                  after={`POLICY_FIELDS = ["price", "inventory", "category", "return_policy"]`}
                />
              )}

              {/* Healing Timer */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900">Healing Status</h3>
                  <div className={`status-badge ${activeTrace.status === 'complete' ? 'success' : 'info'}`}>
                    {activeTrace.status === 'complete' ? (
                      <>
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Healed in {activeTrace.duration?.toFixed(1)}s
                      </>
                    ) : (
                      <>
                        <Activity className="h-4 w-4 mr-1 animate-spin" />
                        {activeTrace.status}
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Empty State */
          <div className="text-center py-12">
            <Code className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Active Healing Process</h3>
            <p className="text-gray-600 mb-6">Trigger a failure to see the autonomous healing system in action</p>
            <TriggerButton onTrigger={triggerHealing} variant="primary" />
          </div>
        )}
      </main>
    </div>
  );
}

export default App; 