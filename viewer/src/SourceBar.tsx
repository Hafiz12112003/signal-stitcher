import type { Theme } from "./types";

// Two-tone bar: how much of a theme comes from GitHub vs Google Play.
export default function SourceBar({ sources }: { sources: Theme["sources"] }) {
  const gh = sources.github_issues ?? 0;
  const pl = sources.play_reviews ?? 0;
  const total = gh + pl || 1;
  return (
    <span className="sourcebar" title={`${gh} GitHub issues, ${pl} Play reviews`}>
      <span className="seg gh" style={{ width: `${(gh / total) * 100}%` }} />
      <span className="seg pl" style={{ width: `${(pl / total) * 100}%` }} />
    </span>
  );
}
