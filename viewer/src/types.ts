export type Source = "github_issues" | "play_reviews";

export interface Member {
  id: string;
  source: Source;
  rating: number | null;
  url: string;
  created_at: string;
  text: string;
  featured: boolean; // one of the 3 signals closest to the theme centre
}

export interface Theme {
  theme_id: string;
  title: string;
  example: string; // one readable line from the signal closest to the theme centre
  size: number;
  sources: Partial<Record<Source, number>>;
  keywords: string[];
  date_first: string;
  date_last: string;
  members: Member[];
}

export interface Stats {
  n_signals: number;
  n_themes: number;
  n_clustered: number;
  n_unclustered: number;
  cross_source_themes: number;
  method: string;
  threshold: number;
}

export interface Data {
  stats: Stats;
  themes: Theme[];
}
