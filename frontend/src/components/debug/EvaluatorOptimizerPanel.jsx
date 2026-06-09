import { ShieldCheck } from "lucide-react";
import { zhField, zhStatus, zhText } from "../../utils/zh.js";

export default function EvaluatorOptimizerPanel({ answer, selfCheck, trace }) {
  const check = selfCheck || answer?.self_check;
  const traceSummary = trace || answer?.trace_summary || [];
  const modelInfo = answer?.model_info;

  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <ShieldCheck size={17} />
        <h2>评估器与优化器</h2>
      </header>
      {modelInfo && <ModelInfoBlock modelInfo={modelInfo} />}
      {check ? (
        <div className="selfCheck">
          <div className="checkRow"><span>{zhField("SelfCheckReport.passed")}</span><strong>{check.passed ? "是" : "否"}</strong></div>
          <div className="checkRow"><span>{zhField("evidence coverage")}</span><strong>{Math.round((check.evidence_coverage || 0) * 100)}%</strong></div>
          <div className="checkRow"><span>{zhField("suggested_action")}</span><strong>{zhStatus(check.suggested_action)}</strong></div>
          <DebugList title="hallucination risks" items={check.hallucination_risks} />
          <DebugList title="missing evidence" items={check.missing_evidence} />
          <DebugList title="conflicts" items={check.conflicts} />
        </div>
      ) : (
        <p className="muted">暂无自检报告。</p>
      )}
      <DebugList title="optimizer changes / decision trace" items={traceSummary} />
    </section>
  );
}

function ModelInfoBlock({ modelInfo }) {
  return (
    <div className="debugListBlock">
      <h3>LLM 调试信息</h3>
      <div className="selfCheck">
        <div className="checkRow"><span>provider</span><strong>{modelInfo.provider || "mock"}</strong></div>
        <div className="checkRow"><span>model</span><strong>{modelInfo.model || "mock-deterministic"}</strong></div>
        <div className="checkRow"><span>prompt_type</span><strong>{modelInfo.prompt_type || "general"}</strong></div>
        <div className="checkRow"><span>evidence_count</span><strong>{modelInfo.evidence_count ?? 0}</strong></div>
        <div className="checkRow"><span>elapsed_ms</span><strong>{modelInfo.elapsed_ms ?? 0}</strong></div>
        <div className="checkRow"><span>success</span><strong>{modelInfo.success ? "true" : "false"}</strong></div>
        <div className="checkRow"><span>used_llm</span><strong>{modelInfo.used_llm ? "true" : "false"}</strong></div>
        <div className="checkRow"><span>fallback_to_mock</span><strong>{modelInfo.fallback_to_mock ? "true" : "false"}</strong></div>
        {modelInfo.error_message && (
          <div className="debugField">
            <span>error message</span>
            <strong>{modelInfo.error_message}</strong>
          </div>
        )}
      </div>
    </div>
  );
}

function DebugList({ title, items = [] }) {
  return (
    <div className="debugListBlock">
      <h3>{zhField(title)}</h3>
      {items.length ? (
        <ul>
          {items.map((item) => <li key={item}>{zhText(item)}</li>)}
        </ul>
      ) : (
        <p className="muted">暂无</p>
      )}
    </div>
  );
}
