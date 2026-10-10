import { useState } from "react";
import type { Theme } from "./types";

interface Props {
  themes: Theme[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

interface Hover {
  theme: Theme;
  x: number;
}

// One bar per theme, tallest first. Each bar is split by source, so themes that
// combine GitHub and Play show both colors.
export default function ThemeStrip({ themes, selectedId, onSelect }: Props) {
  const [hover, setHover] = useState<Hover | null>(null);
  const sorted = [...themes].sort((a, b) => b.size - a.size);
  const max = Math.max(...sorted.map((t) => t.size), 1);

  const show = (el: HTMLElement, theme: Theme) => {
    const parent = el.parentElement as HTMLElement;
    const centre = el.offsetLeft + el.offsetWidth / 2;
    setHover({ theme, x: Math.min(Math.max(centre, 110), parent.clientWidth - 110) });
  };

  return (
    <div className="stripwrap">
      <div className="strip" role="group" aria-label="All themes, largest first. Select a bar to open a theme.">
        {hover && (
          <div className="tip" style={{ left: hover.x }} aria-hidden="true">
            <strong>{hover.theme.title}</strong>
            <span>
              {hover.theme.sources.github_issues ?? 0} GitHub, {hover.theme.sources.play_reviews ?? 0} Play
            </span>
          </div>
        )}
        {sorted.map((t, i) => {
          const gh = t.sources.github_issues ?? 0;
          const pl = t.sources.play_reviews ?? 0;
          const height = 16 + Math.sqrt(t.size / max) * 84;
          return (
            <button
              key={t.theme_id}
              className={"bar" + (t.theme_id === selectedId ? " on" : "")}
              style={{ height: `${height}%`, animationDelay: `${i * 7}ms` }}
              aria-label={`${t.title}, ${gh} GitHub issues and ${pl} Play reviews`}
              onClick={() => onSelect(t.theme_id)}
              onMouseEnter={(e) => show(e.currentTarget, t)}
              onMouseLeave={() => setHover(null)}
              onFocus={(e) => show(e.currentTarget, t)}
              onBlur={() => setHover(null)}
            >
              <span className="gh" style={{ flexGrow: gh }} />
              <span className="pl" style={{ flexGrow: pl }} />
            </button>
          );
        })}
      </div>
      <div className="axis">
        <span>Largest theme</span>
        <span>Smallest theme</span>
      </div>
    </div>
  );
}
