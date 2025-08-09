import React from 'react';
import { CheckCircle, AlertCircle, Clock, Activity } from 'lucide-react';
import { HealingTrace, TraceStep } from '../types/events';

interface TraceVisualizationProps {
  trace: HealingTrace;
}

const TraceVisualization: React.FC<TraceVisualizationProps> = ({ trace }) => {
  const getStepIcon = (step: TraceStep) => {
    switch (step.status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-success-600" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-error-600" />;
      case 'running':
        return <Activity className="h-5 w-5 text-primary-600 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStepColor = (step: TraceStep) => {
    switch (step.status) {
      case 'success':
        return 'border-success-200 bg-success-50';
      case 'error':
        return 'border-error-200 bg-error-50';
      case 'running':
        return 'border-primary-200 bg-primary-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Healing Trace</h3>
        <div className="text-sm text-gray-500">
          Trace ID: {trace.trace_id.slice(0, 8)}...
        </div>
      </div>

      <div className="space-y-4">
        {trace.steps.map((step, index) => (
          <div key={index} className="flex items-start space-x-4">
            {/* Step Icon */}
            <div className="flex-shrink-0 mt-1">
              {getStepIcon(step)}
            </div>

            {/* Step Content */}
            <div className="flex-1">
              <div className={`rounded-lg border p-4 ${getStepColor(step)}`}>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">{step.step}</h4>
                  <span className="text-xs text-gray-500">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                
                {step.details && (
                  <p className="text-sm text-gray-600">{step.details}</p>
                )}
                
                {step.duration && (
                  <div className="text-xs text-gray-500 mt-1">
                    Duration: {step.duration}ms
                  </div>
                )}
              </div>
            </div>

            {/* Connector Line */}
            {index < trace.steps.length - 1 && (
              <div className="absolute left-6 mt-8 w-px h-8 bg-gray-200" 
                   style={{ marginLeft: '10px' }} />
            )}
          </div>
        ))}
      </div>

      {/* Overall Status */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Overall Status:</span>
          <div className={`status-badge ${trace.status === 'complete' ? 'success' : 
                          trace.status === 'failed' ? 'error' : 'info'}`}>
            {trace.status}
          </div>
        </div>
        
        {trace.duration && (
          <div className="mt-2 text-sm text-gray-600">
            Total duration: {trace.duration.toFixed(1)}s
          </div>
        )}
      </div>
    </div>
  );
};

export default TraceVisualization; 