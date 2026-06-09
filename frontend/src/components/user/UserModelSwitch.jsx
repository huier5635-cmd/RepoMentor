import { Bot, Settings, Sparkles } from "lucide-react";

export default function UserModelSwitch({ status, busy, onSwitchProvider, onOpenSettings }) {
  const requested = status?.provider_requested || status?.provider || "deepseek";
  const active = status?.provider_active || (status?.fallback_to_mock ? "mock" : requested);
  const model = status?.model || "mock-deterministic";
  const missingDeepSeekKey = requested === "deepseek" && active === "mock" && status?.reason === "missing_deepseek_api_key";
  const summary = modelSummary({ requested, active, missingDeepSeekKey });

  return (
    <section className="modelControl modelControlCompact panel userModelSwitch">
      <header className="panelHeader">
        <Bot size={17} />
        <h2>模型模式</h2>
      </header>

      <div className="modelStatusGrid compact">
        <StatusItem label="当前模式" value={providerLabel(active)} />
        <StatusItem label="当前模型" value={model} />
        <StatusItem label="状态" value={summary.status} />
        <button className="miniButton" type="button" onClick={onOpenSettings}>
          <Settings size={14} />
          打开模型设置
        </button>
      </div>

      <div className="userModelActions" aria-label="模型切换">
        <button className="miniButton" type="button" disabled={busy || requested === "mock"} onClick={() => onSwitchProvider("mock")}>
          免费 Mock 模式
        </button>
        <button className="iconButton" type="button" disabled={busy || requested === "deepseek"} onClick={() => onSwitchProvider("deepseek")}>
          <Sparkles size={15} />
          DeepSeek 模式
        </button>
      </div>

      <p className="modelHint">{summary.description}</p>
      {missingDeepSeekKey && <p className="modelWarning">DeepSeek 未配置 API Key，请到调试控制台或本地 backend/.env 配置。</p>}
    </section>
  );
}

function StatusItem({ label, value }) {
  return (
    <div className="modelStatusItem">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function modelSummary({ requested, active, missingDeepSeekKey }) {
  if (missingDeepSeekKey) {
    return {
      status: "已自动使用 Mock",
      description: "当前使用 Mock 模式：DeepSeek API Key 未配置。Mock 不调用真实大模型，适合免费演示和确定性分析。"
    };
  }
  if (active === "deepseek") {
    return {
      status: "已连接",
      description: "DeepSeek 会调用真实大语言模型，回答更自然，但需要本地 API Key。"
    };
  }
  if (requested === "openai" && active === "mock") {
    return {
      status: "已自动使用 Mock",
      description: "当前请求 OpenAI，但未完成本地配置；系统已使用免费 Mock 模式。"
    };
  }
  return {
    status: "免费演示",
    description: "Mock 不调用真实大模型，适合免费演示、确定性仓库分析和无 Key 环境。"
  };
}

function providerLabel(provider) {
  if (provider === "deepseek") return "DeepSeek";
  if (provider === "openai") return "OpenAI";
  return "Mock";
}
