import { ClipboardList, XCircle } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

const ITEMS = [
  ["has_readme", "README"],
  ["has_architecture_doc", "架构文档"],
  ["has_contributing", "贡献规范"],
  ["has_issue_template", "Issue 模板"],
  ["has_pr_template", "PR 模板"],
  ["has_good_first_issue", "good first issue"],
  ["has_skill_labels", "技能标签"],
  ["has_ci", "CI"],
  ["has_test_entry", "测试入口"],
  ["has_lint_format_doc", "lint/format 说明"],
  ["has_translation_support", "中文/双语支持"],
  ["has_beginner_friendly_commands", "新手命令闭环"]
];

export default function OnboardingDebtPanel({ onboardingDebt }) {
  const report = onboardingDebt || {};
  return (
    <section className="panel onboardingDebtPanel">
      <header className="panelHeader">
        <ClipboardList size={17} />
        <h2>新手友好度检查</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.newcomerFriendliness} />
      {!report.repo_id ? (
        <p className="muted">分析仓库后，这里会显示新贡献者入门材料的准备度和维护者改进建议。</p>
      ) : (
        <>
          <div className="debtChecklist">
            {ITEMS.map(([key, label]) => (
              <span className={report[key] ? "ok" : "missing"} key={key}>
                {report[key] ? "已发现" : "缺失"} · {label}
              </span>
            ))}
          </div>
          <DebtList title="新手友好度风险" items={report.onboarding_risks} />
          <DebtList title="维护者建议" items={report.recommended_maintainer_actions} />
          {report.evidence?.length > 0 && (
            <div className="evidenceChips">
              {report.evidence.slice(0, 5).map((item) => <small key={item.evidence_id}>{item.source_ref}</small>)}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function DebtList({ title, items }) {
  if (!items?.length) return null;
  return (
    <article className="workflowBlock">
      <h3><XCircle size={15} />{title}</h3>
      <ul>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </article>
  );
}
