import { useEffect, useMemo, useState } from "react";
import type { Data, Theme } from "./types";
import ThemeList from "./ThemeList";
import ThemeDetail from "./ThemeDetail";
import ThemeStrip from "./ThemeStrip";
import { EVALUATION } from "./meta";

type Filter = "all" | "both" | "github" | "play";
type Sort = "size" | "balanced";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "both", label: "Both sources" },
  { id: "github", label: "GitHub only" },
  { id: "play", label: "Play only" },
];

const counts = (t: Theme) => [t.sources.github_issues ?? 0, t.sources.play_reviews ?? 0] as const;

function matchesFilter(t: Theme, filter: Filter): boolean {
  const [gh, pl] = counts(t);
  if (filter === "both") return gh > 0 && pl > 0;
  if (filter === "github") return gh > 0 && pl === 0;
  if (filter === "play") return pl > 0 && gh === 0;
  return true;
}

function BrandMark() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M2 7c6 0 6 10 12 10h8" stroke="var(--gh)" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M2 17c6 0 6-10 12-10h8" stroke="var(--pl)" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<Sort>("size");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [methodOpen, setMethodOpen] = useState(false);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`Could not load data.json (${r.status}). Run export_viewer_data.py first.`);
        return r.json() as Promise<Data>;
      })
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  const visible = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    const list = data.themes.filter((t) => {
      if (!matchesFilter(t, filter)) return false;
      if (!q) return true;
      const haystack = (t.title + " " + t.keywords.join(" ") + " " + t.members.map((m) => m.text).join(" ")).toLowerCase();
      return haystack.includes(q);
    });
    return [...list].sort((a, b) =>
      sort === "balanced"
        ? Math.min(...counts(b)) - Math.min(...counts(a)) || b.size - a.size
        : b.size - a.size
    );
  }, [data, filter, sort, query]);

  if (error) return <div className="state error">{error}</div>;
  if (!data) return <div className="state">Loading signals…</div>;

  const selected = visible.find((t) => t.theme_id === selectedId) ?? visible[0] ?? null;
  const s = data.stats;

  const openFromStrip = (id: string) => {
    setFilter("all");
    setQuery("");
    setSelectedId(id);
    if (window.matchMedia("(max-width: 900px)").matches) {
      setTimeout(() => document.getElementById("detail")?.scrollIntoView({ block: "start" }), 0);
    }
  };

  const showMethod = () => {
    setMethodOpen(true);
    setTimeout(() => document.getElementById("method")?.scrollIntoView({ block: "start" }), 0);
  };

  return (
    <div className="page">
      <nav className="topnav">
        <span className="brand">
          <BrandMark />
          Signal Stitcher
        </span>
        <a href="#method" onClick={(e) => { e.preventDefault(); showMethod(); }}>
          Method and limits
        </a>
      </nav>

      <header className="hero">
        <h1>
          {s.cross_source_themes} of {s.n_themes} themes combine GitHub issues and Google Play reviews
        </h1>
        <p className="lede">
          Signal Stitcher reads feedback from separate places, finds the signals that describe the same problem,
          and keeps the evidence behind every theme. This demo uses {s.n_signals} public signals about the
          Nextcloud Android app; {s.n_unclustered} of them did not fit any theme.
        </p>
        <p className="proof">
          Grouping accuracy on {EVALUATION.pairs} hand-labeled pairs: F1 {EVALUATION.rows[1].f1.toFixed(2)} with
          sentence embeddings, against {EVALUATION.rows[0].f1.toFixed(2)} for a word-count baseline.{" "}
          <a href="#method" onClick={(e) => { e.preventDefault(); showMethod(); }}>See how it was measured</a>
        </p>
        <ThemeStrip themes={data.themes} selectedId={selected?.theme_id ?? null} onSelect={openFromStrip} />
        <div className="legend">
          <span><i className="dot gh" />GitHub issue</span>
          <span><i className="dot pl" />Play review</span>
          <span className="hint">Each bar is a theme and taller means more signals. Bars with both colors join the two sources. Select one to read the evidence.</span>
        </div>
      </header>
      <div className="thread" aria-hidden="true" />

      <div className="controls">
        <input
          className="search"
          type="search"
          placeholder="Search themes and evidence"
          aria-label="Search themes and evidence"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="chips" role="group" aria-label="Filter themes by source">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              className="chip"
              aria-pressed={filter === f.id}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
              <span className="n">{data.themes.filter((t) => matchesFilter(t, f.id)).length}</span>
            </button>
          ))}
        </div>
        <select className="sort" aria-label="Sort themes" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
          <option value="size">Largest first</option>
          <option value="balanced">Most balanced across sources</option>
        </select>
      </div>

      <main className="layout">
        <aside className="listwrap">
          <ThemeList themes={visible} selectedId={selected?.theme_id ?? null} onSelect={setSelectedId} />
        </aside>
        <div id="detail">
          {selected ? (
            <ThemeDetail key={selected.theme_id} theme={selected} />
          ) : (
            <p className="empty">Nothing to show for this search.</p>
          )}
        </div>
      </main>

      <details
        id="method"
        className="method"
        open={methodOpen}
        onToggle={(e) => setMethodOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary>How good is the grouping? Method and limits</summary>
        <div className="body">
          <p>
            Each text becomes a multilingual sentence embedding. Signals closer than a cosine distance of{" "}
            {s.threshold} are grouped, and groups larger than 50 are split again. A group of three or more
            becomes a theme. Themes are named by their top keywords, with one real example line from the signal
            closest to the centre.
          </p>
          <p>
            Measured on {EVALUATION.pairs} GitHub-and-Play pairs I labeled by hand ({EVALUATION.same} describe the
            same problem):
          </p>
          <table>
            <thead>
              <tr><th>Method</th><th>F1</th><th>Precision</th><th>Recall</th></tr>
            </thead>
            <tbody>
              {EVALUATION.rows.map((r) => (
                <tr key={r.method}>
                  <td>{r.method}</td>
                  <td>{r.f1.toFixed(2)}</td>
                  <td>{r.precision.toFixed(2)}</td>
                  <td>{r.recall.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul>
            <li>Only 55 pairs, labeled by one person, and the threshold was tuned on the same labels.</li>
            <li>The pairs came from similar-looking pools plus random ones, so recall means "among these pairs".</li>
            <li>Typical mistakes: very short reviews, uninformative issue titles, and joins that share an area but not a specific problem.</li>
            <li>GitHub links open the exact issue. Google Play has no public link to a single review, so Play cards link to the app page. Review text was collected with the unofficial google-play-scraper library.</li>
            <li>Public data only: no customer identity, revenue or accounts. This is a proof of work, not HyperOrbit's system.</li>
          </ul>
        </div>
      </details>

      <p className="foot">Independent project on public data. Not affiliated with HyperOrbit or Nextcloud.</p>
    </div>
  );
}
