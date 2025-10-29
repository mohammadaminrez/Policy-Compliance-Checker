export interface EvaluationResult {
  user_index: number;
  policy_index: number;
  user_data: Record<string, any>;
  policy: Record<string, any>;
  passed: boolean;
  details: any;
}

export interface ApiResponse {
  message: string;
  [key: string]: any;
}
