import { CheckCircle2, Circle, Loader2, Play, Search } from "lucide-react";

const PHASES = [
  { id: "reading", label: "读取仓库" },
  { id: "structure", label: "分析结构" },
  { id: "learning", label: "生成学习路径" },
  { id: "done", label: "完成" }
];

export default function RepoInput({ value, onChange, onAnalyze, busy, phase }) {
  function submit(event) {
    event.preventDefault();
    onAnalyze(value);
  }

  return (
    <section className="repoInputPanel">
      <form className="repoInput" onSubmit={submit}>
        <Search size={18} />
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="https://github.com/owner/repo"
          disabled={busy}
          aria-label="GitHub 仓库链接"
        />
        <button type="submit" disabled={busy || !value.trim()} title="分析">
          {busy ? <Loader2 className="spin" size={17} /> : <Play size={17} />}
          分析
        </button>
      </form>
      <ol className="analysisSteps" aria-label="分析状态">
        {PHASES.map((item) => {
          const currentIndex = PHASES.findIndex((phaseItem) => phaseItem.id === phase);
          const itemIndex = PHASES.findIndex((phaseItem) => phaseItem.id === item.id);
          const complete = phase === "done" || (busy && currentIndex > itemIndex);
          const active = phase === item.id;
          return (
            <li key={item.id} className={active ? "active" : complete ? "complete" : ""}>
              {active && busy ? <Loader2 className="spin" size={14} /> : complete ? <CheckCircle2 size={14} /> : <Circle size={14} />}
              <span>{item.label}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
