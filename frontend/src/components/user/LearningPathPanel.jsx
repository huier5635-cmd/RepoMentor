import { Route } from "lucide-react";
import { zhText } from "../../utils/zh.js";

export default function LearningPathPanel({ learningPath }) {
  const steps = learningPath?.steps || [];
  return (
    <section className="panel">
      <header className="panelHeader">
        <Route size={17} />
        <h2>学习路径</h2>
      </header>
      {learningPath?.conclusion && <p className="workflowConclusion">{zhText(learningPath.conclusion)}</p>}
      {steps.length ? (
        <div className="timeline">
          {steps.map((step) => (
            <div className="timelineRow" key={step.order}>
              <span>{step.order}</span>
              <div>
                <strong>{step.title || `第 ${step.order} 步`}</strong>
                <p>{zhText(step.reason)}</p>
                {step.evidence?.length > 0 && (
                  <div className="evidenceChips">
                    {step.evidence.slice(0, 3).map((item) => (
                      <small key={item.evidence_id}>{item.source_ref}</small>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">分析仓库后，这里会按步骤显示学习路径，并包含“开发流程与代码规范”阶段。</p>
      )}
    </section>
  );
}
