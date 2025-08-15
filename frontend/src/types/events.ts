export interface Event {
  type: string;
  key: string;
  payload: Record<string, any>;
  timestamp: string;
  trace_id?: string;
  ui_hint?: string;
}

export interface TraceStep {
  step: string;
  status: 'pending' | 'running' | 'success' | 'error';
  timestamp: string;
  latency_ms?: number;
  details?: string;
  failure?: {
    type: string;
    field?: string;
    expected?: any;
    actual?: any;
    message: string;
  };
  expanded?: boolean;
}

export interface HealingTrace {
  trace_id: string;
  status: 'idle' | 'failing' | 'rca_ready' | 'applying' | 'reloaded' | 'verifying' | 'healed' | 'rolled_back';
  start_time: string;
  duration?: number;
  steps: TraceStep[];
  cause?: string;
  taxonomy?: string[];
  confidence?: number;
  fix_applied?: boolean;
  error_message?: string;
  code_change?: CodeChange;
  verification?: VerificationResult;
  audit?: AuditInfo;
  // 🔧 Enhanced: AI analysis details
  detailed_reasoning?: {
    analysis_steps?: string[];
    evidence?: string;
    patterns_recognized?: string;
    confidence_explanation?: string;
    alternative_playbooks?: string[];
    risk_assessment?: string;
  };
  technical_details?: {
    affected_components?: string[];
    data_flow_impact?: string;
    performance_implications?: string;
    security_considerations?: string;
    scalability_concerns?: string;
  };
  code_analysis?: {
    file_patterns?: string[];
    function_signatures?: string;
    data_structures?: string;
    api_contracts?: string;
  };
  recommendations?: {
    immediate_action?: string;
    prevention?: string;
    monitoring?: string;
    long_term_improvements?: string;
  };
}

export interface CodeChange {
  file: string;
  diff_lines: string[];
  loc_changed: number;
  guardrails: {
    allowlist: boolean;
    max_loc: boolean;
    no_secrets: boolean;
    no_dangerous_ops: boolean;
  };
  diff_id?: string;
  // 🔧 OPTIMIZED: Essential code change information only
  original_code?: string;
  updated_code?: string;
}

export interface VerificationResult {
  before: Record<string, any>;
  after: Record<string, any>;
  latency_ms: number;
  tests: TestResult[];
  metrics_deltas?: {
    p95_change_percent: number;
    fail_rate_change_percent: number;
  };
}

export interface TestResult {
  name: string;
  passed: boolean;
  message?: string;
}

export interface AuditInfo {
  commit_sha?: string;
  files_touched: string[];
  bytes_written: number;
  pid?: number;
  uptime_s?: number;
  incident_id: string;
  hot_reload_success: boolean;
}

export interface HealingStats {
  total_healings: number;
  successful_healings: number;
  failed_healings: number;
  average_duration: number;
  active_healings: number;
}

export interface UIState {
  auto_heal_enabled: boolean;
  show_raw: boolean;
  expanded_step?: string;
  selected_tab?: 'steps' | 'reasoning';
} 