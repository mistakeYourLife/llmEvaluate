export type Provider = {
  id: number;
  name: string;
  code: string;
  provider_type: string;
  base_url: string;
  default_model: string;
  timeout_ms: number;
  enabled: boolean;
  is_default: boolean;
};

export type RecordItem = {
  id: number;
  name: string;
  provider_id: number;
  request_type: string;
  model?: string | null;
  is_stream: boolean;
  http_status?: number | null;
  response_id?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type RecordDetail = RecordItem & {
  source_app?: string | null;
  request_headers_json: Record<string, unknown>;
  request_body_json: Record<string, unknown>;
  request_text_snapshot?: string | null;
  response: {
    id?: number | null;
    http_status?: number | null;
    response_headers_json: Record<string, unknown>;
    response_body_json: Record<string, unknown>;
    response_text_snapshot?: string | null;
    first_token_latency_ms?: number | null;
    complete_latency_ms?: number | null;
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
    tokens_per_second?: number | null;
    error_code?: string | null;
    error_message?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
  };
};

export type ExecutionTask = {
  id: number;
  name: string;
  source_type: string;
  source_ref_id: number;
  target_provider_ids_json?: { ids?: number[] } | null;
  target_models_json?: { models?: string[] } | null;
  status: string;
  progress_total: number;
  progress_done: number;
  run_count?: number;
};

export type EvaluationTask = {
  id: number;
  name: string;
  source_type: string;
  source_ref_id: number;
  evaluator_type: string;
  judge_provider_id: number;
  judge_model: string;
  status: string;
  progress_total: number;
  progress_done: number;
};

export type ExecutionResultItem = {
  id: number;
  provider_id: number;
  model?: string | null;
  run_index: number;
  success: boolean;
  http_status?: number | null;
  first_token_latency_ms?: number | null;
  complete_latency_ms?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  tokens_per_second?: number | null;
  error_code?: string | null;
  error_message?: string | null;
};

export type ExecutionResultDetail = ExecutionResultItem & {
  execution_task_id: number;
  source_request_id?: number | null;
  sample_id?: number | null;
  run_index: number;
  request_body_json: Record<string, unknown>;
  response_body_json: Record<string, unknown>;
  output_text?: string | null;
  created_at: string;
  updated_at: string;
};

export type EvaluationScoreItem = {
  id: number;
  execution_result_id: number;
  score: number;
  verdict?: string | null;
  reasoning_summary?: string | null;
  dimension_scores_json: Record<string, unknown>;
  judge_model: string;
};

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (response.status === 204) {
    return undefined as T;
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: string; error?: { message?: string } };
      if (typeof payload.detail === "string" && payload.detail) {
        message = payload.detail;
      } else if (typeof payload.error?.message === "string" && payload.error.message) {
        message = payload.error.message;
      }
    } catch {
      try {
        const rawText = await response.text();
        if (rawText) {
          message = rawText;
        }
      } catch {
        // Ignore secondary parsing failure and keep fallback status text.
      }
    }
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listProviders: () => request<{ items: Provider[] }>("/admin/providers"),
  createProvider: (payload: unknown) =>
    request<Provider>("/admin/providers", { method: "POST", body: JSON.stringify(payload) }),
  updateProvider: (id: number, payload: unknown) =>
    request<Provider>(`/admin/providers/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  toggleProvider: (id: number, enabled: boolean) =>
    request<Provider>(`/admin/providers/${id}/${enabled ? "enable" : "disable"}`, { method: "POST" }),
  setDefaultProvider: (id: number) => request<Provider>(`/admin/providers/${id}/set-default`, { method: "POST" }),
  deleteProvider: (id: number) => request<void>(`/admin/providers/${id}`, { method: "DELETE" }),
  testProvider: (id: number) => request<{ ok: boolean; detail: string }>(`/admin/providers/${id}/test`, { method: "POST" }),
  listRecords: () => request<{ items: RecordItem[] }>("/admin/records"),
  getRecord: (id: number) => request<RecordDetail>(`/admin/records/${id}`),
  updateRecord: (id: number, payload: unknown) =>
    request<RecordDetail>(`/admin/records/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteRecord: (id: number) => request<void>(`/admin/records/${id}`, { method: "DELETE" }),
  listExecutionTasks: () => request<{ items: ExecutionTask[] }>("/admin/execution-tasks"),
  createExecutionTask: (payload: unknown) =>
    request<ExecutionTask>("/admin/execution-tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateExecutionTask: (id: number, payload: unknown) =>
    request<ExecutionTask>(`/admin/execution-tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  startExecutionTask: (id: number) => request<ExecutionTask>(`/admin/execution-tasks/${id}/start`, { method: "POST" }),
  stopExecutionTask: (id: number) => request<ExecutionTask>(`/admin/execution-tasks/${id}/stop`, { method: "POST" }),
  retryExecutionTask: (id: number) => request<ExecutionTask>(`/admin/execution-tasks/${id}/retry`, { method: "POST" }),
  listExecutionResults: (id: number) =>
    request<{ items: ExecutionResultItem[] }>(`/admin/execution-tasks/${id}/results`),
  getExecutionResult: (taskId: number, resultId: number) =>
    request<ExecutionResultDetail>(`/admin/execution-tasks/${taskId}/results/${resultId}`),
  listEvaluationTasks: () => request<{ items: EvaluationTask[] }>("/admin/evaluation-tasks"),
  createEvaluationTask: (payload: unknown) =>
    request<EvaluationTask>("/admin/evaluation-tasks", { method: "POST", body: JSON.stringify(payload) }),
  startEvaluationTask: (id: number) => request<EvaluationTask>(`/admin/evaluation-tasks/${id}/start`, { method: "POST" }),
  retryEvaluationTask: (id: number) => request<EvaluationTask>(`/admin/evaluation-tasks/${id}/retry`, { method: "POST" }),
  deleteEvaluationTask: (id: number) => request<void>(`/admin/evaluation-tasks/${id}`, { method: "DELETE" }),
  listEvaluationScores: (id: number) =>
    request<{ items: EvaluationScoreItem[] }>(`/admin/evaluation-tasks/${id}/scores`),
};
