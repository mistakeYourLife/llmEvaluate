import { useEffect, useState } from "react";
import {
  api,
  type EvaluationTask,
  type ExecutionResultItem,
  type ExecutionTask,
  type Provider,
  type RecordItem,
} from "./api/client";

type Tab = "providers" | "records" | "execution" | "evaluation" | "results";

export default function App() {
  const [tab, setTab] = useState<Tab>("providers");
  return (
    <div className="shell">
      <aside className="sidebar">
        <h1>llmEvaluate</h1>
        <nav>
          {[
            ["providers", "Providers"],
            ["records", "Records"],
            ["execution", "Execution"],
            ["evaluation", "Evaluation"],
            ["results", "Results"],
          ].map(([key, label]) => (
            <button key={key} className={tab === key ? "nav active" : "nav"} onClick={() => setTab(key as Tab)}>
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        {tab === "providers" ? <ProvidersPage /> : null}
        {tab === "records" ? <RecordsPage /> : null}
        {tab === "execution" ? <ExecutionPage /> : null}
        {tab === "evaluation" ? <EvaluationPage /> : null}
        {tab === "results" ? <ResultsPage /> : null}
      </main>
    </div>
  );
}

function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    code: "",
    provider_type: "openai",
    base_url: "",
    api_key: "",
    default_model: "",
  });

  const refresh = async () => {
    try {
      const result = await api.listProviders();
      setProviders(result.items);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <section>
      <h2>Providers</h2>
      {error ? <p className="error">{error}</p> : null}
      <form
        className="card form-grid"
        onSubmit={async (e) => {
          e.preventDefault();
          await api.createProvider(form);
          setForm({ name: "", code: "", provider_type: "openai", base_url: "", api_key: "", default_model: "" });
          await refresh();
        }}
      >
        {Object.entries(form).map(([key, value]) => (
          <label key={key}>
            <span>{key}</span>
            <input value={value} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
          </label>
        ))}
        <button type="submit">Create</button>
      </form>
      <div className="grid">
        {providers.map((provider) => (
          <article className="card" key={provider.id}>
            <strong>{provider.name}</strong>
            <div>{provider.code}</div>
            <div>{provider.default_model}</div>
            <div>{provider.enabled ? "enabled" : "disabled"}</div>
            <div className="row">
              <button onClick={() => api.toggleProvider(provider.id, !provider.enabled).then(refresh)}>Toggle</button>
              <button onClick={() => api.testProvider(provider.id).then(refresh)}>Test</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RecordsPage() {
  const [items, setItems] = useState<RecordItem[]>([]);
  useEffect(() => {
    api.listRecords().then((result) => setItems(result.items)).catch(() => undefined);
  }, []);
  return (
    <section>
      <h2>Records</h2>
      <div className="grid">
        {items.map((item) => (
          <article className="card" key={item.id}>
            <strong>#{item.id}</strong>
            <div>{item.request_type}</div>
            <div>{item.model}</div>
            <div>{item.http_status}</div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ExecutionPage() {
  const [items, setItems] = useState<ExecutionTask[]>([]);
  const [results, setResults] = useState<ExecutionResultItem[]>([]);
  const [form, setForm] = useState({
    name: "batch-1",
    source_type: "recorded_request",
    source_ref_id: "1",
    provider_ids: "1,2",
    models: "gpt-4o-mini",
  });

  const refresh = () => {
    api.listExecutionTasks().then((result) => setItems(result.items)).catch(() => undefined);
  };

  useEffect(() => {
    refresh();
  }, []);
  return (
    <section>
      <h2>Execution Tasks</h2>
      <form
        className="card form-grid"
        onSubmit={async (e) => {
          e.preventDefault();
          await api.createExecutionTask({
            name: form.name,
            source_type: form.source_type,
            source_ref_id: Number(form.source_ref_id),
            target_provider_ids_json: { ids: form.provider_ids.split(",").map((item) => Number(item.trim())) },
            target_models_json: { models: form.models.split(",").map((item) => item.trim()) },
            task_config_json: {},
          });
          refresh();
        }}
      >
        <label>
          <span>name</span>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          <span>source_type</span>
          <input value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })} />
        </label>
        <label>
          <span>source_ref_id</span>
          <input value={form.source_ref_id} onChange={(e) => setForm({ ...form, source_ref_id: e.target.value })} />
        </label>
        <label>
          <span>provider ids</span>
          <input value={form.provider_ids} onChange={(e) => setForm({ ...form, provider_ids: e.target.value })} />
        </label>
        <label>
          <span>models</span>
          <input value={form.models} onChange={(e) => setForm({ ...form, models: e.target.value })} />
        </label>
        <button type="submit">Create</button>
      </form>
      <div className="grid">
        {items.map((item) => (
          <article className="card" key={item.id}>
            <strong>{item.name}</strong>
            <div>{item.status}</div>
            <div>
              {item.progress_done}/{item.progress_total}
            </div>
            <div className="row">
              <button onClick={() => api.startExecutionTask(item.id).then(refresh)}>Start</button>
              <button onClick={() => api.stopExecutionTask(item.id).then(refresh)}>Stop</button>
              <button onClick={() => api.retryExecutionTask(item.id).then(refresh)}>Retry</button>
              <button onClick={() => api.listExecutionResults(item.id).then((result) => setResults(result.items))}>
                View Results
              </button>
            </div>
          </article>
        ))}
      </div>
      {results.length ? (
        <div className="card table">
          {results.map((item) => (
            <div key={item.id}>
              result #{item.id} provider={item.provider_id} model={item.model} success={String(item.success)}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function EvaluationPage() {
  const [items, setItems] = useState<EvaluationTask[]>([]);
  const [form, setForm] = useState({
    name: "judge-1",
    source_type: "execution_task",
    source_ref_id: "1",
    evaluator_type: "llm_judge",
    judge_provider_id: "1",
    judge_model: "gpt-4o-mini",
  });

  const refresh = () => {
    api.listEvaluationTasks().then((result) => setItems(result.items)).catch(() => undefined);
  };

  useEffect(() => {
    refresh();
  }, []);
  return (
    <section>
      <h2>Evaluation Tasks</h2>
      <form
        className="card form-grid"
        onSubmit={async (e) => {
          e.preventDefault();
          await api.createEvaluationTask({
            name: form.name,
            source_type: form.source_type,
            source_ref_id: Number(form.source_ref_id),
            evaluator_type: form.evaluator_type,
            judge_provider_id: Number(form.judge_provider_id),
            judge_model: form.judge_model,
            task_config_json: {},
          });
          refresh();
        }}
      >
        {Object.entries(form).map(([key, value]) => (
          <label key={key}>
            <span>{key}</span>
            <input value={value} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
          </label>
        ))}
        <button type="submit">Create</button>
      </form>
      <div className="grid">
        {items.map((item) => (
          <article className="card" key={item.id}>
            <strong>{item.name}</strong>
            <div>{item.evaluator_type}</div>
            <div>{item.status}</div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ResultsPage() {
  const [evaluationTaskId, setEvaluationTaskId] = useState("1");
  const [payload, setPayload] = useState("No score data loaded.");

  return (
    <section>
      <h2>Results</h2>
      <div className="card form-grid">
        <label>
          <span>evaluation_task_id</span>
          <input value={evaluationTaskId} onChange={(e) => setEvaluationTaskId(e.target.value)} />
        </label>
        <button
          onClick={async () => {
            const result = await api.listEvaluationScores(Number(evaluationTaskId));
            setPayload(JSON.stringify(result.items, null, 2));
          }}
        >
          Load Scores
        </button>
      </div>
      <pre className="card pre">{payload}</pre>
    </section>
  );
}
