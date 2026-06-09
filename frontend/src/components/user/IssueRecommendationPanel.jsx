import { BadgeCheck, Tags } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function IssueRecommendationPanel({ issueRanking }) {
  const issues = issueRanking?.issues || [];
  return (
    <section className="panel">
      <header className="panelHeader">
        <BadgeCheck size={17} />
        <h2>推荐任务 / Contribution Funnel</h2>
        <span className="count">{issues.length}</span>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.recommendation} />
      {issueRanking?.message && <p className="muted">{issueRanking.message}</p>}
      {issues.length ? (
        <div className="issueList">
          {issues.map((issue) => (
            <article className="issueItem expanded" key={issue.issue_number}>
              <div>
                <strong>
                  {issue.is_github_issue === false ? "入门练习任务" : `GitHub Issue #${issue.issue_number}`} · {issue.title}
                </strong>
                <p>{issue.why_this_is_a_good_first_step || issue.why_fit_for_beginner || issue.recommendation_reason}</p>
                {issue.is_github_issue === false && <p className="modelWarning">不是 GitHub Issue；source = {issue.source || "internal_suggestion"}</p>}
                <div className="tagList">
                  <Tags size={13} />
                  {(issue.skill_tags || []).map((tag) => <small key={tag}>{tag}</small>)}
                  {issue.task_type ? <small>{issue.task_type}</small> : null}
                  <small>{difficultyLabel(issue.difficulty)}</small>
                </div>
                {issue.expected_output && (
                  <p><strong>预期产物：</strong>{issue.expected_output}</p>
                )}
                {issue.expected_prerequisites?.length > 0 && (
                  <p><strong>前置条件：</strong>{issue.expected_prerequisites.join("、")}</p>
                )}
                {issue.suggested_first_steps?.length > 0 && (
                  <>
                    <h3>建议第一步</h3>
                    <ol>
                      {issue.suggested_first_steps.map((step) => <li key={step}>{step}</li>)}
                    </ol>
                  </>
                )}
                {issue.evidence?.length > 0 && (
                  <div className="evidenceChips">
                    {issue.evidence.slice(0, 5).map((item) => <small key={item.evidence_id}>{item.source_ref}</small>)}
                  </div>
                )}
              </div>
              <span>{issue.is_github_issue === false ? "内部建议" : "GitHub"}</span>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">{issueRanking?.message || "暂无推荐任务。"}</p>
      )}
    </section>
  );
}

function difficultyLabel(value) {
  if (value === "easy") return "简单";
  if (value === "medium") return "中等";
  if (value === "hard") return "较难";
  return value || "未标注难度";
}
