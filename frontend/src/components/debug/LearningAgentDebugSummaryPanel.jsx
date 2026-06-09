import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function LearningAgentDebugSummaryPanel({ bundle }) {
  if (!bundle) {
    return (
      <section className="panel debugPanel">
        <header className="panelHeader">
          <Activity size={17} />
          <h2>学习 Agent 调试摘要</h2>
        </header>
        <p className="muted">暂无学习 Agent 调试摘要。</p>
      </section>
    );
  }
  const learning = bundle.learning_path_v2 || {};
  const bilingual = bundle.bilingual_docs || {};
  const funnel = bundle.contribution_funnel || {};
  const debt = bundle.onboarding_debt || {};
  const tasks = funnel.issues || [];
  const internalTasks = tasks.filter((task) => task.source === "internal_suggestion");
  const warnings = bilingual.fidelity_warnings || [];
  const missingDebt = debt.onboarding_risks || [];
  return (
    <section className="panel debugPanel learningAgentSummaryPanel">
      <header className="panelHeader">
        <Activity size={17} />
        <h2>学习 Agent 调试摘要</h2>
      </header>
      <div className="metricGrid">
        <Metric label="学习步骤" value={(learning.steps || []).length} />
        <Metric label="证据覆盖" value={learning.evidence_coverage ?? 0} />
        <Metric label="模块卡" value={(bundle.module_study_cards || []).length} />
        <Metric label="internal tasks" value={internalTasks.length} />
        <Metric label="翻译切片" value={(bilingual.chunks || []).length} />
        <Metric label="新手友好度" value={missingDebt.length} />
      </div>
      <DebugList
        icon={warnings.length ? AlertTriangle : CheckCircle2}
        title="translation fidelity"
        items={warnings.length ? warnings : ["未发现翻译保真 warning"]}
      />
      <DebugList title="internal first tasks trace" items={internalTasks.map((task) => `${task.task_type || "task"} · ${task.title}`)} />
      <DebugList title="newcomer friendliness JSON 摘要" items={missingDebt} />
      <DebugList title="hallucination guardrails" items={learning.hallucination_guardrails || []} />
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DebugList({ icon: Icon = CheckCircle2, title, items }) {
  if (!items?.length) return null;
  return (
    <article className="debugListBlock">
      <h3><Icon size={14} /> {title}</h3>
      <ul>
        {items.slice(0, 8).map((item, index) => <li key={`${title}-${index}-${item}`}>{item}</li>)}
      </ul>
    </article>
  );
}
