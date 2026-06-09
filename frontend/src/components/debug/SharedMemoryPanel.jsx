import { Clipboard, Copy } from "lucide-react";
import { useRef, useState } from "react";
import { zhField, zhText } from "../../utils/zh.js";

export default function SharedMemoryPanel({ memory }) {
  const [copied, setCopied] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const messageTimer = useRef(null);
  const json = JSON.stringify(memory || {}, null, 2);

  async function copyJson() {
    try {
      await copyText(json);
      setCopied(true);
      showAction("原始 JSON 已复制。");
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      showAction("复制失败，请展开 JSON 后手动复制。");
    }
  }

  function showAction(message) {
    setActionMessage(message);
    window.clearTimeout(messageTimer.current);
    messageTimer.current = window.setTimeout(() => setActionMessage(""), 2600);
  }

  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <Clipboard size={17} />
        <h2>共享记忆</h2>
        <button className="miniButton" type="button" onClick={copyJson} disabled={!memory}>
          <Copy size={14} />
          {copied ? "已复制" : "复制原始 JSON"}
        </button>
      </header>
      {actionMessage && <p className="actionStatus" role="status">{actionMessage}</p>}
      {memory ? (
        <>
          <div className="dataRows">
            <span>{zhField("current_task")}</span><strong>{zhText(memory.current_task || "not available")}</strong>
            <span>{zhField("user_question")}</span><strong>{zhText(memory.user_question || "not available")}</strong>
            <span>{zhField("retrieved_evidence")}</span><strong>{memory.retrieved_evidence?.length || 0}</strong>
            <span>{zhField("intermediate_conclusions")}</span><strong>{memory.intermediate_conclusions?.length || 0}</strong>
            <span>{zhField("unresolved_uncertainties")}</span><strong>{memory.unresolved_uncertainties?.length || 0}</strong>
            <span>{zhField("worker_outputs")}</span><strong>{memory.worker_outputs?.length || 0}</strong>
            <span>{zhField("final_decision_trace")}</span><strong>{memory.final_decision_trace?.length || 0}</strong>
          </div>
          <details open>
            <summary>原始共享记忆 JSON</summary>
            <pre>{json}</pre>
          </details>
        </>
      ) : (
        <p className="muted">尚未加载共享记忆。请打开 /debug/session/:sessionId，或在当前浏览器会话中先运行一次分析。</p>
      )}
    </section>
  );
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return;
    } catch {
      // Fall back to a temporary textarea below.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("copy failed");
}
