import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Eye, 
  EyeOff, 
  Shield, 
  CheckCircle,
  AlertCircle,
  Clock,
  Activity
} from 'lucide-react';
import { HealingTrace, UIState } from '../types/events';

interface ControlBarProps {
  trace: HealingTrace | null;
  uiState: UIState;
  onToggleAutoHeal: () => void;
  onReplay: () => void;
  onRollback: () => void;
  onToggleRaw: () => void;
  onApprove?: () => void;
  onTrigger: () => void;
}

const ControlBar: React.FC<ControlBarProps> = ({
  trace,
  uiState,
  onToggleAutoHeal,
  onReplay,
  onRollback,
  onToggleRaw,
  onApprove,
  onTrigger
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);

  // Update elapsed time for active traces
  useEffect(() => {
    if (!trace || trace.status === 'healed' || trace.status === 'rolled_back') {
      return;
    }

    const startTime = new Date(trace.start_time).getTime();
    const interval = setInterval(() => {
      const now = Date.now();
      setElapsedTime((now - startTime) / 1000);
    }, 100);

    return () => clearInterval(interval);
  }, [trace]);

  const getStatusIcon = () => {
    if (!trace) return <Clock className="h-4 w-4 text-gray-400" />;
    
    switch (trace.status) {
      case 'healed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'rolled_back':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'failing':
      case 'rca_ready':
      case 'applying':
      case 'reloaded':
      case 'verifying':
        return <Activity className="h-4 w-4 text-blue-600 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusColor = () => {
    if (!trace) return 'bg-gray-100 text-gray-800';
    
    switch (trace.status) {
      case 'healed':
        return 'bg-green-100 text-green-800';
      case 'rolled_back':
        return 'bg-red-100 text-red-800';
      case 'failing':
      case 'rca_ready':
      case 'applying':
      case 'reloaded':
      case 'verifying':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = () => {
    if (!trace) return 'Idle';
    
    switch (trace.status) {
      case 'healed':
        return `Healed in ${trace.duration?.toFixed(1)}s`;
      case 'rolled_back':
        return 'Rolled Back';
      case 'failing':
        return 'Analyzing Failure';
      case 'rca_ready':
        return 'Generating Fix';
      case 'applying':
        return 'Applying Patch';
      case 'reloaded':
        return 'Service Reloaded';
      case 'verifying':
        return 'Verifying Fix';
      default:
        return trace.status;
    }
  };

  const canReplay = trace && ['reloaded', 'verifying', 'healed'].includes(trace.status);
  const canRollback = trace && ['healed', 'rolled_back'].includes(trace.status);
  const needsApproval = !uiState.auto_heal_enabled && trace && trace.status === 'rca_ready';

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Left: Status and Timer */}
        <div className="flex items-center space-x-4">
          {/* Status Chip */}
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
            {getStatusIcon()}
            <span className="ml-2">{getStatusText()}</span>
          </div>

          {/* Incident ID */}
          {trace?.audit?.incident_id && (
            <div className="text-sm text-gray-600">
              ID: <code className="font-mono">{trace.audit.incident_id}</code>
            </div>
          )}

          {/* Live Timer */}
          {trace && trace.status !== 'healed' && trace.status !== 'rolled_back' && (
            <div className="text-sm text-gray-600">
              {elapsedTime.toFixed(1)}s
            </div>
          )}
        </div>

        {/* Right: Controls */}
        <div className="flex items-center space-x-3">
          {/* Auto-Heal Toggle */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700">Auto-Heal</span>
            <button
              onClick={onToggleAutoHeal}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                uiState.auto_heal_enabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  uiState.auto_heal_enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Approval Button (when auto-heal is off) */}
          {needsApproval && onApprove && (
            <button
              onClick={onApprove}
              className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Approve Patch
            </button>
          )}

          {/* Replay Button */}
          <button
            onClick={onReplay}
            disabled={!canReplay}
            className={`inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md transition-colors ${
              canReplay
                ? 'text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                : 'text-gray-400 bg-gray-100 cursor-not-allowed'
            }`}
          >
            <Play className="h-4 w-4 mr-1" />
            Replay
          </button>

          {/* Rollback Button */}
          <button
            onClick={onRollback}
            disabled={!canRollback}
            className={`inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md transition-colors ${
              canRollback
                ? 'text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500'
                : 'text-gray-400 bg-gray-100 cursor-not-allowed'
            }`}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            Rollback
          </button>

          {/* Show Raw Toggle */}
          <button
            onClick={onToggleRaw}
            className={`inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md transition-colors ${
              uiState.show_raw
                ? 'text-blue-700 bg-blue-50 border-blue-300'
                : 'text-gray-700 bg-white hover:bg-gray-50'
            } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          >
            {uiState.show_raw ? (
              <EyeOff className="h-4 w-4 mr-1" />
            ) : (
              <Eye className="h-4 w-4 mr-1" />
            )}
            Show Raw
          </button>

          {/* Risk Details Popover */}
          {trace?.code_change && (
            <div className="relative">
              <button className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <Shield className="h-4 w-4 mr-1" />
                Risk Details
              </button>
            </div>
          )}

          {/* Trigger New Failure */}
          {(!trace || trace.status === 'healed' || trace.status === 'rolled_back') && (
            <button
              onClick={onTrigger}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Play className="h-4 w-4 mr-2" />
              Trigger Failure
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ControlBar; 