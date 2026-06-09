import { Braces } from "lucide-react";

export default function FinalAnswerJsonPanel({ answer, finalAnswerJson }) {
  const payload = finalAnswerJson || answer;
  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <Braces size={17} />
        <h2>最终答案 JSON</h2>
      </header>
      {payload ? (
        <pre>{JSON.stringify(payload, null, 2)}</pre>
      ) : (
        <p className="muted">
          暂无最终答案 JSON。请先提出一个 RepoMentor 问题，或打开包含最终答案的调试会话。
        </p>
      )}
    </section>
  );
}
