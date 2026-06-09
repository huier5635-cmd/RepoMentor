import { SearchCode } from "lucide-react";
import { zhField, zhText } from "../../utils/zh.js";

export default function RetrievalTracePanel({ trace, memory }) {
  const effectiveTrace = trace || {};
  const evidence = effectiveTrace.final_evidence || memory?.retrieved_evidence || [];

  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <SearchCode size={17} />
        <h2>检索轨迹</h2>
      </header>
      <div className="dataRows">
        <span>{zhField("query")}</span><strong>{zhText(effectiveTrace.query || memory?.user_question || "not available")}</strong>
        <span>{zhField("route")}</span><strong>{zhText(effectiveTrace.route || memory?.current_task || "not available")}</strong>
        <span>{zhField("metadata filters")}</span><strong>{formatValue(effectiveTrace.metadata_filters) || "暂无数据"}</strong>
      </div>
      <DebugList title="keyword results" items={effectiveTrace.keyword_results || []} />
      <DebugList title="vector results" items={effectiveTrace.vector_results || []} />
      <DebugList title="final evidence" items={evidence.map((item) => `${item.source_ref}：${zhText(item.supports_claim)}`)} />
      {!trace && (
        <p className="muted">后端暂未提供专用检索轨迹接口；这里会优先展示当前共享记忆中的证据。</p>
      )}
    </section>
  );
}

function DebugList({ title, items }) {
  return (
    <div className="debugListBlock">
      <h3>{zhField(title)}</h3>
      {items.length ? (
        <ul>
          {items.slice(0, 8).map((item) => <li key={formatValue(item)}>{zhText(formatValue(item))}</li>)}
        </ul>
      ) : (
        <p className="muted">暂无</p>
      )}
    </div>
  );
}

function formatValue(value) {
  if (!value) return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}
