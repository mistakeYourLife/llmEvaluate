import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

type JsonValue = Record<string, unknown> | Array<unknown>;

function createJsonResponse(payload: JsonValue, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 204 ? "No Content" : "OK",
    json: async () => payload,
  } as Response);
}

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
    window.location.hash = "";
  });

  it("allows editing a provider and saving updated config", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 7,
              name: "MockProvider",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              timeout_ms: 30000,
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/providers/7" && init?.method === "PUT") {
        return createJsonResponse({
          id: 7,
          name: "Updated Provider",
          code: "mock-provider",
          provider_type: "openai",
          base_url: "http://127.0.0.1:8020/v1",
          default_model: "mock-model-2",
          timeout_ms: 60000,
          enabled: true,
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("MockProvider");
    await user.click(screen.getByRole("button", { name: "编辑" }));

    const formPanel = screen.getByText("编辑供应商 #7").closest("form");
    expect(formPanel).not.toBeNull();
    const formScope = within(formPanel as HTMLElement);

    const nameInput = formScope.getByLabelText("名称");
    const baseUrlInput = formScope.getByLabelText("API 地址");
    const modelInput = formScope.getByLabelText("默认模型");
    const timeoutInput = formScope.getByLabelText("超时时间（毫秒）");

    await user.clear(nameInput);
    await user.type(nameInput, "Updated Provider");
    await user.clear(baseUrlInput);
    await user.type(baseUrlInput, "http://127.0.0.1:8020/v1");
    await user.clear(modelInput);
    await user.type(modelInput, "mock-model-2");
    await user.clear(timeoutInput);
    await user.type(timeoutInput, "60000");
    await user.click(formScope.getByRole("button", { name: "保存变更" }));

    await waitFor(() => {
      const updateCall = fetchMock.mock.calls.find(
        ([path, init]) => String(path) === "/admin/providers/7" && (init as RequestInit | undefined)?.method === "PUT",
      );
      expect(updateCall).toBeDefined();
      expect(updateCall?.[1]).toEqual(
        expect.objectContaining({
          method: "PUT",
        }),
      );
      expect(JSON.parse(String((updateCall?.[1] as RequestInit).body))).toEqual({
        name: "Updated Provider",
        base_url: "http://127.0.0.1:8020/v1",
        default_model: "mock-model-2",
        api_key: "",
        timeout_ms: 60000,
      });
    });
    expect(alertMock).toHaveBeenCalledWith("供应商 Updated Provider 已更新。");
  });

  it("shows provider test feedback near the clicked provider card", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 7,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/providers/7/test" && init?.method === "POST") {
        return createJsonResponse({ ok: true, detail: "model_available:mock-model" });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    const providersTable = await screen.findByRole("table", { name: "供应商列表" });
    const providerRow = within(providersTable).getByText("模拟供应商").closest("tr");
    expect(providerRow).not.toBeNull();
    const providerScope = within(providerRow as HTMLElement);

    await user.click(providerScope.getByRole("button", { name: "测试模型" }));

    await waitFor(() => {
      expect(providerScope.getByText("连接结果：模型可用（mock-model）")).toBeInTheDocument();
    });
  });

  it("restores the current tab from the URL hash after a page refresh", async () => {
    window.location.hash = "#records";

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({ items: [] });
      }
      if (path === "/admin/records") {
        return createJsonResponse({ items: [] });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => undefined);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "录制样本" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/admin/records", expect.anything());
  });

  it("shows a handbook page with sample recording instructions", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({ items: [] });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "手册" }));

    expect(await screen.findByRole("heading", { name: "使用手册" })).toBeInTheDocument();
    expect(screen.getByText("如何录制样本")).toBeInTheDocument();
    expect(screen.getByText(/POST \/v1\/chat\/completions/)).toBeInTheDocument();
    expect(screen.getByText("curl 示例")).toBeInTheDocument();
    expect(screen.getByText(/curl http:\/\/127\.0\.0\.1:8000\/v1\/chat\/completions/)).toBeInTheDocument();
    expect(screen.getByText("录制成功后去哪里看")).toBeInTheDocument();
  });

  it("allows deleting a provider from the provider list", async () => {
    let providerDeleted = false;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: providerDeleted
            ? []
            : [
                {
                  id: 7,
                  name: "模拟供应商",
                  code: "mock-provider",
                  provider_type: "openai",
                  base_url: "http://127.0.0.1:8010/v1",
                  default_model: "mock-model",
                  enabled: true,
                },
              ],
        });
      }
      if (path === "/admin/providers/7" && init?.method === "DELETE") {
        providerDeleted = true;
        return createJsonResponse({}, 204);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    const providersTable = await screen.findByRole("table", { name: "供应商列表" });
    const providerRow = within(providersTable).getByText("模拟供应商").closest("tr");
    expect(providerRow).not.toBeNull();
    const providerScope = within(providerRow as HTMLElement);

    await user.click(providerScope.getByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/admin/providers/7", expect.objectContaining({ method: "DELETE" }));
    });
    await waitFor(() => {
      expect(screen.queryByText("模拟供应商")).not.toBeInTheDocument();
    });
    expect(alertMock).toHaveBeenCalledWith("供应商 模拟供应商 已删除。");
  });

  it("renders providers in a list table for easier browsing", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 7,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              timeout_ms: 30000,
              enabled: true,
            },
          ],
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const providersTable = await screen.findByRole("table", { name: "供应商列表" });
    expect(within(providersTable).getByRole("columnheader", { name: "名称" })).toBeInTheDocument();
    expect(within(providersTable).getByRole("columnheader", { name: "服务地址" })).toBeInTheDocument();
    expect(within(providersTable).getByText("模拟供应商")).toBeInTheDocument();
  });

  it("shows backend delete reason in a popup when provider deletion is blocked", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 7,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/providers/7" && init?.method === "DELETE") {
        return createJsonResponse({ detail: "该供应商已关联 4 条录制样本，暂不允许删除。" }, 409);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    const providersTable = await screen.findByRole("table", { name: "供应商列表" });
    const providerRow = within(providersTable).getByText("模拟供应商").closest("tr");
    expect(providerRow).not.toBeNull();
    const providerScope = within(providerRow as HTMLElement);

    await user.click(providerScope.getByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith("该供应商已关联 4 条录制样本，暂不允许删除。");
    });
  });

  it("shows default provider status and allows switching the default provider", async () => {
    let providers = [
      {
        id: 7,
        name: "模拟供应商A",
        code: "mock-a",
        provider_type: "openai",
        base_url: "http://127.0.0.1:8010/v1",
        default_model: "mock-model-a",
        timeout_ms: 30000,
        enabled: true,
        is_default: true,
      },
      {
        id: 8,
        name: "模拟供应商B",
        code: "mock-b",
        provider_type: "openai",
        base_url: "http://127.0.0.1:8020/v1",
        default_model: "mock-model-b",
        timeout_ms: 30000,
        enabled: true,
        is_default: false,
      },
    ];

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({ items: providers });
      }
      if (path === "/admin/providers/8/set-default" && init?.method === "POST") {
        providers = providers.map((provider) => ({
          ...provider,
          is_default: provider.id === 8,
        }));
        return createJsonResponse(providers.find((provider) => provider.id === 8) as Record<string, unknown>);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    const providersTable = await screen.findByRole("table", { name: "供应商列表" });
    expect(within(providersTable).getAllByText("默认录制").length).toBeGreaterThan(0);

    const providerRowA = within(providersTable).getByText("模拟供应商A").closest("tr");
    const providerRowB = within(providersTable).getByText("模拟供应商B").closest("tr");
    expect(providerRowA).not.toBeNull();
    expect(providerRowB).not.toBeNull();

    expect(within(providerRowA as HTMLElement).queryByRole("button", { name: "设为默认" })).not.toBeInTheDocument();

    await user.click(within(providerRowB as HTMLElement).getByRole("button", { name: "设为默认" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/admin/providers/8/set-default", expect.objectContaining({ method: "POST" }));
    });
    await waitFor(() => {
      expect(within(providerRowB as HTMLElement).getByText("默认录制")).toBeInTheDocument();
    });
    expect(alertMock).toHaveBeenCalledWith("供应商 模拟供应商B 已设为默认录制供应商。");
  });

  it("shows record detail content after opening a sample", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
            {
              id: 2,
              name: "第二供应商",
              code: "mock-provider-2",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8020/v1",
              default_model: "mock-model-2",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 3,
              name: "客服样本-3",
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/records/3") {
        return createJsonResponse({
          id: 3,
          provider_id: 1,
          request_type: "chat_completions",
          model: "mock-model",
          is_stream: false,
          http_status: 200,
          response_id: 2,
          source_app: "unit-test",
          request_headers_json: { "x-source": "unit" },
          request_body_json: { messages: [{ role: "user", content: "你好" }] },
          request_text_snapshot: "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}",
          created_at: "2026-05-25T08:00:00",
          updated_at: "2026-05-25T08:00:00",
          response: {
            id: 2,
            http_status: 200,
            response_headers_json: { "content-type": "application/json" },
            response_body_json: { choices: [{ message: { content: "世界" } }] },
            response_text_snapshot: "{\"choices\":[{\"message\":{\"content\":\"世界\"}}]}",
            first_token_latency_ms: 120,
            complete_latency_ms: 280,
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
            tokens_per_second: 17,
            error_code: null,
            error_message: null,
            created_at: "2026-05-25T08:00:01",
            updated_at: "2026-05-25T08:00:01",
          },
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "录制样本" })[0]);
    const recordsTable = await screen.findByRole("table", { name: "录制样本列表" });
    const recordRow = within(recordsTable).getByText("样本 #3").closest("tr");
    expect(recordRow).not.toBeNull();
    await user.click(within(recordRow as HTMLElement).getByRole("button", { name: "查看详情" }));

    const dialog = await screen.findByRole("dialog", { name: "样本详情 · 3" });
    await waitFor(() => {
      expect(within(dialog).getByText(/unit-test/)).toBeInTheDocument();
      expect(within(dialog).getAllByText(/你好/).length).toBeGreaterThan(0);
      expect(within(dialog).getAllByText(/世界/).length).toBeGreaterThan(0);
    });

    expect(document.querySelectorAll(".detail-grid-item")).toHaveLength(4);
    expect(document.querySelectorAll(".detail-grid-code-block")).toHaveLength(4);
  });

  it("opens long record text in a modal dialog for full viewing", async () => {
    const longText = "LONG_PAYLOAD_内容_".repeat(160);
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
            {
              id: 2,
              name: "第二供应商",
              code: "mock-provider-2",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8020/v1",
              default_model: "mock-model-2",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 13,
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 9,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/records/13") {
        return createJsonResponse({
          id: 13,
          provider_id: 1,
          request_type: "chat_completions",
          model: "mock-model",
          is_stream: false,
          http_status: 200,
          response_id: 9,
          source_app: "unit-test",
          request_headers_json: { "x-source": "unit" },
          request_body_json: { messages: [{ role: "user", content: longText }] },
          request_text_snapshot: longText,
          created_at: "2026-05-25T08:00:00",
          updated_at: "2026-05-25T08:00:00",
          response: {
            id: 9,
            http_status: 200,
            response_headers_json: { "content-type": "application/json" },
            response_body_json: { choices: [{ message: { content: longText } }] },
            response_text_snapshot: longText,
            first_token_latency_ms: 120,
            complete_latency_ms: 280,
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
            tokens_per_second: 17,
            error_code: null,
            error_message: null,
            created_at: "2026-05-25T08:00:01",
            updated_at: "2026-05-25T08:00:01",
          },
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "录制样本" })[0]);
    const recordsTable = await screen.findByRole("table", { name: "录制样本列表" });
    const recordRow = within(recordsTable).getByText("样本 #13").closest("tr");
    expect(recordRow).not.toBeNull();

    await user.click(within(recordRow as HTMLElement).getByRole("button", { name: "查看详情" }));
    await screen.findByRole("dialog", { name: "样本详情 · 13" });
    await user.click(await screen.findByRole("button", { name: "请求快照 查看全文" }));

    const dialog = await screen.findByRole("dialog", { name: "请求快照 全文" });
    expect(within(dialog).getByText(longText)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "关闭" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "请求快照 全文" })).not.toBeInTheDocument();
    });
  });

  it("allows deleting an unused record from the records page", async () => {
    let recordDeleted = false;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: recordDeleted
            ? []
            : [
                {
                  id: 5,
                  provider_id: 1,
                  request_type: "chat_completions",
                  model: "mock-model",
                  is_stream: false,
                  http_status: 200,
                  response_id: 2,
                  created_at: "2026-05-25T08:00:00",
                  updated_at: "2026-05-25T08:00:00",
                },
              ],
        });
      }
      if (path === "/admin/records/5" && init?.method === "DELETE") {
        recordDeleted = true;
        return createJsonResponse({}, 204);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "录制样本" })[0]);
    const recordsTable = await screen.findByRole("table", { name: "录制样本列表" });
    const recordRow = within(recordsTable).getByText("样本 #5").closest("tr");
    expect(recordRow).not.toBeNull();
    const recordScope = within(recordRow as HTMLElement);

    await user.click(recordScope.getByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/admin/records/5", expect.objectContaining({ method: "DELETE" }));
    });
    await waitFor(() => {
      expect(screen.queryByText("样本 #5")).not.toBeInTheDocument();
    });
    expect(alertMock).toHaveBeenCalledWith("录制样本 5 已删除。");
  });

  it("renders recorded samples in a list table for easier browsing", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 8,
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "录制样本" })[0]);

    const recordsTable = await screen.findByRole("table", { name: "录制样本列表" });
    expect(within(recordsTable).getByRole("columnheader", { name: "名称" })).toBeInTheDocument();
    expect(within(recordsTable).getByRole("columnheader", { name: "来源供应商" })).toBeInTheDocument();
    expect(within(recordsTable).getByText("样本 #8")).toBeInTheDocument();
  });

  it("allows renaming a recorded sample from a modal opened by the list action", async () => {
    let currentName = "3";
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 3,
              name: currentName,
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/records/3" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          id: 3,
          name: currentName,
          provider_id: 1,
          request_type: "chat_completions",
          model: "mock-model",
          is_stream: false,
          http_status: 200,
          response_id: 2,
          source_app: "unit-test",
          request_headers_json: { "x-source": "unit" },
          request_body_json: { messages: [{ role: "user", content: "你好" }] },
          request_text_snapshot: "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}",
          created_at: "2026-05-25T08:00:00",
          updated_at: "2026-05-25T08:00:00",
          response: {
            id: 2,
            http_status: 200,
            response_headers_json: { "content-type": "application/json" },
            response_body_json: { choices: [{ message: { content: "世界" } }] },
            response_text_snapshot: "{\"choices\":[{\"message\":{\"content\":\"世界\"}}]}",
            first_token_latency_ms: 120,
            complete_latency_ms: 280,
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
            tokens_per_second: 17,
            error_code: null,
            error_message: null,
            created_at: "2026-05-25T08:00:01",
            updated_at: "2026-05-25T08:00:01",
          },
        });
      }
      if (path === "/admin/records/3" && init?.method === "PUT") {
        currentName = "客服问答样本";
        return createJsonResponse({
          id: 3,
          name: currentName,
          provider_id: 1,
          request_type: "chat_completions",
          model: "mock-model",
          is_stream: false,
          http_status: 200,
          response_id: 2,
          source_app: "unit-test",
          request_headers_json: { "x-source": "unit" },
          request_body_json: { messages: [{ role: "user", content: "你好" }] },
          request_text_snapshot: "{\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}",
          created_at: "2026-05-25T08:00:00",
          updated_at: "2026-05-25T08:00:00",
          response: {
            id: 2,
            http_status: 200,
            response_headers_json: { "content-type": "application/json" },
            response_body_json: { choices: [{ message: { content: "世界" } }] },
            response_text_snapshot: "{\"choices\":[{\"message\":{\"content\":\"世界\"}}]}",
            first_token_latency_ms: 120,
            complete_latency_ms: 280,
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
            tokens_per_second: 17,
            error_code: null,
            error_message: null,
            created_at: "2026-05-25T08:00:01",
            updated_at: "2026-05-25T08:00:01",
          },
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "录制样本" })[0]);
    const recordsTable = await screen.findByRole("table", { name: "录制样本列表" });
    const recordRow = within(recordsTable).getByText("样本 #3").closest("tr");
    expect(recordRow).not.toBeNull();

    await user.click(within(recordRow as HTMLElement).getByRole("button", { name: "修改名称" }));

    const dialog = await screen.findByRole("dialog", { name: "修改样本名称" });
    const dialogScope = within(dialog);
    const nameInput = dialogScope.getByLabelText("样本名称");
    expect(dialogScope.getByText("样本 #3")).toBeInTheDocument();

    await user.clear(nameInput);
    await user.type(nameInput, "客服问答样本");
    await user.click(dialogScope.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "修改样本名称" })).not.toBeInTheDocument();
    });

    await user.click(within(recordRow as HTMLElement).getByRole("button", { name: "查看详情" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/admin/records/3",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ name: "客服问答样本" }),
        }),
      );
    });
    const recordDetailDialog = await screen.findByRole("dialog", { name: "样本详情 · 客服问答样本" });
    await waitFor(() => {
      expect(within(recordsTable).getByText("客服问答样本")).toBeInTheDocument();
      expect(within(recordDetailDialog).getByText("样本名称")).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("样本名称")).not.toBeInTheDocument();
    expect(alertMock).toHaveBeenCalledWith("录制样本 3 名称已更新。");
  });

  it("shows backend record delete reason in a popup when deletion is blocked", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 4,
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/records/4" && init?.method === "DELETE") {
        return createJsonResponse({ detail: "该录制样本已关联 1 条执行任务，暂不允许删除。" }, 409);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "录制样本" })[0]);
    const recordsTable = await screen.findByRole("table", { name: "录制样本列表" });
    const recordRow = within(recordsTable).getByText("样本 #4").closest("tr");
    expect(recordRow).not.toBeNull();
    const recordScope = within(recordRow as HTMLElement);

    await user.click(recordScope.getByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith("该录制样本已关联 1 条执行任务，暂不允许删除。");
    });
  });

  it("renders execution tasks in a list table and shows results in a modal", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
            {
              id: 2,
              name: "第二供应商",
              code: "mock-provider-2",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8020/v1",
              default_model: "mock-model-2",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 3,
              name: "客服样本-3",
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 21,
              name: "batch-1",
              source_type: "recorded_request",
              source_ref_id: 3,
              target_provider_ids_json: { ids: [1] },
              target_models_json: { models: ["gpt-4.1-mini"] },
              status: "completed",
              progress_total: 1,
              progress_done: 1,
            },
            {
              id: 22,
              name: "batch-default",
              source_type: "recorded_request",
              source_ref_id: 3,
              target_provider_ids_json: { ids: [1, 2] },
              target_models_json: {},
              status: "pending",
              progress_total: 0,
              progress_done: 0,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks/21/results") {
        return createJsonResponse({
          items: [
            {
              id: 31,
              provider_id: 1,
              model: "mock-model",
              run_index: 0,
              success: true,
              http_status: 200,
              first_token_latency_ms: 120,
              complete_latency_ms: 860,
              prompt_tokens: 128,
              completion_tokens: 64,
              total_tokens: 192,
              tokens_per_second: 74,
            },
            {
              id: 32,
              provider_id: 2,
              model: "mock-model-2",
              run_index: 0,
              success: true,
              http_status: 200,
              first_token_latency_ms: 150,
              complete_latency_ms: 920,
              prompt_tokens: 136,
              completion_tokens: 72,
              total_tokens: 208,
              tokens_per_second: 60,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks/21/results/31") {
        return createJsonResponse({
          id: 31,
          execution_task_id: 21,
          provider_id: 1,
          model: "mock-model",
          run_index: 0,
          success: true,
          http_status: 200,
          first_token_latency_ms: 120,
          complete_latency_ms: 860,
          prompt_tokens: 128,
          completion_tokens: 64,
          total_tokens: 192,
          tokens_per_second: 74,
          request_body_json: {
            model: "mock-model",
            messages: [{ role: "user", content: "你好" }],
          },
          response_body_json: {
            id: "resp-31",
            choices: [{ message: { content: "你好，有什么可以帮你？" } }],
          },
          output_text: "你好，有什么可以帮你？",
          error_code: null,
          error_message: null,
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "执行任务" })[0]);

    const executionTable = await screen.findByRole("table", { name: "执行任务列表" });
    expect(within(executionTable).getByRole("columnheader", { name: "任务名称" })).toBeInTheDocument();
    expect(within(executionTable).getByRole("columnheader", { name: "样本名称" })).toBeInTheDocument();
    expect(within(executionTable).getByRole("columnheader", { name: "样本 ID" })).toBeInTheDocument();
    expect(within(executionTable).getByRole("columnheader", { name: "执行模型" })).toBeInTheDocument();
    expect(within(executionTable).getByRole("columnheader", { name: "执行次数" })).toBeInTheDocument();
    expect(within(executionTable).getByText("batch-1")).toBeInTheDocument();

    const taskRow = within(executionTable).getByText("batch-1").closest("tr");
    expect(taskRow).not.toBeNull();
    const taskRowScope = within(taskRow as HTMLElement);
    expect(taskRowScope.getByText("客服样本-3")).toBeInTheDocument();
    expect(taskRowScope.getByText("#3")).toBeInTheDocument();
    expect(taskRowScope.getByText("gpt-4.1-mini")).toBeInTheDocument();
    expect(taskRowScope.getByText("1")).toBeInTheDocument();
    const defaultTaskRow = within(executionTable).getByText("batch-default").closest("tr");
    expect(defaultTaskRow).not.toBeNull();
    expect(within(defaultTaskRow as HTMLElement).getByText("mock-model, mock-model-2")).toBeInTheDocument();
    await user.click(taskRowScope.getByRole("button", { name: "查看结果" }));

    const resultDialog = await screen.findByRole("dialog", { name: "执行结果 · batch-1" });
    const resultTable = within(resultDialog).getByRole("table", { name: "执行结果列表" });
    expect(within(resultDialog).getByText("任务 #21")).toBeInTheDocument();
    expect(within(resultTable).getByText("结果 #31")).toBeInTheDocument();
    expect(within(resultTable).getByText("结果 #32")).toBeInTheDocument();
    expect(within(resultTable).getAllByText("第 1 次").length).toBeGreaterThan(0);
    expect(within(resultTable).getByText("模拟供应商")).toBeInTheDocument();
    expect(within(resultTable).getAllByText("是").length).toBeGreaterThan(0);
    expect(within(resultTable).getByText("120")).toBeInTheDocument();
    expect(within(resultTable).getByText("860")).toBeInTheDocument();
    expect(within(resultTable).getByText("192")).toBeInTheDocument();
    const resultRow = within(resultTable).getByText("结果 #31").closest("tr");
    expect(resultRow).not.toBeNull();
    expect(within(resultRow as HTMLElement).getAllByText("最佳").length).toBeGreaterThan(0);
    await user.click(within(resultRow as HTMLElement).getByRole("button", { name: "查看详情" }));
    expect(await screen.findByText("执行结果详情 · 31")).toBeInTheDocument();
    expect(screen.getByText("请求体")).toBeInTheDocument();
    expect(screen.getByText("响应体")).toBeInTheDocument();
    expect(screen.getByText("输出文本")).toBeInTheDocument();
    expect(screen.getAllByText(/你好，有什么可以帮你/).length).toBeGreaterThan(0);
  });

  it("renames an execution task from a modal", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 3,
              name: "客服样本-3",
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 21,
              name: "batch-1",
              source_type: "recorded_request",
              source_ref_id: 3,
              target_provider_ids_json: { ids: [1] },
              target_models_json: { models: ["gpt-4.1-mini"] },
              status: "completed",
              progress_total: 1,
              progress_done: 1,
              run_count: 1,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks/21" && init?.method === "PUT") {
        return createJsonResponse({
          id: 21,
          name: "客服问答批次",
          source_type: "recorded_request",
          source_ref_id: 3,
          target_provider_ids_json: { ids: [1] },
          target_models_json: { models: ["gpt-4.1-mini"] },
          status: "completed",
          progress_total: 1,
          progress_done: 1,
          run_count: 1,
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "执行任务" })[0]);
    const executionTable = await screen.findByRole("table", { name: "执行任务列表" });
    const taskRow = within(executionTable).getByText("batch-1").closest("tr");
    expect(taskRow).not.toBeNull();

    await user.click(within(taskRow as HTMLElement).getByRole("button", { name: "修改名称" }));

    const dialog = await screen.findByRole("dialog", { name: "修改执行任务名称" });
    const dialogScope = within(dialog);
    const nameInput = dialogScope.getByLabelText("任务名称");
    expect(dialogScope.getByText("任务 #21")).toBeInTheDocument();

    await user.clear(nameInput);
    await user.type(nameInput, "客服问答批次");
    await user.click(dialogScope.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/admin/execution-tasks/21",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ name: "客服问答批次" }),
        }),
      );
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "修改执行任务名称" })).not.toBeInTheDocument();
      expect(within(executionTable).getByText("客服问答批次")).toBeInTheDocument();
    });
    expect(alertMock).toHaveBeenCalledWith("执行任务 21 名称已更新。");
  });

  it("compares two execution tasks from the same recorded sample", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
            {
              id: 2,
              name: "第二供应商",
              code: "mock-provider-2",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8020/v1",
              default_model: "mock-model-2",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 3,
              name: "客服样本-3",
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 21,
              name: "batch-1",
              source_type: "recorded_request",
              source_ref_id: 3,
              target_provider_ids_json: { ids: [1] },
              target_models_json: { models: ["mock-model"] },
              status: "completed",
              progress_total: 1,
              progress_done: 1,
              run_count: 1,
            },
            {
              id: 22,
              name: "batch-2",
              source_type: "recorded_request",
              source_ref_id: 3,
              target_provider_ids_json: { ids: [1] },
              target_models_json: { models: ["mock-model"] },
              status: "completed",
              progress_total: 1,
              progress_done: 1,
              run_count: 1,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks/21/results") {
        return createJsonResponse({
          items: [
            {
              id: 31,
              provider_id: 1,
              model: "mock-model",
              run_index: 0,
              success: true,
              http_status: 200,
              first_token_latency_ms: 120,
              complete_latency_ms: 860,
              prompt_tokens: 128,
              completion_tokens: 64,
              total_tokens: 192,
              tokens_per_second: 74,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks/22/results") {
        return createJsonResponse({
          items: [
            {
              id: 41,
              provider_id: 1,
              model: "mock-model",
              run_index: 0,
              success: true,
              http_status: 200,
              first_token_latency_ms: 180,
              complete_latency_ms: 940,
              prompt_tokens: 132,
              completion_tokens: 70,
              total_tokens: 202,
              tokens_per_second: 58,
            },
          ],
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "执行任务" })[0]);

    await screen.findByRole("table", { name: "执行任务列表" });
    await user.click(screen.getByRole("checkbox", { name: "选择对比任务 batch-1" }));
    await user.click(screen.getByRole("checkbox", { name: "选择对比任务 batch-2" }));
    await user.click(screen.getByRole("button", { name: "开始对比" }));

    const dialog = await screen.findByRole("dialog", { name: "执行任务对比" });
    expect(within(dialog).getAllByText(/batch-1/).length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText(/batch-2/).length).toBeGreaterThan(0);

    const summaryTable = within(dialog).getByRole("table", { name: "任务概览对比" });
    expect(within(summaryTable).getByText("平均首 token(ms)")).toBeInTheDocument();
    expect(within(summaryTable).getByText("120.00")).toBeInTheDocument();
    expect(within(summaryTable).getByText("180.00")).toBeInTheDocument();
    const firstTokenRow = within(summaryTable).getByText("平均首 token(ms)").closest("tr");
    expect(firstTokenRow).not.toBeNull();
    const firstTokenCells = within(firstTokenRow as HTMLElement).getAllByRole("cell");
    expect(firstTokenCells[1]).toHaveClass("comparison-summary-cell", "is-better");
    expect(within(firstTokenCells[1]).getByText("更优")).toBeInTheDocument();
    expect(firstTokenCells[2]).toHaveClass("comparison-summary-cell");
    expect(firstTokenCells[2]).not.toHaveClass("is-better");
    const successRateRow = within(summaryTable).getByText("成功率").closest("tr");
    expect(successRateRow).not.toBeNull();
    const successRateCells = within(successRateRow as HTMLElement).getAllByRole("cell");
    expect(successRateCells[1]).not.toHaveClass("is-better");
    expect(successRateCells[2]).not.toHaveClass("is-better");

    const detailTable = within(dialog).getByRole("table", { name: "结果明细对比" });
    expect(within(detailTable).queryByRole("columnheader", { name: "任务 A 状态" })).not.toBeInTheDocument();
    expect(within(detailTable).queryByRole("columnheader", { name: "任务 B 状态" })).not.toBeInTheDocument();
    expect(within(detailTable).getByText("batch-1 · 模拟供应商 · mock-model · 第 1 次")).toBeInTheDocument();
    expect(within(detailTable).getByText("batch-2 · 模拟供应商 · mock-model · 第 1 次")).toBeInTheDocument();
    expect(within(detailTable).getByText("74")).toBeInTheDocument();
    expect(within(detailTable).getByText("58")).toBeInTheDocument();
  });

  it("optimistically marks an execution task as running and blocks duplicate starts", async () => {
    let listCalls = 0;
    let resolveStartRequest: ((value: Response) => void) | null = null;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "模拟供应商",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 3,
              name: "客服样本-3",
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
              created_at: "2026-05-25T08:00:00",
              updated_at: "2026-05-25T08:00:00",
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks" && (!init?.method || init.method === "GET")) {
        listCalls += 1;
        return createJsonResponse({
          items: [
            {
              id: 41,
              name: "待启动任务",
              source_type: "recorded_request",
              source_ref_id: 3,
              target_provider_ids_json: { ids: [1] },
              target_models_json: {},
              status: listCalls > 1 ? "running" : "pending",
              progress_total: 0,
              progress_done: 0,
              run_count: 1,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks/41/start" && init?.method === "POST") {
        return new Promise<Response>((resolve) => {
          resolveStartRequest = resolve;
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "执行任务" })[0]);

    const executionTable = await screen.findByRole("table", { name: "执行任务列表" });
    const taskRow = within(executionTable).getByText("待启动任务").closest("tr");
    expect(taskRow).not.toBeNull();
    const taskRowScope = within(taskRow as HTMLElement);

    const startButton = taskRowScope.getByRole("button", { name: "开始执行" });
    expect(startButton).toBeEnabled();

    await user.click(startButton);

    await waitFor(() => {
      expect(taskRowScope.getByText("执行中")).toBeInTheDocument();
      expect(startButton).toBeDisabled();
    });

    await user.click(startButton);
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/admin/execution-tasks/41/start")).toHaveLength(1);

    expect(resolveStartRequest).not.toBeNull();
    resolveStartRequest?.({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        id: 41,
        name: "待启动任务",
        source_type: "recorded_request",
        source_ref_id: 3,
        target_provider_ids_json: { ids: [1] },
        target_models_json: {},
        status: "running",
        progress_total: 0,
        progress_done: 0,
        run_count: 1,
      }),
    } as Response);

    await waitFor(() => {
      expect(taskRowScope.getByText("执行中")).toBeInTheDocument();
      expect(startButton).toBeDisabled();
    });
  });

  it("prefers selecting records and execution tasks from loaded options", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "MockProvider",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/records") {
        return createJsonResponse({
          items: [
            {
              id: 3,
              provider_id: 1,
              request_type: "chat_completions",
              model: "mock-model",
              is_stream: false,
              http_status: 200,
              response_id: 2,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks") {
        if (init?.method === "POST") {
          return createJsonResponse({
            id: 11,
            name: "batch-new",
            source_type: "recorded_request",
            source_ref_id: 3,
            status: "pending",
            progress_total: 0,
            progress_done: 0,
          });
        }
        return createJsonResponse({
          items: [
            {
              id: 9,
              name: "batch-existing",
              source_type: "recorded_request",
              source_ref_id: 3,
              status: "completed",
              progress_total: 1,
              progress_done: 1,
            },
          ],
        });
      }
      if (path === "/admin/evaluation-tasks") {
        if (init?.method === "POST") {
          return createJsonResponse({
            id: 12,
            name: "judge-new",
            source_type: "execution_task",
            source_ref_id: 9,
            evaluator_type: "llm_judge",
            judge_provider_id: 1,
            judge_model: "mock-model",
            status: "pending",
            progress_total: 0,
            progress_done: 0,
          });
        }
        return createJsonResponse({ items: [] });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "执行任务" })[0]);
    const recordSelect = await screen.findByLabelText("录制样本");
    const runCountInput = screen.getByLabelText("执行次数");
    await user.selectOptions(recordSelect, "3");
    await user.clear(runCountInput);
    await user.type(runCountInput, "3");
    await user.click(screen.getAllByRole("button", { name: "创建" })[0]);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/admin/execution-tasks",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            name: "执行批次-1",
            source_type: "recorded_request",
            source_ref_id: 3,
            target_provider_ids_json: { ids: [1] },
            target_models_json: {},
            task_config_json: { run_count: 3 },
          }),
        }),
      );
    });

    await user.click(screen.getAllByRole("button", { name: "评估任务" })[0]);
    const executionSelect = await screen.findByLabelText("执行任务");
    await user.selectOptions(executionSelect, "9");
    await user.click(screen.getAllByRole("button", { name: "创建" })[0]);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/admin/evaluation-tasks",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            name: "评估批次-1",
            source_type: "execution_task",
            source_ref_id: 9,
            evaluator_type: "llm_judge",
            judge_provider_id: 1,
            judge_model: "mock-model",
            task_config_json: {},
          }),
        }),
      );
    });
  });

  it("renders evaluation tasks in a list table and allows deleting pending tasks", async () => {
    let taskDeleted = false;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "MockProvider",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks") {
        return createJsonResponse({
          items: [
            {
              id: 9,
              name: "batch-existing",
              source_type: "recorded_request",
              source_ref_id: 3,
              status: "completed",
              progress_total: 1,
              progress_done: 1,
            },
          ],
        });
      }
      if (path === "/admin/evaluation-tasks" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: taskDeleted
            ? []
            : [
                {
                  id: 12,
                  name: "judge-new",
                  source_type: "execution_task",
                  source_ref_id: 9,
                  evaluator_type: "llm_judge",
                  judge_provider_id: 1,
                  judge_model: "mock-model",
                  status: "pending",
                  progress_total: 0,
                  progress_done: 0,
                },
              ],
        });
      }
      if (path === "/admin/evaluation-tasks/12" && init?.method === "DELETE") {
        taskDeleted = true;
        return createJsonResponse({}, 204);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "评估任务" })[0]);

    const evaluationTable = await screen.findByRole("table", { name: "评估任务列表" });
    expect(within(evaluationTable).getByRole("columnheader", { name: "任务名称" })).toBeInTheDocument();
    expect(within(evaluationTable).getByRole("columnheader", { name: "评委模型" })).toBeInTheDocument();

    const taskRow = within(evaluationTable).getByText("judge-new").closest("tr");
    expect(taskRow).not.toBeNull();
    await user.click(within(taskRow as HTMLElement).getByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/admin/evaluation-tasks/12", expect.objectContaining({ method: "DELETE" }));
    });
    await waitFor(() => {
      expect(screen.queryByText("judge-new")).not.toBeInTheDocument();
    });
    expect(alertMock).toHaveBeenCalledWith("评估任务 judge-new 已删除。");
  });

  it("shows backend delete reason when evaluated task deletion is blocked", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "MockProvider",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks") {
        return createJsonResponse({
          items: [
            {
              id: 9,
              name: "batch-existing",
              source_type: "recorded_request",
              source_ref_id: 3,
              status: "completed",
              progress_total: 1,
              progress_done: 1,
            },
          ],
        });
      }
      if (path === "/admin/evaluation-tasks" && (!init?.method || init.method === "GET")) {
        return createJsonResponse({
          items: [
            {
              id: 13,
              name: "judge-completed",
              source_type: "execution_task",
              source_ref_id: 9,
              evaluator_type: "llm_judge",
              judge_provider_id: 1,
              judge_model: "mock-model",
              status: "completed",
              progress_total: 1,
              progress_done: 1,
            },
          ],
        });
      }
      if (path === "/admin/evaluation-tasks/13" && init?.method === "DELETE") {
        return createJsonResponse({ detail: "该评估任务已运行或已生成评分结果，暂不允许删除。" }, 409);
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const alertMock = vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "评估任务" })[0]);

    const evaluationTable = await screen.findByRole("table", { name: "评估任务列表" });
    const taskRow = within(evaluationTable).getByText("judge-completed").closest("tr");
    expect(taskRow).not.toBeNull();
    await user.click(within(taskRow as HTMLElement).getByRole("button", { name: "删除" }));

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith("该评估任务已运行或已生成评分结果，暂不允许删除。");
    });
  });

  it("optimistically marks an evaluation task as running and blocks duplicate starts", async () => {
    let listCalls = 0;
    let resolveStartRequest: ((value: Response) => void) | null = null;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/admin/providers") {
        return createJsonResponse({
          items: [
            {
              id: 1,
              name: "MockProvider",
              code: "mock-provider",
              provider_type: "openai",
              base_url: "http://127.0.0.1:8010/v1",
              default_model: "mock-model",
              enabled: true,
            },
          ],
        });
      }
      if (path === "/admin/execution-tasks") {
        return createJsonResponse({
          items: [
            {
              id: 9,
              name: "batch-existing",
              source_type: "recorded_request",
              source_ref_id: 3,
              status: "completed",
              progress_total: 1,
              progress_done: 1,
            },
          ],
        });
      }
      if (path === "/admin/evaluation-tasks" && (!init?.method || init.method === "GET")) {
        listCalls += 1;
        return createJsonResponse({
          items: [
            {
              id: 15,
              name: "judge-pending",
              source_type: "execution_task",
              source_ref_id: 9,
              evaluator_type: "llm_judge",
              judge_provider_id: 1,
              judge_model: "mock-model",
              status: listCalls > 1 ? "running" : "pending",
              progress_total: 0,
              progress_done: 0,
            },
          ],
        });
      }
      if (path === "/admin/evaluation-tasks/15/start" && init?.method === "POST") {
        return new Promise<Response>((resolve) => {
          resolveStartRequest = resolve;
        });
      }
      return createJsonResponse({ items: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => undefined);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: "评估任务" })[0]);

    const evaluationTable = await screen.findByRole("table", { name: "评估任务列表" });
    const taskRow = within(evaluationTable).getByText("judge-pending").closest("tr");
    expect(taskRow).not.toBeNull();
    const taskRowScope = within(taskRow as HTMLElement);

    const startButton = taskRowScope.getByRole("button", { name: "开始评估" });
    const retryButton = taskRowScope.getByRole("button", { name: "重跑" });
    expect(startButton).toBeEnabled();
    expect(retryButton).toBeEnabled();

    await user.click(startButton);

    await waitFor(() => {
      expect(taskRowScope.getByText("执行中")).toBeInTheDocument();
      expect(startButton).toBeDisabled();
      expect(retryButton).toBeDisabled();
    });

    await user.click(startButton);
    expect(fetchMock.mock.calls.filter(([path]) => String(path) === "/admin/evaluation-tasks/15/start")).toHaveLength(1);

    expect(resolveStartRequest).not.toBeNull();
    resolveStartRequest?.({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        id: 15,
        name: "judge-pending",
        source_type: "execution_task",
        source_ref_id: 9,
        evaluator_type: "llm_judge",
        judge_provider_id: 1,
        judge_model: "mock-model",
        status: "running",
        progress_total: 0,
        progress_done: 0,
      }),
    } as Response);

    await waitFor(() => {
      expect(taskRowScope.getByText("执行中")).toBeInTheDocument();
      expect(startButton).toBeDisabled();
      expect(retryButton).toBeDisabled();
    });
  });
});
