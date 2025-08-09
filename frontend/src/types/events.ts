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
  duration?: number;
  details?: string;
}

export interface HealingTrace {
  trace_id: string;
  status: 'analyzing' | 'generating' | 'applying' | 'verifying' | 'complete' | 'failed';
  start_time: string;
  duration?: number;
  steps: TraceStep[];
  cause?: string;
  fix_applied?: boolean;
  error_message?: string;
}

export interface CodeDiff {
  filename: string;
  before: string;
  after: string;
  diff_lines: string[];
  lines_changed: number;
}

export interface HealingStats {
  total_healings: number;
  successful_healings: number;
  failed_healings: number;
  average_duration: number;
  active_healings: number;
} 