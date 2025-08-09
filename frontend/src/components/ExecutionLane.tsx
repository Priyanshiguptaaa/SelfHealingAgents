import React, { useState } from 'react';
import { CheckCircle, AlertCircle, Clock, Activity, ChevronDown, ChevronRight } from 'lucide-react';
import { HealingTrace, TraceStep } from '../types/events';

interface ExecutionLaneProps {
  trace: HealingTrace;
  onStepExpand: (stepName: string) => void;
  expandedStep?: string;
}

const ExecutionLane: React.FC<ExecutionLaneProps> = ({ trace, onStepExpand, expandedStep }) => {
  const getStepIcon = (step: TraceStep) => {
    switch (step.status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'running':
        return <Activity className="h-4 w-4 text-blue-600 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStepColor = (step: TraceStep) => {
    switch (step.status) {
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      case 'running':
        return 'border-blue-200 bg-blue-50 animate-pulse';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const getTaxonomyBadge = (step: TraceStep) => {
    if (step.failure?.type) {
      const badge = step.failure.field 
        ? `${step.failure.type}:${step.failure.field}`
        : step.failure.type;
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
          {badge}
        </span>
      );
    }
    return null;
  };

  const renderExpectedVsGot = (step: TraceStep) => {
    if (!step.failure) return null;

    return (
      <div className="mt-3 p-3 bg-gray-50 rounded border">
        <h5 className="text-sm font-medium text-gray-900 mb-2">Schema Validation</h5>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Field:</span>
            <code className="font-mono text-gray-900">{step.failure.field || 'unknown'}</code>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Expected:</span>
            <code className="font-mono text-green-700">{JSON.stringify(step.failure.expected)}</code>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Actual:</span>
            <code className="font-mono text-red-700">{JSON.stringify(step.failure.actual)}</code>
          </div>
        </div>
        <button className="mt-2 text-xs text-blue-600 hover:text-blue-800">
          View raw event →
        </button>
      </div>
    );
  };

  const isExpanded = (step: TraceStep) => expandedStep === step.step;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Timeline</h3>
      
      <div className="relative">
        {trace.steps.map((step, index) => (
          <div key={index} className="relative">
            {/* Timeline connector */}
            {index < trace.steps.length - 1 && (
              <div className="absolute left-6 top-12 w-px h-8 bg-gray-200" />
            )}
            
            {/* Step card */}
            <div className={`border rounded-lg p-4 ${getStepColor(step)} transition-all duration-200`}>
              <div 
                className="flex items-center justify-between cursor-pointer"
                onClick={() => onStepExpand(step.step)}
              >
                <div className="flex items-center space-x-3">
                  {getStepIcon(step)}
                  <div>
                    <h4 className="font-medium text-gray-900">{step.step}</h4>
                    <div className="flex items-center space-x-2 mt-1">
                      {step.latency_ms && (
                        <span className="text-xs text-gray-500">
                          {step.latency_ms}ms
                        </span>
                      )}
                      {getTaxonomyBadge(step)}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                  {step.failure && (
                    isExpanded(step) 
                      ? <ChevronDown className="h-4 w-4 text-gray-400" />
                      : <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                </div>
              </div>

              {/* Expanded content */}
              {isExpanded(step) && renderExpectedVsGot(step)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ExecutionLane; 