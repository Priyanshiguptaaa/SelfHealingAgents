import React, { useState, useEffect } from 'react';
import { useEventStream } from './hooks/useEventStream';
import { HealingTrace, Event, UIState } from './types/events';
import ControlBar from './components/ControlBar';
import ExecutionLane from './components/ExecutionLane';
import ReasoningLane from './components/ReasoningLane';

function App() {
  const { events, isConnected, error } = useEventStream('/api/events/stream');
  const [activeTrace, setActiveTrace] = useState<HealingTrace | null>(null);
  const [uiState, setUiState] = useState<UIState>({
    auto_heal_enabled: true,
    show_raw: false,
    expanded_step: undefined,
    selected_tab: 'steps'
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
          trace_id: event.trace_id!,
          status: 'failing',
          start_time: event.timestamp,
          steps: [],
          audit: {
            incident_id: event.trace_id!.slice(0, 8),
            files_touched: [],
            bytes_written: 0,
            hot_reload_success: false
          }
        };
        return updateTraceWithEvent(newTrace, event);
      }

      return updateTraceWithEvent(prev, event);
    });
  };

  const updateTraceWithEvent = (trace: HealingTrace, event: Event): HealingTrace => {
    console.log('Processing event:', event.type, event.payload);
    const updatedTrace = { ...trace };

    switch (event.type) {
      case 'return_api.failure':
        // This is the initial trigger event
        updatedTrace.status = 'failing';
        if (updatedTrace.steps.length === 0) {
          updatedTrace.steps = [{
            step: 'Failure Detected',
            status: 'success',
            timestamp: event.timestamp,
            latency_ms: 214,
            details: `${event.payload.endpoint}: ${event.payload.detail}`,
            failure: {
              type: event.payload.error_type || 'SchemaMismatch',
              field: 'return_policy',
              expected: 'string',
              actual: null,
              message: 'return_policy field is required but missing'
            }
          }];
        }
        break;

      case 'trace.start':
        updatedTrace.status = 'failing';
        if (updatedTrace.steps.length === 0) {
          updatedTrace.steps = [{
            step: 'Failure Detected',
            status: 'success',
            timestamp: event.timestamp,
            latency_ms: 214,
            details: event.payload.failing_step,
            failure: {
              type: 'SchemaMismatch',
              field: 'return_policy',
              expected: 'string',
              actual: null,
              message: 'return_policy field is required but missing'
            }
          }];
        }
        break;

      case 'rca.ready':
        updatedTrace.status = 'rca_ready';
        updatedTrace.cause = event.payload.cause;
        updatedTrace.taxonomy = [event.payload.playbook, 'SchemaMismatch:return_policy'];
        updatedTrace.confidence = event.payload.confidence;
        
        // Only add if not already present
        const existingRCA = updatedTrace.steps.find(s => s.step === 'Root Cause Analysis');
        if (!existingRCA) {
          updatedTrace.steps.push({
            step: 'Root Cause Analysis',
            status: 'success',
            timestamp: event.timestamp,
            latency_ms: 450,
            details: `Playbook: ${event.payload.playbook}`
          });
        }
        break;

      case 'morph.apply.requested':
        // Only add if not already present
        const existingGen = updatedTrace.steps.find(s => s.step === 'Generating Patch');
        if (!existingGen) {
          updatedTrace.steps.push({
            step: 'Generating Patch',
            status: 'running',
            timestamp: event.timestamp,
            details: `File: ${event.payload.file}`
          });
        }
        break;

      case 'morph.apply.succeeded':
        updatedTrace.status = 'applying';
        
        // Update the generating step to success
        const genIndex = updatedTrace.steps.findIndex(s => s.step === 'Generating Patch');
        if (genIndex !== -1) {
          updatedTrace.steps[genIndex].status = 'success';
          updatedTrace.steps[genIndex].latency_ms = 850;
        }
        
        // Add code change info
        updatedTrace.code_change = {
          file: event.payload.file,
          diff_lines: event.payload.diff_preview || [
            '- POLICY_FIELDS = ["price", "inventory", "category"]',
            '+ POLICY_FIELDS = ["price", "inventory", "category", "return_policy"]'
          ],
          loc_changed: event.payload.loc_changed || 1,
          guardrails: {
            allowlist: true,
            max_loc: true,
            no_secrets: true,
            no_dangerous_ops: true
          }
        };

        // Only add applying step if not already present
        const existingApply = updatedTrace.steps.find(s => s.step === 'Applying Patch');
        if (!existingApply) {
          updatedTrace.steps.push({
            step: 'Applying Patch',
            status: 'running',
            timestamp: event.timestamp,
            details: `${event.payload.loc_changed || 1} lines changed`
          });
        }
        break;

      case 'reload.done':
        updatedTrace.status = 'reloaded';
        
        // Update applying step to success
        const applyIndex = updatedTrace.steps.findIndex(s => s.step === 'Applying Patch');
        if (applyIndex !== -1) {
          updatedTrace.steps[applyIndex].status = 'success';
          updatedTrace.steps[applyIndex].latency_ms = 320;
        }

        // Only add service reloaded step if not already present
        const existingReload = updatedTrace.steps.find(s => s.step === 'Service Reloaded');
        if (!existingReload) {
          updatedTrace.steps.push({
            step: 'Service Reloaded',
            status: 'success',
            timestamp: event.timestamp,
            latency_ms: 180,
            details: `PID: ${event.payload.pid}`
          });
        }

        // Update audit info
        if (updatedTrace.audit) {
          updatedTrace.audit.pid = event.payload.pid;
          updatedTrace.audit.hot_reload_success = true;
          updatedTrace.audit.files_touched = [updatedTrace.code_change?.file || 'unknown'];
          updatedTrace.audit.bytes_written = updatedTrace.code_change?.loc_changed || 1;
        }
        break;

      case 'verify.replay.pass':
        updatedTrace.status = 'verifying';
        updatedTrace.fix_applied = true;
        
        // Add verification results
        updatedTrace.verification = {
          before: event.payload.before,
          after: event.payload.after,
          latency_ms: event.payload.replay_ms,
          tests: [
            { name: 'policy_present', passed: true },
            { name: 'eligibility_rule_clearance', passed: true }
          ],
          metrics_deltas: {
            p95_change_percent: -18,
            fail_rate_change_percent: -100
          }
        };

        // Only add verification step if not already present
        const existingVerify = updatedTrace.steps.find(s => s.step === 'Verification');
        if (!existingVerify) {
          updatedTrace.steps.push({
            step: 'Verification',
            status: 'success',
            timestamp: event.timestamp,
            latency_ms: event.payload.replay_ms,
            details: `Replay successful`
          });
        }
        break;

      case 'heal.completed':
        updatedTrace.status = event.payload.status === 'pass' ? 'healed' : 'rolled_back';
        updatedTrace.duration = event.payload.duration_seconds;
        
        if (event.payload.status !== 'pass') {
          updatedTrace.error_message = event.payload.message;
        }

        // Add commit SHA
        if (updatedTrace.audit && event.payload.outcome?.commit_sha) {
          updatedTrace.audit.commit_sha = event.payload.outcome.commit_sha;
        }
        break;
        
      default:
        console.log('Unhandled event type:', event.type);
        break;
    }

    return updatedTrace;
  };

  const handleStepExpand = (stepName: string) => {
    setUiState(prev => ({
      ...prev,
      expanded_step: prev.expanded_step === stepName ? undefined : stepName
    }));
  };

  const handleToggleAutoHeal = () => {
    setUiState(prev => ({ ...prev, auto_heal_enabled: !prev.auto_heal_enabled }));
  };

  const handleToggleRaw = () => {
    setUiState(prev => ({ ...prev, show_raw: !prev.show_raw }));
  };

  const handleCopyEvidence = () => {
    if (!activeTrace) return;
    
    const evidence = {
      cause: activeTrace.cause,
      diff: activeTrace.code_change?.diff_lines?.join('\n'),
      verification: activeTrace.verification,
      incident_id: activeTrace.audit?.incident_id
    };
    
    navigator.clipboard.writeText(JSON.stringify(evidence, null, 2));
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

  const handleReplay = async () => {
    if (!activeTrace) return;
    
    try {
      const response = await fetch(`/api/replay/${activeTrace.trace_id}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Replay result:', result);
      } else {
        console.error('Replay failed:', await response.text());
      }
    } catch (error) {
      console.error('Replay error:', error);
    }
  };

  const handleRollback = async () => {
    if (!activeTrace) return;
    
    if (!confirm('Are you sure you want to rollback this patch? This will restore the original code.')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/rollback/${activeTrace.trace_id}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Rollback result:', result);
      } else {
        console.error('Rollback failed:', await response.text());
      }
    } catch (error) {
      console.error('Rollback error:', error);
    }
  };

  const handleApprove = async () => {
    if (!activeTrace) return;
    
    try {
      const response = await fetch(`/api/approve/${activeTrace.trace_id}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Approval result:', result);
      } else {
        console.error('Approval failed:', await response.text());
      }
    } catch (error) {
      console.error('Approval error:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Control Bar */}
      <ControlBar
        trace={activeTrace}
        uiState={uiState}
        onToggleAutoHeal={handleToggleAutoHeal}
        onReplay={handleReplay}
        onRollback={handleRollback}
        onToggleRaw={handleToggleRaw}
        onApprove={handleApprove}
        onTrigger={triggerHealing}
      />

      {/* Connection Error */}
      {error && (
        <div className="mx-6 mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <span className="text-red-700">{error}</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="px-6 py-6">
        {activeTrace ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Execution Lane */}
            <ExecutionLane
              trace={activeTrace}
              onStepExpand={handleStepExpand}
              expandedStep={uiState.expanded_step}
            />

            {/* Right: Reasoning Lane */}
            <ReasoningLane
              trace={activeTrace}
              onCopyEvidence={handleCopyEvidence}
            />
          </div>
        ) : (
          /* Empty State */
          <div className="text-center py-16">
            <div className="max-w-md mx-auto">
              <div className="h-16 w-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                <span className="text-2xl">🤖</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Self-Healing System Ready
              </h3>
              <p className="text-gray-600 mb-6">
                Autonomous agents are standing by to detect, analyze, and fix issues in real-time.
              </p>
              <button
                onClick={triggerHealing}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Trigger Demo Failure
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App; 