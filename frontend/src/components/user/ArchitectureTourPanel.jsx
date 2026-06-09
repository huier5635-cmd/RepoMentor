import { Compass, FileText, GitBranch, ShieldCheck } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function ArchitectureTourPanel({ architectureTour }) {
  const tour = architectureTour || {};
  return (
    <section className="panel architectureTourPanel">
      <header className="panelHeader">
        <Compass size={17} />
        <h2>Architecture Tour</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.architectureTour} />
      {!tour.repo_id ? (
        <p className="muted">分析仓库后，这里会按照新手、贡献者和维护者的不同解释窗口组织架构讲解。</p>
      ) : (
        <>
          <div className="overviewSummary">
            <Metric label="项目目标" value={tour.project_goal} />
            <Metric label="现实问题" value={tour.real_world_problem} />
          </div>
          <Section icon={GitBranch} title="系统流程" items={tour.system_pipeline} />
          <div className="componentGrid">
            {(tour.major_components || []).map((component) => (
              <article className="componentCard" key={component.name}>
                <strong>{component.name}</strong>
                <p>{component.role}</p>
                <div className="codeChipList">
                  {(component.representative_files || []).slice(0, 6).map((file) => <code key={file}>{file}</code>)}
                </div>
              </article>
            ))}
          </div>
          <Section icon={ShieldCheck} title="关键不变量" items={tour.key_invariants} />
          <div className="criticalPathList">
            {(tour.critical_paths || []).map((path) => (
              <article key={path.entrypoint}>
                <strong>{path.entrypoint}</strong>
                <span>{(path.downstream_dependencies || []).join(" → ") || "未发现下游依赖边"}</span>
              </article>
            ))}
          </div>
          <Section icon={FileText} title="相关文档" items={tour.related_docs} code />
          <Section title="相关测试" items={tour.related_tests} code />
          {tour.uncertainties?.length > 0 && (
            <div className="warningList">
              {tour.uncertainties.map((item) => <span key={item}>{item}</span>)}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="overviewMetric">
      <span>{label}</span>
      <strong>{value || "未发现明确证据"}</strong>
    </div>
  );
}

function Section({ icon: Icon, title, items, code = false }) {
  if (!items?.length) return null;
  return (
    <article className="workflowBlock">
      <h3>{Icon ? <Icon size={15} /> : null}{title}</h3>
      <div className={code ? "codeChipList" : "plainChipList"}>
        {items.slice(0, 12).map((item) => code ? <code key={item}>{item}</code> : <span key={item}>{item}</span>)}
      </div>
    </article>
  );
}
