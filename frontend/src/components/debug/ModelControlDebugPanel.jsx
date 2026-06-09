import { Bot, CheckCircle2, KeyRound, Loader2, Power, RotateCcw, Save, ShieldCheck, TestTube2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const PROVIDERS = [
  { id: "mock", label: "MockProvider" },
  { id: "deepseek", label: "DeepSeekProvider" },
  { id: "openai", label: "OpenAIProvider" }
];

const DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-reasoner"];
const DEEPSEEK_BASE_URL = "https://api.deepseek.com";
const OPENAI_BASE_URL = "https://api.openai.com/v1";
const SDK_MISSING_HINT = "后端缺少 openai SDK，请安装依赖并重启后端。";
const SDK_INSTALL_COMMANDS = "pip install openai 或 pip install -r backend/requirements.txt";

export default function ModelControlDebugPanel({ status, busy, onRefresh, onConfigure, onTest }) {
  const [provider, setProvider] = useState(status?.provider_requested || "deepseek");
  const [model, setModel] = useState(modelForForm(status));
  const [baseUrl, setBaseUrl] = useState(status?.base_url || DEEPSEEK_BASE_URL);
  const [apiKey, setApiKey] = useState("");
  const [persist, setPersist] = useState(false);
  const [message, setMessage] = useState("");
  const [testResult, setTestResult] = useState(null);

  const requested = status?.provider_requested || provider;
  const active = status?.provider_active || "mock";
  const reason = status?.reason || "";
  const keyConfigured = Boolean(status?.api_key_configured);
  const sdkMissing = reason === "openai_sdk_missing";
  const displayModel = modelForStatus(status, active);
  const modelOptions = useMemo(() => (provider === "deepseek" ? DEEPSEEK_MODELS : []), [provider]);

  useEffect(() => {
    if (status?.provider_requested) setProvider(status.provider_requested);
    setModel(modelForForm(status));
    if (status?.base_url) setBaseUrl(status.base_url);
    if (status?.provider_requested === "deepseek" && !status?.base_url) setBaseUrl(DEEPSEEK_BASE_URL);
  }, [status]);

  function handleProviderChange(event) {
    const nextProvider = event.target.value;
    setProvider(nextProvider);
    if (nextProvider === "deepseek") {
      setModel((current) => DEEPSEEK_MODELS.includes(current) ? current : "deepseek-chat");
      setBaseUrl(DEEPSEEK_BASE_URL);
    } else if (nextProvider === "openai") {
      setModel((current) => current && current !== "mock-deterministic" ? current : "gpt-4o-mini");
      setBaseUrl(OPENAI_BASE_URL);
    } else {
      setModel("mock-deterministic");
      setBaseUrl("");
    }
  }

  async function saveConfig(event) {
    event.preventDefault();
    const next = await onConfigure({
      provider,
      model: provider === "mock" ? "" : model,
      base_url: provider === "mock" ? "" : baseUrl,
      api_key: apiKey.trim(),
      persist
    });
    setApiKey("");
    setTestResult(null);
    if (next?.reason === "openai_sdk_missing") {
      setMessage(`${SDK_MISSING_HINT} ${SDK_INSTALL_COMMANDS}`);
    } else {
      setMessage(next?.fallback_to_mock ? "配置已保存，但当前仍回退到 Mock。" : "模型配置已保存。");
    }
  }

  async function testConnection() {
    setMessage("");
    try {
      const result = await onTest();
      setTestResult(result);
    } catch (error) {
      setTestResult({ success: false, error_message: error.message });
    }
  }

  return (
    <section className="panel debugPanel modelControl modelControlDebugPanel">
      <header className="panelHeader">
        <Bot size={17} />
        <h2>模型控制</h2>
        <button className="miniButton" type="button" onClick={onRefresh} disabled={busy}>
          <RotateCcw size={14} />
          刷新状态
        </button>
      </header>

      <div className="modelStatusGrid debugModelGrid">
        <StatusItem label="provider_requested" value={requested} />
        <StatusItem label="provider_active" value={active} />
        <StatusItem label="model" value={displayModel} />
        <StatusItem label="base_url" value={status?.base_url || "无"} />
        <StatusItem label="API Key" value={keyConfigured ? `已配置 ${status?.api_key_masked || ""}` : "未配置"} />
        <StatusItem label="fallback_to_mock" value={String(Boolean(status?.fallback_to_mock))} />
        <StatusItem label="reason" value={reason || "无"} />
      </div>

      {sdkMissing && <p className="errorBar">{SDK_MISSING_HINT}</p>}

      <form className="modelForm debugModelForm" onSubmit={saveConfig}>
        <label>
          <span>模型 Provider</span>
          <select value={provider} onChange={handleProviderChange} disabled={busy}>
            {PROVIDERS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>

        <label>
          <span>模型</span>
          {modelOptions.length ? (
            <select value={model} onChange={(event) => setModel(event.target.value)} disabled={busy}>
              {modelOptions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          ) : (
            <input value={model} onChange={(event) => setModel(event.target.value)} disabled={busy || provider === "mock"} />
          )}
          <small>DeepSeek 支持 deepseek-chat 和 deepseek-reasoner；保存后生效。</small>
        </label>

        <label>
          <span>Base URL</span>
          <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} disabled={busy || provider === "mock"} />
        </label>

        <label>
          <span><KeyRound size={14} /> API Key</span>
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="输入新的 DeepSeek API Key"
            autoComplete="off"
            disabled={busy || provider === "mock"}
          />
          <small>不填写则保留已有 Key；保存后输入框会清空，响应中不会返回明文。</small>
        </label>

        <label className="persistToggle">
          <input type="checkbox" checked={persist} onChange={(event) => setPersist(event.target.checked)} disabled={busy} />
          <span>写入 backend/.env</span>
          <small>仅在本地使用；请确认不要提交 .env。</small>
        </label>

        <div className="modelActions">
          <button className="iconButton" type="submit" disabled={busy}>
            {busy ? <Loader2 className="spin" size={15} /> : <Save size={15} />}
            保存配置
          </button>
          <button className="miniButton" type="button" onClick={testConnection} disabled={busy}>
            <TestTube2 size={14} />
            测试连接
          </button>
          <button className="miniButton" type="button" onClick={() => onConfigure({ provider: "mock" })} disabled={busy}>
            <Power size={14} />
            切回 Mock
          </button>
        </div>
      </form>

      <p className="modelHint">
        <ShieldCheck size={14} />
        API Key 只会发送到本地后端内存；不会写入浏览器存储，也不会在响应中返回明文。
      </p>

      {message && (
        <p className="actionStatus" role="status">
          <CheckCircle2 size={14} />
          {message}
        </p>
      )}

      {testResult && (
        <div className={testResult.success ? "actionStatus" : "errorBar"} role="status">
          {testResult.success ? <CheckCircle2 size={14} /> : <TestTube2 size={14} />}
          <span>{testResult.success ? "测试连接成功" : testErrorMessage(testResult)}</span>
        </div>
      )}

      {status?.last_call && (
        <details>
          <summary>最近一次 LLM 调用信息</summary>
          <pre>{JSON.stringify(status.last_call, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}

function StatusItem({ label, value }) {
  return (
    <div className="modelStatusItem">
      <span>{label}</span>
      <strong>{String(value || "无")}</strong>
    </div>
  );
}

function modelForForm(status) {
  if (status?.requested_model) return status.requested_model;
  if (status?.provider_requested === "deepseek") return "deepseek-chat";
  if (status?.provider_requested === "openai") return status?.model || "gpt-4o-mini";
  return status?.model || "deepseek-chat";
}

function modelForStatus(status, active) {
  if (active === "mock") return "mock-deterministic";
  if (active === "deepseek" && (!status?.model || status.model === "mock-deterministic")) {
    return status?.requested_model || "deepseek-chat";
  }
  return status?.model || status?.requested_model || "mock-deterministic";
}

function testErrorMessage(result) {
  const error = result.error || result.error_message || result.reason || "未知错误";
  if (result.reason === "openai_sdk_missing" || error.includes("openai SDK")) {
    return `测试连接失败：${error} 请运行 ${SDK_INSTALL_COMMANDS}，然后重启后端。`;
  }
  return `测试连接失败：${error}`;
}
