import { useState } from "react";
import type { Member, Theme } from "./types";
import { SOURCE_LABEL } from "./meta";
import SourceBar from "./SourceBar";

const fmtDay = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
const fmtMonth = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short" });

function Stars({ n }: { n: number }) {
  return (
    <span className="stars" aria-label={`${n} out of 5 stars`}>
      {"★".repeat(n) + "☆".repeat(5 - n)}
    </span>
  );
}

function Evidence({ m }: { m: Member }) {
  const isGithub = m.source === "github_issues";
  return (
    <article className={"evidence " + (isGithub ? "gh" : "pl")}>
      <header className="evhead">
        <span className="src">{SOURCE_LABEL[m.source]}</span>
        {m.rating != null && <Stars n={m.rating} />}
        <span>{fmtDay(m.created_at)}</span>
        <a
          href={m.url}
          target="_blank"
          rel="noopener noreferrer"
          title={
            isGithub
              ? undefined
              : "Google Play has no public link to a single review, so this opens the app page."
          }
        >
          {isGithub ? "Open original ↗" : "Play page ↗"}
        </a>
      </header>
      <p>{m.text}</p>
    </article>
  );
}

// Signals per month, split by source. Counts come from our sample, not from the whole population.
function Timeline({ members }: { members: Member[] }) {
  const buckets = new Map<string, { gh: number; pl: number }>();
  for (const m of members) {
    const key = m.created_at.slice(0, 7);
    const b = buckets.get(key) ?? { gh: 0, pl: 0 };
    if (m.source === "github_issues") b.gh += 1;
    else b.pl += 1;
    buckets.set(key, b);
  }
  const keys = [...buckets.keys()].sort();
  if (keys.length < 2) return null;

  const months: string[] = [];
  let [y, mo] = keys[0].split("-").map(Number);
  const [endY, endM] = keys[keys.length - 1].split("-").map(Number);
  while ((y < endY || (y === endY && mo <= endM)) && months.length < 72) {
    months.push(`${y}-${String(mo).padStart(2, "0")}`);
    mo += 1;
    if (mo > 12) {
      mo = 1;
      y += 1;
    }
  }
  const totalOf = (k: string) => {
    const b = buckets.get(k);
    return b ? b.gh + b.pl : 0;
  };
  const max = Math.max(...months.map(totalOf), 1);

  return (
    <div className="timeline">
      <h3>When these were reported</h3>
      <div className="tbars">
        {months.map((k) => {
          const b = buckets.get(k) ?? { gh: 0, pl: 0 };
          return (
            <span
              key={k}
              className="tcol"
              style={{ height: `${Math.max((totalOf(k) / max) * 100, totalOf(k) ? 8 : 0)}%` }}
              title={`${k}: ${b.gh} GitHub, ${b.pl} Play`}
            >
              <i className="gh" style={{ flexGrow: b.gh }} />
              <i className="pl" style={{ flexGrow: b.pl }} />
            </span>
          );
        })}
      </div>
      <div className="taxis">
        <span>{fmtMonth(`${months[0]}-01T00:00:00Z`)}</span>
        <span>Signals per month in this sample</span>
        <span>{fmtMonth(`${months[months.length - 1]}-01T00:00:00Z`)}</span>
      </div>
    </div>
  );
}

const PAGE = 8;

export default function ThemeDetail({ theme }: { theme: Theme }) {
  const [shown, setShown] = useState(PAGE);
  const featured = theme.members.filter((m) => m.featured);
  const rest = [...theme.members]
    .filter((m) => !m.featured)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  const gh = theme.sources.github_issues ?? 0;
  const pl = theme.sources.play_reviews ?? 0;

  return (
    <section className="detail">
      <h2>{theme.title}</h2>
      <div className="facts">
        <span>
          <strong>{theme.size}</strong> signals
        </span>
        <span>
          {fmtMonth(theme.date_first)} to {fmtMonth(theme.date_last)}
        </span>
      </div>
      <div className="keywords">
        {theme.keywords.map((k) => (
          <span key={k} className="kw">
            {k}
          </span>
        ))}
      </div>

      <div className="split">
        <SourceBar sources={theme.sources} />
        <div className="splitlegend">
          <span>
            <i className="dot gh" />
            {gh} GitHub issues
          </span>
          <span>
            <i className="dot pl" />
            {pl} Play reviews
          </span>
        </div>
      </div>

      <Timeline members={theme.members} />

      <h3>Closest to the centre of the theme</h3>
      {featured.map((m) => (
        <Evidence key={m.id} m={m} />
      ))}

      {rest.length > 0 && <h3>Everything else in this theme, newest first ({rest.length})</h3>}
      {rest.slice(0, shown).map((m) => (
        <Evidence key={m.id} m={m} />
      ))}
      {shown < rest.length && (
        <button className="more" onClick={() => setShown(shown + PAGE)}>
          Show {Math.min(PAGE, rest.length - shown)} more
        </button>
      )}
    </section>
  );
}
