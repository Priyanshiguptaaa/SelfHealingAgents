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

    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-start space-x-3">
          <Brain className="h-5 w-5 text-purple-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-medium text-gray-900 mb-2">Root Cause Analysis</h4>
            <p className="text-gray-700 mb-3">{trace.cause}</p>
            
            <div className="flex items-center space-x-3">
              {trace.taxonomy?.map((tag, index) => (
                <span 
                  key={index}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
                >
                  {tag}
                </span>
              ))}
              {trace.confidence && (
                <span className="text-sm text-gray-600">
                  Confidence: {(trace.confidence * 100).toFixed(0)}%
                </span>
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

            {/* Diff viewer */}
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
      <AuditCard />
    </div>
  );
};

export default ReasoningLane; 