import { useEffect, useMemo, useState } from "react";
import {
  api,
  type ExecutionResultDetail,
  type EvaluationScoreItem,
  type EvaluationTask,
  type ExecutionResultItem,
  type ExecutionTask,
  type Provider,
  type RecordDetail,
  type RecordItem,
} from "./api/client";

type Tab = "handbook" | "providers" | "records" | "execution" | "evaluation" | "results";

type ProviderFormState = {
  name: string;
  code: string;
  provider_type: string;
  base_url: string;
  api_key: string;
  default_model: string;
  timeout_ms: string;
};

const emptyProviderForm: ProviderFormState = {
  name: "",
  code: "",
  provider_type: "openai",
  base_url: "",
  api_key: "",
  default_model: "",
  timeout_ms: "30000",
};

const tabLabels: Array<[Tab, string]> = [
  ["handbook", "手册"],
  ["providers", "供应商管理"],
  ["records", "录制样本"],
  ["execution", "执行任务"],
  ["evaluation", "评估任务"],
  ["results", "评分结果"],
];

const validTabs = new Set<Tab>(tabLabels.map(([tab]) => tab));
const detailPreviewLineLimit = 18;
const detailPreviewCharLimit = 1200;

const requestTypeLabels: Record<string, string> = {
  chat_completions: "对话补全",
};

const taskStatusLabels: Record<string, string> = {
  pending: "待执行",
  running: "执行中",
  completed: "已完成",
  failed: "执行失败",
  stopped: "已停止",
};

const verdictLabels: Record<string, string> = {
  pass: "通过",
  fail: "不通过",
  review: "需复核",
};

const dimensionLabels: Record<string, string> = {
  relevance: "相关性",
  correctness: "正确性",
  completeness: "完整性",
  format_following: "格式遵循",
  format_consistency: "格式一致性",
  semantic_consistency: "语义一致性",
  quality_parity: "水平接近度",
  risk_control: "风险控制",
};

function formatRequestType(requestType: string) {
  return requestTypeLabels[requestType] ?? requestType;
}

function formatTaskStatus(status: string) {
  return taskStatusLabels[status] ?? status;
}

function formatVerdict(verdict?: string | null) {
  if (!verdict) {
    return "未判定";
  }
  return verdictLabels[verdict] ?? verdict;
}

function formatProviderProbeDetail(detail: string) {
  if (detail.startsWith("model_available:")) {
    const model = detail.slice("model_available:".length);
    return model ? `模型可用（${model}）` : "模型可用";
  }
  if (detail === "reachable") {
    return "连接正常";
  }
  if (detail.includes("invalid OpenAI response")) {
    return "返回内容不是有效的 OpenAI 对话结果，请检查 API 地址是否填写到了兼容根路径（通常以 /v1 结尾）。";
  }
  if (detail.startsWith("provider returned an error payload:")) {
    return `供应商返回错误：${detail.replace("provider returned an error payload:", "").trim()}`;
  }
  return detail;
}

function formatTimeoutMs(timeoutMs?: number | null) {
  const normalized = timeoutMs ?? 30000;
  if (normalized % 1000 === 0) {
    return `${normalized} 毫秒（${normalized / 1000} 秒）`;
  }
  return `${normalized} 毫秒`;
}

function formatDimensionName(dimension: string) {
  return dimensionLabels[dimension] ?? dimension;
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").slice(0, 19);
}

function formatMetricValue(value?: number | null) {
  if (value === null || value === undefined) {
    return "-";
  }
  return String(value);
}

function formatJsonContent(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function formatRecordName(record: { id: number; name?: string | null }) {
  if (record.name && record.name.trim()) {
    return record.name.trim();
  }
  return String(record.id);
}

function formatExecutionTaskModels(
  task: Pick<ExecutionTask, "target_models_json" | "target_provider_ids_json">,
  providerById: Map<number, Provider>,
) {
  const overrideModels = (task.target_models_json?.models ?? []).map((item) => item.trim()).filter(Boolean);
  if (overrideModels.length > 0) {
    return Array.from(new Set(overrideModels)).join(", ");
  }

  const defaultModels = (task.target_provider_ids_json?.ids ?? [])
    .map((providerId) => providerById.get(providerId)?.default_model?.trim() ?? "")
    .filter(Boolean);
  if (defaultModels.length > 0) {
    return Array.from(new Set(defaultModels)).join(", ");
  }

  return "-";
}

type ComparableExecutionMetricKey =
  | "first_token_latency_ms"
  | "complete_latency_ms"
  | "prompt_tokens"
  | "completion_tokens"
  | "total_tokens"
  | "tokens_per_second";

type ExecutionTaskComparisonData = {
  leftTask: ExecutionTask;
  rightTask: ExecutionTask;
  leftResults: ExecutionResultItem[];
  rightResults: ExecutionResultItem[];
};

type SummaryComparisonWinner = "任务 A" | "任务 B" | "持平" | "-";

type ExecutionTaskSummaryRow = {
  label: string;
  left: string;
  right: string;
  better: SummaryComparisonWinner;
};

const lowerBetterMetricKeys: ComparableExecutionMetricKey[] = [
  "first_token_latency_ms",
  "complete_latency_ms",
  "prompt_tokens",
  "completion_tokens",
  "total_tokens",
];

const higherBetterMetricKeys: ComparableExecutionMetricKey[] = ["tokens_per_second"];

function getExecutionMetricValue(result: ExecutionResultItem, key: ComparableExecutionMetricKey) {
  const value = result[key];
  return typeof value === "number" ? value : null;
}

function buildExecutionResultBestValues(results: ExecutionResultItem[]) {
  const candidateResults = results.some((item) => item.success) ? results.filter((item) => item.success) : results;
  const bestValues: Partial<Record<ComparableExecutionMetricKey, number>> = {};

  for (const key of lowerBetterMetricKeys) {
    const values = candidateResults.map((item) => getExecutionMetricValue(item, key)).filter((item) => item !== null);
    if (values.length > 0) {
      bestValues[key] = Math.min(...values);
    }
  }

  for (const key of higherBetterMetricKeys) {
    const values = candidateResults.map((item) => getExecutionMetricValue(item, key)).filter((item) => item !== null);
    if (values.length > 0) {
      bestValues[key] = Math.max(...values);
    }
  }

  return bestValues;
}

function isBestExecutionMetric(
  result: ExecutionResultItem,
  key: ComparableExecutionMetricKey,
  bestValues: Partial<Record<ComparableExecutionMetricKey, number>>,
  resultCount: number,
) {
  if (resultCount < 2) {
    return false;
  }
  const value = getExecutionMetricValue(result, key);
  return value !== null && bestValues[key] !== undefined && value === bestValues[key];
}

function getComparableExecutionResults(results: ExecutionResultItem[]) {
  const successfulResults = results.filter((item) => item.success);
  return successfulResults.length ? successfulResults : results;
}

function averageExecutionMetric(results: ExecutionResultItem[], key: ComparableExecutionMetricKey) {
  const values = getComparableExecutionResults(results)
    .map((item) => getExecutionMetricValue(item, key))
    .filter((item) => item !== null);
  if (!values.length) {
    return null;
  }
  return values.reduce((sum, item) => sum + item, 0) / values.length;
}

function getExecutionSuccessRate(results: ExecutionResultItem[]) {
  if (!results.length) {
    return null;
  }
  return results.filter((item) => item.success).length / results.length;
}

function formatAverageMetricValue(value: number | null) {
  if (value === null) {
    return "-";
  }
  return value.toFixed(2);
}

function formatPercentValue(value: number | null) {
  if (value === null) {
    return "-";
  }
  return `${(value * 100).toFixed(2)}%`;
}

function compareMetricValues(left: number | null, right: number | null, direction: "lower" | "higher"): SummaryComparisonWinner {
  if (left === null && right === null) {
    return "-";
  }
  if (left === null) {
    return "任务 B";
  }
  if (right === null) {
    return "任务 A";
  }
  if (left === right) {
    return "持平";
  }
  if (direction === "lower") {
    return left < right ? "任务 A" : "任务 B";
  }
  return left > right ? "任务 A" : "任务 B";
}

function buildExecutionTaskSummaryRows(leftResults: ExecutionResultItem[], rightResults: ExecutionResultItem[]) {
  const leftSuccessRate = getExecutionSuccessRate(leftResults);
  const rightSuccessRate = getExecutionSuccessRate(rightResults);
  const leftFirstToken = averageExecutionMetric(leftResults, "first_token_latency_ms");
  const rightFirstToken = averageExecutionMetric(rightResults, "first_token_latency_ms");
  const leftDuration = averageExecutionMetric(leftResults, "complete_latency_ms");
  const rightDuration = averageExecutionMetric(rightResults, "complete_latency_ms");
  const leftPromptTokens = averageExecutionMetric(leftResults, "prompt_tokens");
  const rightPromptTokens = averageExecutionMetric(rightResults, "prompt_tokens");
  const leftCompletionTokens = averageExecutionMetric(leftResults, "completion_tokens");
  const rightCompletionTokens = averageExecutionMetric(rightResults, "completion_tokens");
  const leftTotalTokens = averageExecutionMetric(leftResults, "total_tokens");
  const rightTotalTokens = averageExecutionMetric(rightResults, "total_tokens");
  const leftTps = averageExecutionMetric(leftResults, "tokens_per_second");
  const rightTps = averageExecutionMetric(rightResults, "tokens_per_second");

  return [
    {
      label: "结果数",
      left: String(leftResults.length),
      right: String(rightResults.length),
      better: "-",
    },
    {
      label: "成功率",
      left: formatPercentValue(leftSuccessRate),
      right: formatPercentValue(rightSuccessRate),
      better: compareMetricValues(leftSuccessRate, rightSuccessRate, "higher"),
    },
    {
      label: "平均首 token(ms)",
      left: formatAverageMetricValue(leftFirstToken),
      right: formatAverageMetricValue(rightFirstToken),
      better: compareMetricValues(leftFirstToken, rightFirstToken, "lower"),
    },
    {
      label: "平均总耗时(ms)",
      left: formatAverageMetricValue(leftDuration),
      right: formatAverageMetricValue(rightDuration),
      better: compareMetricValues(leftDuration, rightDuration, "lower"),
    },
    {
      label: "平均输入 token",
      left: formatAverageMetricValue(leftPromptTokens),
      right: formatAverageMetricValue(rightPromptTokens),
      better: compareMetricValues(leftPromptTokens, rightPromptTokens, "lower"),
    },
    {
      label: "平均输出 token",
      left: formatAverageMetricValue(leftCompletionTokens),
      right: formatAverageMetricValue(rightCompletionTokens),
      better: compareMetricValues(leftCompletionTokens, rightCompletionTokens, "lower"),
    },
    {
      label: "平均总 token",
      left: formatAverageMetricValue(leftTotalTokens),
      right: formatAverageMetricValue(rightTotalTokens),
      better: compareMetricValues(leftTotalTokens, rightTotalTokens, "lower"),
    },
    {
      label: "平均 TPS",
      left: formatAverageMetricValue(leftTps),
      right: formatAverageMetricValue(rightTps),
      better: compareMetricValues(leftTps, rightTps, "higher"),
    },
  ] satisfies ExecutionTaskSummaryRow[];
}

function isSummaryMetricWinner(better: SummaryComparisonWinner, side: "left" | "right") {
  return (side === "left" && better === "任务 A") || (side === "right" && better === "任务 B");
}

function buildExecutionResultCompareKey(result: ExecutionResultItem, providerNameById: Map<number, string>) {
  const providerName = providerNameById.get(result.provider_id) ?? `#${result.provider_id}`;
  return `${providerName} · ${result.model ?? "-"} · 第 ${result.run_index + 1} 次`;
}

function buildExecutionResultComparisonRows(
  leftTask: ExecutionTask,
  rightTask: ExecutionTask,
  leftResults: ExecutionResultItem[],
  rightResults: ExecutionResultItem[],
  providerNameById: Map<number, string>,
) {
  const rows = [
    ...leftResults.map((result) => {
      const baseKey = buildExecutionResultCompareKey(result, providerNameById);
      return {
        key: `${leftTask.id}-${result.id}`,
        label: `${leftTask.name} · ${baseKey}`,
        sortKey: baseKey,
        taskOrder: 0,
        result,
      };
    }),
    ...rightResults.map((result) => {
      const baseKey = buildExecutionResultCompareKey(result, providerNameById);
      return {
        key: `${rightTask.id}-${result.id}`,
        label: `${rightTask.name} · ${baseKey}`,
        sortKey: baseKey,
        taskOrder: 1,
        result,
      };
    }),
  ];

  return rows.sort((left, right) => {
    const baseCompare = left.sortKey.localeCompare(right.sortKey, "zh-Hans-CN");
    if (baseCompare !== 0) {
      return baseCompare;
    }
    if (left.taskOrder !== right.taskOrder) {
      return left.taskOrder - right.taskOrder;
    }
    return left.label.localeCompare(right.label, "zh-Hans-CN");
  });
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function showPopup(message: string) {
  window.alert(message);
}

function reportStatus(setStatus: (message: string) => void, message: string) {
  setStatus(message);
  showPopup(message);
}

function reportError(setError: ((message: string) => void) | undefined, error: unknown) {
  const message = getErrorMessage(error);
  setError?.(message);
  showPopup(message);
  return message;
}

function shouldCollapseDetailText(content: string) {
  return content.length > detailPreviewCharLimit || content.split("\n").length > detailPreviewLineLimit;
}

function buildDetailTextPreview(content: string) {
  const lines = content.split("\n");
  if (lines.length > detailPreviewLineLimit) {
    const truncatedLines = lines.slice(0, detailPreviewLineLimit).join("\n");
    if (truncatedLines.length > detailPreviewCharLimit) {
      return `${truncatedLines.slice(0, detailPreviewCharLimit)}\n...`;
    }
    return `${truncatedLines}\n...`;
  }
  if (content.length > detailPreviewCharLimit) {
    return `${content.slice(0, detailPreviewCharLimit)}...`;
  }
  return content;
}

function parseTimeoutMs(value: string) {
  const normalized = Number(value);
  if (!Number.isInteger(normalized) || normalized <= 0) {
    throw new Error("超时时间必须是大于 0 的整数毫秒值。");
  }
  return normalized;
}

function parseTabFromHash(hash: string): Tab | null {
  const normalized = hash.replace(/^#/, "");
  return validTabs.has(normalized as Tab) ? (normalized as Tab) : null;
}

export default function App() {
  const [tab, setTabState] = useState<Tab>(() => parseTabFromHash(window.location.hash) ?? "providers");
  const [executionSourceRefId, setExecutionSourceRefId] = useState<string>("");
  const [evaluationSourceRefId, setEvaluationSourceRefId] = useState<string>("");
  const [selectedEvaluationTaskId, setSelectedEvaluationTaskId] = useState<string>("");

  const setTab = (nextTab: Tab) => {
    setTabState(nextTab);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${nextTab}`);
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-mark">
          <span className="brand-kicker">评测控制台</span>
          <h1>llmEvaluate</h1>
        </div>
        <nav>
          {tabLabels.map(([key, label]) => (
            <button key={key} className={tab === key ? "nav active" : "nav"} onClick={() => setTab(key as Tab)}>
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        {tab === "handbook" ? <HandbookPage /> : null}
        {tab === "providers" ? <ProvidersPage /> : null}
        {tab === "records" ? (
          <RecordsPage
            onUseRecord={(recordId) => {
              setExecutionSourceRefId(String(recordId));
              setTab("execution");
            }}
          />
        ) : null}
        {tab === "execution" ? (
          <ExecutionPage
            initialSourceRefId={executionSourceRefId}
            onUseExecutionTask={(taskId) => {
              setEvaluationSourceRefId(String(taskId));
              setTab("evaluation");
            }}
          />
        ) : null}
        {tab === "evaluation" ? (
          <EvaluationPage
            initialExecutionTaskId={evaluationSourceRefId}
            onViewScores={(taskId) => {
              setSelectedEvaluationTaskId(String(taskId));
              setTab("results");
            }}
          />
        ) : null}
        {tab === "results" ? <ResultsPage initialEvaluationTaskId={selectedEvaluationTaskId} /> : null}
      </main>
    </div>
  );
}

function HandbookPage() {
  return (
    <section className="stack">
      <SectionHeading
        title="使用手册"
        description="帮助业务方快速理解如何通过标准 OpenAI 格式接入本系统，并成功录制样本。"
      />
      <div className="card stack">
        <strong>如何录制样本</strong>
        <p className="manual-paragraph">
          录制样本不是在页面里手工创建，而是让你的业务请求真实打到 `llmEvaluate` 的代理接口。系统在转发给默认录制供应商的同时，会旁路保存这次请求和响应。
        </p>
      </div>
      <div className="card stack">
        <strong>前置条件</strong>
        <ol className="manual-list">
          <li>先到“供应商管理”里创建至少一个可用供应商。</li>
          <li>确认有一个供应商被标记为“默认录制”。录制请求只会走这个默认供应商。</li>
          <li>确认该供应商“测试模型”通过，避免录制时直接拿到错误响应。</li>
        </ol>
      </div>
      <div className="card stack">
        <strong>请求地址</strong>
        <p className="manual-paragraph">把你业务里原本请求 OpenAI 兼容接口的地址，改成下面这个代理地址：</p>
        <pre className="code-block">POST http://127.0.0.1:8000/v1/chat/completions</pre>
        <p className="manual-paragraph">只有真正请求 `POST /v1/chat/completions` 才会产生录制样本。仅访问 `http://127.0.0.1:8000/v1` 不会录制。</p>
      </div>
      <div className="card stack">
        <strong>curl 示例</strong>
        <pre className="code-block">{`curl http://127.0.0.1:8000/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{
    "model": "gpt-5.4",
    "messages": [
      { "role": "system", "content": "你是一个客服助手" },
      { "role": "user", "content": "请帮我总结这段对话" }
    ]
  }'`}</pre>
      </div>
      <div className="card stack">
        <strong>录制成功后去哪里看</strong>
        <ol className="manual-list">
          <li>请求返回成功后，进入左侧“录制样本”。</li>
          <li>列表里会新增一条样本记录，默认名称先跟样本 ID 一致。</li>
          <li>点击“查看详情”，可以看到请求头、请求体、响应头、响应体以及时延和 token 信息。</li>
          <li>如果样本有意义，建议立刻点“修改名称”，方便后续创建执行任务时识别。</li>
        </ol>
      </div>
      <div className="card stack">
        <strong>常见误区</strong>
        <ol className="manual-list">
          <li>只打开页面不会生成样本，必须由业务侧真实发起一次对话请求。</li>
          <li>录制阶段不会同时打多个供应商，只会走默认录制供应商。</li>
          <li>想比较多个供应商时，请先录好样本，再去“执行任务”里重跑多个供应商。</li>
          <li>如果页面里没看到新样本，先检查请求是否真的打到了 `8000`，以及默认录制供应商是否可用。</li>
        </ol>
      </div>
    </section>
  );
}

function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [form, setForm] = useState<ProviderFormState>(emptyProviderForm);
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);
  const [testingProviderId, setTestingProviderId] = useState<number | null>(null);
  const [providerProbeMessages, setProviderProbeMessages] = useState<Record<number, string>>({});

  const refresh = async () => {
    try {
      const result = await api.listProviders();
      setProviders(result.items);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  const editingProvider = providers.find((provider) => provider.id === editingProviderId) ?? null;

  const submitLabel = editingProviderId ? "保存变更" : "新建供应商";

  return (
    <section className="stack">
      <SectionHeading
        title="供应商管理"
        description="配置真实供应商，验证连通性，并维护后续执行与评估共用的模型入口。"
      />
      <div className="card tip-card">
        <strong>填写说明</strong>
        <p>API 地址请填写到 OpenAI 兼容根路径，通常需要以 `/v1` 结尾。例如 `https://api.openai.com/v1`。</p>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {status ? <p className="status">{status}</p> : null}
      <form
        className="card form-grid form-panel"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            const timeoutMs = parseTimeoutMs(form.timeout_ms);
            if (editingProviderId) {
              await api.updateProvider(editingProviderId, {
                name: form.name,
                base_url: form.base_url,
                default_model: form.default_model,
                api_key: form.api_key,
                timeout_ms: timeoutMs,
              });
              reportStatus(setStatus, `供应商 ${form.name} 已更新。`);
            } else {
              await api.createProvider({
                name: form.name,
                code: form.code,
                provider_type: form.provider_type,
                base_url: form.base_url,
                api_key: form.api_key,
                default_model: form.default_model,
                timeout_ms: timeoutMs,
              });
              reportStatus(setStatus, `供应商 ${form.name} 已创建。`);
            }
            setForm(emptyProviderForm);
            setEditingProviderId(null);
            await refresh();
          } catch (err) {
            reportError(setError, err);
          }
        }}
      >
        <div className="form-header">
          <strong>{editingProvider ? `编辑供应商 #${editingProvider.id}` : "新建供应商"}</strong>
          <span>{editingProvider ? editingProvider.code : "创建一个兼容 OpenAI 协议的供应商配置。"}</span>
        </div>
        <label>
          <span>名称</span>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          <span>编码</span>
          <input
            value={form.code}
            disabled={editingProviderId !== null}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
        </label>
        <label>
          <span>供应商类型</span>
          <input
            value={form.provider_type}
            disabled={editingProviderId !== null}
            onChange={(e) => setForm({ ...form, provider_type: e.target.value })}
          />
        </label>
        <label>
          <span>API 地址</span>
          <input
            placeholder="例如：https://api.openai.com/v1"
            value={form.base_url}
            onChange={(e) => setForm({ ...form, base_url: e.target.value })}
          />
        </label>
        <label>
          <span>API 密钥</span>
          <input
            type="password"
            placeholder={editingProviderId ? "留空表示保持不变" : ""}
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
          />
        </label>
        <label>
          <span>默认模型</span>
          <input value={form.default_model} onChange={(e) => setForm({ ...form, default_model: e.target.value })} />
        </label>
        <label>
          <span>超时时间（毫秒）</span>
          <input
            type="number"
            min="1"
            step="1"
            value={form.timeout_ms}
            onChange={(e) => setForm({ ...form, timeout_ms: e.target.value })}
          />
        </label>
        <div className="actions">
          <button type="submit">{submitLabel}</button>
          {editingProviderId ? (
            <button
              type="button"
              className="button-secondary"
              onClick={() => {
                setEditingProviderId(null);
                setForm(emptyProviderForm);
                setStatus("已取消编辑。");
              }}
            >
              取消
            </button>
          ) : null}
        </div>
      </form>
      <div className="card table-card">
        <div className="table-wrap">
          <table className="data-table" aria-label="供应商列表">
            <thead>
              <tr>
                <th>名称</th>
                <th>编码</th>
                <th>状态</th>
                <th>默认模型</th>
                <th>服务地址</th>
                <th>超时时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {providers.length ? (
                providers.map((provider) => (
                  <tr key={provider.id}>
                    <td>
                      <div className="cell-primary">{provider.name}</div>
                      <div className="muted">#{provider.id}</div>
                      {providerProbeMessages[provider.id] ? (
                        <div className="cell-subtle" aria-live="polite">
                          {providerProbeMessages[provider.id]}
                        </div>
                      ) : null}
                    </td>
                    <td>{provider.code}</td>
                    <td>
                      <div className="pill-stack">
                        <span className={provider.enabled ? "pill pill-enabled" : "pill pill-disabled"}>
                          {provider.enabled ? "已启用" : "已禁用"}
                        </span>
                        {provider.is_default ? <span className="pill">默认录制</span> : null}
                      </div>
                    </td>
                    <td>{provider.default_model}</td>
                    <td>{provider.base_url}</td>
                    <td>{formatTimeoutMs(provider.timeout_ms)}</td>
                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={() => {
                            setEditingProviderId(provider.id);
                            setForm({
                              name: provider.name,
                              code: provider.code,
                              provider_type: provider.provider_type,
                              base_url: provider.base_url,
                              api_key: "",
                              default_model: provider.default_model,
                              timeout_ms: String(provider.timeout_ms ?? 30000),
                            });
                            setStatus(`正在编辑供应商 ${provider.name}。`);
                          }}
                        >
                          编辑
                        </button>
                        {!provider.is_default ? (
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={async () => {
                              try {
                                await api.setDefaultProvider(provider.id);
                                reportStatus(setStatus, `供应商 ${provider.name} 已设为默认录制供应商。`);
                                await refresh();
                              } catch (err) {
                                reportError(setError, err);
                              }
                            }}
                          >
                            设为默认
                          </button>
                        ) : null}
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={async () => {
                            try {
                              await api.toggleProvider(provider.id, !provider.enabled);
                              reportStatus(setStatus, `供应商 ${provider.name} 已${provider.enabled ? "禁用" : "启用"}。`);
                              await refresh();
                            } catch (err) {
                              reportError(setError, err);
                            }
                          }}
                        >
                          {provider.enabled ? "禁用" : "启用"}
                        </button>
                        <button
                          type="button"
                          className="button-secondary button-danger"
                          onClick={async () => {
                            if (!window.confirm(`确认删除供应商「${provider.name}」吗？`)) {
                              return;
                            }
                            try {
                              await api.deleteProvider(provider.id);
                              reportStatus(setStatus, `供应商 ${provider.name} 已删除。`);
                              if (editingProviderId === provider.id) {
                                setEditingProviderId(null);
                                setForm(emptyProviderForm);
                              }
                              await refresh();
                            } catch (err) {
                              reportError(setError, err);
                            }
                          }}
                        >
                          删除
                        </button>
                        <button
                          type="button"
                          disabled={testingProviderId === provider.id}
                          onClick={async () => {
                            setTestingProviderId(provider.id);
                            setProviderProbeMessages((current) => ({
                              ...current,
                              [provider.id]: "连接结果：检测中...",
                            }));
                            try {
                              const result = await api.testProvider(provider.id);
                              const detail = formatProviderProbeDetail(result.detail);
                              reportStatus(setStatus, `${provider.name}：${detail}`);
                              setProviderProbeMessages((current) => ({
                                ...current,
                                [provider.id]: `连接结果：${detail}`,
                              }));
                            } catch (err) {
                              const message = `连接结果：检测失败 - ${getErrorMessage(err)}`;
                              reportError(setError, err);
                              setProviderProbeMessages((current) => ({
                                ...current,
                                [provider.id]: message,
                              }));
                            } finally {
                              setTestingProviderId((current) => (current === provider.id ? null : current));
                            }
                          }}
                        >
                          {testingProviderId === provider.id ? "检测中..." : "测试模型"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="table-empty" colSpan={7}>
                    暂无供应商。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function RecordsPage({ onUseRecord }: { onUseRecord: (recordId: number) => void }) {
  const [items, setItems] = useState<RecordItem[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [selectedRecord, setSelectedRecord] = useState<RecordDetail | null>(null);
  const [loadingRecordId, setLoadingRecordId] = useState<number | null>(null);
  const [recordNameDraft, setRecordNameDraft] = useState("");
  const [recordNameModal, setRecordNameModal] = useState<{ id: number; name: string } | null>(null);
  const [textPreviewModal, setTextPreviewModal] = useState<{ title: string; content: string } | null>(null);

  const refresh = async () => {
    try {
      const [recordResult, providerResult] = await Promise.all([api.listRecords(), api.listProviders()]);
      setItems(recordResult.items);
      setProviders(providerResult.items);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  const enabledProviderIds = providers.filter((item) => item.enabled).map((item) => item.id);
  const providerNameById = new Map(providers.map((provider) => [provider.id, provider.name]));

  return (
    <section className="stack">
      <SectionHeading
        title="录制样本"
        description="查看录制下来的原始请求样本，把实际业务流量直接转成可复跑的执行任务。"
      />
      <div className="card tip-card">
        <strong>如何录制</strong>
        <p>将你的业务请求发到 `POST /v1/chat/completions`。仅访问 `http://127.0.0.1:8000/v1` 不会产生录制样本。</p>
        <div className="row">
          <button type="button" className="button-secondary" onClick={() => refresh().then(() => setStatus("录制列表已刷新。"))}>
            刷新列表
          </button>
        </div>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {status ? <p className="status">{status}</p> : null}
      <div className="card table-card">
        <div className="table-wrap">
          <table className="data-table" aria-label="录制样本列表">
            <thead>
              <tr>
                <th>名称</th>
                <th>请求类型</th>
                <th>来源供应商</th>
                <th>模型</th>
                <th>状态码</th>
                <th>录制时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((item) => (
                  <tr key={item.id} className={selectedRecord?.id === item.id ? "table-row-active" : undefined}>
                    <td>
                      <div className="cell-primary">{formatRecordName(item)}</div>
                      <div className="muted">样本 #{item.id}</div>
                      {item.error_message ? <div className="cell-error">异常：{item.error_message}</div> : null}
                    </td>
                    <td>{formatRequestType(item.request_type)}</td>
                    <td>{providerNameById.get(item.provider_id) ?? `#${item.provider_id}`}</td>
                    <td>{item.model ?? "-"}</td>
                    <td>{item.http_status ?? "-"}</td>
                    <td>{formatDateTime(item.created_at)}</td>
                    <td>
                      <div className="table-actions">
                        <button type="button" onClick={() => onUseRecord(item.id)}>
                          用于执行
                        </button>
                        <button
                          type="button"
                          className="button-secondary"
                          disabled={loadingRecordId === item.id}
                          onClick={async () => {
                            setLoadingRecordId(item.id);
                            try {
                              const detail = await api.getRecord(item.id);
                              setSelectedRecord(detail);
                              setRecordNameDraft(formatRecordName(detail));
                              setStatus(`已加载样本 ${item.id} 的详情。`);
                            } catch (err) {
                              setError((err as Error).message);
                            } finally {
                              setLoadingRecordId((current) => (current === item.id ? null : current));
                            }
                          }}
                        >
                          {loadingRecordId === item.id ? "加载中..." : "查看详情"}
                        </button>
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={() => {
                            setRecordNameModal({ id: item.id, name: formatRecordName(item) });
                            setRecordNameDraft(formatRecordName(item));
                          }}
                        >
                          修改名称
                        </button>
                        <button
                          type="button"
                          className="button-secondary button-danger"
                          onClick={async () => {
                            if (!window.confirm(`确认删除录制样本 #${item.id} 吗？`)) {
                              return;
                            }
                            try {
                              await api.deleteRecord(item.id);
                              if (selectedRecord?.id === item.id) {
                                setSelectedRecord(null);
                              }
                              if (recordNameModal?.id === item.id) {
                                setRecordNameModal(null);
                                setRecordNameDraft("");
                              }
                              reportStatus(setStatus, `录制样本 ${item.id} 已删除。`);
                              await refresh();
                            } catch (err) {
                              reportError(setError, err);
                            }
                          }}
                        >
                          删除
                        </button>
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={async () => {
                            if (enabledProviderIds.length === 0) {
                              reportStatus(setStatus, "请先创建并启用至少一个供应商。");
                              return;
                            }
                            try {
                              await api.createExecutionTask({
                                name: `样本-${formatRecordName(item)}-执行任务`,
                                source_type: "recorded_request",
                                source_ref_id: item.id,
                                target_provider_ids_json: { ids: enabledProviderIds },
                                target_models_json: {},
                                task_config_json: {},
                              });
                              reportStatus(setStatus, `已基于样本 ${item.id} 创建执行任务。`);
                            } catch (err) {
                              reportError(setError, err);
                            }
                          }}
                        >
                          快速建任务
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="table-empty" colSpan={7}>
                    暂无录制样本。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {selectedRecord ? (
        <RecordDetailModal
          detail={selectedRecord}
          providerNameById={providerNameById}
          onClose={() => {
            setSelectedRecord(null);
            setRecordNameDraft("");
          }}
          onOpenFull={(payload) => setTextPreviewModal(payload)}
        />
      ) : null}
      {recordNameModal ? (
        <RecordNameModal
          recordId={recordNameModal.id}
          value={recordNameDraft}
          onChange={setRecordNameDraft}
          onClose={() => {
            setRecordNameModal(null);
            setRecordNameDraft("");
          }}
          onSubmit={async () => {
            try {
              const updated = await api.updateRecord(recordNameModal.id, { name: recordNameDraft });
              if (selectedRecord?.id === updated.id) {
                setSelectedRecord(updated);
              }
              setRecordNameModal(null);
              setRecordNameDraft("");
              await refresh();
              reportStatus(setStatus, `录制样本 ${updated.id} 名称已更新。`);
            } catch (err) {
              reportError(setError, err);
            }
          }}
        />
      ) : null}
      {textPreviewModal ? (
        <TextPreviewModal
          title={textPreviewModal.title}
          content={textPreviewModal.content}
          onClose={() => setTextPreviewModal(null)}
        />
      ) : null}
    </section>
  );
}

function ExecutionPage({
  initialSourceRefId,
  onUseExecutionTask,
}: {
  initialSourceRefId: string;
  onUseExecutionTask: (taskId: number) => void;
}) {
  const [items, setItems] = useState<ExecutionTask[]>([]);
  const [results, setResults] = useState<ExecutionResultItem[]>([]);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [status, setStatus] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [selectedResultDetail, setSelectedResultDetail] = useState<ExecutionResultDetail | null>(null);
  const [resultTextPreviewModal, setResultTextPreviewModal] = useState<{ title: string; content: string } | null>(null);
  const [executionTaskNameModal, setExecutionTaskNameModal] = useState<{ id: number; name: string } | null>(null);
  const [executionTaskNameDraft, setExecutionTaskNameDraft] = useState("");
  const [comparisonTaskIds, setComparisonTaskIds] = useState<number[]>([]);
  const [taskComparison, setTaskComparison] = useState<ExecutionTaskComparisonData | null>(null);
  const [form, setForm] = useState({
    name: "执行批次-1",
    selected_record_id: initialSourceRefId,
    provider_ids: [] as number[],
    models: "",
    run_count: "1",
  });

  const refresh = async () => {
    const [tasksResult, providersResult, recordsResult] = await Promise.all([
      api.listExecutionTasks(),
      api.listProviders(),
      api.listRecords(),
    ]);
    setItems(tasksResult.items);
    setProviders(providersResult.items);
    setRecords(recordsResult.items);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!items.some((item) => item.status === "running")) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
      if (selectedTaskId !== null) {
        api
          .listExecutionResults(selectedTaskId)
          .then((result) => setResults(result.items))
          .catch(() => undefined);
      }
    }, 3000);

    return () => window.clearInterval(timer);
  }, [items, selectedTaskId]);

  useEffect(() => {
    setForm((current) => ({
      ...current,
      selected_record_id: initialSourceRefId || current.selected_record_id,
    }));
  }, [initialSourceRefId]);

  useEffect(() => {
    const enabledProviderIds = providers.filter((item) => item.enabled).map((item) => item.id);
    if (enabledProviderIds.length > 0 && form.provider_ids.length === 0) {
      setForm((current) => ({ ...current, provider_ids: enabledProviderIds }));
    }
  }, [providers, form.provider_ids.length]);

  useEffect(() => {
    setComparisonTaskIds((current) => current.filter((taskId) => items.some((item) => item.id === taskId)).slice(0, 2));
  }, [items]);

  const recordOptions = useMemo(
    () =>
      records.map((record) => ({
        value: String(record.id),
        label: `${formatRecordName(record)} · #${record.id} · ${formatRequestType(record.request_type)} · ${record.model ?? "无模型"}`,
      })),
    [records],
  );
  const recordById = useMemo(() => new Map(records.map((record) => [record.id, record])), [records]);
  const providerById = useMemo(() => new Map(providers.map((provider) => [provider.id, provider])), [providers]);
  const providerNameById = useMemo(() => new Map(providers.map((provider) => [provider.id, provider.name])), [providers]);
  const executionResultBestValues = useMemo(() => buildExecutionResultBestValues(results), [results]);
  const selectedTask = useMemo(
    () => items.find((item) => item.id === selectedTaskId) ?? null,
    [items, selectedTaskId],
  );
  const comparisonTasks = useMemo(
    () =>
      comparisonTaskIds
        .map((taskId) => items.find((item) => item.id === taskId) ?? null)
        .filter((item): item is ExecutionTask => item !== null),
    [comparisonTaskIds, items],
  );
  const comparisonSampleName =
    comparisonTasks.length > 0 ? formatRecordName(recordById.get(comparisonTasks[0].source_ref_id) ?? { id: comparisonTasks[0].source_ref_id }) : "-";

  const updateTaskRow = (taskId: number, updater: (task: ExecutionTask) => ExecutionTask) => {
    setItems((current) => current.map((task) => (task.id === taskId ? updater(task) : task)));
  };

  const toggleComparisonTask = (task: ExecutionTask) => {
    if (comparisonTaskIds.includes(task.id)) {
      setComparisonTaskIds((current) => current.filter((taskId) => taskId !== task.id));
      setTaskComparison(null);
      return;
    }

    if (comparisonTaskIds.length >= 2) {
      reportStatus(setStatus, "一次最多选择两个执行任务进行对比。");
      return;
    }

    if (comparisonTasks.length === 1 && comparisonTasks[0].source_ref_id !== task.source_ref_id) {
      reportStatus(setStatus, "只能比较同一个录制样本下的两个执行任务。");
      return;
    }

    setComparisonTaskIds((current) => [...current, task.id]);
    setTaskComparison(null);
  };

  const clearTaskComparisonSelection = () => {
    setComparisonTaskIds([]);
    setTaskComparison(null);
  };

  const loadTaskComparison = async () => {
    if (comparisonTasks.length !== 2) {
      reportStatus(setStatus, "请先选择两个同样本的执行任务。");
      return;
    }

    const [leftTask, rightTask] = comparisonTasks;
    if (leftTask.source_ref_id !== rightTask.source_ref_id) {
      reportStatus(setStatus, "只能比较同一个录制样本下的两个执行任务。");
      return;
    }

    try {
      const [leftResult, rightResult] = await Promise.all([
        api.listExecutionResults(leftTask.id),
        api.listExecutionResults(rightTask.id),
      ]);
      setTaskComparison({
        leftTask,
        rightTask,
        leftResults: leftResult.items,
        rightResults: rightResult.items,
      });
      setStatus(`已加载执行任务 ${leftTask.id} 与 ${rightTask.id} 的对比结果。`);
    } catch (err) {
      reportError(undefined, err);
    }
  };

  return (
    <section className="stack">
      <SectionHeading
        title="执行任务"
        description="为某批录制样本选择多个供应商重跑，执行结果单独保存，后续评估可独立发起。"
      />
      {status ? <p className="status">{status}</p> : null}
      <form
        className="card form-grid form-panel"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api.createExecutionTask({
              name: form.name,
              source_type: "recorded_request",
              source_ref_id: Number(form.selected_record_id),
              target_provider_ids_json: { ids: form.provider_ids },
              target_models_json: form.models.trim()
                ? { models: form.models.split(",").map((item) => item.trim()).filter(Boolean) }
                : {},
              task_config_json: { run_count: Math.max(1, Number(form.run_count) || 1) },
            });
            reportStatus(setStatus, "执行任务已创建。");
            await refresh();
          } catch (err) {
            reportError(undefined, err);
          }
        }}
      >
        <div className="form-header">
          <strong>新建执行任务</strong>
          <span>从录制数据选择输入样本，再勾选目标供应商。</span>
        </div>
        <label>
          <span>任务名称</span>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          <span>录制样本</span>
          <select
            value={form.selected_record_id}
            onChange={(e) => setForm({ ...form, selected_record_id: e.target.value })}
          >
            <option value="">请选择录制请求</option>
            {recordOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="wide">
          <span>目标供应商</span>
          <div className="check-grid">
            {providers
              .filter((provider) => provider.enabled)
              .map((provider) => (
                <label key={provider.id} className="check-pill">
                  <input
                    type="checkbox"
                    checked={form.provider_ids.includes(provider.id)}
                    onChange={(e) => {
                      setForm((current) => ({
                        ...current,
                        provider_ids: e.target.checked
                          ? [...current.provider_ids, provider.id]
                          : current.provider_ids.filter((item) => item !== provider.id),
                      }));
                    }}
                  />
                  <span>
                    {provider.name}
                    <small>{provider.default_model}</small>
                  </span>
                </label>
              ))}
          </div>
        </label>
        <label>
          <span>覆盖模型</span>
          <input
            value={form.models}
            placeholder="可选：用逗号分隔，覆盖默认模型"
            onChange={(e) => setForm({ ...form, models: e.target.value })}
          />
        </label>
        <label>
          <span>执行次数</span>
          <input
            type="number"
            min="1"
            value={form.run_count}
            onChange={(e) => setForm({ ...form, run_count: e.target.value })}
          />
        </label>
        <div className="actions">
          <button type="submit" disabled={!form.selected_record_id || form.provider_ids.length === 0}>
            创建
          </button>
        </div>
      </form>
      <div className="card compare-toolbar">
        <div className="card-header">
          <div>
            <strong>任务对比</strong>
            <div className="muted">选择同一个录制样本下的两个执行任务，做基础指标与结果明细对比。</div>
          </div>
        </div>
        <div className="comparison-selection-list">
          <span className="pill pill-selection">{comparisonTasks[0] ? `任务 A：${comparisonTasks[0].name}` : "任务 A：未选择"}</span>
          <span className="pill pill-selection">{comparisonTasks[1] ? `任务 B：${comparisonTasks[1].name}` : "任务 B：未选择"}</span>
          <span className="muted">{comparisonTasks.length ? `样本：${comparisonSampleName}` : "请选择两个同样本任务。"}</span>
        </div>
        <div className="actions">
          <button type="button" disabled={comparisonTasks.length !== 2} onClick={() => loadTaskComparison()}>
            开始对比
          </button>
          <button
            type="button"
            className="button-secondary"
            disabled={comparisonTasks.length === 0 && taskComparison === null}
            onClick={clearTaskComparisonSelection}
          >
            清空选择
          </button>
        </div>
      </div>
      <div className="card table-card">
        <div className="table-wrap">
          <table className="data-table" aria-label="执行任务列表">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>状态</th>
                <th>样本名称</th>
                <th>样本 ID</th>
                <th>执行模型</th>
                <th>执行次数</th>
                <th>对比</th>
                <th>进度</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((item) => {
                  const sourceRecord = recordById.get(item.source_ref_id);
                  const isRunning = item.status === "running";

                  return (
                    <tr key={item.id} className={selectedTaskId === item.id ? "table-row-active" : undefined}>
                      <td>
                        <div className="cell-primary">{item.name}</div>
                        <div className="muted">#{item.id}</div>
                      </td>
                      <td>
                        <span className="pill">{formatTaskStatus(item.status)}</span>
                      </td>
                      <td>{sourceRecord ? formatRecordName(sourceRecord) : "-"}</td>
                      <td>#{item.source_ref_id}</td>
                      <td>{formatExecutionTaskModels(item, providerById)}</td>
                      <td>{item.run_count ?? 1}</td>
                      <td>
                        <input
                          className="compare-checkbox"
                          type="checkbox"
                          aria-label={`选择对比任务 ${item.name}`}
                          checked={comparisonTaskIds.includes(item.id)}
                          onChange={() => toggleComparisonTask(item)}
                        />
                      </td>
                      <td>
                        {item.progress_done}/{item.progress_total}
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            type="button"
                            disabled={isRunning}
                            onClick={async () => {
                              const previousStatus = item.status;
                              updateTaskRow(item.id, (currentTask) => ({ ...currentTask, status: "running" }));
                              try {
                                const startedTask = await api.startExecutionTask(item.id);
                                updateTaskRow(item.id, () => startedTask);
                                reportStatus(setStatus, `执行任务 ${item.id} 已开始。`);
                                await refresh();
                              } catch (err) {
                                updateTaskRow(item.id, (currentTask) => ({ ...currentTask, status: previousStatus }));
                                reportError(undefined, err);
                              }
                            }}
                          >
                            开始执行
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={!isRunning}
                            onClick={async () => {
                              try {
                                await api.stopExecutionTask(item.id);
                                reportStatus(setStatus, `执行任务 ${item.id} 已停止。`);
                                await refresh();
                              } catch (err) {
                                reportError(undefined, err);
                              }
                            }}
                          >
                            停止
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={isRunning}
                            onClick={async () => {
                              try {
                                await api.retryExecutionTask(item.id);
                                reportStatus(setStatus, `执行任务 ${item.id} 已重跑。`);
                                await refresh();
                              } catch (err) {
                                reportError(undefined, err);
                              }
                            }}
                          >
                            重跑
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={() => {
                              setExecutionTaskNameModal({ id: item.id, name: item.name });
                              setExecutionTaskNameDraft(item.name);
                            }}
                          >
                            修改名称
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={async () => {
                              try {
                                const result = await api.listExecutionResults(item.id);
                                setSelectedTaskId(item.id);
                                setResults(result.items);
                                setStatus(`已加载执行任务 ${item.id} 的结果。`);
                              } catch (err) {
                                reportError(undefined, err);
                              }
                            }}
                          >
                            查看结果
                          </button>
                          <button type="button" onClick={() => onUseExecutionTask(item.id)}>
                            用于评估
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td className="table-empty" colSpan={9}>
                    暂无执行任务。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {taskComparison ? (
        <ExecutionTaskComparisonPanel
          comparison={taskComparison}
          sampleName={comparisonSampleName}
          providerNameById={providerNameById}
          onClose={() => setTaskComparison(null)}
        />
      ) : null}
      {selectedTask ? (
        <ExecutionResultsModal
          task={selectedTask}
          results={results}
          providerNameById={providerNameById}
          executionResultBestValues={executionResultBestValues}
          onClose={() => setSelectedTaskId(null)}
          onViewDetail={async (resultId) => {
            try {
              const detail = await api.getExecutionResult(selectedTask.id, resultId);
              setSelectedResultDetail(detail);
            } catch (err) {
              reportError(undefined, err);
            }
          }}
        />
      ) : null}
      {executionTaskNameModal ? (
        <ExecutionTaskNameModal
          taskId={executionTaskNameModal.id}
          value={executionTaskNameDraft}
          onChange={setExecutionTaskNameDraft}
          onClose={() => {
            setExecutionTaskNameModal(null);
            setExecutionTaskNameDraft("");
          }}
          onSubmit={async () => {
            const updatedTask = await api.updateExecutionTask(executionTaskNameModal.id, { name: executionTaskNameDraft });
            setItems((current) => current.map((item) => (item.id === updatedTask.id ? updatedTask : item)));
            setExecutionTaskNameModal(null);
            setExecutionTaskNameDraft("");
            reportStatus(setStatus, `执行任务 ${updatedTask.id} 名称已更新。`);
          }}
        />
      ) : null}
      {selectedResultDetail ? (
        <ExecutionResultDetailModal
          detail={selectedResultDetail}
          onClose={() => setSelectedResultDetail(null)}
          onOpenFull={(payload) => setResultTextPreviewModal(payload)}
        />
      ) : null}
      {resultTextPreviewModal ? (
        <TextPreviewModal
          title={resultTextPreviewModal.title}
          content={resultTextPreviewModal.content}
          onClose={() => setResultTextPreviewModal(null)}
        />
      ) : null}
    </section>
  );
}

function MetricCompareValue({ value, best }: { value?: number | null; best: boolean }) {
  return (
    <div className="metric-compare-cell">
      <span>{formatMetricValue(value)}</span>
      {best ? <span className="comparison-best-mark">最佳</span> : null}
    </div>
  );
}

function ExecutionResultsModal({
  task,
  results,
  providerNameById,
  executionResultBestValues,
  onClose,
  onViewDetail,
}: {
  task: ExecutionTask;
  results: ExecutionResultItem[];
  providerNameById: Map<number, string>;
  executionResultBestValues: Partial<Record<ComparableExecutionMetricKey, number>>;
  onClose: () => void;
  onViewDetail: (resultId: number) => void | Promise<void>;
}) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel results-modal-panel stack"
        role="dialog"
        aria-modal="true"
        aria-labelledby="execution-results-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <div className="comparison-caption">
            <h3 className="modal-title" id="execution-results-modal-title">
              执行结果 · {task.name}
            </h3>
            <div className="muted">任务 #{task.id}</div>
          </div>
          <button type="button" className="button-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="table-wrap">
          <table className="data-table" aria-label="执行结果列表">
            <thead>
              <tr>
                <th>结果 ID</th>
                <th>供应商</th>
                <th>模型</th>
                <th>执行次数</th>
                <th>是否成功</th>
                <th>状态码</th>
                <th>首 token(ms)</th>
                <th>总耗时(ms)</th>
                <th>输入 token</th>
                <th>输出 token</th>
                <th>总 token</th>
                <th>TPS</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {results.length ? (
                results.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="cell-primary">结果 #{item.id}</div>
                    </td>
                    <td>{providerNameById.get(item.provider_id) ?? `#${item.provider_id}`}</td>
                    <td>{item.model ?? "-"}</td>
                    <td>{`第 ${item.run_index + 1} 次`}</td>
                    <td>{item.success ? "是" : "否"}</td>
                    <td>{item.http_status ?? "-"}</td>
                    <td>
                      <MetricCompareValue
                        value={item.first_token_latency_ms}
                        best={isBestExecutionMetric(item, "first_token_latency_ms", executionResultBestValues, results.length)}
                      />
                    </td>
                    <td>
                      <MetricCompareValue
                        value={item.complete_latency_ms}
                        best={isBestExecutionMetric(item, "complete_latency_ms", executionResultBestValues, results.length)}
                      />
                    </td>
                    <td>
                      <MetricCompareValue
                        value={item.prompt_tokens}
                        best={isBestExecutionMetric(item, "prompt_tokens", executionResultBestValues, results.length)}
                      />
                    </td>
                    <td>
                      <MetricCompareValue
                        value={item.completion_tokens}
                        best={isBestExecutionMetric(item, "completion_tokens", executionResultBestValues, results.length)}
                      />
                    </td>
                    <td>
                      <MetricCompareValue
                        value={item.total_tokens}
                        best={isBestExecutionMetric(item, "total_tokens", executionResultBestValues, results.length)}
                      />
                    </td>
                    <td>
                      <MetricCompareValue
                        value={item.tokens_per_second}
                        best={isBestExecutionMetric(item, "tokens_per_second", executionResultBestValues, results.length)}
                      />
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="button-secondary"
                          onClick={() => {
                            void onViewDetail(item.id);
                          }}
                        >
                          查看详情
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="table-empty" colSpan={13}>
                    该执行任务暂无结果。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SummaryMetricValue({
  value,
  better,
}: {
  value: string;
  better: boolean;
}) {
  return (
    <td className={`comparison-summary-cell${better ? " is-better" : ""}`}>
      <div className="comparison-summary-value">
        <span>{value}</span>
        {better ? <span className="comparison-summary-mark">更优</span> : null}
      </div>
    </td>
  );
}

function ExecutionTaskComparisonPanel({
  comparison,
  sampleName,
  providerNameById,
  onClose,
}: {
  comparison: ExecutionTaskComparisonData;
  sampleName: string;
  providerNameById: Map<number, string>;
  onClose: () => void;
}) {
  const summaryRows = useMemo(
    () => buildExecutionTaskSummaryRows(comparison.leftResults, comparison.rightResults),
    [comparison.leftResults, comparison.rightResults],
  );
  const detailRows = useMemo(
    () =>
      buildExecutionResultComparisonRows(
        comparison.leftTask,
        comparison.rightTask,
        comparison.leftResults,
        comparison.rightResults,
        providerNameById,
      ),
    [comparison.leftTask, comparison.rightTask, comparison.leftResults, comparison.rightResults, providerNameById],
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel comparison-modal-panel stack"
        role="dialog"
        aria-modal="true"
        aria-labelledby="execution-task-comparison-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <div className="comparison-caption">
            <h3 className="modal-title" id="execution-task-comparison-modal-title">
              执行任务对比
            </h3>
            <div className="muted">样本：{sampleName}</div>
            <div className="muted">
              任务 A：{comparison.leftTask.name} · #{comparison.leftTask.id}
            </div>
            <div className="muted">
              任务 B：{comparison.rightTask.name} · #{comparison.rightTask.id}
            </div>
          </div>
          <button type="button" className="button-secondary" onClick={onClose}>
            关闭对比
          </button>
        </div>
        <div className="card table-card">
          <div className="table-wrap">
            <table className="data-table" aria-label="任务概览对比">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>任务 A</th>
                  <th>任务 B</th>
                  <th>更优</th>
                </tr>
              </thead>
              <tbody>
                {summaryRows.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    <SummaryMetricValue value={row.left} better={isSummaryMetricWinner(row.better, "left")} />
                    <SummaryMetricValue value={row.right} better={isSummaryMetricWinner(row.better, "right")} />
                    <td>{row.better}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card table-card">
          <div className="table-card-header">
            <strong>结果明细对比</strong>
            <span className="muted">按统一结果标识展示，用任务名区分两次执行任务的单条结果。</span>
          </div>
          <div className="table-wrap">
            <table className="data-table" aria-label="结果明细对比">
              <thead>
                <tr>
                  <th>结果标识</th>
                  <th>是否成功</th>
                  <th>状态码</th>
                  <th>首 token(ms)</th>
                  <th>总耗时(ms)</th>
                  <th>输入 token</th>
                  <th>输出 token</th>
                  <th>总 token</th>
                  <th>TPS</th>
                </tr>
              </thead>
              <tbody>
                {detailRows.length ? (
                  detailRows.map((row) => (
                    <tr key={row.key}>
                      <td>{row.label}</td>
                      <td>{row.result.success ? "成功" : "失败"}</td>
                      <td>{row.result.http_status ?? "-"}</td>
                      <td>{formatMetricValue(row.result.first_token_latency_ms)}</td>
                      <td>{formatMetricValue(row.result.complete_latency_ms)}</td>
                      <td>{formatMetricValue(row.result.prompt_tokens)}</td>
                      <td>{formatMetricValue(row.result.completion_tokens)}</td>
                      <td>{formatMetricValue(row.result.total_tokens)}</td>
                      <td>{formatMetricValue(row.result.tokens_per_second)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="table-empty" colSpan={9}>
                      这两个执行任务暂无可对比的结果。
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function EvaluationPage({
  initialExecutionTaskId,
  onViewScores,
}: {
  initialExecutionTaskId: string;
  onViewScores: (taskId: number) => void;
}) {
  const [items, setItems] = useState<EvaluationTask[]>([]);
  const [executionTasks, setExecutionTasks] = useState<ExecutionTask[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [status, setStatus] = useState("");
  const [form, setForm] = useState({
    name: "评估批次-1",
    selected_execution_task_id: initialExecutionTaskId,
    evaluator_type: "llm_judge",
    judge_provider_id: "",
    judge_model: "",
  });

  const refresh = async () => {
    const [tasksResult, providersResult, executionResult] = await Promise.all([
      api.listEvaluationTasks(),
      api.listProviders(),
      api.listExecutionTasks(),
    ]);
    setItems(tasksResult.items);
    setProviders(providersResult.items);
    setExecutionTasks(executionResult.items);
  };

  useEffect(() => {
    refresh().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!items.some((item) => item.status === "running")) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 3000);

    return () => window.clearInterval(timer);
  }, [items]);

  useEffect(() => {
    setForm((current) => ({
      ...current,
      selected_execution_task_id: initialExecutionTaskId || current.selected_execution_task_id,
    }));
  }, [initialExecutionTaskId]);

  useEffect(() => {
    const firstEnabledProvider = providers.find((item) => item.enabled);
    if (!firstEnabledProvider) {
      return;
    }
    setForm((current) => ({
      ...current,
      judge_provider_id: current.judge_provider_id || String(firstEnabledProvider.id),
      judge_model: current.judge_model || firstEnabledProvider.default_model,
    }));
  }, [providers]);

  const updateTaskRow = (taskId: number, updater: (task: EvaluationTask) => EvaluationTask) => {
    setItems((current) => current.map((task) => (task.id === taskId ? updater(task) : task)));
  };

  return (
    <section className="stack">
      <SectionHeading
        title="评估任务"
        description="从已有执行结果里挑选一批任务，独立触发语义评估，评分与执行阶段保持解耦。"
      />
      {status ? <p className="status">{status}</p> : null}
      <form
        className="card form-grid form-panel"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api.createEvaluationTask({
              name: form.name,
              source_type: "execution_task",
              source_ref_id: Number(form.selected_execution_task_id),
              evaluator_type: form.evaluator_type,
              judge_provider_id: Number(form.judge_provider_id),
              judge_model: form.judge_model,
              task_config_json: {},
            });
            reportStatus(setStatus, "评估任务已创建。");
            await refresh();
          } catch (err) {
            reportError(undefined, err);
          }
        }}
      >
        <div className="form-header">
          <strong>新建评估任务</strong>
          <span>选择一个执行任务，再指定用于评分的裁判模型。</span>
        </div>
        <label>
          <span>任务名称</span>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          <span>执行任务</span>
          <select
            value={form.selected_execution_task_id}
            onChange={(e) => setForm({ ...form, selected_execution_task_id: e.target.value })}
          >
            <option value="">请选择执行任务</option>
            {executionTasks.map((task) => (
              <option key={task.id} value={String(task.id)}>
                #{task.id} · {task.name} · {formatTaskStatus(task.status)}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>评委供应商</span>
          <select
            value={form.judge_provider_id}
            onChange={(e) => {
              const provider = providers.find((item) => item.id === Number(e.target.value));
              setForm((current) => ({
                ...current,
                judge_provider_id: e.target.value,
                judge_model: provider?.default_model ?? current.judge_model,
              }));
            }}
          >
            <option value="">请选择评委供应商</option>
            {providers
              .filter((provider) => provider.enabled)
              .map((provider) => (
                <option key={provider.id} value={String(provider.id)}>
                  {provider.name} · {provider.default_model}
                </option>
              ))}
          </select>
        </label>
        <label>
          <span>评委模型</span>
          <input value={form.judge_model} onChange={(e) => setForm({ ...form, judge_model: e.target.value })} />
        </label>
        <div className="actions">
          <button
            type="submit"
            disabled={!form.selected_execution_task_id || !form.judge_provider_id || !form.judge_model}
          >
            创建
          </button>
        </div>
      </form>
      <div className="card table-card">
        <div className="table-wrap">
          <table className="data-table" aria-label="评估任务列表">
            <thead>
              <tr>
                <th>任务名称</th>
                <th>状态</th>
                <th>来源执行</th>
                <th>评委模型</th>
                <th>进度</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((item) => {
                  const isRunning = item.status === "running";

                  return (
                    <tr key={item.id}>
                      <td>
                        <div className="cell-primary">{item.name}</div>
                        <div className="muted">#{item.id}</div>
                      </td>
                      <td>
                        <span className="pill">{formatTaskStatus(item.status)}</span>
                      </td>
                      <td>任务 #{item.source_ref_id}</td>
                      <td>{item.judge_model}</td>
                      <td>
                        {item.progress_done}/{item.progress_total}
                      </td>
                      <td>
                        <div className="table-actions">
                          <button
                            type="button"
                            disabled={isRunning}
                            onClick={async () => {
                              const previousStatus = item.status;
                              updateTaskRow(item.id, (currentTask) => ({ ...currentTask, status: "running" }));
                              try {
                                const startedTask = await api.startEvaluationTask(item.id);
                                updateTaskRow(item.id, () => startedTask);
                                reportStatus(setStatus, `评估任务 ${item.id} 已开始。`);
                                await refresh();
                              } catch (err) {
                                updateTaskRow(item.id, (currentTask) => ({ ...currentTask, status: previousStatus }));
                                reportError(undefined, err);
                              }
                            }}
                          >
                            开始评估
                          </button>
                          <button
                            type="button"
                            className="button-secondary"
                            disabled={isRunning}
                            onClick={async () => {
                              const previousStatus = item.status;
                              updateTaskRow(item.id, (currentTask) => ({ ...currentTask, status: "running" }));
                              try {
                                const startedTask = await api.retryEvaluationTask(item.id);
                                updateTaskRow(item.id, () => startedTask);
                                reportStatus(setStatus, `评估任务 ${item.id} 已重跑。`);
                                await refresh();
                              } catch (err) {
                                updateTaskRow(item.id, (currentTask) => ({ ...currentTask, status: previousStatus }));
                                reportError(undefined, err);
                              }
                            }}
                          >
                            重跑
                          </button>
                          <button type="button" className="button-secondary" onClick={() => onViewScores(item.id)}>
                            查看评分
                          </button>
                          <button
                            type="button"
                            disabled={isRunning}
                            className="button-secondary button-danger"
                            onClick={async () => {
                              if (!window.confirm(`确认删除评估任务「${item.name}」吗？`)) {
                                return;
                              }
                              try {
                                await api.deleteEvaluationTask(item.id);
                                reportStatus(setStatus, `评估任务 ${item.name} 已删除。`);
                                await refresh();
                              } catch (err) {
                                reportError(undefined, err);
                              }
                            }}
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td className="table-empty" colSpan={6}>
                    暂无评估任务。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function ResultsPage({ initialEvaluationTaskId }: { initialEvaluationTaskId: string }) {
  const [evaluationTaskId, setEvaluationTaskId] = useState(initialEvaluationTaskId);
  const [tasks, setTasks] = useState<EvaluationTask[]>([]);
  const [scores, setScores] = useState<EvaluationScoreItem[]>([]);
  const [status, setStatus] = useState("尚未加载评分数据。");

  const refreshTasks = async () => {
    const result = await api.listEvaluationTasks();
    setTasks(result.items);
  };

  const loadScores = async (taskId: string) => {
    setEvaluationTaskId(taskId);
    const result = await api.listEvaluationScores(Number(taskId));
    setScores(result.items);
    setStatus(result.items.length ? `已加载 ${result.items.length} 条评分。` : "未找到评分数据。");
  };

  useEffect(() => {
    refreshTasks().catch(() => undefined);
  }, []);

  useEffect(() => {
    setEvaluationTaskId(initialEvaluationTaskId);
    if (initialEvaluationTaskId) {
      loadScores(initialEvaluationTaskId).catch(() => undefined);
    }
  }, [initialEvaluationTaskId]);

  return (
    <section className="stack">
      <SectionHeading
        title="评分结果"
        description="浏览某个评估任务下的分数、结论和维度评分，支撑后续对比分析。"
      />
      <div className="card form-grid form-panel">
        <label>
          <span>评估任务 ID</span>
          <input value={evaluationTaskId} onChange={(e) => setEvaluationTaskId(e.target.value)} />
        </label>
        <div className="actions">
          <button type="button" onClick={() => loadScores(evaluationTaskId)}>
            加载评分
          </button>
        </div>
      </div>
      <div className="grid">
        {tasks.map((task) => (
          <article className="card" key={task.id}>
            <div className="card-header">
              <strong>{task.name}</strong>
              <span className="pill">{formatTaskStatus(task.status)}</span>
            </div>
            <button type="button" onClick={() => loadScores(String(task.id))}>
              打开
            </button>
          </article>
        ))}
      </div>
      <div className="card stack">
        <strong>{status}</strong>
      </div>
      {scores.length ? (
        <div className="grid">
          {scores.map((score) => (
            <article className="card" key={score.id}>
              <div className="card-header">
                <strong>评分 #{score.id}</strong>
                <span className="pill">{formatVerdict(score.verdict)}</span>
              </div>
              <dl className="meta-list">
                <div>
                  <dt>执行结果</dt>
                  <dd>#{score.execution_result_id}</dd>
                </div>
                <div>
                  <dt>总分</dt>
                  <dd>{score.score}</dd>
                </div>
                <div>
                  <dt>评委模型</dt>
                  <dd>{score.judge_model}</dd>
                </div>
                <div>
                  <dt>评语摘要</dt>
                  <dd>{score.reasoning_summary ?? "无"}</dd>
                </div>
              </dl>
              <div className="score-breakdown">
                <strong>维度评分</strong>
                {Object.entries(score.dimension_scores_json ?? {}).length ? (
                  Object.entries(score.dimension_scores_json).map(([dimension, value]) => (
                    <div className="score-row" key={dimension}>
                      <span>{formatDimensionName(dimension)}</span>
                      <span>{String(value)}</span>
                    </div>
                  ))
                ) : (
                  <div className="muted">暂无维度评分。</div>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="card">
          <span className="muted">当前没有可展示的评分项。</span>
        </div>
      )}
    </section>
  );
}

function SectionHeading({ title, description }: { title: string; description: string }) {
  return (
    <header className="section-heading">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </header>
  );
}

function DetailTextBlock({
  title,
  content,
  uniformHeight = false,
  onOpenFull,
}: {
  title: string;
  content: string;
  uniformHeight?: boolean;
  onOpenFull: (payload: { title: string; content: string }) => void;
}) {
  const collapsed = shouldCollapseDetailText(content);
  const preview = collapsed ? buildDetailTextPreview(content) : content;
  const rootClassName = uniformHeight ? "stack detail-grid-item" : "stack";
  const codeBlockClassName = [
    "code-block",
    collapsed ? "code-block-preview" : "",
    uniformHeight ? "detail-grid-code-block" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rootClassName}>
      <div className="detail-block-header">
        <strong>{title}</strong>
        {collapsed ? (
          <button
            type="button"
            className="button-secondary"
            aria-label={`${title} 查看全文`}
            onClick={() => onOpenFull({ title, content })}
          >
            查看全文
          </button>
        ) : null}
      </div>
      <pre className={codeBlockClassName}>{preview}</pre>
      {uniformHeight ? (
        <p className={collapsed ? "preview-hint" : "preview-hint preview-hint-hidden"}>
          内容较长，当前仅展示预览。
        </p>
      ) : collapsed ? (
        <p className="preview-hint">内容较长，当前仅展示预览。</p>
      ) : null}
    </div>
  );
}

function ExecutionResultDetailModal({
  detail,
  onClose,
  onOpenFull,
}: {
  detail: ExecutionResultDetail;
  onClose: () => void;
  onOpenFull: (payload: { title: string; content: string }) => void;
}) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="execution-result-detail-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <h3 className="modal-title" id="execution-result-detail-modal-title">
            执行结果详情 · {detail.id}
          </h3>
          <button type="button" className="button-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
        <dl className="meta-list meta-list-wide">
          <div>
            <dt>供应商 ID</dt>
            <dd>#{detail.provider_id}</dd>
          </div>
          <div>
            <dt>模型</dt>
            <dd>{detail.model ?? "-"}</dd>
          </div>
          <div>
            <dt>第几次</dt>
            <dd>{`第 ${detail.run_index + 1} 次`}</dd>
          </div>
          <div>
            <dt>是否成功</dt>
            <dd>{detail.success ? "是" : "否"}</dd>
          </div>
          <div>
            <dt>状态码</dt>
            <dd>{formatMetricValue(detail.http_status)}</dd>
          </div>
          <div>
            <dt>首 token</dt>
            <dd>{formatMetricValue(detail.first_token_latency_ms)}</dd>
          </div>
          <div>
            <dt>总耗时</dt>
            <dd>{formatMetricValue(detail.complete_latency_ms)}</dd>
          </div>
          <div>
            <dt>输入 token</dt>
            <dd>{formatMetricValue(detail.prompt_tokens)}</dd>
          </div>
          <div>
            <dt>输出 token</dt>
            <dd>{formatMetricValue(detail.completion_tokens)}</dd>
          </div>
          <div>
            <dt>总 token</dt>
            <dd>{formatMetricValue(detail.total_tokens)}</dd>
          </div>
          <div>
            <dt>TPS</dt>
            <dd>{formatMetricValue(detail.tokens_per_second)}</dd>
          </div>
          <div>
            <dt>错误码</dt>
            <dd>{detail.error_code ?? "-"}</dd>
          </div>
          <div>
            <dt>错误信息</dt>
            <dd>{detail.error_message ?? "-"}</dd>
          </div>
          <div>
            <dt>创建时间</dt>
            <dd>{formatDateTime(detail.created_at)}</dd>
          </div>
          <div>
            <dt>更新时间</dt>
            <dd>{formatDateTime(detail.updated_at)}</dd>
          </div>
        </dl>
        <div className="detail-grid">
          <DetailTextBlock
            title="请求体"
            content={formatJsonContent(detail.request_body_json)}
            uniformHeight
            onOpenFull={onOpenFull}
          />
          <DetailTextBlock
            title="响应体"
            content={formatJsonContent(detail.response_body_json)}
            uniformHeight
            onOpenFull={onOpenFull}
          />
          <DetailTextBlock
            title="输出文本"
            content={detail.output_text?.trim() ? detail.output_text : "-"}
            uniformHeight
            onOpenFull={onOpenFull}
          />
        </div>
      </div>
    </div>
  );
}

function RecordDetailModal({
  detail,
  providerNameById,
  onClose,
  onOpenFull,
}: {
  detail: RecordDetail;
  providerNameById: Map<number, string>;
  onClose: () => void;
  onOpenFull: (payload: { title: string; content: string }) => void;
}) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel results-modal-panel stack"
        role="dialog"
        aria-modal="true"
        aria-labelledby="record-detail-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <div>
            <h3 className="modal-title" id="record-detail-modal-title">
              样本详情 · {formatRecordName(detail)}
            </h3>
            <div className="muted">样本 #{detail.id}</div>
          </div>
          <button type="button" className="button-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
        <dl className="meta-list meta-list-wide">
          <div>
            <dt>样本名称</dt>
            <dd>{formatRecordName(detail)}</dd>
          </div>
          <div>
            <dt>来源供应商</dt>
            <dd>{providerNameById.get(detail.provider_id) ?? `#${detail.provider_id}`}</dd>
          </div>
          <div>
            <dt>来源应用</dt>
            <dd>{detail.source_app ?? "-"}</dd>
          </div>
          <div>
            <dt>模型</dt>
            <dd>{detail.model ?? "-"}</dd>
          </div>
          <div>
            <dt>请求类型</dt>
            <dd>{formatRequestType(detail.request_type)}</dd>
          </div>
          <div>
            <dt>请求时间</dt>
            <dd>{formatDateTime(detail.created_at)}</dd>
          </div>
          <div>
            <dt>响应状态</dt>
            <dd>{detail.response.http_status ?? "-"}</dd>
          </div>
          <div>
            <dt>首 Token 延迟</dt>
            <dd>{detail.response.first_token_latency_ms ?? "-"}</dd>
          </div>
          <div>
            <dt>总耗时</dt>
            <dd>{detail.response.complete_latency_ms ?? "-"}</dd>
          </div>
          <div>
            <dt>总 Token</dt>
            <dd>{detail.response.total_tokens ?? "-"}</dd>
          </div>
          <div>
            <dt>异常信息</dt>
            <dd>{detail.response.error_message ?? "-"}</dd>
          </div>
        </dl>
        <div className="detail-grid">
          <DetailTextBlock
            title="请求头"
            content={JSON.stringify(detail.request_headers_json, null, 2)}
            uniformHeight
            onOpenFull={onOpenFull}
          />
          <DetailTextBlock
            title="请求体"
            content={JSON.stringify(detail.request_body_json, null, 2)}
            uniformHeight
            onOpenFull={onOpenFull}
          />
          <DetailTextBlock
            title="响应头"
            content={JSON.stringify(detail.response.response_headers_json, null, 2)}
            uniformHeight
            onOpenFull={onOpenFull}
          />
          <DetailTextBlock
            title="响应体"
            content={JSON.stringify(detail.response.response_body_json, null, 2)}
            uniformHeight
            onOpenFull={onOpenFull}
          />
        </div>
        {detail.request_text_snapshot ? (
          <DetailTextBlock title="请求快照" content={detail.request_text_snapshot} onOpenFull={onOpenFull} />
        ) : null}
        {detail.response.response_text_snapshot ? (
          <DetailTextBlock title="响应快照" content={detail.response.response_text_snapshot} onOpenFull={onOpenFull} />
        ) : null}
      </div>
    </div>
  );
}

function TextPreviewModal({
  title,
  content,
  onClose,
}: {
  title: string;
  content: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="text-preview-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <h3 className="modal-title" id="text-preview-modal-title">
            {title} 全文
          </h3>
          <button type="button" className="button-secondary" onClick={onClose}>
            关闭
          </button>
        </div>
        <pre className="code-block modal-code-block">{content}</pre>
      </div>
    </div>
  );
}

function RecordNameModal({
  recordId,
  value,
  onChange,
  onClose,
  onSubmit,
}: {
  recordId: number;
  value: string;
  onChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, saving]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={saving ? undefined : onClose}>
      <div
        className="modal-panel modal-panel-compact"
        role="dialog"
        aria-modal="true"
        aria-labelledby="record-name-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <h3 className="modal-title" id="record-name-modal-title">
            修改样本名称
          </h3>
          <button type="button" className="button-secondary" onClick={onClose} disabled={saving}>
            取消
          </button>
        </div>
        <p className="muted modal-subtitle">样本 #{recordId}</p>
        <form
          className="form-grid modal-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setSaving(true);
            try {
              await onSubmit();
            } finally {
              setSaving(false);
            }
          }}
        >
          <label className="wide">
            <span>样本名称</span>
            <input
              value={value}
              placeholder={`默认使用 ${recordId}`}
              onChange={(event) => onChange(event.target.value)}
              disabled={saving}
              autoFocus
            />
          </label>
          <div className="actions">
            <button type="submit" disabled={saving}>
              {saving ? "保存中..." : "保存"}
            </button>
            <button type="button" className="button-secondary" onClick={onClose} disabled={saving}>
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ExecutionTaskNameModal({
  taskId,
  value,
  onChange,
  onClose,
  onSubmit,
}: {
  taskId: number;
  value: string;
  onChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !saving) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, saving]);

  return (
    <div className="modal-backdrop" role="presentation" onClick={saving ? undefined : onClose}>
      <div
        className="modal-panel modal-panel-compact"
        role="dialog"
        aria-modal="true"
        aria-labelledby="execution-task-name-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="card-header">
          <h3 className="modal-title" id="execution-task-name-modal-title">
            修改执行任务名称
          </h3>
          <button type="button" className="button-secondary" onClick={onClose} disabled={saving}>
            取消
          </button>
        </div>
        <p className="muted modal-subtitle">任务 #{taskId}</p>
        <form
          className="form-grid modal-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setSaving(true);
            try {
              await onSubmit();
            } finally {
              setSaving(false);
            }
          }}
        >
          <label className="wide">
            <span>任务名称</span>
            <input
              value={value}
              placeholder={`默认使用 ${taskId}`}
              onChange={(event) => onChange(event.target.value)}
              disabled={saving}
              autoFocus
            />
          </label>
          <div className="actions">
            <button type="submit" disabled={saving}>
              {saving ? "保存中..." : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
