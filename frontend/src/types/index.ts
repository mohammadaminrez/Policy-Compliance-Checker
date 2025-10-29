export interface ResultContext {
  label: string;
  source: string;
  index: number;
  record_id?: number;
  record_position?: number;
  filename?: string;
  policy_id?: number;
  section?: string;
  position?: number;
}

export interface ConditionSummary {
  field?: string;
  operator?: string;
  expected?: any;
  actual?: any;
  error?: string;
}

export interface EvaluationResult {
  user_index: number;
  policy_index: number;
  user_data: Record<string, any>;
  policy: Record<string, any>;
  passed: boolean;
  details: any;
  user_context?: ResultContext;
  policy_context?: ResultContext;
  failed_conditions?: ConditionSummary[];
}

export interface ApiResponse {
  message: string;
  [key: string]: any;
}
