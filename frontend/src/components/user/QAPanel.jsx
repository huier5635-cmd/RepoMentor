import { Send, Sparkles } from "lucide-react";
import { useState } from "react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";
import UserEvidencePanel from "./UserEvidencePanel.jsx";

export default function QAPanel({ repoReady, onAsk, answer, busy }) {
  const [question, setQuestion] = useState("这个项目怎么启动？");

  function submit(event) {
    event.preventDefault();
    onAsk(question);
  }

  return (
    <section className="panel qaPanel">
      <header className="panelHeader">
        <Sparkles size={17} />
        <h2>仓库问答</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.qa} />
      <form className="questionBar" onSubmit={submit}>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={!repoReady || busy}
          aria-label="向 RepoMentor 提问"
        />
        <button disabled={!repoReady || busy || !question.trim()} title="提问">
          <Send size={16} />
        </button>
      </form>
      {answer ? (
        <div className="answerBox">
          <h3>结论</h3>
          <p>{answer.conclusion}</p>
          <h3>操作步骤</h3>
          <ol>
            {(answer.steps || []).map((step) => <li key={step}>{step}</li>)}
          </ol>
          <h3>风险提示</h3>
          <ul>
            {(answer.risks || []).map((risk) => <li key={risk}>{risk}</li>)}
          </ul>
          <h3>可验证命令</h3>
          <div className="commandList">
            {(answer.verifiable_commands || []).map((command) => <code key={command}>{command}</code>)}
          </div>
          {answer.model_info && (
            <p className="modelBadge">
              模型增强：{modelLabel(answer.model_info)}
            </p>
          )}
          <UserEvidencePanel answer={answer} />
        </div>
      ) : (
        <p className="muted">用户页只展示回答、简化证据和可验证命令；worker 输出、共享记忆和 SelfCheck JSON 放在调试页。</p>
      )}
    </section>
  );
}

function modelLabel(modelInfo) {
  if (!modelInfo?.used_llm && modelInfo?.fallback_to_mock) return "Mock（模型回退）";
  if (!modelInfo?.used_llm) return "Mock";
  if (modelInfo.provider === "deepseek") return "DeepSeek";
  return modelInfo.provider || "Mock";
}
