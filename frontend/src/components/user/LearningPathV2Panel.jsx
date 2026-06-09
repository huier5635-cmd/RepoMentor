import { BookOpenCheck, CheckCircle2, FileCode2, Route, TerminalSquare } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";
import TutorialDraftPanel from "./TutorialDraftPanel.jsx";

export default function LearningPathV2Panel({ learningPathV2, fallbackLearningPath, tutorials }) {
  const steps = learningPathV2?.steps || [];
  if (!steps.length) {
    return (
      <section className="panel">
        <header className="panelHeader">
          <Route size={17} />
          <h2>学习路径 V2</h2>
        </header>
        <DesignBasisBadge {...DESIGN_BASIS.learningPath} />
        <p className="muted">新版学习路径还没有返回，暂时使用旧学习路径作为兜底。</p>
        {fallbackLearningPath?.steps?.length ? (
          <ol className="compactList">
            {fallbackLearningPath.steps.map((step) => <li key={step.order}>{step.title || step.reason}</li>)}
          </ol>
        ) : null}
      </section>
    );
  }

  return (
    <section className="panel learningV2Panel">
      <header className="panelHeader">
        <Route size={17} />
        <h2>学习路径 V2</h2>
        <span className="count">{steps.length}</span>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.learningPath} />
      <p className="workflowConclusion">{learningPathV2.conclusion}</p>
      <div className="learningStepGrid">
        {steps.map((step, index) => (
          <article className="learningStepCard" key={step.step_id}>
            <div className="stepIndex">{index + 1}</div>
            <div>
              <h3>{step.title}</h3>
              <p>{step.goal}</p>
              <small>{step.why_now}</small>
            </div>
            <FactBlock icon={FileCode2} title="要看的文件" items={step.concrete_files} code />
            <FactBlock icon={TerminalSquare} title="要运行的命令" items={step.concrete_commands} code />
            <FactBlock icon={CheckCircle2} title="预期观察" items={step.expected_observations} />
            {step.worked_example && <p className="workedExample">{step.worked_example}</p>}
            <FactBlock title="自检问题" items={step.self_check_questions} />
            <FactBlock title="常见误区" items={step.common_mistakes} />
            <EvidenceLine evidence={step.evidence} />
            {step.uncertainties?.length > 0 && (
              <div className="warningList">
                {step.uncertainties.map((item) => <span key={item}>{item}</span>)}
              </div>
            )}
          </article>
        ))}
      </div>
      <TutorialDraftPanel tutorials={tutorials} />
      <div className="guardrailBox">
        <BookOpenCheck size={16} />
        <div>
          <strong>证据约束</strong>
          <p>{(learningPathV2.hallucination_guardrails || []).join("；")}</p>
        </div>
      </div>
    </section>
  );
}

function FactBlock({ icon: Icon, title, items, code = false }) {
  if (!items?.length) return null;
  return (
    <div className="factBlock">
      <strong>{Icon ? <Icon size={14} /> : null}{title}</strong>
      <div className={code ? "codeChipList" : "plainChipList"}>
        {items.slice(0, 8).map((item) => code ? <code key={item}>{item}</code> : <span key={item}>{item}</span>)}
      </div>
    </div>
  );
}

function EvidenceLine({ evidence }) {
  if (!evidence?.length) return null;
  return (
    <div className="evidenceChips">
      {evidence.slice(0, 4).map((item) => <small key={item.evidence_id}>{item.source_ref}</small>)}
    </div>
  );
}
