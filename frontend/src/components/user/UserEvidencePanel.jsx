import { FileSearch } from "lucide-react";
import { zhEvidenceGroup, zhText } from "../../utils/zh.js";

export default function UserEvidencePanel({ answer }) {
  const groups = [
    { id: "docs", label: "docs", items: answer?.evidence_docs || [] },
    { id: "code", label: "code", items: answer?.evidence_code || [] },
    { id: "issues", label: "issues", items: answer?.evidence_issues || [] }
  ];
  const hasEvidence = groups.some((group) => group.items.length > 0);

  return (
    <section className="userEvidence">
      <h3><FileSearch size={15} /> 简化证据</h3>
      {!hasEvidence ? (
        <p className="muted">当前回答没有返回可展示的文档、代码或 Issue 证据摘要。</p>
      ) : (
        <div className="evidenceSummaryGrid">
          {groups.map((group) => (
            <EvidenceGroup key={group.id} title={group.label} items={group.items} />
          ))}
        </div>
      )}
    </section>
  );
}

function EvidenceGroup({ title, items }) {
  return (
    <article className="evidenceGroup compact">
      <h4>{zhEvidenceGroup(title)}</h4>
      {items.length ? items.slice(0, 3).map((item) => (
        <div className="evidenceItem compact" key={item.evidence_id}>
          <strong>{item.source_ref}</strong>
          <p>{zhText(item.supports_claim || item.quote)}</p>
        </div>
      )) : <p className="muted">暂无</p>}
    </article>
  );
}
