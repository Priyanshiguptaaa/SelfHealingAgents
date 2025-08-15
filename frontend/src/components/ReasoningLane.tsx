import React, { useState } from 'react';
import { 
  Brain, 
  Code, 
  TestTube, 
  FileText, 
  CheckCircle, 
  XCircle,
  ChevronDown,
  ChevronUp,
  Shield,
  GitCommit,
  Copy
} from 'lucide-react';
import { HealingTrace } from '../types/events';

interface ReasoningLaneProps {
  trace: HealingTrace;
  onCopyEvidence: () => void;
}

const ReasoningLane: React.FC<ReasoningLaneProps> = ({ trace, onCopyEvidence }) => {
  const [auditExpanded, setAuditExpanded] = useState(false);

  console.log('ReasoningLane trace:', trace);

  const CauseCard = () => {
    console.log('CauseCard - trace.cause:', trace.cause);
    if (!trace.cause) return null;

    // 🔧 OPTIMIZED: Simplified data structure for faster rendering
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <Brain className="h-5 w-5 text-purple-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-medium text-gray-900 mb-2">Root Cause Analysis</h4>
            <p className="text-gray-700 mb-3">{trace.cause}</p>
            
            {/* 🔧 OPTIMIZED: Simple confidence display */}
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <span>Confidence: {trace.confidence || 'N/A'}</span>
              {trace.taxonomy && trace.taxonomy.length > 0 && (
                <span>• Playbook: {trace.taxonomy[0]}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const CodeChangeCard = () => {
    if (!trace.code_change) return null;

    const { file, diff_lines, loc_changed, guardrails } = trace.code_change;
    
    // 🔧 Enhanced: Get original and updated code if available
    const originalCode = (trace.code_change as any).original_code;
    const updatedCode = (trace.code_change as any).updated_code;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <Code className="h-5 w-5 text-blue-600 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-gray-900">Code Change</h4>
              <div className="flex items-center space-x-2">
                {guardrails.allowlist && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-800">
                    <Shield className="h-3 w-3 mr-1" />
                    Allowlist ✓
                  </span>
                )}
                <span className="text-xs text-gray-600">LOC {loc_changed}</span>
              </div>
            </div>

            {/* File path breadcrumb */}
            <div className="mb-3">
              <code className="text-sm bg-gray-100 px-2 py-1 rounded font-mono text-gray-800">
                {file}
              </code>
            </div>

            {/* 🔧 Enhanced: RCA Analysis Context - Why This Was Fixed */}
            {trace.cause && (
              <div className="mb-4 p-3 bg-amber-50 rounded border border-amber-200">
                <h5 className="text-sm font-medium text-amber-800 mb-2">🔍 Why This Was Fixed</h5>
                <div className="text-sm text-amber-700">
                  <p className="mb-2"><strong>Root Cause:</strong> {trace.cause}</p>
                  {trace.taxonomy && trace.taxonomy.length > 0 && (
                    <p><strong>Issue Type:</strong> {trace.taxonomy.join(', ')}</p>
                  )}
                  {trace.confidence && (
                    <p><strong>Confidence:</strong> {Math.round(trace.confidence * 100)}%</p>
                  )}
                </div>
              </div>
            )}

            {/* 🔧 Enhanced: Before/After Code Display - More Prominent */}
            {originalCode && updatedCode && (
              <div className="mb-4">
                <h5 className="text-sm font-medium text-gray-700 mb-3">📝 Code Changes - Before vs After</h5>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div>
                    <h6 className="text-xs font-medium text-red-700 mb-2 flex items-center">
                      <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                      Before (Original Code)
                    </h6>
                    <div className="bg-red-50 rounded p-3 text-xs font-mono border border-red-200 max-h-64 overflow-y-auto">
                      <pre className="text-red-800 whitespace-pre-wrap">{originalCode}</pre>
                    </div>
                  </div>
                  <div>
                    <h6 className="text-xs font-medium text-green-700 mb-2 flex items-center">
                      <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                      After (Updated Code)
                    </h6>
                    <div className="bg-green-50 rounded p-3 text-xs font-mono border border-green-200 max-h-64 overflow-y-auto">
                      <pre className="text-green-800 whitespace-pre-wrap">{updatedCode}</pre>
                    </div>
                  </div>
                </div>
                
                {/* 🔧 Enhanced: Rollback Button */}
                <div className="mt-3 flex justify-center">
                  <button
                    onClick={() => {
                      if (window.confirm('Are you sure you want to rollback this patch? This will restore the original code.')) {
                        // Trigger rollback - this will be handled by the parent component
                        window.dispatchEvent(new CustomEvent('rollbackRequested', { 
                          detail: { traceId: trace.trace_id } 
                        }));
                      }
                    }}
                    className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                  >
                    <span className="mr-2">↩️</span>
                    Rollback Changes
                  </button>
                </div>
              </div>
            )}

            {/* 🔧 OPTIMIZED: Remove verbose AI recommendations for faster rendering */}
            {/* Focus on essential code change information only */}
            
            {/* Diff viewer */}
            <div className="mb-3">
              <h5 className="text-sm font-medium text-gray-700 mb-2">🔍 Diff View (What Changed)</h5>
              <div className="bg-gray-900 rounded-lg p-3 text-sm font-mono overflow-x-auto">
                {diff_lines.map((line, index) => {
                  const isAddition = line.startsWith('+');
                  const isDeletion = line.startsWith('-');
                  const isContext = !isAddition && !isDeletion && !line.startsWith('@@');
                  
                  return (
                    <div
                      key={index}
                      className={`${
                        isAddition ? 'bg-green-900 text-green-100' :
                        isDeletion ? 'bg-red-900 text-red-100' :
                        isContext ? 'text-gray-300' : 'text-gray-500'
                      } px-2 py-0.5`}
                    >
                      {line}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Guardrails summary */}
            <div className="mt-3 flex items-center space-x-4 text-xs text-gray-600">
              <span className={guardrails.allowlist ? 'text-green-600' : 'text-red-600'}>
                {guardrails.allowlist ? '✓' : '✗'} Allowlist
              </span>
              <span className={guardrails.max_loc ? 'text-green-600' : 'text-red-600'}>
                {guardrails.max_loc ? '✓' : '✗'} Size Check
              </span>
              <span className={guardrails.no_secrets ? 'text-green-600' : 'text-red-600'}>
                {guardrails.no_secrets ? '✓' : '✗'} No Secrets
              </span>
              <span className={guardrails.no_dangerous_ops ? 'text-green-600' : 'text-red-600'}>
                {guardrails.no_dangerous_ops ? '✓' : '✗'} Safe Ops
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const VerificationCard = () => {
    if (!trace.verification) return null;

    const { before, after, latency_ms, tests, metrics_deltas } = trace.verification;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <TestTube className="h-5 w-5 text-green-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-medium text-gray-900 mb-3">Verification</h4>

            {/* Before/After JSON */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">Before</h5>
                <div className="bg-red-50 rounded p-2 text-xs font-mono">
                  <pre className="text-red-800">{JSON.stringify(before, null, 2)}</pre>
                </div>
              </div>
              <div>
                <h5 className="text-sm font-medium text-gray-700 mb-2">After</h5>
                <div className="bg-green-50 rounded p-2 text-xs font-mono">
                  <pre className="text-green-800">{JSON.stringify(after, null, 2)}</pre>
                </div>
              </div>
            </div>

            {/* Test results */}
            <div className="mb-4">
              <h5 className="text-sm font-medium text-gray-700 mb-2">Tests</h5>
              <div className="space-y-1">
                {tests.map((test, index) => (
                  <div key={index} className="flex items-center space-x-2 text-sm">
                    {test.passed ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <span className={test.passed ? 'text-green-700' : 'text-red-700'}>
                      {test.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Metrics */}
            {metrics_deltas && (
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-gray-600">Replay: {latency_ms}ms</span>
                <span className="text-green-600">
                  p95 {metrics_deltas.p95_change_percent > 0 ? '+' : ''}{metrics_deltas.p95_change_percent}%
                </span>
                <span className="text-green-600">
                  fail_rate {metrics_deltas.fail_rate_change_percent}%
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const RecommendationsCard = () => {
    // 🔧 Enhanced: Get recommendations from payload if available
    const recommendations = (trace as any).recommendations;
    if (!recommendations) return null;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <FileText className="h-5 w-5 text-orange-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-medium text-gray-900 mb-3">AI Recommendations</h4>
            
            <div className="space-y-4">
              {recommendations.immediate_action && (
                <div className="p-3 bg-orange-50 rounded border border-orange-200">
                  <h5 className="text-sm font-medium text-orange-800 mb-2">🚨 Immediate Action Required</h5>
                  <p className="text-sm text-orange-700 whitespace-pre-wrap">
                    {recommendations.immediate_action}
                  </p>
                </div>
              )}
              
              {recommendations.prevention && (
                <div className="p-3 bg-blue-50 rounded border border-blue-200">
                  <h5 className="text-sm font-medium text-blue-800 mb-2">🛡️ Prevention Strategy</h5>
                  <p className="text-sm text-blue-700 whitespace-pre-wrap">
                    {recommendations.prevention}
                  </p>
                </div>
              )}
              
              {recommendations.monitoring && (
                <div className="p-3 bg-green-50 rounded border border-green-200">
                  <h5 className="text-sm font-medium text-green-800 mb-2">📊 Monitoring & Alerting</h5>
                  <p className="text-sm text-green-700 whitespace-pre-wrap">
                    {recommendations.monitoring}
                  </p>
                </div>
              )}
              
              {recommendations.long_term_improvements && (
                <div className="p-3 bg-purple-50 rounded border border-purple-200">
                  <h5 className="text-sm font-medium text-purple-800 mb-2">🚀 Long-term Improvements</h5>
                  <p className="text-sm text-purple-700 whitespace-pre-wrap">
                    {recommendations.long_term_improvements}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const AuditCard = () => {
    if (!trace.audit) return null;

    const { commit_sha, files_touched, bytes_written, pid, uptime_s, incident_id, hot_reload_success } = trace.audit;

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <FileText className="h-5 w-5 text-gray-600 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-gray-900">Audit Trail</h4>
              <button
                onClick={() => setAuditExpanded(!auditExpanded)}
                className="flex items-center text-sm text-gray-600 hover:text-gray-800"
              >
                {auditExpanded ? (
                  <>
                    <ChevronUp className="h-4 w-4 mr-1" />
                    Collapse
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-4 w-4 mr-1" />
                    Expand
                  </>
                )}
              </button>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Incident ID:</span>
                <code className="font-mono text-gray-900">{incident_id}</code>
              </div>
              
              {auditExpanded && (
                <>
                  {commit_sha && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Commit SHA:</span>
                      <div className="flex items-center space-x-2">
                        <GitCommit className="h-3 w-3 text-gray-500" />
                        <code className="font-mono text-gray-900 text-xs">{commit_sha}</code>
                      </div>
                    </div>
                  )}
                  
                  <div className="flex justify-between">
                    <span className="text-gray-600">Files touched:</span>
                    <span className="text-gray-900">{files_touched.length}</span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-gray-600">Bytes written:</span>
                    <span className="text-gray-900">{bytes_written}</span>
                  </div>
                  
                  {pid && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Hot reload:</span>
                      <span className={hot_reload_success ? 'text-green-600' : 'text-red-600'}>
                        PID {pid} {hot_reload_success ? '✓' : '✗'}
                      </span>
                    </div>
                  )}
                  
                  {uptime_s && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Uptime:</span>
                      <span className="text-gray-900">{uptime_s}s</span>
                    </div>
                  )}
                </>
              )}
            </div>

            <button
              onClick={onCopyEvidence}
              className="mt-3 flex items-center text-sm text-blue-600 hover:text-blue-800"
            >
              <Copy className="h-4 w-4 mr-1" />
              Copy Evidence
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis & Actions</h3>
      
      <CauseCard />
      <CodeChangeCard />
      <VerificationCard />
      <RecommendationsCard />
      <AuditCard />
    </div>
  );
};

export default ReasoningLane; 