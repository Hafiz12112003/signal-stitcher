import type { Theme } from "./types";
import SourceBar from "./SourceBar";

interface Props {
  themes: Theme[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ThemeList({ themes, selectedId, onSelect }: Props) {
  if (themes.length === 0) {
    return <p className="empty">No themes match. Clear the search or choose another filter.</p>;
  }
  return (
    <ul className="themelist">
      {themes.map((t) => {
        const gh = t.sources.github_issues ?? 0;
        const pl = t.sources.play_reviews ?? 0;
        const active = t.theme_id === selectedId;
        return (
          <li key={t.theme_id}>
            <button
              className={"row" + (active ? " active" : "")}
              aria-current={active ? "true" : undefined}
              onClick={() => onSelect(t.theme_id)}
            >
              <span className="rowhead">
                <span className="rowtitle">{t.title}</span>
                <span className="rowsize">{t.size}</span>
              </span>
              <span className="rowexample">“{t.example}”</span>
              <SourceBar sources={t.sources} />
              <span className="rowmeta">
                <span>{gh} GitHub</span>
                <span>{pl} Play</span>
                {gh > 0 && pl > 0 && <span className="both">both sources</span>}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
