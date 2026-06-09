import { GraduationCap, Send } from "lucide-react";
import { useState } from "react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function LearningCheckPanel({ repoReady, busy, result, onSubmit }) {
  const [topic, setTopic] = useState("项目目标和启动方式");
  const [learnerAnswer, setLearnerAnswer] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!learnerAnswer.trim()) return;
    await onSubmit({ topic, learner_answer: learnerAnswer });
  }

  return (
    <section className="panel learningCheckPanel">
      <header className="panelHeader">
        <GraduationCap size={17} />
        <h2>学习检查</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.learningCheck} />
      <form className="learningForm" onSubmit={submit}>
        <label>
          <span>检查主题</span>
          <input value={topic} onChange={(event) => setTopic(event.target.value)} disabled={!repoReady || busy} />
        </label>
        <label>
          <span>用自己的话解释</span>
          <textarea
            value={learnerAnswer}
            onChange={(event) => setLearnerAnswer(event.target.value)}
            disabled={!repoReady || busy}
            placeholder="例如：这个项目的目标是……推荐先运行……入口文件是……测试边界在……"
          />
        </label>
        <button className="miniButton" disabled={!repoReady || busy || !learnerAnswer.trim()}>
          <Send size={14} />
          提交检查
        </button>
      </form>
      {result ? (
        <div className="feedbackBox">
          <strong>掌握度：{masteryLabel(result.mastery_estimate)}</strong>
          <p>{result.grounded_feedback}</p>
          {result.missing_key_points?.length > 0 && (
            <>
              <h3>还缺少</h3>
              <ul>
                {result.missing_key_points.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </>
          )}
          {result.evidence_refs?.length > 0 && (
            <div className="evidenceChips">
              {result.evidence_refs.map((item) => <small key={item}>{item}</small>)}
            </div>
          )}
        </div>
      ) : (
        <p className="muted">这里会给出基于证据的反馈，不做空泛鼓励，也不会引用图谱外事实。</p>
      )}
    </section>
  );
}

function masteryLabel(value) {
  if (value === "high") return "高";
  if (value === "medium") return "中";
  return "低";
}
