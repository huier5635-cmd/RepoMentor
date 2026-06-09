import { Copy, Download } from "lucide-react";
import { useRef, useState } from "react";

export default function TraceExportPanel({ sessionId, tracePayload }) {
  const [copied, setCopied] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const messageTimer = useRef(null);
  const payload = tracePayload || {};

  async function copySessionId() {
    if (!sessionId) return;
    try {
      await copyText(sessionId);
      setCopied(true);
      showAction("会话 ID 已复制。");
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      showAction("复制失败，请手动复制会话 ID。");
    }
  }

  function exportTrace() {
    if (!Object.keys(payload).length) {
      showAction("当前没有可导出的轨迹数据。");
      return;
    }
    const filename = `repomentor-trace-${sessionId || "current"}.json`;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showAction(`已触发下载：${filename}`);
  }

  function showAction(message) {
    setActionMessage(message);
    window.clearTimeout(messageTimer.current);
    messageTimer.current = window.setTimeout(() => setActionMessage(""), 2600);
  }

  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <Download size={17} />
        <h2>轨迹导出</h2>
      </header>
      <div className="debugActions">
        <button className="miniButton" type="button" onClick={exportTrace} disabled={!Object.keys(payload).length}>
          <Download size={14} />
          导出轨迹 JSON
        </button>
        <button className="miniButton" type="button" onClick={copySessionId} disabled={!sessionId}>
          <Copy size={14} />
          {copied ? "已复制" : "复制会话 ID"}
        </button>
      </div>
      {actionMessage && <p className="actionStatus" role="status">{actionMessage}</p>}
      <p className="muted">
        调试控制台用于开发调试和技术展示，会展示智能体编排、工作器输出、共享记忆和评估决策；它不面向普通新贡献者。
      </p>
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
