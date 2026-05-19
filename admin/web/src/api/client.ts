export type Provider = {
  id: number;
  name: string;
  code: string;
  provider_type: string;
  base_url: string;
  default_model: string;
  enabled: boolean;
};

export type RecordItem = {
  id: number;
  provider_id: number;
  request_type: string;
  model?: string | null;
  is_stream: boolean;
  http_status?: number | null;
  response_id?: number | null;
};

export type ExecutionTask = {
  id: number;
  name: string;
  source_type: string;
  source_ref_id: number;
  status: string;
  progress_total: number;
  progress_done: number;
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
  success: boolean;
  http_status?: number | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
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
  testProvider: (id: number) => request<{ ok: boolean; detail: string }>(`/admin/providers/${id}/test`, { method: "POST" }),
  listRecords: () => request<{ items: RecordItem[] }>("/admin/records"),
  listExecutionTasks: () => request<{ items: ExecutionTask[] }>("/admin/execution-tasks"),
  createExecutionTask: (payload: unknown) =>
    request<ExecutionTask>("/admin/execution-tasks", { method: "POST", body: JSON.stringify(payload) }),
  startExecutionTask: (id: number) => request<ExecutionTask>(`/admin/execution-tasks/${id}/start`, { method: "POST" }),
  stopExecutionTask: (id: number) => request<ExecutionTask>(`/admin/execution-tasks/${id}/stop`, { method: "POST" }),
  retryExecutionTask: (id: number) => request<ExecutionTask>(`/admin/execution-tasks/${id}/retry`, { method: "POST" }),
  listExecutionResults: (id: number) =>
    request<{ items: ExecutionResultItem[] }>(`/admin/execution-tasks/${id}/results`),
  listEvaluationTasks: () => request<{ items: EvaluationTask[] }>("/admin/evaluation-tasks"),
  createEvaluationTask: (payload: unknown) =>
    request<EvaluationTask>("/admin/evaluation-tasks", { method: "POST", body: JSON.stringify(payload) }),
  listEvaluationScores: (id: number) => request<{ items: unknown[] }>(`/admin/evaluation-tasks/${id}/scores`),
};
