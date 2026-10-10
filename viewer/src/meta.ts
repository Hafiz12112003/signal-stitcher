import type { Source } from "./types";

export const SOURCE_LABEL: Record<Source, string> = {
  github_issues: "GitHub issue",
  play_reviews: "Play review",
};

// Results from evaluate.py on 55 hand-labeled GitHub-vs-Play pairs.
// Update these numbers if you re-run the evaluation.
export const EVALUATION = {
  pairs: 55,
  same: 32,
  rows: [
    { method: "Word-count baseline (TF-IDF)", f1: 0.38, precision: 0.80, recall: 0.25 },
    { method: "Sentence embeddings (full text, used here)", f1: 0.63, precision: 0.72, recall: 0.56 },
    { method: "Embeddings (GitHub title only)", f1: 0.67, precision: 0.76, recall: 0.59 },
  ],
};
