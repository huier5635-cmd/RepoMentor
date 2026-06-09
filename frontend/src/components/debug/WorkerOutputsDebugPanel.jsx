import { ClipboardList } from "lucide-react";
import { zhField, zhStatus, zhText, zhWorkerName } from "../../utils/zh.js";

export default function WorkerOutputsDebugPanel({ outputs }) {
  const workerOutputs = outputs || [];
  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <ClipboardList size={17} />
        <h2>工作器输出调试</h2>
        <span className="count">{workerOutputs.length}</span>
      </header>
      {workerOutputs.length ? (
        <div className="outputList">
          {workerOutputs.map((output) => (
            <article className="outputItem debugOutput" key={output.worker_name}>
              <div className="outputTitle">
                <strong>{zhWorkerName(output.worker_name)}</strong>
                <span className={`status ${output.status}`}>{zhStatus(output.status)}</span>
              </div>
              <DebugList title="task" items={[output.task]} />
              <DebugList title="findings" items={output.findings} />
              <DebugList title="evidence" items={(output.evidence || []).map((item) => `${item.source_ref}：${zhText(item.supports_claim)}`)} />
              <DebugList title="uncertainties" items={output.uncertainties} />
              <DebugList title="next_actions" items={output.next_actions} />
              <details>
                <summary>{zhField("raw output")}</summary>
                <pre>{JSON.stringify(output, null, 2)}</pre>
              </details>
            </article>
          ))}
        </div>
      ) : (
        <p className="muted">当前仓库或会话暂无工作器输出。</p>
      )}
    </section>
  );
}

function DebugList({ title, items = [] }) {
  return (
    <div className="debugListBlock">
      <h3>{zhField(title)}</h3>
      {items.length ? (
        <ul>
          {items.slice(0, 8).map((item) => <li key={item}>{zhText(item)}</li>)}
        </ul>
      ) : (
        <p className="muted">暂无</p>
      )}
    </div>
  );
}
