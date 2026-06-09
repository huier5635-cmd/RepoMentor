import { Lightbulb } from "lucide-react";

export default function DesignBasisBadge({
  title = "设计依据",
  basis,
  description,
  sourceType,
  displayMode = "compact"
}) {
  if (!basis && !description) return null;

  return (
    <aside className={`designBasisBadge ${displayMode}`}>
      <div className="designBasisTitle">
        <Lightbulb size={15} />
        <strong>{title}：{basis}</strong>
      </div>
      {description ? <p>{description}</p> : null}
      {sourceType ? <small>{sourceType}</small> : null}
    </aside>
  );
}
