import { PlaySquare } from "lucide-react";

export default function TutorialDraftPanel({ tutorials }) {
  const items = tutorials || [];
  if (!items.length) return null;
  return (
    <section className="tutorialDrafts">
      <header className="panelHeader compactHeader">
        <PlaySquare size={16} />
        <h2>教程草稿</h2>
      </header>
      <div className="tutorialGrid">
        {items.map((tutorial) => (
          <article className="tutorialCard" key={tutorial.tutorial_id}>
            <strong>{tutorial.title}</strong>
            <ol>
              {(tutorial.steps || []).slice(0, 5).map((step) => (
                <li key={`${tutorial.tutorial_id}-${step.title}`}>
                  {step.title}
                  {step.command ? <code>{step.command}</code> : null}
                  {step.related_file ? <small>{step.related_file}</small> : null}
                </li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}
